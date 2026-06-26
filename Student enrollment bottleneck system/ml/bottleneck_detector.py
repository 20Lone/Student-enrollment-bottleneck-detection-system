"""
Decision Engine: Combines Random Forest classification and LSTM forecasting
to generate bottleneck assessments and recommendations.
"""

import os
import sys
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ml.random_forest import predict as rf_predict
from ml.lstm_model import forecast as lstm_forecast
from ml.preprocessing import load_system_logs, engineer_features

BOTTLENECK_PROB_THRESHOLD = 0.65
REQUEST_COUNT_THRESHOLD = 800
RESPONSE_TIME_THRESHOLD = 1.5

# Training data baseline ratios (from actual bottleneck patterns)
# Normal: reqs~159, users~30, cpu~25%, mem~34%, resp~0.3s
# Moderate: reqs~569, users~94, cpu~56%, mem~63%, resp~1.1s
# Bottleneck: reqs~2003, users~257, cpu~79%, mem~85%, resp~4.2s
# Used to estimate features when only request_count is known from LSTM
_ESTIMATE_RATIOS = {
    'users_per_req': 0.128,      # ~257/2003
    'cpu_base': 20.0,            # baseline cpu at low load
    'cpu_scale': 0.030,          # cpu增长 per req
    'mem_base': 30.0,            # baseline mem at low load
    'mem_scale': 0.028,          # mem增长 per req
}


def _estimate_features_from_request_count(pred_rc, pred_rt, forecast_time, current):
    """
    Estimate all RF features from predicted request_count.
    The RF model learned that bottleneck requires elevated values across ALL features,
    so we estimate cpu/memory/users proportionally from request_count.
    """
    est_users = max(0, pred_rc * _ESTIMATE_RATIOS['users_per_req'])
    est_cpu = min(100, _ESTIMATE_RATIOS['cpu_base'] + pred_rc * _ESTIMATE_RATIOS['cpu_scale'])
    est_mem = min(100, _ESTIMATE_RATIOS['mem_base'] + pred_rc * _ESTIMATE_RATIOS['mem_scale'])

    return {
        'request_count': pred_rc,
        'active_users': est_users,
        'cpu_usage': est_cpu,
        'memory_usage': est_mem,
        'response_time': pred_rt,
        'hour_of_day': forecast_time.hour,
        'day_of_week': forecast_time.weekday(),
        'is_weekend': 1 if forecast_time.weekday() >= 5 else 0,
        'users_per_request': est_users / max(pred_rc, 1),
        'cpu_memory_interaction': est_cpu * est_mem / 100,
    }


def _convert(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}
    return obj


def get_current_metrics():
    df = load_system_logs()
    if df.empty:
        return None
    df = engineer_features(df)
    latest = df.iloc[-1]
    return {
        'request_count': latest['request_count'],
        'active_users': latest['active_users'],
        'cpu_usage': latest['cpu_usage'],
        'memory_usage': latest['memory_usage'],
        'response_time': latest['response_time'],
        'hour_of_day': latest['hour_of_day'],
        'day_of_week': latest['day_of_week'],
        'is_weekend': latest['is_weekend'],
        'users_per_request': latest['users_per_request'],
        'cpu_memory_interaction': latest['cpu_memory_interaction'],
    }


def get_history_sequence(sequence_length=60):
    df = load_system_logs()
    if len(df) < sequence_length:
        return None
    df = engineer_features(df)
    feature_cols = ['request_count', 'active_users', 'cpu_usage', 'memory_usage', 'response_time']
    recent = df[feature_cols].iloc[-sequence_length:].values
    return recent


def combined_assessment():
    current = get_current_metrics()
    if current is None:
        return {
            'status': 'Unknown',
            'status_color': 'gray',
            'message': 'No system log data available.',
            'rf_result': None,
            'lstm_result': None,
            'recommendation': 'Please ensure the system logging module is active.'
        }

    rf_result = rf_predict(current)
    rf_class = rf_result['class']
    rf_prob = rf_result['confidence']

    history = get_history_sequence()
    lstm_result = None
    if history is not None:
        try:
            lstm_result = lstm_forecast(history)
        except Exception as e:
            lstm_result = {'error': str(e)}

    predicted_request_count = lstm_result.get('predicted_request_count', 0) if lstm_result else 0
    predicted_response_time = lstm_result.get('predicted_response_time', 0) if lstm_result else 0

    bottleneck_likely = False
    if rf_class == 2 and rf_prob >= BOTTLENECK_PROB_THRESHOLD:
        bottleneck_likely = True
    if lstm_result and predicted_request_count > REQUEST_COUNT_THRESHOLD:
        bottleneck_likely = True
    if lstm_result and predicted_response_time > RESPONSE_TIME_THRESHOLD:
        bottleneck_likely = True

    if rf_class == 2 or bottleneck_likely:
        status = 'Critical'
        status_color = 'red'
        recommendation = (
            "Bottleneck detected or highly likely. "
            "Scale up server instances, enable load balancing, "
            "prioritize critical requests, and notify students of potential delays."
        )
    elif rf_class == 1 or (lstm_result and predicted_request_count > REQUEST_COUNT_THRESHOLD * 0.6):
        status = 'Warning'
        status_color = 'orange'
        recommendation = (
            "System load is moderate to high. "
            "Monitor closely, prepare additional resources, "
            "alert on-call administrator."
        )
    else:
        status = 'Normal'
        status_color = 'green'
        recommendation = "System operating within normal parameters. No action required."

    return {
        'status': status,
        'status_color': status_color,
        'rf_result': _convert(rf_result),
        'lstm_result': _convert(lstm_result),
        'current_metrics': _convert(current),
        'predicted_request_count': float(round(predicted_request_count, 1)),
        'predicted_response_time': float(round(predicted_response_time, 3)),
        'bottleneck_probability': float(round(rf_prob, 4)),
        'recommendation': recommendation,
        'timestamp': datetime.utcnow().isoformat()
    }


def enrollment_advice():
    """
    Student-facing traffic light system.
    Returns simple go/wait/stop advice with helpful messages.
    """
    current = get_current_metrics()
    if current is None:
        return {
            'status': 'wait',
            'message': 'System data unavailable. Please try again shortly.',
            'recommendation': 'Try again in a few minutes.'
        }

    history = get_history_sequence()
    lstm_result = None
    if history is not None:
        try:
            lstm_result = lstm_forecast(history)
        except Exception:
            pass

    predicted_requests = lstm_result.get('predicted_request_count', current['request_count']) if lstm_result else current['request_count']
    current_requests = current['request_count']

    if current_requests > 800 or predicted_requests > 1000:
        status = 'stop'
        message = 'The system is very busy right now. Enrollment may be slow or fail.'
        recommendation = 'Please try again in 30-60 minutes when the system is less crowded.'
    elif current_requests > 400 or predicted_requests > 600:
        status = 'wait'
        message = 'The system is a bit busy right now. You can try, but expect some delays.'
        recommendation = 'For the best experience, try again in 15-30 minutes.'
    else:
        status = 'go'
        message = 'Everything looks good! Now is a great time to enroll.'
        recommendation = 'Go ahead and complete your enrollment.'

    return {
        'status': status,
        'message': message,
        'recommendation': recommendation
    }


def realtime_forecast():
    """
    Real-time forecast for AJAX polling.
    Returns current state + 60-minute history + 60-minute LSTM forecast.
    """
    df = load_system_logs()
    if df.empty:
        return {'error': 'No data available'}

    df = engineer_features(df)
    latest = df.iloc[-1]

    # Current metrics
    current = {
        'request_count': int(latest['request_count']),
        'active_users': int(latest['active_users']),
        'cpu_usage': round(float(latest['cpu_usage']), 1),
        'memory_usage': round(float(latest['memory_usage']), 1),
        'response_time': round(float(latest['response_time']), 3),
    }

    # RF classification
    rf_result = rf_predict(current)

    # Enrollment advice
    advice = enrollment_advice()

    # Last 60 minutes of actual data for the chart
    feature_cols = ['request_count', 'active_users', 'cpu_usage', 'memory_usage', 'response_time']
    history_60 = df[['log_time'] + feature_cols].tail(60).to_dict('records')
    for row in history_60:
        row['log_time'] = row['log_time'].isoformat()
        for k in feature_cols:
            row[k] = round(float(row[k]), 2)

    # LSTM forecast for next 60 minutes + RF classification per point
    # Also compute recent trend to blend with LSTM predictions
    recent_60 = df.tail(60)
    avg_response_time = float(recent_60['response_time'].mean())
    avg_request_count = float(recent_60['request_count'].mean())
    bottleneck_count = int((recent_60['load_class'] == 2).sum())
    moderate_count = int((recent_60['load_class'] == 1).sum())
    trend_bottleneck = bottleneck_count >= 5 or avg_response_time > 1.5
    trend_moderate = (bottleneck_count + moderate_count) >= 10

    # Use elevated entries for trend blending (not diluted by calm entries)
    elevated = recent_60[recent_60['load_class'] >= 1]
    if len(elevated) > 0:
        elevated_rt = float(elevated['response_time'].mean())
        elevated_rc = float(elevated['request_count'].mean())
    else:
        elevated_rt = avg_response_time
        elevated_rc = avg_request_count

    history_seq = get_history_sequence(sequence_length=60)
    forecast_60 = []
    now = datetime.utcnow().replace(second=0, microsecond=0)
    if history_seq is not None:
        try:
            current_seq = history_seq.copy()
            for minute in range(60):
                pred = lstm_forecast(current_seq)
                forecast_time = now + timedelta(minutes=minute + 1)
                pred_rc = float(pred['predicted_request_count'])
                pred_rt = float(pred['predicted_response_time'])

                # Blend: early minutes lean toward current trend, later lean toward LSTM
                decay = max(0.0, 1.0 - (minute / 30.0))  # full influence for first 30 min
                if trend_bottleneck:
                    pred_rt = max(pred_rt, elevated_rt * (0.5 + 0.5 * decay))
                    pred_rc = max(pred_rc, elevated_rc * (0.5 + 0.5 * decay))
                elif trend_moderate:
                    pred_rt = max(pred_rt, elevated_rt * 0.8 * decay)
                    pred_rc = max(pred_rc, elevated_rc * 0.7 * decay)

                # Classify this forecast point using RF with estimated features
                forecast_features = _estimate_features_from_request_count(
                    pred_rc, pred_rt, forecast_time, current
                )
                rf_pred = rf_predict(forecast_features)

                forecast_60.append({
                    'time': forecast_time.isoformat(),
                    'request_count': round(pred_rc, 1),
                    'response_time': round(pred_rt, 3),
                    'load_class': rf_pred['class'],
                    'load_class_name': rf_pred['class_name'],
                    'bottleneck_prob': round(float(rf_pred['probability'][2]), 3),
                })
                new_row = current_seq[-1].copy()
                new_row[0] = pred['predicted_request_count']
                new_row[4] = pred['predicted_response_time']
                current_seq = np.vstack([current_seq[1:], new_row])
        except Exception as e:
            forecast_60 = [{'time': (now + timedelta(minutes=i + 1)).isoformat(), 'error': str(e)} for i in range(60)]

    return {
        'current': _convert(current),
        'load_class': rf_result['class'],
        'load_class_name': rf_result['class_name'],
        'advice': _convert(advice),
        'history': _convert(history_60),
        'forecast': _convert(forecast_60),
        'timestamp': datetime.utcnow().isoformat()
    }


def predict_next_24h():
    history = get_history_sequence(sequence_length=60)
    if history is None:
        return []

    current = get_current_metrics()

    # Recent trend for blending
    df = load_system_logs()
    df = engineer_features(df)
    recent_60 = df.tail(60)
    avg_response_time = float(recent_60['response_time'].mean())
    avg_request_count = float(recent_60['request_count'].mean())
    bottleneck_count = int((recent_60['load_class'] == 2).sum())
    moderate_count = int((recent_60['load_class'] == 1).sum())
    trend_bottleneck = bottleneck_count >= 5 or avg_response_time > 1.5
    trend_moderate = (bottleneck_count + moderate_count) >= 10

    elevated = recent_60[recent_60['load_class'] >= 1]
    if len(elevated) > 0:
        elevated_rt = float(elevated['response_time'].mean())
        elevated_rc = float(elevated['request_count'].mean())
    else:
        elevated_rt = avg_response_time
        elevated_rc = avg_request_count

    predictions = []
    current_seq = history.copy()

    for hour in range(24):
        try:
            pred = lstm_forecast(current_seq)
            pred_rc = float(pred['predicted_request_count'])
            pred_rt = float(pred['predicted_response_time'])

            # Blend: early hours lean toward current trend, later lean toward LSTM
            decay = max(0.0, 1.0 - (hour / 12.0))
            if trend_bottleneck:
                pred_rt = max(pred_rt, elevated_rt * (0.5 + 0.5 * decay))
                pred_rc = max(pred_rc, elevated_rc * (0.5 + 0.5 * decay))
            elif trend_moderate:
                pred_rt = max(pred_rt, elevated_rt * 0.8 * decay)
                pred_rc = max(pred_rc, elevated_rc * 0.7 * decay)

            forecast_features = _estimate_features_from_request_count(
                pred_rc, pred_rt,
                datetime.utcnow() + timedelta(hours=hour + 1),
                current
            )
            rf_pred = rf_predict(forecast_features)

            predictions.append({
                'hour': hour + 1,
                'request_count': round(pred_rc, 1),
                'response_time': round(pred_rt, 3),
                'load_class': rf_pred['class'],
                'load_class_name': rf_pred['class_name'],
                'bottleneck_prob': round(float(rf_pred['probability'][2]), 3),
            })
            new_row = current_seq[-1].copy()
            new_row[0] = pred['predicted_request_count']
            new_row[4] = pred['predicted_response_time']
            current_seq = np.vstack([current_seq[1:], new_row])
        except Exception as e:
            predictions.append({'hour': hour + 1, 'error': str(e)})
            break

    return predictions
