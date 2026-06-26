"""
Random Forest Classifier for Bottleneck Detection.
Trains a model to classify system load as Normal (0), Moderate (1), or Bottleneck (2).
"""

import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report)

from ml.preprocessing import prepare_random_forest_data

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, 'rf_bottleneck_classifier.joblib')
SCALER_PATH = os.path.join(MODEL_DIR, 'rf_scaler.joblib')


def train_random_forest(n_estimators=200, max_depth=20, random_state=42):
    """Train and evaluate Random Forest classifier."""
    print("Loading and preprocessing data for Random Forest...")
    X_train, X_test, y_train, y_test, feature_names, scaler = prepare_random_forest_data()

    print(f"Training set size: {len(X_train)}")
    print(f"Test set size: {len(X_test)}")
    print(f"Feature names: {feature_names}")

    print("\nTraining Random Forest classifier...")
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        class_weight='balanced',
        n_jobs=-1
    )
    clf.fit(X_train, y_train)

    # Predictions
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    # Evaluation
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    rec = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

    print("\n=== Random Forest Evaluation ===")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Normal', 'Moderate', 'Bottleneck']))

    # Feature importance
    importances = clf.feature_importances_
    indices = np.argsort(importances)[::-1]
    print("\nFeature Importances:")
    for i in indices:
        print(f"  {feature_names[i]:30s}: {importances[i]:.4f}")

    # Save model and scaler
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")
    print(f"Scaler saved to: {SCALER_PATH}")

    return clf, scaler, acc, prec, rec, f1


def load_model():
    """Load trained Random Forest model and scaler."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run train_random_forest() first.")
    clf = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return clf, scaler


def predict(features_dict):
    """
    Predict load class from a dictionary of features.
    features_dict keys: request_count, active_users, cpu_usage, memory_usage,
                        response_time, hour_of_day, day_of_week, is_weekend,
                        users_per_request, cpu_memory_interaction
    Returns: {'class': int, 'probability': list, 'class_name': str}
    """
    clf, scaler = load_model()
    feature_names = [
        'request_count', 'active_users', 'cpu_usage', 'memory_usage',
        'response_time', 'hour_of_day', 'day_of_week', 'is_weekend',
        'users_per_request', 'cpu_memory_interaction'
    ]
    X = np.array([[features_dict.get(f, 0) for f in feature_names]])
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        X_scaled = scaler.transform(X)
    pred_class = clf.predict(X_scaled)[0]
    proba = clf.predict_proba(X_scaled)[0].tolist()
    class_names = ['Normal', 'Moderate', 'Bottleneck']
    return {
        'class': int(pred_class),
        'probability': proba,
        'class_name': class_names[pred_class],
        'confidence': float(max(proba))
    }


if __name__ == '__main__':
    train_random_forest()
