# modules/restaurant/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from datetime import datetime
import json
from flask_login import login_required

def register_routes(app, db):
    bp = Blueprint('restaurant', __name__, url_prefix='/restaurant', template_folder='templates', static_folder='static')

    # استيراد الجداول
    Table = db.Model.metadata.tables['restaurant_tables']
    MenuItem = db.Model.metadata.tables['restaurant_menu_items']
    Order = db.Model.metadata.tables['restaurant_orders']

    # --- الحماية: جميع مسارات المطعم تتطلب تسجيل دخول ---
    @bp.before_request
    @login_required
    def require_login():
        pass

    # --- الصفحة الرئيسية ---
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
        table = db.session.execute(db.select(Table).where(Table.c.id == table_id)).first()
        if not table:
            flash("الطاولة غير موجودة", "error")
            return redirect(url_for('restaurant.list_tables'))
        orders = db.session.execute(db.select(Order).where(Order.c.table_id == table_id)).fetchall()
        return render_template('restaurant/table_orders.html', table=table, orders=orders)

    # --- جلب المنيو ---
    @bp.route('/menu')
    def get_menu():
        items = db.session.execute(db.select(MenuItem)).fetchall()
        return jsonify([
            {'id': item.id, 'name': item.name, 'price': item.price, 'category': item.category}
            for item in items
        ])
	
# --- دالة: التحقق من توفر المكونات ---
def check_ingredients_availability(db, menu_item_ids_quantities):
    """
    menu_item_ids_quantities: قائمة بأرقام عناصر المنيو (مكررة حسب الكمية)
    مثال: [1, 1, 2] تعني: عنصر 1 مرتين، وعنصر 2 مرة
    """
    from sqlalchemy import select

    # جلب جميع عناصر الطلب مع مكوناتها
    query = select(
        MenuItemIngredient.menu_item_id,
        MenuItemIngredient.inventory_item_id,
        MenuItemIngredient.quantity_used,
        InventoryItem.quantity.label('current_quantity'),
        InventoryItem.name.label('item_name')
    ).join(InventoryItem, MenuItemIngredient.inventory_item_id == InventoryItem.id)

    result = db.session.execute(query).fetchall()

    # تحويل النتائج إلى هيكل سهل المعالجة
    ingredient_map = {}
    for row in result:
        key = (row.menu_item_id, row.inventory_item_id)
        if key not in ingredient_map:
            ingredient_map[key] = {
                'quantity_needed_per_item': row.quantity_used,
                'current_quantity': row.current_quantity,
                'item_name': row.item_name
            }

    # حساب الكمية المطلوبة لكل مكون
    required = {}
    for menu_item_id in menu_item_ids_quantities:
        # جلب مكونات هذا الصنف
        item_query = select(MenuItemIngredient).where(MenuItemIngredient.menu_item_id == menu_item_id)
        ingredients = db.session.execute(item_query).fetchall()
        for ing in ingredients:
            inv_id = ing.inventory_item_id
            qty_per = ing.quantity_used
            required[inv_id] = required.get(inv_id, 0) + qty_per

    # التحقق من التوفر
    unavailable = []
    for inv_id, needed in required.items():
        current = ingredient_map.get((0, inv_id), {}).get('current_quantity', 0)
        item_name = ingredient_map.get((0, inv_id), {}).get('item_name', 'مكوّن غير معروف')
        if needed > current:
            unavailable.append({
                'item': item_name,
                'needed': needed,
                'available': current
            })

    return unavailable 
    
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

        # --- التحقق من توفر المكونات ---
        # استخراج قائمة بأرقام عناصر المنيو (مكررة حسب الكمية)
        menu_item_ids = []
        for item in items:
            try:
                count = int(item.get('quantity', 1))
            except:
                count = 1
            for _ in range(count):
                menu_item_ids.append(item['id'])

        unavailable = check_ingredients_availability(db, menu_item_ids)
        if unavailable:
            msg = "لا يمكن إتمام الطلب بسبب نقص في المخزون:<br>"
            for u in unavailable:
                msg += f"- {u['item']}: مطلوب {u['needed']:.2f}، متوفر {u['available']:.2f}<br>"
            flash(msg, "error")
            return redirect(url_for('restaurant.list_tables'))

        # --- إنشاء الطلب ---
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

        # --- خصم الكمية من المخزون ---
        for menu_item_id in menu_item_ids:
            item_query = db.select(MenuItemIngredient).where(MenuItemIngredient.menu_item_id == menu_item_id)
            ingredients = db.session.execute(item_query).fetchall()
            for ing in ingredients:
                db.session.execute(
                    db.update(InventoryItem)
                    .where(InventoryItem.id == ing.inventory_item_id)
                    .values(quantity=InventoryItem.quantity - ing.quantity_used)
                )
        db.session.commit()

        # --- تحديث حالة الطاولة ---
        db.session.execute(
            db.update(Table).where(Table.c.id == table_id).values(status='occupied')
        )
        db.session.commit()

        flash("تم إنشاء الطلب بنجاح", "success")
        return redirect(url_for('restaurant.list_tables'))

        # عرض الطلبات
        orders = db.session.execute(
            db.select(Order, Table.c.number.label('table_number'))
            .join(Table, Order.c.table_id == Table.c.id)
            .order_by(Order.c.timestamp.desc())
        ).fetchall()

        return render_template('restaurant/orders.html', orders=orders)

    # --- تحديث حالة الطلب ---
    @bp.route('/order/<int:order_id>/status', methods=['PUT'])
    def update_order_status(order_id):
        data = request.get_json()
        status = data.get('status')
        valid_statuses = ['pending', 'cooking', 'ready', 'served', 'paid']

        if status not in valid_statuses:
            return jsonify({'error': 'حالة غير صالحة'}), 400

        result = db.session.execute(
            db.update(Order).where(Order.c.id == order_id).values(status=status)
        )
        db.session.commit()

        if result.rowcount == 0:
            return jsonify({'error': 'الطلب غير موجود'}), 404

        # إذا تم الدفع، حرر الطاولة
        if status == 'paid':
            order = db.session.execute(db.select(Order).where(Order.c.id == order_id)).first()
            db.session.execute(
                db.update(Table).where(Table.c.id == order.table_id).values(status='free')
            )
            db.session.commit()

        return jsonify({'success': True})

    # --- طباعة الإيصال ---
    @bp.route('/receipt/<int:order_id>')
    def print_receipt(order_id):
        order = db.session.execute(
            db.select(Order).where(Order.c.id == order_id)
        ).first()

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

	# --- إدارة المكونات (Ingredients Management) ---
@bp.route('/ingredients')
def manage_ingredients():
    # جلب جميع عناصر المنيو
    menu_items = db.session.execute(db.select(MenuItem)).fetchall()
    
    # جلب جميع عناصر المخزون
    inventory_items = db.session.execute(db.select(InventoryItem)).fetchall()
    
    # جلب جميع المكونات الحالية
    ingredients = db.session.execute(
        db.select(MenuItemIngredient)
        .join(MenuItem, MenuItem.id == MenuItemIngredient.menu_item_id)
        .join(InventoryItem, InventoryItem.id == MenuItemIngredient.inventory_item_id)
    ).fetchall()

    return render_template('restaurant/ingredients.html',
                           menu_items=menu_items,
                           inventory_items=inventory_items,
                           ingredients=ingredients)


@bp.route('/ingredient/add', methods=['POST'])
def add_ingredient():
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

    # التحقق من أن الارتباط غير مكرر
    exists = db.session.execute(
        db.select(MenuItemIngredient)
        .where(MenuItemIngredient.menu_item_id == menu_item_id)
        .where(MenuItemIngredient.inventory_item_id == inventory_item_id)
    ).first()

    if exists:
        flash("هذا المكون مضاف مسبقًا لهذا الصنف", "info")
    else:
        db.session.execute(
            db.insert(MenuItemIngredient).values(
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
    ingredient = db.session.execute(
        db.select(MenuItemIngredient).where(MenuItemIngredient.id == ingredient_id)
    ).first()

    if not ingredient:
        flash("المكون غير موجود", "error")
    else:
        db.session.execute(
            db.delete(MenuItemIngredient).where(MenuItemIngredient.id == ingredient_id)
        )
        db.session.commit()
        flash("تم حذف المكون من الوصفة", "info")

    return redirect(url_for('restaurant.manage_ingredients'))
	
	
    # تسجيل الـ Blueprint
    app.register_blueprint(bp)
