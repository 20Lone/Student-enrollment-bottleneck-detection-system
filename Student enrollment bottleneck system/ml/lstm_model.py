"""
LSTM Time-Series Forecaster for Enrollment Traffic Prediction.
Predicts future request_count and response_time based on historical system logs.
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.metrics import mean_absolute_error, mean_squared_error

from ml.preprocessing import prepare_lstm_data

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, 'lstm_forecaster.keras')
FEATURE_SCALER_PATH = os.path.join(MODEL_DIR, 'lstm_feature_scaler.joblib')
TARGET_SCALER_PATH = os.path.join(MODEL_DIR, 'lstm_target_scaler.joblib')


def build_lstm_model(sequence_length, n_features, n_outputs):
    """Build LSTM model architecture."""
    model = Sequential([
        LSTM(64, activation='tanh', return_sequences=True,
             input_shape=(sequence_length, n_features)),
        Dropout(0.2),
        LSTM(32, activation='tanh', return_sequences=False),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dense(n_outputs)
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model


def train_lstm(epochs=80, batch_size=8, sequence_length=24):
    """Train and evaluate LSTM forecaster."""
    print("Loading and preprocessing data for LSTM...")
    X_train, X_test, y_train, y_test, feature_scaler, target_scaler, feature_cols, target_cols = prepare_lstm_data(
        sequence_length=sequence_length
    )

    print(f"Sequence length: {sequence_length}")
    print(f"Feature columns: {feature_cols}")
    print(f"Target columns: {target_cols}")
    print(f"Training sequences: {len(X_train)}")
    print(f"Test sequences: {len(X_test)}")

    n_features = X_train.shape[2]
    n_outputs = y_train.shape[1]

    model = build_lstm_model(sequence_length, n_features, n_outputs)
    model.summary()

    # Callbacks
    early_stop = keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=15, restore_best_weights=True
    )
    reduce_lr = keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6
    )

    print("\nTraining LSTM model...")
    history = model.fit(
        X_train, y_train,
        validation_split=0.2,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop, reduce_lr],
        verbose=1
    )

    # Evaluation
    y_pred = model.predict(X_test)

    # Inverse transform for interpretable metrics
    y_test_inv = target_scaler.inverse_transform(y_test)
    y_pred_inv = target_scaler.inverse_transform(y_pred)

    mae = mean_absolute_error(y_test_inv, y_pred_inv, multioutput='raw_values')
    rmse = np.sqrt(mean_squared_error(y_test_inv, y_pred_inv, multioutput='raw_values'))

    print("\n=== LSTM Evaluation ===")
    for i, col in enumerate(target_cols):
        print(f"{col} - MAE: {mae[i]:.4f}, RMSE: {rmse[i]:.4f}")

    # Save model and scalers
    model.save(MODEL_PATH)
    import joblib
    joblib.dump(feature_scaler, FEATURE_SCALER_PATH)
    joblib.dump(target_scaler, TARGET_SCALER_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")

    return model, feature_scaler, target_scaler, history


def load_model():
    """Load trained LSTM model and scalers."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run train_lstm() first.")
    model = keras.models.load_model(MODEL_PATH, compile=False)
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    import joblib
    feature_scaler = joblib.load(FEATURE_SCALER_PATH)
    target_scaler = joblib.load(TARGET_SCALER_PATH)
    return model, feature_scaler, target_scaler


def forecast(history_sequence):
    """
    Forecast next hour's request_count and response_time.
    history_sequence: numpy array of shape (sequence_length, n_features)
    Returns: dict with predicted values
    """
    model, feature_scaler, target_scaler = load_model()
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        seq_scaled = feature_scaler.transform(history_sequence)
    X = np.array([seq_scaled])
    pred_scaled = model.predict(X, verbose=0)
    pred = target_scaler.inverse_transform(pred_scaled)[0]
    return {
        'predicted_request_count': float(pred[0]),
        'predicted_response_time': float(pred[1])
    }


if __name__ == '__main__':
    train_lstm()
