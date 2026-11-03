"""Unit tests for Chronological ML Split and Evaluation Metrics."""
import datetime as dt
import pandas as pd
from app.services.ml_eval_split import (
    chronological_train_val_test_split,
    evaluate_anomaly_predictions,
)


def test_chronological_split_prevents_leakage():
    # Construct sequence of timestamps
    base = dt.datetime(2026, 1, 1, 10, 0, 0)
    records = []
    for i in range(100):
        records.append({
            "payment_id": f"pay_{i}",
            "amount": 100.0 + i,
            "created_at": base + dt.timedelta(minutes=i * 10),
            "is_failure_label": 1 if i % 10 == 0 else 0,
        })
    df = pd.DataFrame(records)

    train_df, val_df, test_df = chronological_train_val_test_split(df, train_ratio=0.70, val_ratio=0.15)

    assert len(train_df) == 70
    assert len(val_df) == 15
    assert len(test_df) == 15

    # Chronological invariant check: no future data in train
    assert train_df["created_at"].max() < val_df["created_at"].min()
    assert val_df["created_at"].max() < test_df["created_at"].min()


def test_evaluate_anomaly_predictions():
    y_true = [1, 0, 1, 1, 0, 0, 1, 0, 0, 1]
    y_pred = [1, 0, 1, 0, 0, 0, 1, 1, 0, 1]  # 4 TP, 1 FP, 1 FN, 4 TN
    y_scores = [0.9, 0.1, 0.8, 0.4, 0.2, 0.15, 0.85, 0.7, 0.2, 0.95]

    res = evaluate_anomaly_predictions(y_true, y_pred, y_scores, detection_latency_ms=12.5)

    assert "metrics" in res
    assert res["metrics"]["precision"] > 0.0
    assert res["metrics"]["recall"] > 0.0
    assert res["metrics"]["f1_score"] > 0.0
    assert res["metrics"]["detection_latency_ms"] == 12.5
    assert "disclaimer" in res
    assert "confusion_matrix" in res
    assert res["confusion_matrix"]["true_positives"] == 4
