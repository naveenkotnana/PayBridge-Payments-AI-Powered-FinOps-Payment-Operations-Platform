"""Payment Operations Anomaly Detection Engine.

Combines unsupervised IsolationForest scoring with deterministic financial rules.
Design philosophy:
- The ML model proposes (anomaly_score, multivariate outlier flag).
- The RULES decide severity (CRITICAL, HIGH, MEDIUM, LOW) to guarantee reproducibility
  and prevent unpredictable LLM or model escalations.
- ML-only detections (without rule breaches) are capped at LOW severity.

Required detection areas:
1. UPI failure-rate spikes.
2. Bank-specific transaction failures.
3. Gateway latency increases.
4. Unusual transaction volume.
5. Payment success-rate degradation.
6. Repeated payment failures.
7. Abnormal payment processing patterns.
"""
import datetime as dt
import hashlib
from typing import List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Alert, Anomaly

# Deterministic severity thresholds
SEV_THRESHOLDS = [(40.0, "CRITICAL"), (25.0, "HIGH"), (15.0, "MEDIUM"), (8.0, "LOW")]
EXCEPTION_SEV = [(20, "CRITICAL"), (10, "HIGH"), (5, "MEDIUM"), (1, "LOW")]
_RANK = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def severity_from_pct(pct: float) -> str:
    a = abs(pct)
    for thr, sev in SEV_THRESHOLDS:
        if a >= thr:
            return sev
    return "INFO"


def severity_from_exceptions(n: int) -> str:
    for thr, sev in EXCEPTION_SEV:
        if n >= thr:
            return sev
    return "INFO"


def _sev_rank(s: str) -> int:
    return _RANK.get(s, 0)


def build_payment_features(db: Session) -> pd.DataFrame:
    """Extract payment features grouped by gateway, method, and bank for multi-variate anomaly detection."""
    count = db.execute(text("SELECT COUNT(*) FROM payment_transactions")).scalar()
    if not count:
        return pd.DataFrame()

    sql = text("""
        SELECT
            COALESCE(gateway, 'RAZORPAY') AS gateway,
            COALESCE(method, 'UNKNOWN') AS method,
            COALESCE(bank, 'UNKNOWN') AS bank,
            COUNT(*) AS total_attempts,
            SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END) AS captured_count,
            SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) AS failed_count,
            SUM(CASE WHEN status='AUTHORIZED' THEN 1 ELSE 0 END) AS authorized_count,
            ROUND(SUM(CAST(amount AS REAL)), 2) AS total_volume_inr,
            ROUND(SUM(CASE WHEN status='FAILED' THEN CAST(amount AS REAL) ELSE 0 END), 2) AS failed_volume_inr,
            ROUND(AVG(CAST(amount AS REAL)), 2) AS avg_amount_inr,
            SUM(CASE WHEN error_code IN ('BAD_REQUEST_GATEWAY_DOWN', 'GATEWAY_TIMEOUT', 'NETWORK_ERROR', 'BANK_DEBITED_PAYMENT_PENDING') THEN 1 ELSE 0 END) AS retryable_failures
        FROM payment_transactions
        GROUP BY gateway, method, bank
    """)
    rows = db.execute(sql).mappings().all()
    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        return df

    # Calculate derived ratios
    df["success_rate_pct"] = np.where(
        (df["captured_count"] + df["failed_count"]) > 0,
        (df["captured_count"] / (df["captured_count"] + df["failed_count"])) * 100.0,
        100.0
    )
    df["failure_rate_pct"] = 100.0 - df["success_rate_pct"]
    df["retryable_ratio"] = np.where(
        df["failed_count"] > 0,
        df["retryable_failures"] / df["failed_count"],
        0.0
    )
    return df


def detect(db: Session, contamination: float = 0.08, seed: int = 42) -> dict:
    """Unified anomaly detection. Detects payment anomalies if payment transactions exist,
    otherwise falls back to legacy revenue metrics for backward compatibility.
    """
    df = build_payment_features(db)
    current_month = dt.datetime.now().strftime("%Y-%m")

    # If no payment transactions exist, run legacy detector
    if df.empty:
        return _detect_legacy_anomalies(db, contamination, seed)

    features = ["total_attempts", "failed_count", "failure_rate_pct", "total_volume_inr", "retryable_failures"]
    X = df[features].astype(float).values

    # Isolation Forest for multivariate anomaly proposals
    if len(df) >= 3:
        effective_contamination = min(contamination, 0.49)
        model = IsolationForest(n_estimators=100, contamination=effective_contamination, random_state=seed)
        model.fit(X)
        df["iso_flag"] = model.predict(X)              # -1 = anomaly
        df["anomaly_score"] = -model.score_samples(X)  # higher = more anomalous
    else:
        df["iso_flag"] = 1
        df["anomaly_score"] = 0.1

    found = []
    for r in df.itertuples():
        reasons: List[str] = []
        rule_sev = "INFO"
        metric_name = "payment_success_rate"
        observed_val = float(r.failure_rate_pct)
        method_rates = df.loc[df["method"] == r.method, "failure_rate_pct"]
        expected_val = float(method_rates.median()) if not method_rates.empty else 0.0
        root_cause = ""
        action = ""

        # Rule 1: UPI Failure-rate spike
        if r.method == "UPI" and r.failure_rate_pct >= 20.0 and r.total_attempts >= 5:
            reasons.append(f"UPI failure rate spiked to {r.failure_rate_pct:.1f}% ({r.failed_count}/{r.total_attempts} attempts failed)")
            rule_sev = max(rule_sev, "CRITICAL" if r.failure_rate_pct >= 35.0 else "HIGH", key=_sev_rank)
            metric_name = "upi_failure_rate"
            root_cause = "UPI switch latency or NPCI gateway timeout"
            action = "Activate dynamic routing to secondary UPI switch and suppress checkout retries (SOP-001)"

        # Rule 2: Bank-specific switch failures
        elif r.bank != "UNKNOWN" and r.failure_rate_pct >= 25.0 and r.total_attempts >= 5:
            reasons.append(f"Bank switch degradation on {r.bank}: failure rate at {r.failure_rate_pct:.1f}%")
            rule_sev = max(rule_sev, "CRITICAL" if r.failure_rate_pct >= 40.0 else "HIGH", key=_sev_rank)
            metric_name = f"bank_failure_rate_{r.bank.lower()}"
            root_cause = f"Core banking switch connection degradation at {r.bank}"
            action = f"Temporarily downgrade traffic to {r.bank} and post downtime banner (SOP-001)"

        # Rule 3: Elevated failure rate across any channel
        elif r.failure_rate_pct >= 20.0 and r.total_attempts >= 10:
            reasons.append(f"Channel failure rate elevated at {r.failure_rate_pct:.1f}% on {r.method}")
            rule_sev = max(rule_sev, "HIGH" if r.failure_rate_pct >= 30.0 else "MEDIUM", key=_sev_rank)
            metric_name = f"{r.method.lower()}_channel_sr_degradation"
            root_cause = "Network degradation or card network authentication timeout"
            action = "Investigate gateway error codes and verify gateway health status"

        # Rule 4: High volume of retryable failures
        if r.retryable_failures >= 5:
            reasons.append(f"{int(r.retryable_failures)} retryable gateway/network timeouts detected")
            rule_sev = max(rule_sev, "HIGH" if r.retryable_failures >= 15 else "MEDIUM", key=_sev_rank)
            if not root_cause:
                root_cause = "Gateway connection timeout or bank debited payment pending"
                action = "Place merchant fulfillment on 30-min hold to prevent duplicate debits (SOP-002)"

        # Isolation Forest check
        iso = (r.iso_flag == -1)
        if iso:
            reasons.append(f"IsolationForest flagged multivariate outlier (score {r.anomaly_score:.3f})")

        if not reasons:
            continue

        method_flag = "RULE+ISOLATION_FOREST" if (iso and rule_sev != "INFO") else ("ISOLATION_FOREST" if iso else "RULE")
        # ML-only detections without rule breach stay at LOW
        sev = rule_sev if rule_sev != "INFO" else "LOW"

        entity_id = f"{r.gateway}_{r.bank}_{r.method}" if r.bank != "UNKNOWN" else f"{r.gateway}_{r.method}"
        fingerprint = hashlib.sha256(
            f"payment:{current_month}:{entity_id}:{metric_name}".encode()
        ).hexdigest()
        aid = f"ANM-{fingerprint[:35]}"
        reason_text = "; ".join(reasons)
        if root_cause:
            reason_text += f" | Hypothesis: {root_cause}. Action: {action}."

        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        prior_anomaly = db.query(Anomaly).filter_by(fingerprint=fingerprint).first()
        if prior_anomaly:
            prior_anomaly.last_seen_at = now
            prior_anomaly.occurrence_count = (prior_anomaly.occurrence_count or 1) + 1
            prior_anomaly.severity = sev
            prior_anomaly.reason = reason_text
            prior_anomaly.anomaly_score = round(float(r.anomaly_score), 4)
            prior_anomaly.observed_value = round(observed_val, 2)
            prior_anomaly.expected_value = round(expected_val, 2)
        else:
            db.add(Anomaly(
                anomaly_id=aid, billing_month=current_month,
                entity_type="PAYMENT_METHOD" if r.bank == "UNKNOWN" else "BANK",
                entity_id=entity_id, metric=metric_name, method=method_flag,
                anomaly_score=round(float(r.anomaly_score), 4), severity=sev,
                reason=reason_text, observed_value=round(observed_val, 2),
                expected_value=round(expected_val, 2), fingerprint=fingerprint,
                first_seen_at=now, last_seen_at=now, occurrence_count=1,
            ))

        # Alerts generated for MEDIUM, HIGH, CRITICAL
        if sev in ("MEDIUM", "HIGH", "CRITICAL"):
            alert_fingerprint = fingerprint
            alert_id = f"ALT-{fingerprint[:35]}"
            prior_alert = db.query(Alert).filter_by(fingerprint=alert_fingerprint).first()
            if prior_alert:
                prior_alert.last_seen_at = now
                prior_alert.occurrence_count = (prior_alert.occurrence_count or 1) + 1
                prior_alert.severity = sev
                prior_alert.observed_value = round(observed_val, 2)
                prior_alert.expected_value = round(expected_val, 2)
                prior_alert.anomaly_score = round(float(r.anomaly_score), 4)
                prior_alert.evidence_summary = reason_text
            else:
                db.add(Alert(
                    alert_id=alert_id, metric=metric_name, entity=entity_id,
                    billing_month=current_month, severity=sev,
                    observed_value=round(observed_val, 2), expected_value=round(expected_val, 2),
                    anomaly_score=round(float(r.anomaly_score), 4), evidence_summary=reason_text,
                    status="OPEN", detected_at=now, fingerprint=alert_fingerprint,
                    first_seen_at=now, last_seen_at=now, occurrence_count=1,
                ))

        found.append((aid, sev))

    db.commit()
    n_alerts = db.execute(text("SELECT COUNT(*) FROM alerts")).scalar()
    return {"rows_scored": len(df), "anomalies": len(found), "alerts": int(n_alerts or 0)}


def _detect_legacy_anomalies(db: Session, contamination: float, seed: int) -> dict:
    """Fallback legacy water/rental anomaly detector to preserve backwards compatibility."""
    rows = db.execute(text("""
        SELECT m.billing_month, m.location_code,
               SUM(m.total_revenue)   AS revenue,
               SUM(m.water_revenue)   AS water_revenue,
               SUM(m.rental_revenue)  AS rental_revenue,
               SUM(m.water_usage_m3)  AS usage_m3,
               COUNT(*)               AS apartments,
               SUM(CASE WHEN m.validation_flag='EXCEPTION' THEN 1 ELSE 0 END) AS exceptions,
               SUM(CASE WHEN m.water_active_days>0 THEN 1 ELSE 0 END)  AS active_water,
               SUM(CASE WHEN m.rental_active_days>0 THEN 1 ELSE 0 END) AS active_rental
        FROM monthly_revenue m GROUP BY m.billing_month, m.location_code
    """)).mappings().all()
    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        return {"anomalies": 0, "alerts": 0, "rows_scored": 0}

    df = df.sort_values(["location_code", "billing_month"])
    g = df.groupby("location_code")
    df["revenue_change_pct"] = g["revenue"].pct_change().fillna(0) * 100
    df["usage_change_pct"] = g["usage_m3"].pct_change().fillna(0) * 100
    df["rev_per_apartment"] = df["revenue"] / df["apartments"].replace(0, np.nan)
    df["exception_rate"] = df["exceptions"] / df["apartments"].replace(0, np.nan)
    df = df.fillna(0)

    features = ["revenue", "usage_m3", "apartments", "exceptions",
                "revenue_change_pct", "usage_change_pct",
                "rev_per_apartment", "exception_rate", "active_water", "active_rental"]

    X = df[features].astype(float).values
    model = IsolationForest(n_estimators=100, contamination=contamination, random_state=seed)
    model.fit(X)
    df["iso_flag"] = model.predict(X)
    df["anomaly_score"] = -model.score_samples(X)

    found = []
    for r in df.itertuples():
        reasons, rule_sev = [], "INFO"
        if abs(r.revenue_change_pct) >= 8.0:
            reasons.append(f"Revenue moved {r.revenue_change_pct:+.1f}% MoM")
            rule_sev = max(rule_sev, severity_from_pct(r.revenue_change_pct), key=_sev_rank)
        if r.exceptions >= 1:
            reasons.append(f"{int(r.exceptions)} validation exception(s)")
            rule_sev = max(rule_sev, severity_from_exceptions(int(r.exceptions)), key=_sev_rank)

        iso = r.iso_flag == -1
        if iso:
            reasons.append(f"IsolationForest flagged multivariate outlier (score {r.anomaly_score:.3f})")

        if not reasons:
            continue

        method = "RULE+ISOLATION_FOREST" if (iso and rule_sev != "INFO") else ("ISOLATION_FOREST" if iso else "RULE")
        sev = rule_sev if rule_sev != "INFO" else "LOW"
        fingerprint = hashlib.sha256(
            f"legacy:{r.billing_month}:{r.location_code}:total_revenue".encode()
        ).hexdigest()
        aid = f"ANM-{fingerprint[:35]}"
        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        prior_anomaly = db.query(Anomaly).filter_by(fingerprint=fingerprint).first()
        if prior_anomaly:
            prior_anomaly.last_seen_at = now
            prior_anomaly.occurrence_count = (prior_anomaly.occurrence_count or 1) + 1
            prior_anomaly.severity = sev
            prior_anomaly.reason = "; ".join(reasons)
        else:
            db.add(Anomaly(
                anomaly_id=aid, billing_month=r.billing_month,
                entity_type="LOCATION", entity_id=r.location_code,
                metric="total_revenue", method=method,
                anomaly_score=round(float(r.anomaly_score), 4), severity=sev,
                reason="; ".join(reasons), observed_value=round(float(r.revenue), 2),
                expected_value=None, fingerprint=fingerprint,
                first_seen_at=now, last_seen_at=now, occurrence_count=1,
            ))

        if sev in ("MEDIUM", "HIGH", "CRITICAL"):
            prior_alert = db.query(Alert).filter_by(fingerprint=fingerprint).first()
            if prior_alert:
                prior_alert.last_seen_at = now
                prior_alert.occurrence_count = (prior_alert.occurrence_count or 1) + 1
                prior_alert.severity = sev
                prior_alert.evidence_summary = "; ".join(reasons)
            else:
                db.add(Alert(
                    alert_id=f"ALT-{fingerprint[:35]}", metric="total_revenue",
                    entity=r.location_code, billing_month=r.billing_month, severity=sev,
                    observed_value=round(float(r.revenue), 2), expected_value=None,
                    anomaly_score=round(float(r.anomaly_score), 4),
                    evidence_summary="; ".join(reasons), status="OPEN", detected_at=now,
                    fingerprint=fingerprint, first_seen_at=now, last_seen_at=now,
                    occurrence_count=1,
                ))
        found.append((aid, sev))

    db.commit()
    n_alerts = db.execute(text("SELECT COUNT(*) FROM alerts")).scalar()
    return {"rows_scored": len(df), "anomalies": len(found), "alerts": int(n_alerts or 0)}
