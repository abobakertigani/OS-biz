# modules/inventory/__init__.py

from .models import register_models
from .routes import register_routes

def register_module(app, db):
    """النقطة الرسمية لتحميل الوحدة"""
    register_models(db)
    register_routes(app, db)
