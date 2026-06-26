import os

class Config:
    # Use a local SQLite database file named 'enrollment.db'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-research-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///enrollment.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Bottleneck detection thresholds
    BOTTLENECK_THRESHOLD = 0.65  # Probability threshold for bottleneck alert
    FORECAST_HORIZON = 60        # Minutes ahead to forecast (minute-level granularity)
    LOAD_CLASS_THRESHOLDS = {
        'normal_max_users': 60,
        'normal_max_cpu': 45,
        'normal_max_response': 0.6,
        'moderate_max_users': 150,
        'moderate_max_cpu': 75,
        'moderate_max_response': 2.0
    }

    # Background ML retraining
    RETRAIN_INTERVAL_MINUTES = 5   # How often to check for new data
    RETRAIN_MIN_NEW_ENTRIES = 100  # Min new log entries before retraining
    RETRAIN_LSTM_EPOCHS = 10        # Fewer epochs for background retraining
