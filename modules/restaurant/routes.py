# modules/restaurant/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from datetime import datetime
import json
from flask_login import login_required

def register_routes(app, db):
    """
    تسجيل مسارات وحدة المطعم
    """
    # --- إنشاء Blueprint ---
    bp = Blueprint('restaurant', __name__, url_prefix='/restaurant', template_folder='templates', static_folder='static')

    # --- استيراد الجداول من قاعدة البيانات ---
    Table = db.Model.metadata.tables['restaurant_tables']
    MenuItem = db.Model.metadata.tables['restaurant_menu_items']
    Order = db.Model.metadata.tables['restaurant_orders']
    try:
        MenuItemIngredient = db.Model.metadata.tables['restaurant_menu_item_ingredients']
    except KeyError:
        MenuItemIngredient = None  # قد لا يكون موجودًا بعد

    # --- قبل كل طلب: التأكد من تسجيل الدخول ---
    @bp.before_request
    @login_required
    def require_login():
        pass

    # --- الصفحة الرئيسية (نقطة البيع) ---
    @bp.route('/')
    def dashboard():
        tables = db.session.execute(db.select(Table)).fetchall()
        return render_template('restaurant/pos.html', tables=tables)

    # --- عرض الطاولات ---
    @bp.route('/tables')
    def list_tables():
        tables = db.session.execute(db.select(Table)).fetchall()
        return render_template('restaurant/tables.html', tables=tables)

    # --- تفاصيل طاولة ---
    @bp.route('/table/<int:table_id>')
    def view_table_orders(table_id):
        table = db.session.execute(
            db.select(Table).where(Table.c.id == table_id)
        ).fetchone()
        if not table:
            flash("الطاولة غير موجودة", "error")
            return redirect(url_for('restaurant.list_tables'))
        orders = db.session.execute(
            db.select(Order).where(Order.c.table_id == table_id)
        ).fetchall()
        return render_template('restaurant/table_orders.html', table=table, orders=orders)

    # --- جلب المنيو ---
    @bp.route('/menu')
    def get_menu():
        items = db.session.execute(db.select(MenuItem)).fetchall()
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
            if MenuItemIngredient is not None:
                menu_item_ids = []
                for item in items:
                    try:
                        count = int(item.get('quantity', 1))
                    except:
                        count = 1
                    for _ in range(count):
                        menu_item_ids.append(item['id'])

                unavailable = []
                for menu_item_id in menu_item_ids:
                    # جلب مكونات هذا الصنف
                    ingredients_result = db.session.execute(
                        db.select(MenuItemIngredient)
                        .where(MenuItemIngredient.c.menu_item_id == menu_item_id)
                    ).fetchall()

                    for row in ingredients_result:
                        # جلب حالة المخزون لهذا المكون
                        inv_item = db.session.execute(
                            db.select(db.Model.metadata.tables['inventory_items'])
                            .where(db.Model.metadata.tables['inventory_items'].c.id == row.inventory_item_id)
                        ).fetchone()

                        if inv_item is None:
                            unavailable.append({
                                'item': 'مكوّن غير معروف',
                                'needed': row.quantity_used,
                                'available': 0
                            })
                        elif row.quantity_used > inv_item.quantity:
                            # جلب اسم الصنف من المنيو
                            menu_item = db.session.execute(
                                db.select(MenuItem).where(MenuItem.c.id == menu_item_id)
                            ).fetchone()
                            item_name = menu_item.name if menu_item else 'عنصر غير معروف'
                            unavailable.append({
                                'item': item_name,
                                'needed': row.quantity_used,
                                'available': inv_item.quantity
                            })

                if unavailable:
                    msg = "لا يمكن إتمام الطلب بسبب نقص في المخزون:<br>"
                    for u in unavailable:
                        msg += f"- {u['item']}: مطلوب {u['needed']:.2f}، متوفر {u['available']:.2f}<br>"
                    flash(msg, "error")
                    return redirect(url_for('restaurant.list_tables'))

            # --- إنشاء الطلب ---
            try:
                db.session.execute(
                    db.insert(Order).values(
                        table_id=table_id,
                        items=items_json,
                        total=float(total),
                        status='pending',
                        timestamp=datetime.now()
                    )
                )
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash("حدث خطأ أثناء إنشاء الطلب", "error")
                return redirect(url_for('restaurant.list_tables'))

            # --- خصم الكمية من المخزون (إن وُجدت المكونات) ---
            if MenuItemIngredient is not None:
                try:
                    for menu_item_id in menu_item_ids:
                        ingredients_result = db.session.execute(
                            db.select(MenuItemIngredient)
                            .where(MenuItemIngredient.c.menu_item_id == menu_item_id)
                        ).fetchall()

                        for row in ingredients_result:
                            db.session.execute(
                                db.update(db.Model.metadata.tables['inventory_items'])
                                .where(db.Model.metadata.tables['inventory_items'].c.id == row.inventory_item_id)
                                .values(quantity=db.Model.metadata.tables['inventory_items'].c.quantity - row.quantity_used)
                            )
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    flash("تم إنشاء الطلب، لكن حدث خطأ في تحديث المخزون", "warning")

            # --- تحديث حالة الطاولة ---
            try:
                db.session.execute(
                    db.update(Table)
                    .where(Table.c.id == table_id)
                    .values(status='occupied')
                )
                db.session.commit()
            except Exception as e:
                db.session.rollback()

            flash("تم إنشاء الطلب بنجاح", "success")
            return redirect(url_for('restaurant.list_tables'))

        # عرض الطلبات
        orders_result = db.session.execute(
            db.select(Order, Table.c.number.label('table_number'))
            .join(Table, Order.c.table_id == Table.c.id)
            .order_by(Order.c.timestamp.desc())
        ).fetchall()

        return render_template('restaurant/orders.html', orders=orders_result)

@bp.route('/menu/add', methods=['GET', 'POST'])
def add_menu_item():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        category = request.form.get('category')

        try:
            price = float(price)
        except:
            flash("السعر يجب أن يكون رقمًا", "error")
            return redirect(url_for('restaurant.add_menu_item'))

        if not name:
            flash("الاسم مطلوب", "error")
            return redirect(url_for('restaurant.add_menu_item'))

        db.session.execute(
            db.insert(MenuItem).values(
                name=name,
                price=price,
                category=category
            )
        )
        db.session.commit()
        flash(f"تم إضافة '{name}' إلى المنيو", "success")
        return redirect(url_for('restaurant.dashboard'))

    return render_template('restaurant/add_menu_item.html')
    
    # --- تحديث حالة الطلب ---
@bp.route('/order/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    data = request.get_json()
    status = data.get('status')
    valid_statuses = ['pending', 'cooking', 'ready', 'served', 'paid']

    if status not in valid_statuses:
        return jsonify({'error': 'حالة غير صالحة'}), 400

    # ✅ تحقق من وجود الطلب أولًا
    order_result = db.session.execute(
        db.select(Order).where(Order.c.id == order_id)
    ).fetchone()

    if not order_result:
        return jsonify({'error': 'الطلب غير موجود'}), 404

    # ✅ التحديث
    db.session.execute(
        db.update(Order).where(Order.c.id == order_id).values(status=status)
    )
    db.session.commit()

    # إذا تم الدفع، حرر الطاولة
    if status == 'paid':
        db.session.execute(
            db.update(Table).where(Table.c.id == order_result.table_id).values(status='free')
        )
        db.session.commit()

    return jsonify({'success': True})
    
    # --- طباعة الإيصال ---
    @bp.route('/receipt/<int:order_id>')
    def print_receipt(order_id):
        order = db.session.execute(
            db.select(Order).where(Order.c.id == order_id)
        ).fetchone()

        if not order:
            return "الطلب غير موجود", 404

        try:
            items = json.loads(order.items)
        except:
            items = []

        return render_template('restaurant/receipt.html', order=order, items=items)

    # --- التقرير اليومي ---
    @bp.route('/report/daily')
    def daily_report():
        today = datetime.now().strftime('%Y-%m-%d')
        result = db.session.execute(
            db.select(Order)
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
        menu_items = db.session.execute(db.select(MenuItem)).fetchall()
        inventory_table = db.Model.metadata.tables['inventory_items']
        inventory_items = db.session.execute(db.select(inventory_table)).fetchall()

        ingredients = []
        if MenuItemIngredient is not None:
            ingredients = db.session.execute(
                db.select(MenuItemIngredient)
                .join(MenuItem, MenuItem.id == MenuItemIngredient.c.menu_item_id)
                .join(inventory_table, inventory_table.c.id == MenuItemIngredient.c.inventory_item_id)
            ).fetchall()

        return render_template('restaurant/ingredients.html',
                               menu_items=menu_items,
                               inventory_items=inventory_items,
                               ingredients=ingredients)

    @bp.route('/ingredient/add', methods=['POST'])
    def add_ingredient():
        if MenuItemIngredient is None:
            flash("جدول المكونات غير متوفر بعد. تأكد من تشغيل النظام بشكل صحيح.", "error")
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
        except Exception as e:
            flash("الرجاء إدخال كميات صحيحة", "error")
            return redirect(url_for('restaurant.manage_ingredients'))

        # التحقق من عدم التكرار
        exists = db.session.execute(
            db.select(MenuItemIngredient)
            .where(MenuItemIngredient.c.menu_item_id == menu_item_id)
            .where(MenuItemIngredient.c.inventory_item_id == inventory_item_id)
        ).fetchone()

        if exists:
            flash("هذا المكون مضاف مسبقًا لهذا الصنف", "info")
        else:
            try:
                db.session.execute(
                    db.insert(MenuItemIngredient).values(
                        menu_item_id=menu_item_id,
                        inventory_item_id=inventory_item_id,
                        quantity_used=quantity_used
                    )
                )
                db.session.commit()
                flash("تم إضافة المكون بنجاح", "success")
            except Exception as e:
                db.session.rollback()
                flash("فشل في إضافة المكون", "error")

        return redirect(url_for('restaurant.manage_ingredients'))

    @bp.route('/ingredient/delete/<int:ingredient_id>', methods=['POST'])
    def delete_ingredient(ingredient_id):
        if MenuItemIngredient is None:
            flash("جدول المكونات غير متوفر", "error")
            return redirect(url_for('restaurant.manage_ingredients'))

        ingredient = db.session.execute(
            db.select(MenuItemIngredient).where(MenuItemIngredient.c.id == ingredient_id)
        ).fetchone()

        if not ingredient:
            flash("المكون غير موجود", "error")
        else:
            try:
                db.session.execute(
                    db.delete(MenuItemIngredient).where(MenuItemIngredient.c.id == ingredient_id)
                )
                db.session.commit()
                flash("تم حذف المكون من الوصفة", "info")
            except Exception as e:
                db.session.rollback()
                flash("فشل في حذف المكون", "error")

        return redirect(url_for('restaurant.manage_ingredients'))

    # --- تسجيل الـ Blueprint في التطبيق ---
    app.register_blueprint(bp) 
