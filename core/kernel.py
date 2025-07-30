# core/kernel.py
import importlib
import os
from ai.predict_sales import predict_next_week


forecast = predict_next_week(store_id)

def load_modules(app, db):
    module_dir = "modules"
    for folder in os.listdir(module_dir):
        if os.path.isdir(os.path.join(module_dir, folder)):
            try:
                module = importlib.import_module(f"modules.{folder}")
                module.register_module(app, db)
                print(f"تم تحميل الوحدة: {folder}")
            except Exception as e:
                print(f"خطأ في تحميل {folder}: {e}")
