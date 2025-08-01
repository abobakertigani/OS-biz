# osbiz/app.py

from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from core.database import db
from core.auth import User
from core.kernel import load_modules
from core.auth_routes import register_auth_routes
import config

def create_app():
    app = Flask(__name__)
    app.config.from_object(config.Config)

    # ربط قاعدة البيانات
    db.init_app(app)

    # إعداد Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى هذه الصفحة."
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # إنشاء الجداول عند التشغيل الأول
    with app.app_context():
        db.create_all()

        # إنشاء مستخدم افتراضي (admin)
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin', full_name='المشرف العام')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ تم إنشاء مستخدم افتراضي: admin / admin123")

    # تسجيل مسارات المصادقة
    register_auth_routes(app, db)

    # تحميل الوحدات
    load_modules(app, db)

    # مسار رئيسي يُوجّه إلى تسجيل الدخول
    @app.route('/')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))

    return app

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return render_template('dashboard/admin.html', user=current_user)
    elif current_user.role in ['cashier', 'waiter']:
        return redirect(url_for('restaurant.dashboard'))


# تشغيل التطبيق
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
