from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, LeaveRequest, LeaveStatus, UserRole
from app.forms import ApprovalForm, ReportForm
from app.decorators import manager_or_admin_required, log_activity
from datetime import datetime
from sqlalchemy import and_

manager_bp = Blueprint('manager', __name__)

@manager_bp.route('/dashboard')
@login_required
@manager_or_admin_required
def dashboard():
    # Get manager's team statistics
    if current_user.is_manager():
        team_members = current_user.employees
        pending_requests = LeaveRequest.query.join(User,LeaveRequest.employee_id == User.id).filter(
            User.manager_id == current_user.id,
            LeaveRequest.status == LeaveStatus.PENDING
        ).count()
        
        approved_requests = LeaveRequest.query.join(User, LeaveRequest.employee_id == User.id).filter(
            User.manager_id == current_user.id,
            LeaveRequest.status == LeaveStatus.APPROVED
        ).count()
        
        total_requests = LeaveRequest.query.join(User, LeaveRequest.employee_id == User.id).filter(
            User.manager_id == current_user.id
        ).count()
        
    else:  # Admin has access to all data
        team_members = User.query.filter_by(role=UserRole.EMPLOYEE).all()
        pending_requests = LeaveRequest.query.filter_by(status=LeaveStatus.PENDING).count()
        approved_requests = LeaveRequest.query.filter_by(status=LeaveStatus.APPROVED).count()
        total_requests = LeaveRequest.query.count()
    
    # Recent requests for review
    if current_user.is_manager():
        recent_requests = LeaveRequest.query.join(User, LeaveRequest.employee_id == User.id).filter(
            User.manager_id == current_user.id,
            LeaveRequest.status == LeaveStatus.PENDING
        ).order_by(LeaveRequest.created_at.desc()).limit(5).all()
    else:
        recent_requests = LeaveRequest.query.filter_by(
            status=LeaveStatus.PENDING
        ).order_by(LeaveRequest.created_at.desc()).limit(5).all()
    
    log_activity('manager_dashboard_viewed')
    
    return render_template('manager/dashboard.html',
                         team_members=team_members,
                         pending_requests=pending_requests,
                         approved_requests=approved_requests,
                         total_requests=total_requests,
                         recent_requests=recent_requests)

@manager_bp.route('/leave_requests')
@login_required
@manager_or_admin_required
def leave_requests():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Filter options
    status_filter = request.args.get('status', '')
    employee_filter = request.args.get('employee', '', type=int)
    
    # Base query depending on user role
    if current_user.is_manager():
        query = LeaveRequest.query.join(User, LeaveRequest.employee_id == User.id).filter(User.manager_id == current_user.id)
    else:  # Admin can see all requests
        query = LeaveRequest.query
    
    # Apply filters
    if status_filter:
        try:
            # Always use enum name (upper-case)
            query = query.filter(LeaveRequest.status == LeaveStatus[status_filter.upper()])
        except KeyError:
            pass  # Ignore invalid status
    
    if employee_filter:
        query = query.filter(LeaveRequest.employee_id == employee_filter)
    
    # Order by creation date
    query = query.order_by(LeaveRequest.created_at.desc())
    
    requests = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get employees for filter dropdown
    if current_user.is_manager():
        employees = current_user.employees
    else:
        employees = User.query.filter_by(role=UserRole.EMPLOYEE).all()
    
    log_activity('leave_requests_viewed')
    
    return render_template('manager/leave_requests.html',
                         requests=requests,
                         employees=employees,
                         status_filter=status_filter,
                         employee_filter=employee_filter)

@manager_bp.route('/review_request/<int:request_id>', methods=['GET', 'POST'])
@login_required
@manager_or_admin_required
def review_request(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Check if manager can approve this request
    if not current_user.can_approve_leave(leave_request.employee_id):
        flash('You do not have permission to review this request', 'danger')
        return redirect(url_for('manager.leave_requests'))
    
    # Check if request is still pending
    if leave_request.status != LeaveStatus.PENDING:
        flash('This request has already been processed', 'warning')
        return redirect(url_for('manager.leave_requests'))
    
    form = ApprovalForm()
    
    if form.validate_on_submit():
        old_status = leave_request.status.value
        
        if form.action.data == 'approve':
            leave_request.status = LeaveStatus.APPROVED
        else:
            leave_request.status = LeaveStatus.REJECTED
            
        leave_request.approved_by = current_user.id
        leave_request.approval_date = datetime.utcnow()
        leave_request.manager_comments = form.comments.data
        leave_request.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        log_activity(f'leave_request_{form.action.data}d', 'leave_request', leave_request.id,
                    old_values={'status': old_status},
                    new_values={'status': leave_request.status.value, 'comments': form.comments.data})
        
        flash(f'Leave request {form.action.data}d successfully', 'success')
        return redirect(url_for('manager.leave_requests'))
    
    return render_template('manager/review_request.html', 
                         form=form, 
                         leave_request=leave_request)

@manager_bp.route('/team_reports', methods=['GET', 'POST'])
@login_required
@manager_or_admin_required
def team_reports():
    form = ReportForm()
    
    # Limit report options for managers
    if current_user.is_manager():
        form.report_type.choices = [('monthly', 'Monthly Report'), ('team', 'Team Report')]
    
    if form.validate_on_submit():
        report_type = form.report_type.data
        format_type = form.format.data
        
        if report_type == 'monthly':
            month = int(form.month.data)
            year = int(form.year.data)
            return generate_manager_monthly_report(month, year, format_type)
        elif report_type == 'team':
            return generate_manager_team_report(format_type)
    
    log_activity('team_reports_viewed')
    
    return render_template('manager/team_reports.html', form=form)

def generate_manager_monthly_report(month, year, format_type):
    from app.admin.routes import generate_monthly_report
    # For managers, filter by their team
    if current_user.is_manager():
        # This would need to be implemented to filter by manager's team
        pass
    return generate_monthly_report(month, year, format_type)

def generate_manager_team_report(format_type):
    from app.admin.routes import generate_team_report
    # Generate report for manager's team only
    manager_id = current_user.id if current_user.is_manager() else None
    return generate_team_report(manager_id, format_type)

@manager_bp.route('/team_members')
@login_required
@manager_or_admin_required
def team_members():
    if current_user.is_manager():
        members = current_user.employees
    else:  # Admin can see all employees
        members = User.query.filter_by(role=UserRole.EMPLOYEE).all()
    
    log_activity('team_members_viewed')
    
    return render_template('manager/team_members.html', members=members)
