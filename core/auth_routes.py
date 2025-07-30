# core/auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .auth import User

def register_auth_routes(app, db):
    bp = Blueprint('auth', __name__, url_prefix='/auth')

    # --- تسجيل الدخول ---
    @bp.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash(f'مرحباً {user.full_name or user.username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')

        return render_template('auth/login.html')

    # --- تسجيل الخروج ---
    @bp.route('/logout')
    @login_required
    def logout():
        username = current_user.username
        logout_user()
        flash(f'تم تسجيل خروج {username} بنجاح', 'info')
        return redirect(url_for('auth.login'))

    # --- لوحة التحكم (حسب الدور) ---
    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.role == 'admin':
            return render_template('dashboard/admin.html', user=current_user)
        elif current_user.role in ['cashier', 'waiter']:
            return redirect(url_for('restaurant.dashboard'))
        elif current_user.role == 'chef':
            return redirect(url_for('restaurant.manage_orders'))
        else:
            return f'<h2>مرحباً {current_user.full_name}</h2><p>دورك: {current_user.role}</p>'

    app.register_blueprint(bp)
