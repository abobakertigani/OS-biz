# osbiz/app.py

from flask import Flask, render_template, redirect, url_for
from core.database import db
from core.auth import User
from core.auth_routes import register_auth_routes
from flask_login import LoginManager
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

	# app.py - جزء من الدالة create_app()
	# إعداد Flask-Login
	login_manager = LoginManager()
	login_manager.login_view = 'auth.login'
	login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى هذه الصفحة."
	login_manager.init_app(app)
    
	@login_manager.user_loader
	def load_user(user_id):
    return User.query.get(int(user_id))

	# تسجيل مسارات المصادقة
	register_auth_routes(app, db)

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
