# osbiz/app.py

from flask import Flask, render_template, redirect, url_for
from core.database import db
from core.auth import User
from core.kernel import load_modules
import config

def create_app():
    app = Flask(__name__)
    app.config.from_object(config.Config)

    # ربط قاعدة البيانات بالتطبيق
    db.init_app(app)

    # إنشاء الجداول عند التشغيل الأول
    with app.app_context():
        db.create_all()

        # إنشاء مستخدم افتراضي (للتجربة)
        if not User.query.filter_by(username='admin').first():
            from werkzeug.security import generate_password_hash
            admin = User(username='admin', password=generate_password_hash('admin123'), role='admin')
            db.session.add(admin)
            db.session.commit()
            print("✅ تم إنشاء مستخدم افتراضي: admin / admin123")

    # تحميل الوحدات
    load_modules(app, db)

    # مسار تجريبي
    @app.route('/')
    def home():
        return '<h1>مرحباً بكم في OS-Biz</h1><p><a href="/login">تسجيل الدخول</a></p>'

    @app.route('/login')
    def login():
        return '<h2>صفحة تسجيل الدخول (قيد التطوير)</h2>'

    return app

# تشغيل التطبيق
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
