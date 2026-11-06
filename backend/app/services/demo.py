"""Database-backed metrics for the local submission demo."""
from decimal import Decimal
from app.models import Alert
from app.models.payments import PaymentTransaction

DEMO_ALERT_ID = "ALT-PAYMENT-DEMO"


def payment_summary(db, merchant_id=None):
    query = db.query(PaymentTransaction)
    if merchant_id:
        query = query.filter_by(merchant_id=merchant_id)
    rows = query.all()
    captured = [r for r in rows if r.status == "CAPTURED"]
    failed = [r for r in rows if r.status == "FAILED"]
    terminal = len(captured) + len(failed)
    banks = []
    for bank in sorted({r.bank or "Unknown" for r in rows}):
        group = [r for r in rows if (r.bank or "Unknown") == bank]
        good = sum(r.status == "CAPTURED" for r in group)
        bad = sum(r.status == "FAILED" for r in group)
        banks.append({"Bank": bank, "Transactions": len(group), "Captured": good,
                      "Failed": bad, "Success rate (%)": round(100 * good / (good + bad), 2)
                      if good + bad else None})
    times = [r.created_at for r in rows if r.created_at]
    return {"total": len(rows), "captured": len(captured), "failed": len(failed),
            "pending": sum(r.status in ("AUTHORIZED", "PENDING", "CREATED") for r in rows),
            "success_rate": round(100 * len(captured) / terminal, 2) if terminal else None,
            "gmv": sum((Decimal(str(r.amount)) for r in captured), Decimal("0.00")),
            "failed_volume": sum((Decimal(str(r.amount)) for r in failed), Decimal("0.00")),
            "banks": banks, "start": min(times) if times else None, "end": max(times) if times else None}


def refresh_demo_alert(db):
    summary = payment_summary(db)
    if not summary["failed"]:
        return None
    rate = round(100 - summary["success_rate"], 2)
    alert = db.get(Alert, DEMO_ALERT_ID)
    if alert is None:
        alert = Alert(alert_id=DEMO_ALERT_ID)
        db.add(alert)
    alert.metric = "payment_failure_rate"
    alert.entity = "GLOBAL_PAYMENTS"
    alert.billing_month = summary["end"].strftime("%Y-%m") if summary["end"] else "unknown"
    alert.severity = "HIGH" if rate >= 10 else "MEDIUM"
    alert.observed_value = Decimal(str(rate))
    alert.evidence_summary = (
        f"All loaded data: {summary['total']} transactions; {summary['failed']} failed; "
        f"failed transaction volume INR {summary['failed_volume']:.2f}. "
        "This is potential sales exposure, not confirmed financial loss. "
        "No measured bank latency or historical outage baseline is supplied."
    )
    alert.status = "OPEN"
    db.commit()
    return alert
