"""Unit tests for payment anomaly detection engine."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.ml.anomaly import (
    build_payment_features,
    detect,
    severity_from_pct,
    severity_from_exceptions
)
from app.models import Alert, Anomaly, PaymentTransaction


def test_payment_anomaly_detection_with_failures():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Seed test payment transactions with high UPI failures on SBI
        for i in range(20):
            status = "FAILED" if i < 10 else "CAPTURED"
            error = "BAD_REQUEST_GATEWAY_DOWN" if status == "FAILED" else None
            db.add(PaymentTransaction(
                payment_id=f"pay_test_{i:03d}",
                order_id=f"order_test_{i:03d}",
                merchant_id="mer_test_01",
                customer_id="cust_001",
                amount=500.0,
                net_amount=500.0,
                currency="INR",
                method="UPI",
                bank="SBI",
                gateway="RAZORPAY",
                status=status,
                error_code=error
            ))
        db.commit()

        # Check feature extraction
        df = build_payment_features(db)
        assert not df.empty
        assert "failure_rate_pct" in df.columns
        assert df["total_attempts"].sum() == 20
        assert df["failed_count"].sum() == 10

        # Run anomaly detector
        res = detect(db)
        assert res["anomalies"] >= 1
        assert res["alerts"] >= 1

        # Verify persisted anomaly record
        anom = db.query(Anomaly).first()
        assert anom is not None
        assert "SBI" in anom.entity_id or "UPI" in anom.entity_id
        assert anom.severity in ("HIGH", "CRITICAL")
        assert "Hypothesis:" in anom.reason
        assert "Action:" in anom.reason

        # Verify alert record
        alert = db.query(Alert).first()
        assert alert is not None
        assert alert.severity in ("HIGH", "CRITICAL")
        assert alert.status == "OPEN"

        # Re-running detection retains the historical alert and updates its
        # occurrence count instead of deleting/recreating the event.
        anomaly_count = db.query(Anomaly).count()
        alert_count = db.query(Alert).count()
        detect(db)
        assert db.query(Anomaly).count() == anomaly_count
        assert db.query(Alert).count() == alert_count
        assert db.query(Anomaly).filter_by(fingerprint=anom.fingerprint).one().occurrence_count == 2
        assert db.query(Alert).filter_by(fingerprint=alert.fingerprint).one().occurrence_count == 2

    finally:
        db.close()


def test_severity_rules_preserved():
    assert severity_from_pct(50.0) == "CRITICAL"
    assert severity_from_pct(30.0) == "HIGH"
    assert severity_from_pct(18.0) == "MEDIUM"
    assert severity_from_pct(10.0) == "LOW"
    assert severity_from_pct(2.0) == "INFO"

    assert severity_from_exceptions(25) == "CRITICAL"
    assert severity_from_exceptions(12) == "HIGH"
    assert severity_from_exceptions(6) == "MEDIUM"
    assert severity_from_exceptions(2) == "LOW"
