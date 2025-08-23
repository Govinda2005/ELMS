import os
from flask.cli import FlaskGroup
from app import create_app, db
from app.models import User, LeaveRequest, AuditLog, UserRole, LeaveType, LeaveStatus
from datetime import date, datetime

app = create_app()
cli = FlaskGroup(app)

@cli.command("create-db")
def create_db():
    """Create database tables."""
    db.create_all()
    print("Database tables created!")

@cli.command("drop-db")
def drop_db():
    """Drop database tables."""
    db.drop_all()
    print("Database tables dropped!")

@cli.command("init-db")
def init_db():
    """Initialize database with sample data."""
    # Drop and create tables
    db.drop_all()
    db.create_all()
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@gmail.com',
        first_name='admin',
        last_name='main',
        role=UserRole.ADMIN
    )
    admin.set_password('admin@123')
    db.session.add(admin)
    
    # Create manager users
    manager1 = User(
        username='dayamanager',
        email='daya@gmail.com',
        first_name='dayakar',
        last_name='Manager',
        role=UserRole.MANAGER
    )
    manager1.set_password('manager123')
    db.session.add(manager1)
    
    manager2 = User(
        username='vijaymanager',
        email='vijay@gmail.com',
        first_name='vijay',
        last_name='Manager',
        role=UserRole.MANAGER
    )
    manager2.set_password('manager123')
    db.session.add(manager2)
    
    # Commit to get IDs
    db.session.commit()
    
    # Create employee users
    employees = [
        ('govi', 'govi@gmail.com', 'govi', 'Employee', manager1.id),
        ('nani', 'nani@gmail.com', 'nani', 'Employee', manager1.id),
        ('ramesh', 'ramesh@gmail.com', 'ramesh', 'Employee', manager2.id),
        ('tharun', 'tharun@gmail.com', 'tharun', 'Employee', manager2.id),
        ('ganesh','ganesh@gmail.com','ganmesh','Employee',manager2.id)
    ]
    
    for username, email, first_name, last_name, manager_id in employees:
        employee = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.EMPLOYEE,
            manager_id=manager_id
        )
        employee.set_password('employee123')
        db.session.add(employee)
    
    # Commit all users
    db.session.commit()
    
    # Create sample leave requests
    employee1 = User.query.filter_by(username='govi').first()
    employee2= User.query.filter_by(username='nani').first()
    employee3= User.query.filter_by(username='ramesh').first()
    employee4 = User.query.filter_by(username='tharun').first()
    employee5 = User.query.filter_by(username='ganesh').first()


    
    sample_leaves = [
        (employee1.id, LeaveType.VACATION, date(2025, 9, 1), date(2025, 9, 5), 'Family vacation'),
        (employee2.id, LeaveType.SICK, date(2025, 8, 15), date(2025, 8, 16), 'Medical appointment'),
        (employee3.id, LeaveType.PERSONAL, date(2025, 8, 20), date(2025, 8, 20), 'Personal matters'),
        (employee4.id, LeaveType.PERSONAL,date(2025,8,27),date(2025,8,27),'My birthaday'),
        (employee5.id, LeaveType.PERSONAL,date(2025,9,27),date(2025,10,7),'personal matters'),    ]
    
    for emp_id, leave_type, start_date, end_date, reason in sample_leaves:
        leave_request = LeaveRequest(
            employee_id=emp_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status=LeaveStatus.PENDING
        )
        db.session.add(leave_request)
    
    db.session.commit()
    
    print("Database initialized with sample data!")
    print("\nSample Users:")
    print("Admin: username='admin', password='admin@123'")
    print("Manager 1: username='dayamanager', password='manager123'")
    print("Manager 2: username='vijaymanager', password='manager123'")
    print("Employee 1: username='govi', password='employee123'")
    print("Employee 2: username='nani', password='employee123'")
    print("Employee 3: username='ramesh', password='employee123'")
    print("Employee 4: username='tharun', password='employee123'")
    print("Employee 5: username='ganesh', password='employee123'")

@cli.command("create-admin")
def create_admin():
    """Create an admin user."""
    username = input("Username: ")
    email = input("Email: ")
    first_name = input("First Name: ")
    last_name = input("Last Name: ")
    password = input("Password: ")
    
    admin = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=UserRole.ADMIN
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    
    print(f"Admin user '{username}' created successfully!")

if __name__ == '__main__':
    cli()