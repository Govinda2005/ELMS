from flask import request, session
from app import db
from app.models import AuditLog
from functools import wraps
from flask_login import current_user
from flask import request, session, redirect, url_for


def log_activity(action, entity_type=None, entity_id=None, old_values=None, new_values=None):
    """Log user activity for audit purposes"""
    if current_user.is_authenticated:
        audit_log = AuditLog(
            user_id=current_user.id,
            action=action,
            entity_type=entity_type or 'system',
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.environ.get('HTTP_X_REAL_IP', request.remote_addr),
            user_agent=request.user_agent.string
        )
        db.session.add(audit_log)
        db.session.commit()

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return redirect(url_for('main.unauthorized'))
        return f(*args, **kwargs)
    return decorated_function

def manager_or_admin_required(f):
    """Decorator to require manager or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_manager() or current_user.is_admin()):
            return redirect(url_for('main.unauthorized'))
        return f(*args, **kwargs)
    return decorated_function