from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime

from app.models import db, Student, Course, Enrollment, Payment, SystemLog, Admin
from ml.bottleneck_detector import combined_assessment, predict_next_24h, enrollment_advice, realtime_forecast

routes_bp = Blueprint('routes', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('routes.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('routes.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'student':
            flash('Student access required.', 'danger')
            return redirect(url_for('routes.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@routes_bp.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('routes.dashboard'))
    return redirect(url_for('routes.login'))


@routes_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Auto-detect role: check admin first, then student
        admin = Admin.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['user_id'] = admin.admin_id
            session['user_name'] = admin.name
            session['role'] = 'admin'
            flash(f'Welcome, {admin.name}!', 'success')
            return redirect(url_for('routes.dashboard'))

        student = Student.query.filter_by(email=email).first()
        if student and check_password_hash(student.password_hash, password):
            session['user_id'] = student.student_id
            session['user_name'] = student.full_name
            session['role'] = 'student'
            flash(f'Welcome, {student.full_name}!', 'success')
            return redirect(url_for('routes.dashboard'))

        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@routes_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        level = request.form.get('level', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not full_name or not email or not password:
            flash('Full name, email, and password are required.', 'danger')
            return redirect(url_for('routes.register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('routes.register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('routes.register'))

        if Student.query.filter_by(email=email).first() or Admin.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return redirect(url_for('routes.register'))

        student = Student(
            full_name=full_name,
            email=email,
            phone=phone,
            department=department,
            level=level,
            password_hash=generate_password_hash(password)
        )
        db.session.add(student)
        db.session.commit()

        session['user_id'] = student.student_id
        session['user_name'] = student.full_name
        session['role'] = 'student'
        flash(f'Welcome, {full_name}! Your account has been created.', 'success')
        return redirect(url_for('routes.dashboard'))

    return render_template('register.html', departments=[
        'Computer Science', 'Electrical Engineering', 'Mechanical Engineering',
        'Civil Engineering', 'Mathematics', 'Physics', 'Chemistry', 'Biology',
        'Economics', 'Business Administration', 'Law', 'Medicine'
    ], levels=['100', '200', '300', '400', '500'])


@routes_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('routes.login'))


# ==================== DASHBOARDS ====================

@routes_bp.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') == 'admin':
        return admin_dashboard()
    return student_dashboard()


def admin_dashboard():
    student_count = Student.query.count()
    course_count = Course.query.count()
    enrollment_count = Enrollment.query.count()
    payment_count = Payment.query.count()
    log_count = SystemLog.query.count()

    recent_logs = SystemLog.query.order_by(SystemLog.log_time.desc()).limit(10).all()
    recent_enrollments = Enrollment.query.order_by(Enrollment.enrollment_time.desc()).limit(10).all()

    approved_enrollments = Enrollment.query.filter_by(enrollment_status='Approved').count()
    successful_payments = Payment.query.filter_by(payment_status='Successful').count()
    bottleneck_logs = SystemLog.query.filter_by(load_class=2).count()

    assessment = combined_assessment()

    return render_template('admin_dashboard.html',
                           student_count=student_count,
                           course_count=course_count,
                           enrollment_count=enrollment_count,
                           payment_count=payment_count,
                           log_count=log_count,
                           recent_logs=recent_logs,
                           recent_enrollments=recent_enrollments,
                           approved_enrollments=approved_enrollments,
                           successful_payments=successful_payments,
                           bottleneck_logs=bottleneck_logs,
                           assessment=assessment)


def student_dashboard():
    student_id = session['user_id']
    student = Student.query.get(student_id)

    my_enrollments = Enrollment.query.filter_by(student_id=student_id)\
        .order_by(Enrollment.enrollment_time.desc()).limit(10).all()
    my_payments = Payment.query.filter_by(student_id=student_id)\
        .order_by(Payment.payment_time.desc()).limit(10).all()

    approved_count = Enrollment.query.filter_by(student_id=student_id, enrollment_status='Approved').count()
    pending_count = Enrollment.query.filter_by(student_id=student_id, enrollment_status='Pending').count()

    advice = enrollment_advice()

    return render_template('student_dashboard.html',
                           student=student,
                           my_enrollments=my_enrollments,
                           my_payments=my_payments,
                           approved_count=approved_count,
                           pending_count=pending_count,
                           advice=advice)


# ==================== STUDENT ROUTES ====================

@routes_bp.route('/enrollments/new', methods=['GET', 'POST'])
@login_required
@student_required
def enroll_new():
    if request.method == 'POST':
        course_id = request.form.get('course_id', type=int)
        if not course_id:
            flash('Please select a course.', 'danger')
            return redirect(url_for('routes.enroll_new'))

        course = Course.query.get(course_id)
        if not course:
            flash('Course not found.', 'danger')
            return redirect(url_for('routes.enroll_new'))

        student_id = session['user_id']
        existing = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
        if existing:
            flash('You are already enrolled in this course.', 'warning')
            return redirect(url_for('routes.my_enrollments'))

        enrollment = Enrollment(
            student_id=student_id,
            course_id=course_id,
            enrollment_status='Pending',
            enrollment_time=datetime.utcnow()
        )
        db.session.add(enrollment)
        db.session.commit()

        flash(f'Enrollment in {course.course_code} - {course.course_title} initiated. Please complete payment.', 'success')
        return redirect(url_for('routes.payment_new', enrollment_id=enrollment.enrollment_id))

    courses = Course.query.filter(Course.enrolled_count < Course.max_capacity)\
        .order_by(Course.course_code).all()
    advice = enrollment_advice()
    return render_template('enroll_new.html', courses=courses, advice=advice)


@routes_bp.route('/enrollments/my')
@login_required
@student_required
def my_enrollments():
    student_id = session['user_id']
    enrollments = Enrollment.query.filter_by(student_id=student_id)\
        .order_by(Enrollment.enrollment_time.desc()).all()
    return render_template('my_enrollments.html', enrollments=enrollments)


@routes_bp.route('/payments/new', methods=['GET', 'POST'])
@login_required
@student_required
def payment_new():
    enrollment_id = request.args.get('enrollment_id', type=int) or request.form.get('enrollment_id', type=int)

    enrollment = Enrollment.query.get(enrollment_id)
    if not enrollment or enrollment.student_id != session['user_id']:
        flash('Invalid enrollment.', 'danger')
        return redirect(url_for('routes.my_enrollments'))

    if request.method == 'POST':
        card_number = request.form.get('card_number', '').replace(' ', '')
        card_name = request.form.get('card_name', '')
        card_expiry = request.form.get('card_expiry', '')
        card_cvv = request.form.get('card_cvv', '')

        # Server-side Luhn validation
        if not _luhn_check(card_number):
            flash('Invalid card number.', 'danger')
            return redirect(url_for('routes.payment_new', enrollment_id=enrollment_id))

        if len(card_cvv) < 3:
            flash('Invalid CVV.', 'danger')
            return redirect(url_for('routes.payment_new', enrollment_id=enrollment_id))

        # Simulate processing
        import time
        time.sleep(1)

        course = Course.query.get(enrollment.course_id)
        amount = float(course.fee_amount) if course else 50000

        payment = Payment(
            student_id=session['user_id'],
            enrollment_id=enrollment_id,
            amount=amount,
            payment_status='Successful',
            payment_time=datetime.utcnow()
        )
        db.session.add(payment)

        enrollment.enrollment_status = 'Approved'
        if course:
            course.enrolled_count += 1

        db.session.commit()

        flash(f'Payment of NGN {amount:,.2f} successful! Enrollment approved.', 'success')
        return redirect(url_for('routes.my_enrollments'))

    course = Course.query.get(enrollment.course_id)
    return render_template('payment_new.html', enrollment=enrollment, course=course)


@routes_bp.route('/payments/my')
@login_required
@student_required
def my_payments():
    student_id = session['user_id']
    payments = Payment.query.filter_by(student_id=student_id)\
        .order_by(Payment.payment_time.desc()).all()
    return render_template('my_payments.html', payments=payments)


# ==================== ADMIN ROUTES ====================

@routes_bp.route('/students')
@login_required
@admin_required
def students():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = Student.query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('students.html', students=pagination.items, pagination=pagination)


@routes_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        level = request.form.get('level', '').strip()
        password = request.form.get('password', '')

        if not full_name or not email or not password:
            flash('Full name, email, and password are required.', 'danger')
            return redirect(url_for('routes.add_student'))

        student = Student(
            full_name=full_name,
            email=email,
            phone=phone,
            department=department,
            level=level,
            password_hash=generate_password_hash(password)
        )
        db.session.add(student)
        db.session.commit()
        flash(f'Student {full_name} added successfully.', 'success')
        return redirect(url_for('routes.students'))

    return render_template('add_student.html', departments=[
        'Computer Science', 'Electrical Engineering', 'Mechanical Engineering',
        'Civil Engineering', 'Mathematics', 'Physics', 'Chemistry', 'Biology',
        'Economics', 'Business Administration', 'Law', 'Medicine'
    ], levels=['100', '200', '300', '400', '500'])


@routes_bp.route('/courses')
@login_required
def courses():
    all_courses = Course.query.order_by(Course.course_code).all()
    return render_template('courses.html', courses=all_courses)


@routes_bp.route('/enrollments')
@login_required
@admin_required
def enrollments():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    pagination = Enrollment.query.order_by(Enrollment.enrollment_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    return render_template('enrollments.html', enrollments=pagination.items, pagination=pagination)


@routes_bp.route('/payments')
@login_required
@admin_required
def payments():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    pagination = Payment.query.order_by(Payment.payment_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    return render_template('payments.html', payments=pagination.items, pagination=pagination)


@routes_bp.route('/logs')
@login_required
@admin_required
def logs():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    pagination = SystemLog.query.order_by(SystemLog.log_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    return render_template('logs.html', logs=pagination.items, pagination=pagination)


@routes_bp.route('/predictions')
@login_required
@admin_required
def predictions():
    assessment = combined_assessment()
    forecast = predict_next_24h()
    return render_template('predictions.html', assessment=assessment, forecast=forecast)


# ==================== API ROUTES ====================

@routes_bp.route('/api/predict')
@login_required
def api_predict():
    assessment = combined_assessment()
    return jsonify(assessment)


@routes_bp.route('/api/forecast')
@login_required
def api_forecast():
    forecast = predict_next_24h()
    return jsonify({'forecast': forecast})


@routes_bp.route('/api/enrollment-advice')
@login_required
def api_enrollment_advice():
    advice = enrollment_advice()
    return jsonify(advice)


@routes_bp.route('/api/realtime-forecast')
@login_required
def api_realtime_forecast():
    data = realtime_forecast()
    return jsonify(data)


@routes_bp.route('/api/stats')
@login_required
def api_stats():
    latest_log = SystemLog.query.order_by(SystemLog.log_time.desc()).first()
    if latest_log:
        data = {
            'active_users': latest_log.active_users,
            'cpu_usage': latest_log.cpu_usage,
            'memory_usage': latest_log.memory_usage,
            'response_time': latest_log.response_time,
            'request_count': latest_log.request_count,
            'load_class': latest_log.load_class,
            'timestamp': latest_log.log_time.isoformat() if latest_log.log_time else None
        }
    else:
        data = {}
    return jsonify(data)


# ==================== HELPERS ====================

def _luhn_check(card_number):
    """Validate card number using the Luhn algorithm."""
    card_number = card_number.replace(' ', '').replace('-', '')
    if not card_number.isdigit():
        return False
    if len(card_number) < 13 or len(card_number) > 19:
        return False
    if card_number == '0' * len(card_number):
        return False

    digits = [int(d) for d in card_number]
    digits.reverse()
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0
