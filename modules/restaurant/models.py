# modules/restaurant/models.py

from flask_sqlalchemy import SQLAlchemy

def register_models(db):
    """
    نماذج خاصة بالمطعم
    """

    # الطاولة
    class Table(db.Model):
        __tablename__ = 'restaurant_tables'
        id = db.Column(db.Integer, primary_key=True)
        number = db.Column(db.Integer, nullable=False, unique=True)
        status = db.Column(db.String(20), default='free')
        capacity = db.Column(db.Integer, default=4)

        def __repr__(self):
            return f'<Table {self.number} - {self.status}>'

    # العناصر في المنيو
    class MenuItem(db.Model):
        __tablename__ = 'restaurant_menu_items'
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        price = db.Column(db.Float, nullable=False)
        category = db.Column(db.String(50))

        def __repr__(self):
            return f'<MenuItem {self.name} - {self.price} ر.س>'

    # علاقة بين عنصر المنيو ومكوناته من المخزون
    class MenuItemIngredient(db.Model):  # ⬅️ تأكد من كتابة db.Model (بـ Capital M)
        __tablename__ = 'restaurant_menu_item_ingredients'
        id = db.Column(db.Integer, primary_key=True)
        menu_item_id = db.Column(db.Integer, db.ForeignKey('restaurant_menu_items.id'), nullable=False)
        inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
        quantity_used = db.Column(db.Float, nullable=False)

        # علاقات
        menu_item = db.relationship('MenuItem', backref='ingredients')
        inventory_item = db.relationship('InventoryItem', backref='used_in_menu')

        def __repr__(self):
            return f'<MenuItemIngredient: MenuID={self.menu_item_id}, InvID={self.inventory_item_id}, Qty={self.quantity_used}>'

    # الطلب (Order)
    class Order(db.Model):
        __tablename__ = 'restaurant_orders'
        id = db.Column(db.Integer, primary_key=True)
        table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id'), nullable=False)
        items = db.Column(db.Text, nullable=False)
        total = db.Column(db.Float, nullable=False)
        status = db.Column(db.String(20), default='pending')
        timestamp = db.Column(db.DateTime, default=db.func.now())

        table = db.relationship('Table', backref='orders')

        def __repr__(self):
            return f'<Order {self.id} - Table {self.table_id} - {self.status}>'

    # حفظ النماذج في السياق
    globals()['Table'] = Table
    globals()['MenuItem'] = MenuItem
    globals()['MenuItemIngredient'] = MenuItemIngredient
    globals()['Order'] = Order
