from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import LeaveRequest, LeaveStatus, LeaveType
from app.forms import LeaveRequestForm
from app.decorators import log_activity
from datetime import datetime

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_employee():
        return redirect(url_for('main.unauthorized'))
    
    # Get employee's leave statistics
    total_requests = current_user.leave_requests.count()
    pending_requests = current_user.leave_requests.filter_by(status=LeaveStatus.PENDING).count()
    approved_requests = current_user.leave_requests.filter_by(status=LeaveStatus.APPROVED).count()
    rejected_requests = current_user.leave_requests.filter_by(status=LeaveStatus.REJECTED).count()
    
    # Recent leave requests
    recent_requests = current_user.leave_requests.order_by(
        LeaveRequest.created_at.desc()
    ).limit(5).all()
    
    log_activity('employee_dashboard_viewed')
    
    return render_template('employee/dashboard.html',
                         total_requests=total_requests,
                         pending_requests=pending_requests,
                         approved_requests=approved_requests,
                         rejected_requests=rejected_requests,
                         recent_requests=recent_requests)

@employee_bp.route('/apply_leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    if not current_user.is_employee():
        return redirect(url_for('main.unauthorized'))
    
    form = LeaveRequestForm()
    
    if form.validate_on_submit():
        leave_request = LeaveRequest(
            employee_id=current_user.id,
            leave_type=LeaveType(form.leave_type.data),
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data,
            status=LeaveStatus.PENDING
        )
        
        db.session.add(leave_request)
        db.session.commit()
        
        log_activity('leave_request_created', 'leave_request', leave_request.id,
                    new_values={
                        'leave_type': form.leave_type.data,
                        'start_date': form.start_date.data.isoformat(),
                        'end_date': form.end_date.data.isoformat(),
                        'duration': leave_request.duration
                    })
        
        flash('Leave request submitted successfully', 'success')
        return redirect(url_for('employee.my_leaves'))
    
    return render_template('employee/apply_leave.html', form=form)

@employee_bp.route('/my_leaves')
@login_required
def my_leaves():
    if not current_user.is_employee():
        return redirect(url_for('main.unauthorized'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Filter options
    status_filter = request.args.get('status', '')
    
    query = current_user.leave_requests.order_by(LeaveRequest.created_at.desc())
    
    if status_filter:
        query = query.filter_by(status=LeaveStatus[status_filter.upper()])

    leave_requests = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    log_activity('my_leaves_viewed')
    
    return render_template('employee/my_leaves.html', 
                         leave_requests=leave_requests,
                         status_filter=status_filter)

@employee_bp.route('/edit_leave/<int:request_id>', methods=['GET', 'POST'])
@login_required
def edit_leave(request_id):
    if not current_user.is_employee():
        return redirect(url_for('main.unauthorized'))
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Check if user owns this request
    if leave_request.employee_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('employee.my_leaves'))
    
    # Check if request can be edited
    if not leave_request.can_be_edited:
        flash('This leave request cannot be edited', 'warning')
        return redirect(url_for('employee.my_leaves'))
    
    form = LeaveRequestForm(obj=leave_request)
    
    if form.validate_on_submit():
        old_values = {
            'leave_type': leave_request.leave_type.value,
            'start_date': leave_request.start_date.isoformat(),
            'end_date': leave_request.end_date.isoformat(),
            'reason': leave_request.reason
        }
        
        leave_request.leave_type = LeaveType(form.leave_type.data)
        leave_request.start_date = form.start_date.data
        leave_request.end_date = form.end_date.data
        leave_request.reason = form.reason.data
        leave_request.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        new_values = {
            'leave_type': leave_request.leave_type.value,
            'start_date': leave_request.start_date.isoformat(),
            'end_date': leave_request.end_date.isoformat(),
            'reason': leave_request.reason
        }
        
        log_activity('leave_request_updated', 'leave_request', leave_request.id,
                    old_values, new_values)
        
        flash('Leave request updated successfully', 'success')
        return redirect(url_for('employee.my_leaves'))
    
    return render_template('employee/edit_leave.html', form=form, leave_request=leave_request)

@employee_bp.route('/cancel_leave/<int:request_id>')
@login_required
def cancel_leave(request_id):
    if not current_user.is_employee():
        return redirect(url_for('main.unauthorized'))
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Check if user owns this request
    if leave_request.employee_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('employee.my_leaves'))
    
    # Check if request can be cancelled
    if not leave_request.can_be_cancelled:
        flash('This leave request cannot be cancelled', 'warning')
        return redirect(url_for('employee.my_leaves'))
    
    old_status = leave_request.status.value
    leave_request.status = LeaveStatus.CANCELLED
    leave_request.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    log_activity('leave_request_cancelled', 'leave_request', leave_request.id,
                old_values={'status': old_status},
                new_values={'status': 'cancelled'})
    
    flash('Leave request cancelled successfully', 'success')
    return redirect(url_for('employee.my_leaves'))
