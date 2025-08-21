from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, PasswordField, BooleanField, IntegerField,SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from wtforms.widgets import TextArea
from datetime import date, datetime
from app.models import User, UserRole, LeaveType

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('employee', 'Employee'),
            ('manager', 'Manager')], validators=[DataRequired()])
    manager_id = SelectField('Manager', coerce=int, validators=[])

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        # Populate manager choices
        managers = User.query.filter_by(role=UserRole.MANAGER).all()
        self.manager_id.choices = [(0, 'Select Manager')] + [(m.id, m.full_name) for m in managers]

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

    def validate_manager_id(self, manager_id):
        if self.role.data == 'employee' and (not manager_id.data or manager_id.data == 0):
            raise ValidationError('Please select a manager.')

class LeaveRequestForm(FlaskForm):
    leave_type = SelectField('Leave Type', choices=[(lt.value, lt.value.title()) for lt in LeaveType], validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[Length(max=500)])

    def validate_start_date(self, start_date):
        if start_date.data < date.today():
            raise ValidationError('Start date cannot be in the past.')

    def validate_end_date(self, end_date):
        if self.start_date.data and end_date.data < self.start_date.data:
            raise ValidationError('End date must be after start date.')

class ApprovalForm(FlaskForm):
    action = SelectField('Action', choices=[('approve', 'Approve'), ('reject', 'Reject')], validators=[DataRequired()])
    comments = TextAreaField('Comments', validators=[Length(max=500)])

class UserEditForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    role = SelectField('Role', choices=[(role.value, role.value.title()) for role in UserRole], validators=[DataRequired()])
    manager_id = SelectField('Manager', coerce=int, validators=[])
    is_active = BooleanField('Active')

    def __init__(self, original_user=None, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_user = original_user
        # Populate manager choices
        managers = User.query.filter_by(role=UserRole.MANAGER).all()
        self.manager_id.choices = [(0, 'No Manager')] + [(m.id, m.full_name) for m in managers]

    def validate_username(self, username):
        if self.original_user and username.data != self.original_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        if self.original_user and email.data != self.original_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Please use a different email address.')

class ReportForm(FlaskForm):
    report_type = SelectField('Report Type', choices=[
        ('monthly', 'Monthly Report'),
        ('team', 'Team Report'),
        ('user', 'User Report')
    ], validators=[DataRequired()])
    month = SelectField('Month', choices=[(str(i), datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)])
    year = SelectField('Year', choices=[(str(year), str(year)) for year in range(2020, 2030)])
    team_manager = SelectField('Team Manager', coerce=int)
    employee = SelectField('Employee', coerce=int)
    format = SelectField('Format', choices=[('pdf', 'PDF'), ('csv', 'CSV')], validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)
        # Set default values
        current_date = datetime.now()
        self.month.data = str(current_date.month)
        self.year.data = str(current_date.year)
        
        # Populate team manager choices
        managers = User.query.filter_by(role=UserRole.MANAGER).all()
        self.team_manager.choices = [(0, 'All Teams')] + [(m.id, m.full_name) for m in managers]
        
        # Populate employee choices
        employees = User.query.filter_by(role=UserRole.EMPLOYEE).all()
        self.employee.choices = [(0, 'All Employees')] + [(e.id, e.full_name) for e in employees]


class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    role = SelectField('Role', choices=[
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('employee', 'Employee')
    ], validators=[DataRequired()])
    manager_id = IntegerField('Manager ID')  # You can use a SelectField if you want to show manager names
    is_active = BooleanField('Active', default=True)
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Create User')