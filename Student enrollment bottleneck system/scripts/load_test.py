#!/usr/bin/env python3
"""
Load Simulation Script for Enrollment System.
Simulates real user actions (register, login, enroll, pay) against a running Flask server.
Generates realistic system load for testing bottleneck detection.

Usage:
    python scripts/load_test.py --users 100 --concurrent 10 --scenario mixed

Prerequisites:
    Flask server must be running: flask run --port 5000
"""

import argparse
import random
import string
import time
import sys
import os
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from threading import Lock

import requests

# Luhn-valid test card numbers
LUHN_CARDS = [
    '4111111111111111',
    '5500000000000004',
    '6011000000000004',
    '4012888888881881',
    '378282246310005',
]

DEPARTMENTS = [
    'Computer Science', 'Electrical Engineering', 'Mechanical Engineering',
    'Civil Engineering', 'Mathematics', 'Physics', 'Chemistry', 'Biology',
    'Economics', 'Business Administration', 'Law', 'Medicine'
]
LEVELS = ['100', '200', '300', '400', '500']


@dataclass
class TestResult:
    success: int = 0
    failure: int = 0
    response_times: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    users_created: list = field(default_factory=list)
    lock: Lock = field(default_factory=Lock)


def generate_email(index):
    return f'loadtest_{index:04d}@university.edu'


def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


def register_user(session, base_url, index, result):
    """Register a new student. Returns (email, password) on success."""
    email = generate_email(index)
    password = generate_password()

    data = {
        'full_name': f'Load Test User {index}',
        'email': email,
        'phone': f'+234{random.randint(7000000000, 8099999999)}',
        'department': random.choice(DEPARTMENTS),
        'level': random.choice(LEVELS),
        'password': password,
        'confirm_password': password,
    }

    start = time.time()
    try:
        resp = session.post(f'{base_url}/register', data=data, allow_redirects=True, timeout=10)
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            if resp.status_code == 200 and 'Welcome' in resp.text:
                result.success += 1
                result.users_created.append(email)
                return email, password
            else:
                result.failure += 1
                result.errors.append(f'Register failed: {resp.status_code}')
                return None, None
    except Exception as e:
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            result.failure += 1
            result.errors.append(f'Register error: {e}')
        return None, None


def login_user(session, base_url, email, password, result):
    """Login with existing credentials."""
    data = {'email': email, 'password': password}
    start = time.time()
    try:
        resp = session.post(f'{base_url}/login', data=data, allow_redirects=True, timeout=10)
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            if resp.status_code == 200 and 'Welcome' in resp.text:
                result.success += 1
                return True
            else:
                result.failure += 1
                result.errors.append(f'Login failed for {email}: {resp.status_code}')
                return False
    except Exception as e:
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            result.failure += 1
            result.errors.append(f'Login error: {e}')
        return False


def browse_courses(session, base_url, result):
    """GET /courses."""
    start = time.time()
    try:
        resp = session.get(f'{base_url}/courses', timeout=10)
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            if resp.status_code == 200:
                result.success += 1
                return True
            else:
                result.failure += 1
                return False
    except Exception as e:
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            result.failure += 1
            result.errors.append(f'Browse error: {e}')
        return False


def enroll_course(session, base_url, result):
    """Enroll in a random course. Returns enrollment_id or None."""
    start = time.time()
    try:
        resp = session.get(f'{base_url}/enrollments/new', timeout=10)
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)

        if resp.status_code != 200:
            with result.lock:
                result.failure += 1
            return None

        # Parse course options from HTML
        import re
        options = re.findall(r'<option value="(\d+)">', resp.text)
        if not options:
            with result.lock:
                result.failure += 1
            return None

        course_id = random.choice(options)

        start = time.time()
        resp = session.post(
            f'{base_url}/enrollments/new',
            data={'course_id': course_id},
            allow_redirects=True,
            timeout=10
        )
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            if resp.status_code == 200:
                result.success += 1
                # Extract enrollment_id from redirect or response
                match = re.search(r'enrollment_id=(\d+)', resp.url + resp.text)
                if match:
                    return int(match.group(1))
                # Try to find it in the flash message or page
                match = re.search(r'Enrollment #?(\d+)', resp.text)
                if match:
                    return int(match.group(1))
                return 0  # enrollment happened but we couldn't get the ID
            else:
                result.failure += 1
                return None
    except Exception as e:
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            result.failure += 1
            result.errors.append(f'Enroll error: {e}')
        return None


def pay_enrollment(session, base_url, enrollment_id, result):
    """Submit payment for an enrollment."""
    if not enrollment_id:
        return False

    card = random.choice(LUHN_CARDS)
    data = {
        'enrollment_id': enrollment_id,
        'card_number': card,
        'card_name': 'LOAD TEST USER',
        'card_expiry': '12/28',
        'card_cvv': '123',
    }

    start = time.time()
    try:
        resp = session.post(
            f'{base_url}/payments/new',
            data=data,
            allow_redirects=True,
            timeout=15
        )
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            if resp.status_code == 200:
                result.success += 1
                return True
            else:
                result.failure += 1
                result.errors.append(f'Payment failed: {resp.status_code}')
                return False
    except Exception as e:
        elapsed = time.time() - start
        with result.lock:
            result.response_times.append(elapsed)
            result.failure += 1
            result.errors.append(f'Payment error: {e}')
        return False


def logout_user(session, base_url):
    """Logout."""
    try:
        session.get(f'{base_url}/logout', timeout=5)
    except Exception:
        pass


def run_user_session(base_url, user_index, scenario, result):
    """Run a single user session based on the scenario."""
    s = requests.Session()

    try:
        if scenario == 'register':
            email, password = register_user(s, base_url, user_index, result)
            if email:
                login_user(s, base_url, email, password, result)
                browse_courses(s, base_url, result)

        elif scenario == 'enroll':
            email, password = register_user(s, base_url, user_index, result)
            if email:
                login_user(s, base_url, email, password, result)
                browse_courses(s, base_url, result)
                enroll_course(s, base_url, result)

        elif scenario == 'pay':
            email, password = register_user(s, base_url, user_index, result)
            if email:
                login_user(s, base_url, email, password, result)
                eid = enroll_course(s, base_url, result)
                if eid is not None:
                    pay_enrollment(s, base_url, eid, result)

        elif scenario == 'mixed':
            email, password = register_user(s, base_url, user_index, result)
            if email:
                login_user(s, base_url, email, password, result)
                browse_courses(s, base_url, result)
                # 70% enroll, 50% of those also pay
                if random.random() < 0.70:
                    eid = enroll_course(s, base_url, result)
                    if eid is not None and random.random() < 0.50:
                        pay_enrollment(s, base_url, eid, result)

        elif scenario == 'bottleneck':
            email, password = register_user(s, base_url, user_index, result)
            if email:
                login_user(s, base_url, email, password, result)
                # Everyone enrolls and pays
                eid = enroll_course(s, base_url, result)
                if eid is not None:
                    pay_enrollment(s, base_url, eid, result)

    except Exception as e:
        with result.lock:
            result.errors.append(f'Session error for user {user_index}: {e}')


def cleanup_test_users(base_url, users_created):
    """Delete all test-created students and their data."""
    if not users_created:
        return

    print(f'\nCleaning up {len(users_created)} test users...')

    # We need to use the Flask app context to delete directly
    # Add a script that imports the app and deletes test users
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from app import create_app
    from app.models import db, Student, Enrollment, Payment

    app = create_app()
    deleted = 0

    with app.app_context():
        for email in users_created:
            student = Student.query.filter_by(email=email).first()
            if student:
                # Delete payments first
                Payment.query.filter_by(student_id=student.student_id).delete()
                # Delete enrollments
                Enrollment.query.filter_by(student_id=student.student_id).delete()
                # Delete student
                db.session.delete(student)
                deleted += 1
        db.session.commit()

    print(f'Cleaned up {deleted} test users.')


def parse_args():
    parser = argparse.ArgumentParser(
        description='Load test the Enrollment System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  register  - Register new students only
  enroll    - Register, login, browse courses, enroll
  pay       - Register, login, enroll, pay
  mixed     - Mix of all actions (realistic usage)
  bottleneck - All users hit enroll+pay simultaneously

Examples:
  python scripts/load_test.py --users 50 --concurrent 5
  python scripts/load_test.py --users 200 --concurrent 20 --scenario bottleneck
  python scripts/load_test.py --users 100 --scenario mixed --no-cleanup
        """
    )
    parser.add_argument('--users', type=int, default=50, help='Number of virtual users (default: 50)')
    parser.add_argument('--concurrent', type=int, default=10, help='Max concurrent workers (default: 10)')
    parser.add_argument('--scenario', choices=['register', 'enroll', 'pay', 'mixed', 'bottleneck'],
                        default='mixed', help='Simulation scenario (default: mixed)')
    parser.add_argument('--base-url', default='http://127.0.0.1:5000', help='Flask server URL')
    parser.add_argument('--no-cleanup', action='store_true', help='Skip deleting test users after')
    return parser.parse_args()


def main():
    args = parse_args()

    print(f'=== Enrollment System Load Test ===')
    print(f'Server:     {args.base_url}')
    print(f'Users:      {args.users}')
    print(f'Concurrent: {args.concurrent}')
    print(f'Scenario:   {args.scenario}')
    print()

    # Verify server is reachable
    try:
        resp = requests.get(f'{args.base_url}/login', timeout=5)
        if resp.status_code != 200:
            print(f'ERROR: Server returned {resp.status_code} on /login')
            sys.exit(1)
    except requests.ConnectionError:
        print(f'ERROR: Cannot connect to {args.base_url}')
        print('Make sure the Flask server is running: flask run --port 5000')
        sys.exit(1)

    result = TestResult()
    start_time = time.time()

    print(f'Running {args.users} users with {args.concurrent} concurrent workers...')
    print()

    with ThreadPoolExecutor(max_workers=args.concurrent) as executor:
        futures = {}
        for i in range(1, args.users + 1):
            future = executor.submit(run_user_session, args.base_url, i, args.scenario, result)
            futures[future] = i

        completed = 0
        for future in as_completed(futures):
            completed += 1
            user_id = futures[future]
            try:
                future.result()
            except Exception as e:
                with result.lock:
                    result.errors.append(f'Worker {user_id} crashed: {e}')

            # Progress update every 10 users
            if completed % 10 == 0 or completed == args.users:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(f'  [{completed}/{args.users}] users done | {rate:.1f} users/s | '
                      f'{result.success} ok / {result.failure} fail')

    total_time = time.time() - start_time

    # Print summary
    print(f'\n=== Load Test Results ===')
    print(f'Duration:        {total_time:.1f}s')
    print(f'Users completed: {args.users}')
    print(f'Total requests:  {result.success + result.failure}')
    print(f'Successful:      {result.success}')
    print(f'Failed:          {result.failure}')
    if result.errors:
        error_rate = len(set(result.errors))  # unique errors
        print(f'Unique errors:   {error_rate}')
        for err in list(set(result.errors))[:5]:
            print(f'  - {err}')
    if result.response_times:
        print(f'Avg response:    {statistics.mean(result.response_times):.3f}s')
        print(f'Median response: {statistics.median(result.response_times):.3f}s')
        if len(result.response_times) >= 2:
            sorted_times = sorted(result.response_times)
            p95_idx = int(len(sorted_times) * 0.95)
            print(f'P95 response:    {sorted_times[p95_idx]:.3f}s')
            print(f'Max response:    {max(sorted_times):.3f}s')
    print(f'Users created:   {len(result.users_created)}')

    # Cleanup
    if not args.no_cleanup and result.users_created:
        cleanup_test_users(args.base_url, result.users_created)
    elif args.no_cleanup:
        print(f'\nSkipping cleanup. {len(result.users_created)} test users remain in database.')
        print(f'Run with --no-cleanup removed to auto-delete, or manually clean up.')


if __name__ == '__main__':
    main()
