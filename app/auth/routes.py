from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app import db
from app.models import User, UserRole
from app.forms import LoginForm, RegistrationForm
from app.decorators import log_activity
from flask_login import current_user
from werkzeug.urls import url_parse

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            log_activity('login_successful')
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('main.dashboard')
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    log_activity('logout')
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=UserRole(form.role.data)
        )
        user.set_password(form.password.data)
        
        # Set manager if employee
        if form.role.data == 'employee' and form.manager_id.data:
            user.manager_id = form.manager_id.data
            
        db.session.add(user)
        db.session.commit()
        
        log_activity('user_registered', 'user', user.id, 
                    new_values={'username': user.username, 'role': user.role.value})
        
        flash('Registration successful', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register', form=form)
