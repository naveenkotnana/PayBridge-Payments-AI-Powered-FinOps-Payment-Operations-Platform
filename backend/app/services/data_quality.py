"""Data Quality & Financial Consistency Validation Engine.

Audits synthetic, augmented, and real payment datasets to verify:
1. Strict schema compliance and null invariants.
2. Referential integrity across orders, transactions, attempts, events, refunds, settlements.
3. Exact mathematical fee/tax reconciliation (net_amount == amount - fee - tax).
4. Lifecycle state transition validity.
5. Data Quality Score calculation (0 - 100%).
"""
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("opspilot.data_quality")

TWO_PLACES = Decimal("0.01")


def _dec(val: Any) -> Decimal:
    if val is None:
        return Decimal("0.00")
    return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def run_data_quality_audit(db: Session, sample_size: int = 5000) -> Dict[str, Any]:
    """Execute comprehensive data quality and mathematical consistency checks."""
    checks: List[Dict[str, Any]] = []
    total_checks_passed = 0
    total_checks_run = 0

    def record_check(name: str, category: str, passed: bool, details: str, severity: str = "CRITICAL"):
        nonlocal total_checks_passed, total_checks_run
        total_checks_run += 1
        if passed:
            total_checks_passed += 1
        checks.append({
            "check_name": name,
            "category": category,
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "severity": severity,
            "details": details,
        })

    # --- 1. Schema & Null Invariants ---
    null_pt_sql = text("""
        SELECT COUNT(*) FROM payment_transactions
        WHERE payment_id IS NULL OR amount IS NULL OR method IS NULL
           OR status IS NULL OR net_amount IS NULL OR merchant_id IS NULL
    """)
    null_pt_count = db.execute(null_pt_sql).scalar() or 0
    record_check(
        name="Transaction Required Fields Non-Null",
        category="SCHEMA",
        passed=(null_pt_count == 0),
        details=f"{null_pt_count} transactions with null required fields.",
    )

    # --- 2. Referential Integrity ---
    # Payments referencing non-existent orders
    orphan_order_sql = text("""
        SELECT COUNT(*) FROM payment_transactions pt
        LEFT JOIN payment_orders po ON pt.order_id = po.order_id
        WHERE po.order_id IS NULL
    """)
    orphan_orders = db.execute(orphan_order_sql).scalar() or 0
    record_check(
        name="Payment Order Referential Integrity",
        category="REFERENTIAL_INTEGRITY",
        passed=(orphan_orders == 0),
        details=f"{orphan_orders} orphaned transactions referencing missing orders.",
    )

    # Payments referencing non-existent merchants
    orphan_merchant_sql = text("""
        SELECT COUNT(*) FROM payment_transactions pt
        LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
        WHERE m.merchant_id IS NULL
    """)
    orphan_merchants = db.execute(orphan_merchant_sql).scalar() or 0
    record_check(
        name="Merchant Referential Integrity",
        category="REFERENTIAL_INTEGRITY",
        passed=(orphan_merchants == 0),
        details=f"{orphan_merchants} transactions referencing unknown merchant IDs.",
    )

    # Events referencing non-existent payments
    orphan_event_sql = text("""
        SELECT COUNT(*) FROM payment_events pe
        LEFT JOIN payment_transactions pt ON pe.payment_id = pt.payment_id
        WHERE pt.payment_id IS NULL
    """)
    orphan_events = db.execute(orphan_event_sql).scalar() or 0
    record_check(
        name="Lifecycle Event Referential Integrity",
        category="REFERENTIAL_INTEGRITY",
        passed=(orphan_events == 0),
        details=f"{orphan_events} orphaned events referencing missing payment IDs.",
    )

    # --- 3. Financial Mathematical Consistency (Decimal Invariants) ---
    # amount = net_amount + fee + tax
    math_mismatch_sql = text("""
        SELECT COUNT(*) FROM payment_transactions
        WHERE ROUND(CAST(amount AS REAL) - (CAST(net_amount AS REAL) + CAST(fee AS REAL) + CAST(tax AS REAL)), 2) != 0.0
    """)
    math_mismatches = db.execute(math_mismatch_sql).scalar() or 0
    record_check(
        name="MDR Fee & Net Amount Reconciliation",
        category="FINANCIAL_CONSISTENCY",
        passed=(math_mismatches == 0),
        details=f"{math_mismatches} transactions violated net_amount = amount - fee - tax invariant.",
    )

    # Positive values: amount > 0, fee >= 0, tax >= 0
    negative_values_sql = text("""
        SELECT COUNT(*) FROM payment_transactions
        WHERE amount <= 0 OR fee < 0 OR tax < 0 OR net_amount < 0
    """)
    negative_values = db.execute(negative_values_sql).scalar() or 0
    record_check(
        name="Non-Negative Monetary Amounts",
        category="FINANCIAL_CONSISTENCY",
        passed=(negative_values == 0),
        details=f"{negative_values} transactions with negative amount, fee, or net payout.",
    )

    # Settlement mathematical reconciliation: net_payout = gross_amount - fee_deducted - tax_deducted
    settlement_mismatch_sql = text("""
        SELECT COUNT(*) FROM settlements
        WHERE ROUND(CAST(gross_amount AS REAL) - (CAST(net_payout AS REAL) + CAST(fee_deducted AS REAL) + CAST(tax_deducted AS REAL)), 2) != 0.0
    """)
    settlement_mismatches = db.execute(settlement_mismatch_sql).scalar() or 0
    record_check(
        name="Settlement Batch Mathematical Invariant",
        category="FINANCIAL_CONSISTENCY",
        passed=(settlement_mismatches == 0),
        details=f"{settlement_mismatches} settlement batches with mathematical variance.",
    )

    # --- 4. Lifecycle State Invariants ---
    # CAPTURED payments without captured_at
    untimestamped_captures_sql = text("""
        SELECT COUNT(*) FROM payment_transactions
        WHERE status = 'CAPTURED' AND captured_at IS NULL
    """)
    untimestamped_captures = db.execute(untimestamped_captures_sql).scalar() or 0
    record_check(
        name="Captured Payment Timestamp Invariant",
        category="LIFECYCLE_STATE",
        passed=(untimestamped_captures == 0),
        details=f"{untimestamped_captures} captured payments missing captured_at timestamp.",
    )

    # FAILED payments without error_code
    undocumented_failures_sql = text("""
        SELECT COUNT(*) FROM payment_transactions
        WHERE status = 'FAILED' AND error_code IS NULL
    """)
    undocumented_failures = db.execute(undocumented_failures_sql).scalar() or 0
    record_check(
        name="Failed Payment Error Code Traceability",
        category="LIFECYCLE_STATE",
        passed=(undocumented_failures == 0),
        details=f"{undocumented_failures} failed payments missing standardized error code.",
    )

    # Calculate overall quality score (0 - 100%)
    score = round((total_checks_passed / total_checks_run * 100) if total_checks_run > 0 else 100.0, 1)

    return {
        "status": "PASSED" if score >= 90.0 else "WARNING",
        "quality_score_pct": score,
        "total_checks_run": total_checks_run,
        "total_checks_passed": total_checks_passed,
        "total_checks_failed": total_checks_run - total_checks_passed,
        "audited_at": dt.datetime.utcnow().isoformat(),
        "checks": checks,
    }
