# modules/restaurant/__init__.py

from .models import register_models
from .routes import register_routes

def register_module(app, db):
    """
    هذه الدالة هي نقطة الدخول للوحدة
    تُستدعى من النواة (kernel)
    """
    register_models(db)
    register_routes(app, db)
