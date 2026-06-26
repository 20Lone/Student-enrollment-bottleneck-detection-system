from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize the database object here; we bind it to the app in __init__.py
db = SQLAlchemy()


class Student(db.Model):
    __tablename__ = 'students'
    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(15))
    department = db.Column(db.String(100))
    level = db.Column(db.String(20))
    password_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    payments = db.relationship('Payment', backref='student', lazy=True)


class Course(db.Model):
    __tablename__ = 'courses'
    course_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_code = db.Column(db.String(20), unique=True)
    course_title = db.Column(db.String(100), nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False)
    enrolled_count = db.Column(db.Integer, default=0)
    fee_amount = db.Column(db.Numeric(10, 2), nullable=False, default=50000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    enrollment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'))
    enrollment_status = db.Column(db.String(20), default='Pending')  # Pending/Approved/Failed
    enrollment_time = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    __tablename__ = 'payments'
    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'))
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.enrollment_id'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(20), default='Pending')  # Successful/Failed/Pending
    payment_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    enrollment = db.relationship('Enrollment', backref='payments', lazy=True)


class SystemLog(db.Model):
    """
    Critical table for ML training. Captures system load metrics
    to train Random Forest and LSTM models.
    """
    __tablename__ = 'system_logs'
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_count = db.Column(db.Integer, default=0)
    active_users = db.Column(db.Integer, default=0)
    cpu_usage = db.Column(db.Float, default=0.0)       # Server CPU %
    memory_usage = db.Column(db.Float, default=0.0)    # Server Memory %
    response_time = db.Column(db.Float, default=0.0)   # Request latency in seconds
    log_time = db.Column(db.DateTime, default=datetime.utcnow)
    # Engineered label for Random Forest training
    load_class = db.Column(db.Integer, default=0)      # 0=Normal, 1=Moderate, 2=Bottleneck


class Admin(db.Model):
    __tablename__ = 'admins'
    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
