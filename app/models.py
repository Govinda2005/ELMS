from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from enum import Enum

class UserRole(Enum):
    ADMIN = 'admin'
    MANAGER = 'manager'
    EMPLOYEE = 'employee'

class LeaveStatus(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'

class LeaveType(Enum):
    SICK = 'sick'
    VACATION = 'vacation'
    PERSONAL = 'personal'
    MATERNITY = 'maternity'
    PATERNITY = 'paternity'
    EMERGENCY = 'emergency'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Manager relationship
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    manager = db.relationship('User', remote_side=[id], backref='employees')
    
    # Leave requests
    leave_requests = db.relationship('LeaveRequest', foreign_keys='LeaveRequest.employee_id', backref='employee', lazy='dynamic')
    approved_requests = db.relationship('LeaveRequest', foreign_keys='LeaveRequest.approved_by', backref='approver', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    def is_manager(self):
        return self.role == UserRole.MANAGER
    
    def is_employee(self):
        return self.role == UserRole.EMPLOYEE
    
    def can_approve_leave(self, employee_id):
        if self.is_admin():
            return True
        if self.is_manager():
            employee = User.query.get(employee_id)
            return employee and employee.manager_id == self.id
        return False
    
    def get_subordinates(self):
        if self.is_admin():
            return User.query.filter_by(role=UserRole.EMPLOYEE).all()
        elif self.is_manager():
            return self.employees
        return []
    
    def __repr__(self):
        return f'<User {self.username}>'

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.Enum(LeaveType), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.Enum(LeaveStatus), default=LeaveStatus.PENDING)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approval_date = db.Column(db.DateTime, nullable=True)
    manager_comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def duration(self):
        return (self.end_date - self.start_date).days + 1
    
    @property
    def is_pending(self):
        return self.status == LeaveStatus.PENDING
    
    @property
    def is_approved(self):
        return self.status == LeaveStatus.APPROVED
    
    @property
    def is_rejected(self):
        return self.status == LeaveStatus.REJECTED
    
    @property
    def can_be_cancelled(self):
        return self.status in [LeaveStatus.PENDING, LeaveStatus.APPROVED] and self.start_date > date.today()
    
    @property
    def can_be_edited(self):
        return self.status == LeaveStatus.PENDING and self.start_date > date.today()
    
    def __repr__(self):
        return f'<LeaveRequest {self.id} - {self.employee.username}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.id} - {self.action}>'