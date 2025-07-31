# modules/inventory/models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

def register_models(db):
    """
    نموذج المخزون المركزي
    يدعم: اسم، كمية، سعر، وحدة، تاريخ صلاحية (اختياري)، ملاحظات
    """

    class InventoryItem(db.Model):
        __tablename__ = 'inventory_items'

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        quantity = db.Column(db.Integer, default=0, nullable=False)
        unit = db.Column(db.String(20), default='قطعة')  # كجم، لتر، قطعة...
        price_per_unit = db.Column(db.Float, default=0.0)
        category = db.Column(db.String(50))  # طعام، أدوية، منظفات...
        expiry_date = db.Column(db.Date, nullable=True)  # اختياري
        min_stock = db.Column(db.Integer, default=5)  # الحد الأدنى
        supplier = db.Column(db.String(100), nullable=True)
        added_date = db.Column(db.DateTime, default=datetime.utcnow)
        notes = db.Column(db.Text, nullable=True)

        def is_low_stock(self):
            """التحقق من نقص الكمية"""
            return self.quantity <= self.min_stock

        def is_expired(self):
            """التحقق من انتهاء الصلاحية (إذا وُجدت)"""
            if self.expiry_date:
                return self.expiry_date < datetime.utcnow().date()
            return False

        def __repr__(self):
            return f'<InventoryItem {self.name} - {self.quantity} {self.unit}>'

    # تسجيل النموذج
    globals()['InventoryItem'] = InventoryItem
