"""Payment Incident Correlation Engine — Phase 4.

Detects correlated payment failure clusters and groups related anomaly
signals into a single operational incident record.

Detection approach (layered):
1. Rolling statistical baseline — 24h average SR per (gateway, method) pair.
2. Rule-based threshold — trigger if current-hour SR drops ≥ THRESHOLD_PP
   below baseline (default 10 percentage points).
3. IsolationForest — flags multivariate outliers in the (gateway, method,
   hour) feature space. Score alone caps at LOW severity (same policy as
   app/ml/anomaly.py). Rules determine escalation.
4. Minimum sample guard — windows with < MIN_SAMPLE attempts are skipped to
   avoid false positives from low-volume gateways.

Correlation grouping:
- Multiple (gateway, method) signals within the same 60-minute window that
  share a common affected_bank are merged into one incident.
- Severity is the maximum severity across all merged signals.

Incident lifecycle:
- New incidents are written to payment_incidents with status=OPEN.
- If an open incident for the same (gateway, category) combination exists and
  is < 4 hours old, the engine updates it (adds counts) rather than creating
  a new one. This prevents duplicate incidents during the same event.

Financial exposure:
- exposure = SUM(amount) of FAILED payments in the detection window where
  error is RETRYABLE (non-retryable failures are excluded because they would
  have failed regardless of the incident).
"""
import datetime as dt
import logging
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.payments import IncidentMerchant, PaymentIncident

log = logging.getLogger("opspilot.incident_correlation")

# Tunable thresholds — documented here, not scattered through the code.
THRESHOLD_SR_DROP_PP = 10.0      # Success-rate drop vs baseline to trigger rule
MIN_SAMPLE = 10                  # Minimum attempts per window for a valid signal
INCIDENT_DEDUP_HOURS = 4         # Merge into existing open incident if < 4h old
ISOLATION_CONTAMINATION = 0.08   # Expected anomaly fraction (same as anomaly.py)
ISOLATION_SEED = 42

_SEV_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _rank(sev: str) -> int:
    return _SEV_RANK.get(sev, 0)


def _sr_drop_to_severity(drop_pp: float) -> str:
    """Map an SR drop (positive = degradation) to incident severity.

    Thresholds are based on typical fintech SLA expectations:
    - ≥ 30pp drop → payment flow is largely broken → CRITICAL
    - ≥ 20pp drop → significant degradation → HIGH
    - ≥ 10pp drop → noticeable drop, SLA at risk → MEDIUM
    - < 10pp drop → informational / noise → LOW
    """
    if drop_pp >= 30:
        return "CRITICAL"
    if drop_pp >= 20:
        return "HIGH"
    if drop_pp >= 10:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def _fetch_hourly_gateway_stats(db: Session, lookback_hours: int = 25) -> pd.DataFrame:
    """Return per-gateway-method hourly SR and attempt counts.

    Lookback of 25 hours gives 24h baseline + 1h current window.
    """
    sql = text("""
        SELECT
            gateway,
            method,
            bank,
            STRFTIME('%Y-%m-%dT%H:00:00', created_at)              AS hour,
            COUNT(*)                                                AS attempts,
            SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)     AS captured,
            SUM(CASE WHEN status='FAILED'   THEN 1 ELSE 0 END)     AS failed,
            SUM(CASE WHEN status='FAILED'
                     AND error_code IN (
                         'BAD_REQUEST_GATEWAY_DOWN',
                         'BANK_DEBITED_PAYMENT_PENDING',
                         'EXPIRED_TRANSACTION',
                         'GATEWAY_TIMEOUT',
                         'NETWORK_ERROR'
                     )
                     THEN CAST(amount AS REAL) ELSE 0 END)          AS retryable_blocked_inr
        FROM payment_transactions
        WHERE created_at >= DATETIME('now', :lookback)
        GROUP BY gateway, method, bank,
                 STRFTIME('%Y-%m-%dT%H:00:00', created_at)
    """)
    rows = db.execute(sql, {"lookback": f"-{lookback_hours} hours"}).mappings().all()
    df = pd.DataFrame([dict(r) for r in rows])
    return df


def _split_current_baseline(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split df into current 1h window and 24h baseline."""
    if df.empty:
        return df, df
    now_floor = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    current_hour = now_floor.strftime("%Y-%m-%dT%H:00:00")
    current = df[df["hour"] == current_hour].copy()
    baseline = df[df["hour"] != current_hour].copy()
    return current, baseline


# ---------------------------------------------------------------------------
# Signal detection
# ---------------------------------------------------------------------------

def _compute_baseline_sr(baseline: pd.DataFrame) -> pd.DataFrame:
    """Aggregate baseline SR per (gateway, method) from the 24h window."""
    if baseline.empty:
        return pd.DataFrame(columns=["gateway", "method", "baseline_sr_pct", "baseline_attempts"])
    agg = (
        baseline.groupby(["gateway", "method"])
        .agg(
            baseline_attempts=("attempts", "sum"),
            baseline_captured=("captured", "sum"),
        )
        .reset_index()
    )
    agg["baseline_sr_pct"] = np.where(
        agg["baseline_attempts"] >= MIN_SAMPLE,
        (agg["baseline_captured"] / agg["baseline_attempts"].replace(0, np.nan)) * 100,
        np.nan,
    )
    return agg[["gateway", "method", "baseline_sr_pct", "baseline_attempts"]]


def _apply_isolation_forest(current: pd.DataFrame) -> pd.DataFrame:
    """Flag multivariate outliers in the current-hour (gateway×method) window.

    Returns current df with an additional 'iso_anomaly' bool column.
    ML-only detections carry no severity escalation (same policy as anomaly.py).
    """
    if current.empty or len(current) < 3:
        current = current.copy()
        current["iso_anomaly"] = False
        return current

    features = ["attempts", "captured", "failed"]
    X = current[features].fillna(0).astype(float).values
    model = IsolationForest(
        n_estimators=100,
        contamination=ISOLATION_CONTAMINATION,
        random_state=ISOLATION_SEED,
    )
    model.fit(X)
    current = current.copy()
    current["iso_anomaly"] = model.predict(X) == -1
    return current


def _detect_signals(
    current: pd.DataFrame, baseline_sr: pd.DataFrame
) -> List[Dict[str, Any]]:
    """Compare current SR against baseline; return triggered signal dicts."""
    if current.empty:
        return []

    current_agg = (
        current.groupby(["gateway", "method"])
        .agg(
            current_attempts=("attempts", "sum"),
            current_captured=("captured", "sum"),
            current_failed=("failed", "sum"),
            retryable_blocked_inr=("retryable_blocked_inr", "sum"),
            iso_anomaly=("iso_anomaly", "any"),
            # Collect distinct banks affected in this window
            affected_banks=("bank", lambda x: ",".join(sorted(set(x.dropna())))),
        )
        .reset_index()
    )
    current_agg["current_sr_pct"] = np.where(
        current_agg["current_attempts"] >= MIN_SAMPLE,
        (current_agg["current_captured"] / current_agg["current_attempts"].replace(0, np.nan)) * 100,
        np.nan,
    )
    merged = current_agg.merge(baseline_sr, on=["gateway", "method"], how="left")

    signals = []
    for _, row in merged.iterrows():
        current_sr = row.get("current_sr_pct")
        baseline_sr_val = row.get("baseline_sr_pct")
        iso = bool(row.get("iso_anomaly", False))
        attempts = int(row.get("current_attempts", 0))

        if attempts < MIN_SAMPLE:
            continue  # Insufficient data — skip

        drop_pp = None
        rule_triggered = False
        if pd.notna(current_sr) and pd.notna(baseline_sr_val):
            drop_pp = float(baseline_sr_val) - float(current_sr)
            rule_triggered = drop_pp >= THRESHOLD_SR_DROP_PP

        if not rule_triggered and not iso:
            continue

        sev = "LOW"
        if rule_triggered and drop_pp is not None:
            sev = _sr_drop_to_severity(drop_pp)
        # ISO-only stays LOW (no rule confirmation)

        signals.append({
            "gateway": row["gateway"],
            "method": row["method"],
            "affected_banks": row.get("affected_banks", ""),
            "current_attempts": attempts,
            "current_failed": int(row.get("current_failed", 0)),
            "current_sr_pct": round(float(current_sr), 2) if pd.notna(current_sr) else None,
            "baseline_sr_pct": round(float(baseline_sr_val), 2) if pd.notna(baseline_sr_val) else None,
            "sr_drop_pp": round(drop_pp, 2) if drop_pp is not None else None,
            "retryable_blocked_inr": round(float(row.get("retryable_blocked_inr", 0)), 2),
            "severity": sev,
            "detection_method": "RULE+ISO" if (rule_triggered and iso) else ("RULE" if rule_triggered else "ISO"),
        })
    return signals


# ---------------------------------------------------------------------------
# Incident grouping and persistence
# ---------------------------------------------------------------------------

def _group_signals(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge signals that share the same gateway into one incident.

    Rationale: a gateway outage affects all methods routed through it. Grouping
    prevents one outage from producing 4 separate incidents (UPI + CARD +
    NETBANKING + WALLET all failing on HDFC_SMARTHUB).
    """
    groups: Dict[str, Dict[str, Any]] = {}
    for sig in signals:
        key = sig["gateway"]
        if key not in groups:
            groups[key] = {
                "gateway": sig["gateway"],
                "affected_methods": set(),
                "affected_banks": set(),
                "failed_count": 0,
                "retryable_blocked_inr": Decimal("0.00"),
                "baseline_sr_pct": sig["baseline_sr_pct"],
                "current_sr_pct": sig["current_sr_pct"],
                "severity": sig["severity"],
                "detection_method": sig["detection_method"],
                "signals": [],
            }
        g = groups[key]
        g["affected_methods"].add(sig["method"])
        for bank in (sig["affected_banks"] or "").split(","):
            if bank.strip():
                g["affected_banks"].add(bank.strip())
        g["failed_count"] += sig["current_failed"]
        g["retryable_blocked_inr"] += Decimal(str(sig["retryable_blocked_inr"]))
        # Escalate severity to highest seen
        if _rank(sig["severity"]) > _rank(g["severity"]):
            g["severity"] = sig["severity"]
            g["baseline_sr_pct"] = sig["baseline_sr_pct"]
            g["current_sr_pct"] = sig["current_sr_pct"]
        g["signals"].append(sig)

    incidents = []
    for g in groups.values():
        g["affected_methods"] = sorted(g["affected_methods"])
        g["affected_banks"] = sorted(g["affected_banks"])
        incidents.append(g)
    return incidents


def _find_existing_open_incident(
    db: Session, gateway: str, category: str
) -> Optional[PaymentIncident]:
    """Return an open incident for this gateway/category if < DEDUP hours old."""
    cutoff = dt.datetime.utcnow() - dt.timedelta(hours=INCIDENT_DEDUP_HOURS)
    return (
        db.query(PaymentIncident)
        .filter(
            PaymentIncident.status == "OPEN",
            PaymentIncident.category == category,
            PaymentIncident.detected_at >= cutoff,
            PaymentIncident.title.contains(gateway),
        )
        .first()
    )


def _fetch_merchant_exposure(
    db: Session, gateway: str, window_minutes: int = 60
) -> List[Dict[str, Any]]:
    """Return per-merchant failed amount for a gateway in the last window."""
    sql = text("""
        SELECT merchant_id,
               SUM(CAST(amount AS REAL))  AS failed_amount,
               COUNT(*)                   AS failed_count
        FROM payment_transactions
        WHERE gateway = :gateway
          AND status  = 'FAILED'
          AND created_at >= DATETIME('now', :lookback)
        GROUP BY merchant_id
    """)
    rows = db.execute(
        sql, {"gateway": gateway, "lookback": f"-{window_minutes} minutes"}
    ).mappings().all()
    return [dict(r) for r in rows]


def _write_incident(
    db: Session,
    grouped: Dict[str, Any],
    now: dt.datetime,
) -> PaymentIncident:
    """Persist one incident (or update existing) and return it."""
    gateway = grouped["gateway"]
    category = "GATEWAY_DEGRADATION"

    existing = _find_existing_open_incident(db, gateway, category)
    if existing:
        # Update counts rather than creating a duplicate
        existing.failed_transaction_count = (existing.failed_transaction_count or 0) + grouped["failed_count"]
        existing.estimated_financial_exposure = (
            Decimal(str(existing.estimated_financial_exposure or 0))
            + grouped["retryable_blocked_inr"]
        )
        existing.investigation_notes = (
            f"[{now.isoformat()}] Correlation engine added {grouped['failed_count']} failures"
        )
        db.flush()
        return existing

    methods_str = ",".join(grouped["affected_methods"])
    banks_str = ",".join(grouped["affected_banks"])
    incident_id = f"INC-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    evidence_parts = [
        f"Gateway: {gateway}",
        f"Affected methods: {methods_str or 'N/A'}",
        f"Affected banks: {banks_str or 'N/A'}",
        f"Baseline SR: {grouped['baseline_sr_pct']}%",
        f"Current SR: {grouped['current_sr_pct']}%",
        f"Failed transactions: {grouped['failed_count']}",
        f"Detection: {grouped['detection_method']}",
    ]

    hypothesis_parts = [
        "1. Gateway provider infrastructure degradation (most likely if all methods affected).",
        "2. Bank upstream connectivity issue (if only specific bank affected).",
        "3. Network routing anomaly between PG and bank switch.",
        "NOTE: Root cause NOT asserted — hypothesis requires manual confirmation.",
    ]

    incident = PaymentIncident(
        incident_id=incident_id,
        title=f"{gateway} gateway degradation — SR drop detected",
        category=category,
        severity=grouped["severity"],
        status="OPEN",
        affected_banks=banks_str,
        affected_methods=methods_str,
        failed_transaction_count=grouped["failed_count"],
        estimated_financial_exposure=grouped["retryable_blocked_inr"],
        baseline_success_rate=grouped["baseline_sr_pct"],
        observed_success_rate=grouped["current_sr_pct"],
        evidence_summary="; ".join(evidence_parts),
        root_cause_hypothesis="\n".join(hypothesis_parts),
        detected_at=now,
    )
    db.add(incident)
    db.flush()

    # Link affected merchants
    merchant_exposures = _fetch_merchant_exposure(db, gateway)
    for me in merchant_exposures:
        db.add(
            IncidentMerchant(
                incident_id=incident_id,
                merchant_id=me["merchant_id"],
                failed_amount=Decimal(str(me["failed_amount"] or 0)).quantize(Decimal("0.01")),
                failed_count=me["failed_count"],
            )
        )
    return incident


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_incident_correlation(db: Session) -> Dict[str, Any]:
    """Detect correlated payment failures and create/update incident records.

    Intended to be called periodically (e.g., every 5 minutes by the
    event streamer service or a scheduled task).

    Returns a summary dict for observability logging.
    """
    now = dt.datetime.utcnow()
    raw_df = _fetch_hourly_gateway_stats(db)

    if raw_df.empty:
        log.info("Incident correlation: no payment data in lookback window.")
        return {
            "status": "NO_DATA",
            "incidents_created": 0,
            "incidents_updated": 0,
            "signals_detected": 0,
        }

    current, baseline = _split_current_baseline(raw_df)
    baseline_sr = _compute_baseline_sr(baseline)
    current = _apply_isolation_forest(current)
    signals = _detect_signals(current, baseline_sr)

    if not signals:
        log.info("Incident correlation: no anomalous signals detected.")
        return {
            "status": "CLEAN",
            "incidents_created": 0,
            "incidents_updated": 0,
            "signals_detected": 0,
        }

    grouped_incidents = _group_signals(signals)
    created = 0
    updated = 0

    for group in grouped_incidents:
        gateway = group["gateway"]
        existing = _find_existing_open_incident(db, gateway, "GATEWAY_DEGRADATION")
        _write_incident(db, group, now)
        if existing:
            updated += 1
        else:
            created += 1

    db.commit()
    log.info(
        "Incident correlation complete: %d signals, %d created, %d updated",
        len(signals), created, updated,
    )
    return {
        "status": "COMPLETED",
        "signals_detected": len(signals),
        "incidents_created": created,
        "incidents_updated": updated,
        "gateways_affected": [g["gateway"] for g in grouped_incidents],
    }
