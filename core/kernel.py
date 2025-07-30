# osbiz/core/kernel.py

import os
import importlib
from flask import Flask
from .database import db

def load_modules(app: Flask, db_instance):
    """
    تحميل جميع الوحدات من مجلد modules/
    كل وحدة يجب أن تحتوي على register_module(app, db)
    """
    modules_dir = os.path.join(os.path.dirname(__file__), '..', 'modules')
    modules_dir = os.path.abspath(modules_dir)

    if not os.path.exists(modules_dir):
        print("تحذير: مجلد الوحدات (modules/) غير موجود.")
        return

    for folder in os.listdir(modules_dir):
        folder_path = os.path.join(modules_dir, folder)
        if os.path.isdir(folder_path) and not folder.startswith('__'):
            try:
                # استيراد الوحدة
                module = importlib.import_module(f'modules.{folder}')
                if hasattr(module, 'register_module'):
                    module.register_module(app, db_instance)
                    print(f"✅ تم تحميل الوحدة: {folder}")
                else:
                    print(f"⚠️  الوحدة {folder} لا تحتوي على register_module")
            except Exception as e:
                print(f"❌ خطأ في تحميل الوحدة {folder}: {e}")
