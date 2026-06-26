import os
import time
import logging
import threading
import warnings
from datetime import datetime
from collections import deque

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
import tensorflow as tf
tf.get_logger().setLevel('ERROR')

import psutil
from flask import Flask, session, g, request as req
from config import Config
from app.models import db

logger = logging.getLogger(__name__)

# Thread-safe request tracking
_lock = threading.Lock()
_active_requests = 0
_request_times = deque(maxlen=600)  # last 600 request timestamps for counting requests/min


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    from app.routes import routes_bp
    app.register_blueprint(routes_bp)

    @app.before_request
    def log_system_activity():
        global _active_requests
        g.start_time = time.time()
        with _lock:
            _active_requests += 1

    @app.after_request
    def record_system_log(response):
        global _active_requests
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time
        else:
            response_time = 0

        with _lock:
            _active_requests = max(0, _active_requests - 1)

        # Skip static files
        path = req.path
        if path.startswith('/static'):
            return response

        try:
            from app.models import SystemLog

            now = datetime.utcnow()

            # Real CPU and memory usage
            cpu_usage = psutil.cpu_percent(interval=0)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent

            # Real active request count
            active_users = _active_requests

            # Count requests in the last 60 seconds
            cutoff = time.time() - 60
            _request_times.append(time.time())
            with _lock:
                request_count = sum(1 for t in _request_times if t >= cutoff)

            # Derived load class from real metrics
            if cpu_usage > 70 or active_users > 130 or response_time > 2.0:
                load_class = 2
            elif cpu_usage > 40 or active_users > 50 or response_time > 0.8:
                load_class = 1
            else:
                load_class = 0

            log_entry = SystemLog(
                request_count=request_count,
                active_users=active_users,
                cpu_usage=round(cpu_usage, 2),
                memory_usage=round(memory_usage, 2),
                response_time=round(response_time, 3),
                log_time=now,
                load_class=load_class
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.warning(f"Failed to log system activity: {e}")
            db.session.rollback()

        return response

    # Start background ML retrain worker
    from ml.retrain_worker import start_retrain_worker
    start_retrain_worker(app)

    return app
