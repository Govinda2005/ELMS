from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app.models import User, LeaveRequest, AuditLog, LeaveStatus, UserRole
from app.decorators import log_activity
from sqlalchemy import func
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('https://elms-mpfo.onrender.com/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_manager():
            return redirect(url_for('manager.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_manager():
        return redirect(url_for('manager.dashboard'))
    else:
        return redirect(url_for('employee.dashboard'))

@main_bp.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html'), 403

@main_bp.route('/profile')
@login_required
def profile():
    log_activity('profile_viewed')
    return render_template('profile.html', user=current_user)
