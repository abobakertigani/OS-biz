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

            # إدراج الطلب
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

            # تحديث حالة الطاولة
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

    # تسجيل الـ Blueprint
    app.register_blueprint(bp)
