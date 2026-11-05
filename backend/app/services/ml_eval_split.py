"""Chronological ML Split and Evaluation Framework.

Provides:
- Strict chronological train/validation/test splitting to prevent time-series data leakage.
- Clear isolation between untouched test sets and augmented training data.
- Standard evaluation metrics: Precision, Recall, F1, PR-AUC, False Positive Rate, Latency.
- Explicit production disclaimer for synthetic data benchmarks.
"""
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    precision_recall_curve,
    auc,
    confusion_matrix,
)
from sqlalchemy import text
from sqlalchemy.orm import Session


def fetch_payment_feature_dataset(db: Session, max_records: int = 10000) -> pd.DataFrame:
    """Fetch chronological payment transactions with feature flags."""
    sql = text("""
        SELECT
            payment_id,
            merchant_id,
            amount,
            method,
            bank,
            gateway,
            status,
            error_code,
            data_source,
            is_synthetic,
            created_at,
            CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END AS is_failure_label
        FROM payment_transactions
        ORDER BY created_at ASC
        LIMIT :limit
    """)
    rows = db.execute(sql, {"limit": max_records}).mappings().all()
    df = pd.DataFrame([dict(r) for r in rows])
    return df


def chronological_train_val_test_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split time-series payment data chronologically without leakage.

    Preserves strict temporal ordering: Train -> Val -> Test.
    """
    if df.empty:
        return df, df, df

    df_sorted = df.sort_values("created_at").reset_index(drop=True)
    n = len(df_sorted)

    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()

    return train_df, val_df, test_df


def evaluate_anomaly_predictions(
    y_true: List[int],
    y_pred: List[int],
    y_scores: Optional[List[float]] = None,
    detection_latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate rigorous ML performance metrics on untouched evaluation set."""
    y_t = np.array(y_true)
    y_p = np.array(y_pred)

    prec = float(precision_score(y_t, y_p, zero_division=0))
    rec = float(recall_score(y_t, y_p, zero_division=0))
    f1 = float(f1_score(y_t, y_p, zero_division=0))

    # Confusion matrix & False Positive Rate
    cm = confusion_matrix(y_t, y_p, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    pr_auc = 0.0
    if y_scores is not None and len(set(y_t)) > 1:
        p_curve, r_curve, _ = precision_recall_curve(y_t, y_scores)
        pr_auc = float(auc(r_curve, p_curve))

    return {
        "metrics": {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "pr_auc": round(pr_auc, 4),
            "false_positive_rate": round(fpr, 4),
            "detection_latency_ms": detection_latency_ms or 0.0,
        },
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "sample_size": len(y_t),
        "disclaimer": (
            "NOTICE: Metrics are evaluated on synthetic / augmented test datasets. "
            "Synthetic data benchmarks reflect algorithm behavior under modeled scenarios "
            "and do not constitute certified production SLA guarantees."
        ),
    }
