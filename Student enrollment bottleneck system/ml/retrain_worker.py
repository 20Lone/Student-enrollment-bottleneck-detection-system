"""
Background ML Retraining Worker.
Periodically retrains Random Forest and LSTM models from live system logs.
Runs as a daemon thread inside the Flask app — never blocks requests.
"""

import time
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


def _count_new_logs(db, SystemLog, since_id):
    """Count log entries newer than since_id."""
    return db.session.query(SystemLog).filter(SystemLog.log_id > since_id).count()


def _get_max_log_id(db, SystemLog):
    """Get the highest log_id in the database."""
    result = db.session.query(db.func.max(SystemLog.log_id)).scalar()
    return result or 0


def _retrain_rf():
    """Retrain Random Forest. Returns True on success."""
    try:
        from ml.random_forest import train_random_forest
        logger.info("Retraining Random Forest...")
        start = time.time()
        train_random_forest()
        elapsed = round(time.time() - start, 1)
        logger.info(f"Random Forest retrained in {elapsed}s")
        return True
    except Exception as e:
        logger.error(f"Random Forest retraining failed: {e}")
        return False


def _retrain_lstm(epochs=20):
    """Retrain LSTM. Returns True on success."""
    try:
        from ml.lstm_model import train_lstm
        logger.info("Retraining LSTM forecaster...")
        start = time.time()
        train_lstm(epochs=epochs, batch_size=64, sequence_length=60)
        elapsed = round(time.time() - start, 1)
        logger.info(f"LSTM retrained in {elapsed}s")
        return True
    except Exception as e:
        logger.error(f"LSTM retraining failed: {e}")
        return False


def retrain_worker(app, interval_minutes=30, min_new_entries=1000, lstm_epochs=20):
    """
    Background worker that retrains ML models periodically.
    Designed to run as a daemon thread.
    """
    with app.app_context():
        from app.models import db, SystemLog
        last_trained_id = _get_max_log_id(db, SystemLog)
        logger.info(
            f"Retrain worker started. Checking every {interval_minutes}min, "
            f"triggers after {min_new_entries} new entries. Last log ID: {last_trained_id}"
        )

    while True:
        time.sleep(interval_minutes * 60)

        try:
            with app.app_context():
                from app.models import db, SystemLog
                current_max_id = _get_max_log_id(db, SystemLog)
                new_count = current_max_id - last_trained_id

                if new_count < min_new_entries:
                    logger.info(
                        f"Retrain check: {new_count} new logs since last training "
                        f"(need {min_new_entries}). Skipping."
                    )
                    continue

                logger.info(
                    f"Retrain triggered: {new_count} new logs "
                    f"(IDs {last_trained_id + 1} to {current_max_id})"
                )

                rf_ok = _retrain_rf()
                lstm_ok = _retrain_lstm(epochs=lstm_epochs)

                if rf_ok or lstm_ok:
                    last_trained_id = current_max_id
                    logger.info(f"Retraining complete. Next check from log ID {last_trained_id}")

        except Exception as e:
            logger.error(f"Retrain worker error: {e}")


def start_retrain_worker(app):
    """Start the retrain worker as a daemon thread."""
    from config import Config
    interval = getattr(Config, 'RETRAIN_INTERVAL_MINUTES', 30)
    min_entries = getattr(Config, 'RETRAIN_MIN_NEW_ENTRIES', 1000)
    lstm_epochs = getattr(Config, 'RETRAIN_LSTM_EPOCHS', 20)

    thread = threading.Thread(
        target=retrain_worker,
        args=(app, interval, min_entries, lstm_epochs),
        daemon=True,
        name="retrain-worker"
    )
    thread.start()
    logger.info("Background retrain worker thread started")
    return thread
