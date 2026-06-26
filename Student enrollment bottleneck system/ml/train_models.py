#!/usr/bin/env python3
"""
Orchestration script to train all ML models.
Run this after seeding the database.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.random_forest import train_random_forest
from ml.lstm_model import train_lstm


def main():
    print("=" * 60)
    print("ML MODEL TRAINING PIPELINE")
    print("=" * 60)

    print("\n[1/2] Training Random Forest Classifier...\n")
    rf_model, rf_scaler, acc, prec, rec, f1 = train_random_forest()

    print("\n[2/2] Training LSTM Forecaster...\n")
    lstm_model, feat_scaler, tgt_scaler, history = train_lstm()

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print("Models saved to ml/models/")


if __name__ == '__main__':
    main()
