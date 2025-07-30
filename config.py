# osbiz/config.py

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'osbiz-secret-key-2025'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///osbiz.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MODULES_FOLDER = 'modules'  # اسم مجلد الوحدات
