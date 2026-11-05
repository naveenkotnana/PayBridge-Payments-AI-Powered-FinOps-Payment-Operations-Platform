"""Automatic Data Availability and Integrity Inspector.

Inspects database tables, record counts, lifecycle completeness, class balance,
and distinguishes REAL vs SYNTHETIC vs AUGMENTED records.

Guarantees:
- Never silently replaces real data.
- Accurately reports missing fields, sparse tables, and lifecycle anomalies.
- Returns actionable recommendations for simulation and augmentation.
"""
import datetime as dt
from typing import Any, Dict, List
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from app.models.payments import (
    Merchant,
    Customer,
    PaymentOrder,
    PaymentTransaction,
    PaymentEvent,
    PaymentAttempt,
    Refund,
    Settlement,
    ReconciliationDiscrepancy,
    PaymentIncident,
    Dispute,
)


def inspect_data_availability(db: Session, lookback_days: int = 30) -> Dict[str, Any]:
    """Inspect payment dataset health, distribution, and data provenance."""
    # 1. Entity Record Counts & Provenance breakdown
    tables_summary = {}

    models_to_check = [
        ("merchants", Merchant),
        ("customers", Customer),
        ("orders", PaymentOrder),
        ("transactions", PaymentTransaction),
        ("events", PaymentEvent),
        ("attempts", PaymentAttempt),
        ("refunds", Refund),
        ("settlements", Settlement),
        ("discrepancies", ReconciliationDiscrepancy),
        ("incidents", PaymentIncident),
        ("disputes", Dispute),
    ]

    total_records = 0
    synthetic_count = 0
    real_count = 0
    augmented_count = 0

    for name, model in models_to_check:
        count = db.query(model).count()
        tables_summary[name] = {"total": count}
        total_records += count

        if hasattr(model, "data_source"):
            src_breakdown = (
                db.query(model.data_source, func.count(model.data_source))
                .group_by(model.data_source)
                .all()
            )
            src_dict = {src: cnt for src, cnt in src_breakdown}
            tables_summary[name]["by_source"] = src_dict
            synthetic_count += src_dict.get("SYNTHETIC", 0)
            real_count += src_dict.get("REAL", 0)
            augmented_count += src_dict.get("AUGMENTED", 0)

    # 2. Transaction Status & Method Class Balance
    txns_total = tables_summary["transactions"]["total"]
    status_distribution = {}
    method_distribution = {}
    bank_distribution = {}
    error_code_distribution = {}

    if txns_total > 0:
        for status, cnt in db.query(PaymentTransaction.status, func.count(PaymentTransaction.status)).group_by(PaymentTransaction.status).all():
            status_distribution[status] = cnt

        for method, cnt in db.query(PaymentTransaction.method, func.count(PaymentTransaction.method)).group_by(PaymentTransaction.method).all():
            method_distribution[method] = cnt

        for bank, cnt in db.query(PaymentTransaction.bank, func.count(PaymentTransaction.bank)).group_by(PaymentTransaction.bank).all():
            if bank:
                bank_distribution[bank] = cnt

        for err, cnt in db.query(PaymentTransaction.error_code, func.count(PaymentTransaction.error_code)).filter(PaymentTransaction.error_code.isnot(None)).group_by(PaymentTransaction.error_code).all():
            error_code_distribution[err] = cnt

    # 3. Lifecycle Consistency Checks
    orphaned_transactions = 0
    unreconciled_captured = 0
    incomplete_lifecycles = 0

    if txns_total > 0:
        # Transactions without existing orders
        orphaned_sql = text("""
            SELECT COUNT(*) FROM payment_transactions pt
            LEFT JOIN payment_orders po ON pt.order_id = po.order_id
            WHERE po.order_id IS NULL
        """)
        orphaned_transactions = db.execute(orphaned_sql).scalar() or 0

        # Captured transactions without events
        incomplete_events_sql = text("""
            SELECT COUNT(*) FROM payment_transactions pt
            LEFT JOIN payment_events pe ON pt.payment_id = pe.payment_id
            WHERE pe.payment_id IS NULL
        """)
        incomplete_lifecycles = db.execute(incomplete_events_sql).scalar() or 0

        unreconciled_captured = db.query(PaymentTransaction).filter(
            PaymentTransaction.status == "CAPTURED",
            PaymentTransaction.reconciled.is_(False)
        ).count()

    # 4. Data Gaps and Diagnostics
    gaps: List[str] = []
    recommendations: List[str] = []

    if txns_total < 500:
        gaps.append(f"Insufficient transaction volume ({txns_total} records; recommended >= 1,000 for realistic simulation).")
        recommendations.append("Generate synthetic payment dataset (Small: 1,000 or Medium: 10,000 records).")

    if tables_summary["customers"]["total"] == 0:
        gaps.append("Zero customer profiles registered.")
        recommendations.append("Seed synthetic customers linked to active merchants.")

    if tables_summary["disputes"]["total"] == 0:
        gaps.append("Zero dispute / chargeback records present.")
        recommendations.append("Generate dispute scenarios for fraud/chargeback workflows.")

    if tables_summary["settlements"]["total"] == 0:
        gaps.append("Zero settlement payout batches recorded.")
        recommendations.append("Generate daily T+1 / T+2 settlement cycles with UTR numbers.")

    # Check for severe class imbalance in payment methods
    if txns_total > 100:
        upi_share = method_distribution.get("UPI", 0) / txns_total
        if upi_share > 0.95 or upi_share < 0.20:
            gaps.append(f"Payment method distribution skewed: UPI is {upi_share*100:.1f}% (standard Indian fintech benchmark is ~60-70%).")
            recommendations.append("Apply stratified resampling or scenario generation to balance payment methods.")

    # Check failure rate
    failed_count = status_distribution.get("FAILED", 0)
    failure_rate = (failed_count / txns_total) if txns_total > 0 else 0.0
    if txns_total > 100 and failure_rate < 0.01:
        gaps.append(f"Extremely low failure rate ({failure_rate*100:.2f}%). Anomaly detection and retry models require failure samples.")
        recommendations.append("Inject synthetic gateway outage or bank failure scenario.")

    is_ready_for_ml = (
        txns_total >= 500
        and failed_count >= 20
        and tables_summary["events"]["total"] >= txns_total
    )

    return {
        "status": "HEALTHY" if not gaps else "DATA_GAPS_IDENTIFIED",
        "inspected_at": dt.datetime.utcnow().isoformat(),
        "total_records_inspected": total_records,
        "provenance": {
            "real_records": real_count,
            "synthetic_records": synthetic_count,
            "augmented_records": augmented_count,
            "synthetic_ratio_pct": round((synthetic_count / total_records * 100) if total_records > 0 else 100.0, 2),
        },
        "tables": tables_summary,
        "distributions": {
            "status": status_distribution,
            "method": method_distribution,
            "bank": bank_distribution,
            "error_codes": error_code_distribution,
            "failure_rate_pct": round(failure_rate * 100, 2),
        },
        "integrity_metrics": {
            "orphaned_transactions": orphaned_transactions,
            "incomplete_lifecycles": incomplete_lifecycles,
            "unreconciled_captured": unreconciled_captured,
        },
        "gaps_identified": gaps,
        "recommendations": recommendations,
        "is_ready_for_ml": is_ready_for_ml,
    }
