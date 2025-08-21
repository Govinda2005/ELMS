from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from app import db
from app.models import User, LeaveRequest, AuditLog, LeaveStatus, UserRole, LeaveType
from app.forms import UserEditForm, ReportForm, CreateUserForm
from app.decorators import admin_required, log_activity
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
import pandas as pd
import io
from weasyprint import HTML
import csv

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/profile')
@login_required
def profile():
    # current_user is provided by Flask-Login
    return render_template('profile.html', user=current_user)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    users = User.query.order_by(User.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    form = ReportForm()
    log_activity('admin_dashboard_viewed')
    return render_template('admin/dashboard.html', users=users, form=form)

@admin_bp.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=UserRole(form.role.data),
            is_active=form.is_active.data,
            manager_id=form.manager_id.data if form.manager_id.data else None
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        log_activity('user_created', 'user', user.id, new_values={
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'manager_id': user.manager_id,
            'is_active': user.is_active
        })
        flash('User added successfully', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/addnewuser.html', form=form)

@admin_bp.route('/manage_users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    users = User.query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    log_activity('users_management_viewed')
    
    return render_template('admin/manage_users.html', users=users)

@admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(original_user=user, obj=user)
    
    if form.validate_on_submit():
        old_values = {
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'manager_id': user.manager_id,
            'is_active': user.is_active
        }
        
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role = UserRole(form.role.data)
        user.is_active = form.is_active.data
        
        if form.manager_id.data != 0:
            user.manager_id = form.manager_id.data
        else:
            user.manager_id = None
            
        db.session.commit()
        
        new_values = {
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'manager_id': user.manager_id,
            'is_active': user.is_active
        }
        
        log_activity('user_updated', 'user', user.id, old_values, new_values)
        
        flash('User updated successfully', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/edit_user.html', form=form, user=user)

@admin_bp.route('/delete_user/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    # Check if user has pending leave requests
    pending_requests = LeaveRequest.query.filter_by(
        employee_id=user.id, 
        status=LeaveStatus.PENDING
    ).count()
    
    if pending_requests > 0:
        flash('Cannot delete user with pending leave requests', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    managed_users = User.query.filter_by(manager_id=user.id).count()
    if managed_users > 0:
        flash(f'Cannot deactivate manager "{user.full_name}". Please reassign their {managed_users} employees first.', 'danger')
        return redirect(url_for('admin.manage_users'))

    old_values = {'is_active': user.is_active}
    user.is_active = False
    new_values = {'is_active': user.is_active}

    log_activity('user_deactivated', 'user', user.id, old_values, new_values)

    db.session.commit()
    
    flash('User deactivated successfully', 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/audit_logs')
@login_required
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    log_activity('audit_logs_viewed')
    
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/reports', methods=['GET', 'POST'])
@login_required
@admin_required
def reports():
    form = ReportForm()
    
    if form.validate_on_submit():
        report_type = form.report_type.data
        format_type = form.format.data
        
        if report_type == 'monthly':
            month = int(form.month.data)
            year = int(form.year.data)
            return generate_monthly_report(month, year, format_type)
        elif report_type == 'team':
            manager_id = form.team_manager.data if form.team_manager.data and form.team_manager.data != '0' else None
            return generate_team_report(manager_id, format_type)
        elif report_type == 'user':
            employee_id = form.employee.data if form.employee.data and form.employee.data != '0' else None
            return generate_user_report(employee_id, format_type)
    
    log_activity('reports_page_viewed')
    
    return render_template('admin/reports.html', form=form)


def generate_monthly_report(month, year, format_type, manager_id=None):
    # Query leave requests for the specified month and year
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    query = LeaveRequest.query.filter(
        and_(LeaveRequest.start_date >= start_date.date(),
             LeaveRequest.start_date <= end_date.date())
    )

    if manager_id:
        employee_ids = [e.id for e in User.query.get(manager_id).employees]
        query = query.filter(LeaveRequest.employee_id.in_(employee_ids))

    leaves = query.all()
    
    data = []
    for leave in leaves:
        data.append({
            'Employee': leave.employee.full_name,
            'Leave Type': leave.leave_type.value.title(),
            'Start Date': leave.start_date.strftime('%Y-%m-%d'),
            'End Date': leave.end_date.strftime('%Y-%m-%d'),
            'Duration': leave.duration,
            'Status': leave.status.value.title(),
            'Approved By': leave.approver.full_name if leave.approver else 'N/A'
        })
    
    log_activity('monthly_report_generated', new_values={'month': month, 'year': year, 'format': format_type})
    
    if format_type == 'csv':
        return generate_csv_response(data, f'monthly_report_{month}_{year}.csv')
    else:
        return generate_pdf_response(data, f'Monthly Leave Report - {datetime(year, month, 1).strftime("%B %Y")}')


def generate_team_report(manager_id, format_type):
    if manager_id:
        manager = User.query.get(manager_id)
        if not manager:
            flash('Selected manager not found', 'error')
            return redirect(url_for('admin.reports'))
        employees = manager.employees
        title = f'Team Report - {manager.full_name}'
        filename_prefix = f'team_report_{manager.full_name.replace(" ", "_").lower()}'
    else:
        employees = User.query.filter_by(role=UserRole.EMPLOYEE).all()
        title = 'All Teams Report'
        filename_prefix = 'all_teams_report'
    
    data = []
    for employee in employees:
        leaves = LeaveRequest.query.filter_by(employee_id=employee.id).all()
        for leave in leaves:
            data.append({
                'Employee': employee.full_name,
                'Manager': employee.manager.full_name if employee.manager else 'N/A',
                'Leave Type': leave.leave_type.value.title(),
                'Start Date': leave.start_date.strftime('%Y-%m-%d'),
                'End Date': leave.end_date.strftime('%Y-%m-%d'),
                'Duration': leave.duration,
                'Status': leave.status.value.title()
            })
    
    log_activity('team_report_generated', new_values={'manager_id': manager_id, 'format': format_type})
    
    if format_type == 'csv':
        return generate_csv_response(data, f'{filename_prefix}.csv')
    else:
        return generate_pdf_response(data, title)


def generate_user_report(employee_id, format_type):
    if employee_id:
        employee = User.query.get(employee_id)
        if not employee:
            flash('Selected employee not found', 'error')
            return redirect(url_for('admin.reports'))
        leaves = LeaveRequest.query.filter_by(employee_id=employee_id).all()
        title = f'User Report - {employee.full_name}'
        filename_prefix = f'user_report_{employee.full_name.replace(" ", "_").lower()}'
    else:
        leaves = LeaveRequest.query.all()
        title = 'All Users Report'
        filename_prefix = 'all_users_report'
    
    data = []
    for leave in leaves:
        data.append({
            'Employee': leave.employee.full_name,
            'Leave Type': leave.leave_type.value.title(),
            'Start Date': leave.start_date.strftime('%Y-%m-%d'),
            'End Date': leave.end_date.strftime('%Y-%m-%d'),
            'Duration': leave.duration,
            'Status': leave.status.value.title(),
            'Reason': leave.reason or 'N/A'
        })
    
    log_activity('user_report_generated', new_values={'employee_id': employee_id, 'format': format_type})
    
    if format_type == 'csv':
        return generate_csv_response(data, f'{filename_prefix}.csv')
    else:
        return generate_pdf_response(data, title)


def generate_csv_response(data, filename):
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


def generate_pdf_response(data, title):
    df = pd.DataFrame(data) if data else pd.DataFrame()
    html_string = f'''
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; text-align: center; margin-bottom: 20px; }}
            .report-info {{ text-align: center; margin-bottom: 30px; color: #666; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; font-size: 12px; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .no-data {{ text-align: center; color: #666; margin-top: 50px; font-style: italic; }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <div class="report-info">
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total Records: {len(data) if data else 0}</p>
        </div>
        {df.to_html(index=False, table_id='report-table', classes='table', escape=False) if not df.empty else '<div class="no-data"><p>No data available for the selected criteria</p></div>'}
    </body>
    </html>
    '''
    
    pdf = HTML(string=html_string).write_pdf()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={title.replace(" ", "_").lower()}.pdf'
    return response
