# modules/restaurant/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime

def register_routes(app, db):
    # إنشاء Blueprint للوحدة
    bp = Blueprint('restaurant', __name__, url_prefix='/restaurant', template_folder='templates')

    # استيراد النماذج
    Table = db.Model.metadata.tables['restaurant_tables']
    MenuItem = db.Model.metadata.tables['restaurant_menu_items']
    Order = db.Model.metadata.tables['restaurant_orders']

    # --- المسارات ---

    @bp.route('/')
    def dashboard():
        return render_template('restaurant/pos.html')

    @bp.route('/tables')
    def list_tables():
        tables = db.session.execute(db.select(db.Model.metadata.tables['restaurant_tables'])).fetchall()
        return render_template('restaurant/tables.html', tables=tables)

    @bp.route('/menu')
    def menu():
        items = db.session.execute(db.select(db.Model.metadata.tables['restaurant_menu_items'])).fetchall()
        return jsonify([{'id': item.id, 'name': item.name, 'price': item.price, 'category': item.category} for item in items])

    @bp.route('/orders', methods=['GET', 'POST'])
    def manage_orders():
        if request.method == 'POST':
            table_id = request.form.get('table_id')
            items_json = request.form.get('items')  # يجب أن تكون بصيغة JSON بسيطة
            total = request.form.get('total')

            query = db.insert(Order).values(
                table_id=table_id,
                items=items_json,
                total=float(total),
                status='pending',
                timestamp=datetime.now()
            )
            db.session.execute(query)
            db.session.commit()

            return redirect(url_for('restaurant.list_tables'))

        orders = db.session.execute(db.select(Order)).fetchall()
        return render_template('restaurant/orders.html', orders=orders)

    @bp.route('/order/status/<int:order_id>', methods=['PUT'])
    def update_order_status(order_id):
        data = request.get_json()
        status = data.get('status')

        db.session.execute(
            db.update(Order).where(Order.c.id == order_id).values(status=status)
        )
        db.session.commit()
        return jsonify({'success': True})

    # تسجيل المسارات في التطبيق
    app.register_blueprint(bp)
