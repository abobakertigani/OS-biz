# modules/restaurant/routes.py (محدث)

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from datetime import datetime
import json

def register_routes(app, db):
    bp = Blueprint('restaurant', __name__, url_prefix='/restaurant', template_folder='templates', static_folder='static')

    # استيراد الجداول من قاعدة البيانات
    Table = db.Model.metadata.tables['restaurant_tables']
    MenuItem = db.Model.metadata.tables['restaurant_menu_items']
    Order = db.Model.metadata.tables['restaurant_orders']

    # --- الصفحة الرئيسية ---
    @bp.route('/')
    def dashboard():
        tables = db.session.execute(db.select(Table)).fetchall()
        return render_template('restaurant/pos.html', tables=tables)

    # --- إدارة الطاولات ---
    @bp.route('/tables')
    def list_tables():
        tables = db.session.execute(db.select(Table)).fetchall()
        return render_template('restaurant/tables.html', tables=tables)

    @bp.route('/table/<int:table_id>')
    def view_table_orders(table_id):
        table = db.session.execute(db.select(Table).where(Table.c.id == table_id)).first()
        orders = db.session.execute(db.select(Order).where(Order.c.table_id == table_id)).fetchall()
        return render_template('restaurant/table_orders.html', table=table, orders=orders)

    # --- المنيو ---
    @bp.route('/menu')
    def get_menu():
        items = db.session.execute(db.select(MenuItem)).fetchall()
        return jsonify([
            {'id': item.id, 'name': item.name, 'price': item.price, 'category': item.category}
            for item in items
        ])

    # --- الطلبات ---
    @bp.route('/orders', methods=['GET', 'POST'])
    def manage_orders():
        if request.method == 'POST':
            table_id = request.form.get('table_id')
            items_json = request.form.get('items')  # JSON كنص
            total = request.form.get('total')

            try:
                items = json.loads(items_json)
            except:
                return jsonify({'error': 'بيانات الطلبات غير صحيحة'}), 400

            # إدراج الطلب
            result = db.session.execute(
                db.insert(Order).values(
                    table_id=table_id,
                    items=items_json,
                    total=float(total),
                    status='pending',
                    timestamp=datetime.now()
                )
            )
            db.session.commit()

            # تحديث حالة الطاولة إلى "مشغولة"
            db.session.execute(
                db.update(Table).where(Table.c.id == table_id).values(status='occupied')
            )
            db.session.commit()

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
        status = data.get('status')  # pending, cooking, ready, served, paid

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

    # --- تقرير يومي ---
    @bp.route('/report/daily')
    def daily_report():
        today = datetime.now().strftime('%Y-%m-%d')
        orders = db.session.execute(
            db.select(Order)
            .where(db.func.date(Order.c.timestamp) == today)
            .where(Order.c.status == 'paid')
        ).fetchall()

        total_sales = sum(o.total for o in orders)
        num_orders = len(orders)

        return render_template('restaurant/report.html',
                               total_sales=total_sales,
                               num_orders=num_orders,
                               date=today)

    # تسجيل الـ Blueprint
    app.register_blueprint(bp)
