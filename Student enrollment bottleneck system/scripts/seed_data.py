#!/usr/bin/env python3
"""
Seed script for Student Enrollment Bottleneck Detection System.
Generates realistic synthetic data for all 6 tables with engineered
bottleneck patterns to train ML models.
"""

import random
import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, Student, Course, Enrollment, Payment, SystemLog, Admin

random.seed(42)

DEPARTMENTS = ['Computer Science', 'Electrical Engineering', 'Mechanical Engineering',
               'Civil Engineering', 'Mathematics', 'Physics', 'Chemistry', 'Biology',
               'Economics', 'Business Administration', 'Law', 'Medicine']

LEVELS = ['100', '200', '300', '400', '500']

COURSE_PREFIXES = {
    'Computer Science': 'CSC',
    'Electrical Engineering': 'EEE',
    'Mechanical Engineering': 'MEE',
    'Civil Engineering': 'CVE',
    'Mathematics': 'MTH',
    'Physics': 'PHY',
    'Chemistry': 'CHM',
    'Biology': 'BIO',
    'Economics': 'ECO',
    'Business Administration': 'BUS',
    'Law': 'LAW',
    'Medicine': 'MED'
}

COURSE_TITLES = [
    'Introduction to Programming', 'Data Structures', 'Algorithms',
    'Database Systems', 'Computer Networks', 'Operating Systems',
    'Software Engineering', 'Machine Learning', 'Artificial Intelligence',
    'Circuit Analysis', 'Digital Electronics', 'Power Systems',
    'Thermodynamics', 'Fluid Mechanics', 'Strength of Materials',
    'Structural Analysis', 'Transportation Engineering', 'Geotechnics',
    'Calculus I', 'Linear Algebra', 'Differential Equations',
    'Probability & Statistics', 'Classical Mechanics', 'Quantum Physics',
    'Organic Chemistry', 'Inorganic Chemistry', 'Physical Chemistry',
    'Genetics', 'Microbiology', 'Ecology',
    'Microeconomics', 'Macroeconomics', 'Econometrics',
    'Financial Accounting', 'Marketing', 'Organizational Behavior',
    'Constitutional Law', 'Criminal Law', 'Contract Law',
    'Anatomy', 'Physiology', 'Pathology'
]

FEE_AMOUNTS = [50000, 75000, 100000, 125000, 150000]


def generate_courses():
    courses = []
    used_codes = set()
    for i, title in enumerate(COURSE_TITLES):
        dept = random.choice(DEPARTMENTS)
        prefix = COURSE_PREFIXES[dept]
        code_num = random.randint(101, 599)
        code = f"{prefix}{code_num}"
        while code in used_codes:
            code_num = random.randint(101, 599)
            code = f"{prefix}{code_num}"
        used_codes.add(code)
        capacity = random.choice([30, 50, 75, 100, 150, 200])
        courses.append(Course(
            course_code=code,
            course_title=title,
            max_capacity=capacity,
            enrolled_count=0,
            fee_amount=random.choice(FEE_AMOUNTS)
        ))
    return courses


def generate_students(n=500):
    students = []
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer',
                   'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara',
                   'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah',
                   'Charles', 'Karen', 'Daniel', 'Nancy', 'Matthew', 'Lisa',
                   'Anthony', 'Betty', 'Mark', 'Margaret', 'Donald', 'Sandra',
                   'Steven', 'Ashley', 'Paul', 'Kimberly', 'Andrew', 'Emily',
                   'Joshua', 'Donna', 'Kenneth', 'Michelle', 'Kevin', 'Dorothy',
                   'Brian', 'Carol', 'George', 'Amanda', 'Edward', 'Melissa',
                   'Ronald', 'Deborah', 'Timothy', 'Stephanie', 'Jason', 'Rebecca',
                   'Jeffrey', 'Sharon', 'Ryan', 'Laura', 'Jacob', 'Cynthia',
                   'Gary', 'Kathleen', 'Nicholas', 'Amy', 'Eric', 'Angela',
                   'Jonathan', 'Shirley', 'Stephen', 'Anna', 'Larry', 'Brenda',
                   'Justin', 'Pamela', 'Scott', 'Emma', 'Brandon', 'Nicole',
                   'Benjamin', 'Helen', 'Samuel', 'Samantha', 'Gregory', 'Katherine',
                   'Frank', 'Christine', 'Alexander', 'Debra', 'Raymond', 'Rachel',
                   'Patrick', 'Catherine', 'Jack', 'Carolyn', 'Dennis', 'Janet',
                   'Jerry', 'Ruth', 'Tyler', 'Maria']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia',
                  'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez',
                  'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore',
                  'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson', 'White',
                  'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson',
                  'Walker', 'Young', 'Allen', 'King', 'Wright', 'Scott',
                  'Torres', 'Nguyen', 'Hill', 'Flores', 'Green', 'Adams',
                  'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell',
                  'Carter', 'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner',
                  'Diaz', 'Parker', 'Cruz', 'Edwards', 'Collins', 'Reyes',
                  'Stewart', 'Morris', 'Morales', 'Murphy', 'Cook', 'Rogers',
                  'Gutierrez', 'Ortiz', 'Morgan', 'Cooper', 'Peterson', 'Bailey',
                  'Reed', 'Kelly', 'Howard', 'Ramos', 'Kim', 'Cox',
                  'Ward', 'Richardson', 'Watson', 'Brooks', 'Chavez', 'Wood',
                  'James', 'Bennett', 'Gray', 'Mendoza', 'Ruiz', 'Hughes',
                  'Price', 'Alvarez', 'Castillo', 'Sanders', 'Patel', 'Myers']

    for i in range(n):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        full_name = f"{fname} {lname}"
        email = f"student{i+1:04d}@university.edu"
        phone = f"+234{random.randint(7000000000, 8099999999)}"
        dept = random.choice(DEPARTMENTS)
        level = random.choice(LEVELS)
        students.append(Student(
            full_name=full_name,
            email=email,
            phone=phone,
            department=dept,
            level=level,
            password_hash=generate_password_hash('password123')
        ))
    return students


def generate_enrollments(students, courses, n=2500):
    enrollments = []
    used_pairs = set()
    statuses = ['Pending', 'Approved', 'Failed']
    weights = [0.15, 0.80, 0.05]

    start_date = datetime.now() - timedelta(days=90)

    for _ in range(n):
        s = random.choice(students)
        c = random.choice(courses)
        pair = (s.student_id, c.course_id)
        if pair in used_pairs:
            continue
        used_pairs.add(pair)
        status = random.choices(statuses, weights=weights)[0]
        time = start_date + timedelta(
            days=random.randint(0, 90),
            hours=random.randint(7, 18),
            minutes=random.randint(0, 59)
        )
        enrollments.append(Enrollment(
            student_id=s.student_id,
            course_id=c.course_id,
            enrollment_status=status,
            enrollment_time=time
        ))
        if status == 'Approved':
            c.enrolled_count += 1
    return enrollments


def generate_payments(students, enrollments):
    """
    Generate payments linked to enrollments.
    Each approved enrollment has a corresponding successful payment.
    Some failed/pending enrollments may have payments too.
    """
    payments = []
    enrollment_map = {}
    for e in enrollments:
        key = (e.student_id, e.course_id)
        if key not in enrollment_map:
            enrollment_map[key] = e

    for e in enrollments:
        if e.enrollment_status == 'Failed':
            continue
        course = Course.query.get(e.course_id)
        fee = float(course.fee_amount) if course else 50000
        status = 'Successful' if e.enrollment_status == 'Approved' else 'Pending'
        payments.append(Payment(
            student_id=e.student_id,
            enrollment_id=e.enrollment_id,
            amount=fee,
            payment_status=status,
            payment_time=e.enrollment_time + timedelta(minutes=random.randint(1, 15))
        ))

    extra_payments = []
    for _ in range(300):
        s = random.choice(students)
        amount = random.choice(FEE_AMOUNTS)
        status = random.choices(['Successful', 'Failed', 'Pending'], weights=[0.6, 0.3, 0.1])[0]
        start_date = datetime.now() - timedelta(days=90)
        extra_payments.append(Payment(
            student_id=s.student_id,
            enrollment_id=None,
            amount=amount,
            payment_status=status,
            payment_time=start_date + timedelta(
                days=random.randint(0, 90),
                hours=random.randint(7, 18),
                minutes=random.randint(0, 59)
            )
        ))
    payments.extend(extra_payments)
    return payments


def generate_system_logs(n_minutes=65520):
    """
    Generate minute-level system logs with realistic patterns.
    65520 minutes = 45.5 days of data.
    Peak periods: 8-11am and 2-4pm on weekdays have higher load.
    Bottlenecks are engineered around registration deadlines.
    """
    logs = []
    end_time = datetime.now().replace(second=0, microsecond=0)
    start_time = end_time - timedelta(minutes=n_minutes)

    deadline_weeks = [
        (start_time + timedelta(days=5), start_time + timedelta(days=8)),
        (start_time + timedelta(days=20), start_time + timedelta(days=23)),
        (start_time + timedelta(days=35), start_time + timedelta(days=38)),
    ]

    current = start_time
    minute_count = 0

    while current <= end_time:
        hour = current.hour
        weekday = current.weekday()
        minute_of_hour = current.minute

        is_peak_hour = (8 <= hour <= 11) or (14 <= hour <= 16)
        is_weekday = weekday < 5
        is_deadline = any(start <= current <= end for start, end in deadline_weeks)

        # Within an hour, minutes 0-5 and 50-59 have slightly higher load
        in_peak_minute = minute_of_hour <= 5 or minute_of_hour >= 50

        if is_deadline and is_peak_hour and in_peak_minute:
            p_normal, p_moderate, p_bottleneck = 0.05, 0.25, 0.70
        elif is_deadline and is_peak_hour:
            p_normal, p_moderate, p_bottleneck = 0.10, 0.30, 0.60
        elif is_deadline:
            p_normal, p_moderate, p_bottleneck = 0.25, 0.45, 0.30
        elif is_peak_hour and is_weekday and in_peak_minute:
            p_normal, p_moderate, p_bottleneck = 0.30, 0.50, 0.20
        elif is_peak_hour and is_weekday:
            p_normal, p_moderate, p_bottleneck = 0.40, 0.45, 0.15
        elif is_weekday:
            p_normal, p_moderate, p_bottleneck = 0.65, 0.30, 0.05
        else:
            p_normal, p_moderate, p_bottleneck = 0.80, 0.18, 0.02

        load_class = random.choices([0, 1, 2], weights=[p_normal, p_moderate, p_bottleneck])[0]

        if load_class == 0:
            active_users = random.randint(5, 55)
            cpu_usage = random.uniform(8, 42)
            memory_usage = random.uniform(18, 50)
            response_time = random.uniform(0.05, 0.55)
            request_count = random.randint(20, 300)
        elif load_class == 1:
            active_users = random.randint(50, 140)
            cpu_usage = random.uniform(40, 72)
            memory_usage = random.uniform(48, 78)
            response_time = random.uniform(0.50, 1.8)
            request_count = random.randint(250, 900)
        else:
            active_users = random.randint(130, 420)
            cpu_usage = random.uniform(70, 96)
            memory_usage = random.uniform(75, 96)
            response_time = random.uniform(1.5, 6.0)
            request_count = random.randint(800, 3500)

        logs.append(SystemLog(
            request_count=request_count,
            active_users=active_users,
            cpu_usage=round(cpu_usage, 2),
            memory_usage=round(memory_usage, 2),
            response_time=round(response_time, 3),
            log_time=current,
            load_class=load_class
        ))

        current += timedelta(minutes=1)
        minute_count += 1

        if minute_count % 10000 == 0:
            print(f"  Generated {minute_count} log entries...")

    return logs


def seed():
    app = create_app()
    with app.app_context():
        print("Dropping and recreating all tables...")
        db.drop_all()
        db.create_all()
        print("Tables created successfully.")

        print("Generating courses...")
        courses = generate_courses()
        db.session.add_all(courses)
        db.session.commit()
        print(f"Inserted {len(courses)} courses.")

        print("Generating students...")
        students = generate_students(500)
        db.session.add_all(students)
        db.session.commit()
        print(f"Inserted {len(students)} students.")

        print("Generating enrollments...")
        enrollments = generate_enrollments(students, courses, 2500)
        db.session.add_all(enrollments)
        db.session.commit()
        print(f"Inserted {len(enrollments)} enrollments.")

        print("Generating payments linked to enrollments...")
        payments = generate_payments(students, enrollments)
        db.session.add_all(payments)
        db.session.commit()
        print(f"Inserted {len(payments)} payments.")

        print("Generating minute-level system logs (~45 days)...")
        logs = generate_system_logs()
        db.session.add_all(logs)
        db.session.commit()
        print(f"Inserted {len(logs)} system logs.")

        print("Creating default admin account...")
        admin = Admin(
            name='System Administrator',
            email='admin@university.edu',
            password_hash=generate_password_hash('admin123'),
            role='superadmin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Default admin created: admin@university.edu / admin123")

        print("\n=== SEED COMPLETE ===")
        print(f"Students: {Student.query.count()}")
        print(f"Courses: {Course.query.count()}")
        print(f"Enrollments: {Enrollment.query.count()}")
        print(f"Payments: {Payment.query.count()}")
        print(f"System Logs: {SystemLog.query.count()}")
        print(f"Admins: {Admin.query.count()}")

        total_logs = len(logs)
        normal = SystemLog.query.filter_by(load_class=0).count()
        moderate = SystemLog.query.filter_by(load_class=1).count()
        bottleneck = SystemLog.query.filter_by(load_class=2).count()
        print(f"\nLoad Distribution:")
        print(f"  Normal: {normal} ({normal/total_logs*100:.1f}%)")
        print(f"  Moderate: {moderate} ({moderate/total_logs*100:.1f}%)")
        print(f"  Bottleneck: {bottleneck} ({bottleneck/total_logs*100:.1f}%)")


if __name__ == '__main__':
    seed()
