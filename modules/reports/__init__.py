# modules/reports/__init__.py

from .routes import register_routes

def register_module(app, db):
    register_routes(app, db)
