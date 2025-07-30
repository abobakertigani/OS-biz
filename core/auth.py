# osbiz/core/auth.py

from flask_login import UserMixin
from .database import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, cashier, pharmacist...

    def __repr__(self):
        return f'<User {self.username} - {self.role}>'
