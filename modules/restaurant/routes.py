# modules/restaurant/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from datetime import datetime
import json
from flask_login import login_required
from sqlalchemy import select, update, delete, insert

def register_routes(app, db):
    """
    تسجيل مسارات وحدة المطعم
    """
    # --- إنشاء Blueprint ---
    bp = Blueprint('restaurant', __name__, url_prefix='/restaurant', template_folder='templates', static_folder='static')

    # --- قبل كل طلب: التأكد من تسجيل الدخول ---
    @bp.before_request
    @login_required
    def require_login():
        pass

    # --- الصفحة الرئيسية (نقطة البيع) ---
    @bp.route('/')
    def dashboard():
        Table = db.Model.metadata.tables['restaurant_tables']
        tables_result = db.session.execute(select(Table))
        tables = tables_result.fetchall()
        return render_template('restaurant/pos.html', tables=tables)

    # --- عرض الطاولات ---
    @bp.route('/tables')
    def list_tables():
        Table = db.Model.metadata.tables['restaurant_tables']
        tables_result = db.session.execute(select(Table))
        tables = tables_result.fetchall()
        return render_template('restaurant/tables.html', tables=tables)

    # --- تفاصيل طاولة ---
    @bp.route('/table/<int:table_id>')
    def view_table_orders(table_id):
        Table = db.Model.metadata.tables['restaurant_tables']
        Order = db.Model.metadata.tables['restaurant_orders']

        table_result = db.session.execute(
            select(Table).where(Table.c.id == table_id)
        )
        table = table_result.first()

        if not table:
            flash("الطاولة غير موجودة", "error")
            return redirect(url_for('restaurant.list_tables'))

        orders_result = db.session.execute(
            select(Order).where(Order.c.table_id == table_id)
        )
        orders = orders_result.fetchall()

        return render_template('restaurant/table_orders.html', table=table, orders=orders)

    # --- جلب المنيو ---
    @bp.route('/menu')
    def get_menu():
        MenuItem = db.Model.metadata.tables['restaurant_menu_items']
        result = db.session.execute(select(MenuItem))
        items = result.fetchall()
        return jsonify([
            {'id': item.id, 'name': item.name, 'price': item.price, 'category': item.category}
            for item in items
        ])

    # --- إدارة الطلبات ---
    @bp.route('/orders', methods=['GET', 'POST'])
    def manage_orders():
        if request.method == 'POST':
            table_id = request.form.get('table_id')
            items_json = request.form.get('items')
            total = request.form.get('total')

            try:
                items = json.loads(items_json)
            except:
                flash("بيانات الطلب غير صحيحة", "error")
                return redirect(url_for('restaurant.list_tables'))

            # --- التحقق من توفر المكونات (إن وُجدت) ---
            MenuItem = db.Model.metadata.tables['restaurant_menu_items']
            MenuItemIngredient = db.Model.metadata.tables.get('restaurant_menu_item_ingredients')
            InventoryItem = db.Model.metadata.tables.get('inventory_items')
            Order = db.Model.metadata.tables['restaurant_orders']
            Table = db.Model.metadata.tables['restaurant_tables']

            if MenuItemIngredient and InventoryItem:
                menu_item_ids = []
                for item in items:
                    try:
                        count = int(item.get('quantity', 1))
                    except:
                        count = 1
                    for _ in range(count):
                        menu_item_ids.append(item['id'])

                # التحقق من توفر المكونات
                unavailable = []
                for menu_item_id in menu_item_ids:
                    ing_result = db.session.execute(
                        select(MenuItemIngredient)
                        .where(MenuItemIngredient.c.menu_item_id == menu_item_id)
                    ).fetchall()

                    for ing in ing_result:
                        inv_item_result = db.session.execute(
                            select(InventoryItem)
                            .where(InventoryItem.c.id == ing.inventory_item_id)
                        ).first()

                        if inv_item_result and ing.quantity_used > inv_item_result.quantity:
                            menu_item_result = db.session.execute(
                                select(MenuItem).where(MenuItem.c.id == menu_item_id)
                            ).first()
                            item_name = menu_item_result.name if menu_item_result else 'عنصر غير معروف'
                            unavailable.append({
                                'item': item_name,
                                'needed': ing.quantity_used,
                                'available': inv_item_result.quantity
                            })

                if unavailable:
                    msg = "لا يمكن إتمام الطلب بسبب نقص في المخزون:<br>"
                    for u in unavailable:
                        msg += f"- {u['item']}: مطلوب {u['needed']:.2f}، متوفر {u['available']:.2f}<br>"
                    flash(msg, "error")
                    return redirect(url_for('restaurant.list_tables'))

            # --- إنشاء الطلب ---
            db.session.execute(
                insert(Order).values(
                    table_id=table_id,
                    items=items_json,
                    total=float(total),
                    status='pending',
                    timestamp=datetime.now()
                )
            )
            db.session.commit()

            # --- خصم الكمية من المخزون ---
            if MenuItemIngredient and InventoryItem:
                for menu_item_id in menu_item_ids:
                    ing_result = db.session.execute(
                        select(MenuItemIngredient)
                        .where(MenuItemIngredient.c.menu_item_id == menu_item_id)
                    ).fetchall()

                    for ing in ing_result:
                        db.session.execute(
                            update(InventoryItem)
                            .where(InventoryItem.c.id == ing.inventory_item_id)
                            .values(quantity=InventoryItem.c.quantity - ing.quantity_used)
                        )
                db.session.commit()

            # --- تحديث حالة الطاولة ---
            db.session.execute(
                update(Table).where(Table.c.id == table_id).values(status='occupied')
            )
            db.session.commit()

            flash("تم إنشاء الطلب بنجاح", "success")
            return redirect(url_for('restaurant.list_tables'))

        # عرض الطلبات
        Order = db.Model.metadata.tables['restaurant_orders']
        Table = db.Model.metadata.tables['restaurant_tables']
        orders_result = db.session.execute(
            select(Order, Table.c.number.label('table_number'))
            .join(Table, Order.c.table_id == Table.c.id)
            .order_by(Order.c.timestamp.desc())
        )
        orders = orders_result.fetchall()

        return render_template('restaurant/orders.html', orders=orders)

    # --- تحديث حالة الطلب ---
    @bp.route('/order/<int:order_id>/status', methods=['PUT'])
    def update_order_status(order_id):
        data = request.get_json()
        status = data.get('status')
        valid_statuses = ['pending', 'cooking', 'ready', 'served', 'paid']

        if status not in valid_statuses:
            return jsonify({'error': 'حالة غير صالحة'}), 400

        Order = db.Model.metadata.tables['restaurant_orders']
        result = db.session.execute(
            update(Order).where(Order.c.id == order_id).values(status=status)
        )
        db.session.commit()

        if result.rowcount == 0:
            return jsonify({'error': 'الطلب غير موجود'}), 404

        # إذا تم الدفع، حرر الطاولة
        if status == 'paid':
            order_result = db.session.execute(
                select(Order).where(Order.c.id == order_id)
            ).first()
            if order_result:
                Table = db.Model.metadata.tables['restaurant_tables']
                db.session.execute(
                    update(Table)
                    .where(Table.c.id == order_result.table_id)
                    .values(status='free')
                )
                db.session.commit()

        return jsonify({'success': True})

    # --- طباعة الإيصال ---
    @bp.route('/receipt/<int:order_id>')
    def print_receipt(order_id):
        Order = db.Model.metadata.tables['restaurant_orders']
        order_result = db.session.execute(
            select(Order).where(Order.c.id == order_id)
        ).first()

        if not order_result:
            return "الطلب غير موجود", 404

        try:
            items = json.loads(order_result.items)
        except:
            items = []

        return render_template('restaurant/receipt.html', order=order_result, items=items)

    # --- التقرير اليومي ---
    @bp.route('/report/daily')
    def daily_report():
        Order = db.Model.metadata.tables['restaurant_orders']
        today = datetime.now().strftime('%Y-%m-%d')
        result = db.session.execute(
            select(Order)
            .where(db.func.date(Order.c.timestamp) == today)
            .where(Order.c.status == 'paid')
        ).fetchall()

        total_sales = sum(o.total for o in result)
        num_orders = len(result)

        return render_template('restaurant/report.html',
                               total_sales=total_sales,
                               num_orders=num_orders,
                               date=today)

    # --- إدارة المكونات (وصفات المنيو) ---
    @bp.route('/ingredients')
    def manage_ingredients():
        MenuItem = db.Model.metadata.tables['restaurant_menu_items']
        InventoryItem = db.Model.metadata.tables.get('inventory_items')
        MenuItemIngredient = db.Model.metadata.tables.get('restaurant_menu_item_ingredients')

        menu_items_result = db.session.execute(select(MenuItem))
        menu_items = menu_items_result.fetchall()

        if not InventoryItem:
            flash("وحدة المخزون غير متوفرة", "error")
            inventory_items = []
        else:
            inv_result = db.session.execute(select(InventoryItem))
            inventory_items = inv_result.fetchall()

        ingredients = []
        if MenuItemIngredient and InventoryItem:
            try:
                ingredients_result = db.session.execute(
                    select(MenuItemIngredient)
                    .join(MenuItem, MenuItem.id == MenuItemIngredient.c.menu_item_id)
                    .join(InventoryItem, InventoryItem.id == MenuItemIngredient.c.inventory_item_id)
                )
                ingredients = ingredients_result.fetchall()
            except:
                ingredients = []

        return render_template('restaurant/ingredients.html',
                               menu_items=menu_items,
                               inventory_items=inventory_items,
                               ingredients=ingredients)

    @bp.route('/ingredient/add', methods=['POST'])
    def add_ingredient():
        MenuItemIngredient = db.Model.metadata.tables.get('restaurant_menu_item_ingredients')
        if not MenuItemIngredient:
            flash("جدول المكونات غير متوفر", "error")
            return redirect(url_for('restaurant.manage_ingredients'))

        menu_item_id = request.form.get('menu_item_id')
        inventory_item_id = request.form.get('inventory_item_id')
        quantity_used = request.form.get('quantity_used')

        try:
            menu_item_id = int(menu_item_id)
            inventory_item_id = int(inventory_item_id)
            quantity_used = float(quantity_used)
            if quantity_used <= 0:
                raise ValueError
        except:
            flash("الرجاء إدخال كميات صحيحة", "error")
            return redirect(url_for('restaurant.manage_ingredients'))

        # التحقق من عدم التكرار
        exists_result = db.session.execute(
            select(MenuItemIngredient)
            .where(MenuItemIngredient.c.menu_item_id == menu_item_id)
            .where(MenuItemIngredient.c.inventory_item_id == inventory_item_id)
        ).first()

        if exists_result:
            flash("هذا المكون مضاف مسبقًا لهذا الصنف", "info")
        else:
            db.session.execute(
                insert(MenuItemIngredient).values(
                    menu_item_id=menu_item_id,
                    inventory_item_id=inventory_item_id,
                    quantity_used=quantity_used
                )
            )
            db.session.commit()
            flash("تم إضافة المكون بنجاح", "success")

        return redirect(url_for('restaurant.manage_ingredients'))

    @bp.route('/ingredient/delete/<int:ingredient_id>', methods=['POST'])
    def delete_ingredient(ingredient_id):
        MenuItemIngredient = db.Model.metadata.tables.get('restaurant_menu_item_ingredients')
        if not MenuItemIngredient:
            flash("جدول المكونات غير متوفر", "error")
            return redirect(url_for('restaurant.manage_ingredients'))

        ingredient_result = db.session.execute(
            select(MenuItemIngredient).where(MenuItemIngredient.c.id == ingredient_id)
        ).first()

        if not ingredient_result:
            flash("المكون غير موجود", "error")
        else:
            db.session.execute(
                delete(MenuItemIngredient).where(MenuItemIngredient.c.id == ingredient_id)
            )
            db.session.commit()
            flash("تم حذف المكون من الوصفة", "info")

        return redirect(url_for('restaurant.manage_ingredients'))

    # --- تسجيل الـ Blueprint في التطبيق ---
    app.register_blueprint(bp)
