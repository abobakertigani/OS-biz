# modules/inventory/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required
from datetime import datetime

def register_routes(app, db):
    bp = Blueprint('inventory', __name__, url_prefix='/inventory', template_folder='templates')

    # استيراد النموذج
    InventoryItem = db.Model.metadata.tables['inventory_items']

    # --- قبل كل طلب: التأكد من تسجيل الدخول ---
    @bp.before_request
    @login_required
    def require_login():
        pass

    # --- عرض جميع العناصر ---
    @bp.route('/')
    def index():
        search = request.args.get('search', '')
        category = request.args.get('category', '')

        query = db.select(InventoryItem)

        if search:
            query = query.where(InventoryItem.c.name.contains(search))
        if category:
            query = query.where(InventoryItem.c.category == category)

        items = db.session.execute(query).fetchall()

        # جلب الفئات الفريدة لعرضها في الفلاتر
        categories = db.session.execute(
            db.select(InventoryItem.c.category).distinct()
        ).fetchall()
        categories = [c.category for c in categories if c.category]

        # حساب العناصر المنقوصة أو المنتهية
        low_stock_items = [i for i in items if i.quantity <= i.min_stock]
        expired_items = [i for i in items if i.expiry_date and i.expiry_date < datetime.now().date()]

        return render_template('inventory/index.html',
                               items=items,
                               low_stock_items=low_stock_items,
                               expired_items=expired_items,
                               categories=categories,
                               search=search,
                               category=category)

    # --- إضافة عنصر جديد ---
    @bp.route('/add', methods=['GET', 'POST'])
    def add():
        if request.method == 'POST':
            name = request.form.get('name')
            quantity = request.form.get('quantity')
            unit = request.form.get('unit', 'قطعة')
            price_per_unit = request.form.get('price_per_unit')
            category = request.form.get('category')
            min_stock = request.form.get('min_stock', 5)
            supplier = request.form.get('supplier')
            notes = request.form.get('notes')
            expiry_date_str = request.form.get('expiry_date')

            expiry_date = None
            if expiry_date_str:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                except:
                    flash("تاريخ الصلاحية غير صحيح", "error")
                    return redirect(url_for('inventory.add'))

            try:
                quantity = int(quantity)
                price_per_unit = float(price_per_unit) if price_per_unit else 0.0
                min_stock = int(min_stock)
            except:
                flash("الكمية أو السعر أو الحد الأدنى يجب أن تكون أرقامًا", "error")
                return redirect(url_for('inventory.add'))

            if not name:
                flash("الاسم مطلوب", "error")
                return redirect(url_for('inventory.add'))

            # إدراج العنصر
            db.session.execute(
                db.insert(InventoryItem).values(
                    name=name,
                    quantity=quantity,
                    unit=unit,
                    price_per_unit=price_per_unit,
                    category=category,
                    min_stock=min_stock,
                    supplier=supplier,
                    notes=notes,
                    expiry_date=expiry_date
                )
            )
            db.session.commit()
            flash(f"تم إضافة '{name}' إلى المخزون بنجاح", "success")
            return redirect(url_for('inventory.index'))

        return render_template('inventory/add.html')

    # --- تعديل عنصر ---
    @bp.route('/edit/<int:item_id>', methods=['GET', 'POST'])
    def edit(item_id):
        item = db.session.execute(
            db.select(InventoryItem).where(InventoryItem.c.id == item_id)
        ).first()

        if not item:
            flash("العنصر غير موجود", "error")
            return redirect(url_for('inventory.index'))

        if request.method == 'POST':
            name = request.form.get('name')
            quantity = request.form.get('quantity')
            unit = request.form.get('unit')
            price_per_unit = request.form.get('price_per_unit')
            category = request.form.get('category')
            min_stock = request.form.get('min_stock')
            supplier = request.form.get('supplier')
            notes = request.form.get('notes')
            expiry_date_str = request.form.get('expiry_date')

            expiry_date = None
            if expiry_date_str:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                except:
                    flash("تاريخ الصلاحية غير صحيح", "error")
                    return redirect(url_for('inventory.edit', item_id=item_id))

            try:
                quantity = int(quantity)
                price_per_unit = float(price_per_unit) if price_per_unit else 0.0
                min_stock = int(min_stock)
            except:
                flash("الكمية أو السعر أو الحد الأدنى يجب أن تكون أرقامًا", "error")
                return redirect(url_for('inventory.edit', item_id=item_id))

            if not name:
                flash("الاسم مطلوب", "error")
                return redirect(url_for('inventory.edit', item_id=item_id))

            # التحديث
            db.session.execute(
                db.update(InventoryItem).where(InventoryItem.c.id == item_id).values(
                    name=name,
                    quantity=quantity,
                    unit=unit,
                    price_per_unit=price_per_unit,
                    category=category,
                    min_stock=min_stock,
                    supplier=supplier,
                    notes=notes,
                    expiry_date=expiry_date
                )
            )
            db.session.commit()
            flash("تم تحديث العنصر بنجاح", "success")
            return redirect(url_for('inventory.index'))

        # تحويل التاريخ إلى نص لعرضه في النموذج
        expiry_date = item.expiry_date.strftime('%Y-%m-%d') if item.expiry_date else ''

        return render_template('inventory/edit.html', item=item, expiry_date=expiry_date)

    # --- حذف عنصر ---
    @bp.route('/delete/<int:item_id>', methods=['POST'])
    def delete(item_id):
        item = db.session.execute(
            db.select(InventoryItem).where(InventoryItem.c.id == item_id)
        ).first()

        if not item:
            flash("العنصر غير موجود", "error")
        else:
            db.session.execute(
                db.delete(InventoryItem).where(InventoryItem.c.id == item_id)
            )
            db.session.commit()
            flash(f"تم حذف '{item.name}' من المخزون", "info")

        return redirect(url_for('inventory.index'))

    # --- واجهة برمجية للبحث (مفيد للوحدات الأخرى مثل المطعم) ---
    @bp.route('/api/search')
    def api_search():
        query = request.args.get('q', '')
        if not query:
            return jsonify([])
        results = db.session.execute(
            db.select(InventoryItem.c.id, InventoryItem.c.name, InventoryItem.c.price_per_unit)
            .where(InventoryItem.c.name.contains(query))
            .where(InventoryItem.c.quantity > 0)
        ).fetchall()
        return jsonify([
            {'id': r.id, 'name': r.name, 'price': r.price_per_unit}
            for r in results
        ])

    # تسجيل الـ Blueprint
    app.register_blueprint(bp)
