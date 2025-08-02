# modules/reports/routes.py

from flask import Blueprint, render_template
from flask_login import login_required  # استيراد login_required
from datetime import datetime, timedelta
from sqlalchemy import func

def register_routes(app, db):
    bp = Blueprint('reports', __name__, url_prefix='/reports', template_folder='templates')

    # --- لوحة التقارير الرئيسية ---
    @bp.route('/')
    @login_required  # ✅ ضعه هنا على المسار مباشرة
    def dashboard():
        # استيراد الجداول
        Order = db.Model.metadata.tables['restaurant_orders']
        MenuItem = db.Model.metadata.tables['restaurant_menu_items']
        InventoryItem = db.Model.metadata.tables['inventory_items']
        try:
            MenuItemIngredient = db.Model.metadata.tables['restaurant_menu_item_ingredients']
        except KeyError:
            MenuItemIngredient = None

        today = datetime.now().date()
        start_of_month = today.replace(day=1)

        # المبيعات اليومية
        daily_sales_result = db.session.execute(
            db.select(func.sum(Order.c.total))
            .where(func.date(Order.c.timestamp) == today)
            .where(Order.c.status == 'paid')
        ).scalar() or 0

        # المبيعات الشهرية
        monthly_sales_result = db.session.execute(
            db.select(func.sum(Order.c.total))
            .where(func.date(Order.c.timestamp) >= start_of_month)
            .where(func.date(Order.c.timestamp) <= today)
            .where(Order.c.status == 'paid')
        ).scalar() or 0

        # أكثر العناصر مبيعًا (تقديري)
        top_items = []
        MenuItemIngredient = db.Model.metadata.tables.get('restaurant_menu_item_ingredients')

		if MenuItemIngredient is not None:
            orders = db.session.execute(
                db.select(Order.c.items)
                .where(func.date(Order.c.timestamp) == today)
                .where(Order.c.status == 'paid')
            ).fetchall()

            item_counter = {}
            for order in orders:
                try:
                    items = eval(order.items)  # تحذير: استخدم json.loads في الإنتاج
                    for item in items:
                        name = item.get('name', 'عنصر غير معروف')
                        item_counter[name] = item_counter.get(name, 0) + 1
                except:
                    continue

            top_items = sorted(item_counter.items(), key=lambda x: x[1], reverse=True)[:5]
        else:
            top_items = [("لا توجد بيانات", 0)]

        # العناصر منخفضة المخزون
        low_stock_items = db.session.execute(
            db.select(InventoryItem.c.name, InventoryItem.c.quantity, InventoryItem.c.min_stock)
            .where(InventoryItem.c.quantity <= InventoryItem.c.min_stock)
        ).fetchall()

        # تقدير الأرباح
        net_profit = round(daily_sales_result * 0.6, 2)  # هامش ربح 40%

        return render_template('reports/dashboard.html',
                               daily_sales=daily_sales_result,
                               monthly_sales=monthly_sales_result,
                               top_items=top_items,
                               low_stock_items=low_stock_items,
                               net_profit=net_profit,
                               date=today)

    # ✅ تسجيل الـ Blueprint
    app.register_blueprint(bp)
