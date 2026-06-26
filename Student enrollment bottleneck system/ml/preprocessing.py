"""
Data preprocessing module for ML pipeline.
Loads system logs from SQLite, engineers features, and prepares
 datasets for Random Forest and LSTM models.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'enrollment.db')


def load_system_logs():
    """Load system_logs table into a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM system_logs ORDER BY log_time", conn)
    conn.close()
    df['log_time'] = pd.to_datetime(df['log_time'])
    return df


def engineer_features(df):
    """
    Engineer time-based and interaction features for Random Forest.
    Features: request_count, active_users, cpu_usage, memory_usage, response_time,
              hour_of_day, day_of_week, is_weekend, users_per_request,
              cpu_memory_interaction, minute_of_hour
    """
    df = df.copy()
    df['hour_of_day'] = df['log_time'].dt.hour
    df['minute_of_hour'] = df['log_time'].dt.minute
    df['day_of_week'] = df['log_time'].dt.dayofweek  # 0=Monday
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['users_per_request'] = df['active_users'] / (df['request_count'] + 1)
    df['cpu_memory_interaction'] = df['cpu_usage'] * df['memory_usage'] / 100.0
    return df


def prepare_random_forest_data(test_size=0.30, random_state=42):
    """
    Prepare train/test datasets for Random Forest classifier.
    Returns: X_train, X_test, y_train, y_test, feature_names, scaler
    """
    df = load_system_logs()
    df = engineer_features(df)

    feature_cols = [
        'request_count', 'active_users', 'cpu_usage', 'memory_usage',
        'response_time', 'hour_of_day', 'day_of_week', 'is_weekend',
        'users_per_request', 'cpu_memory_interaction'
    ]

    X = df[feature_cols].values
    y = df['load_class'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, feature_cols, scaler


def prepare_lstm_data(sequence_length=60, forecast_horizon=1):
    """
    Prepare time-series data for LSTM forecasting.
    Uses minute-level data with a 60-step sequence (last 60 minutes).
    Returns: X_train, X_test, y_train, y_test, scalers
    """
    df = load_system_logs()
    df = engineer_features(df)

    # Use minute-level data directly (no resampling needed)
    # Features to predict: request_count and response_time (proxy for load)
    feature_cols = ['request_count', 'active_users', 'cpu_usage', 'memory_usage', 'response_time']
    target_cols = ['request_count', 'response_time']

    # Scale features
    feature_scaler = MinMaxScaler()
    target_scaler = MinMaxScaler()

    scaled_features = feature_scaler.fit_transform(df[feature_cols])
    scaled_targets = target_scaler.fit_transform(df[target_cols])

    # Create sequences
    X, y = [], []
    for i in range(len(scaled_features) - sequence_length - forecast_horizon + 1):
        X.append(scaled_features[i:i + sequence_length])
        y.append(scaled_targets[i + sequence_length:i + sequence_length + forecast_horizon].flatten())

    X = np.array(X)
    y = np.array(y)

    # Train/test split (80/20 chronological)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    return X_train, X_test, y_train, y_test, feature_scaler, target_scaler, feature_cols, target_cols
