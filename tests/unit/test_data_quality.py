"""Unit tests for Data Quality and Mathematical Consistency Audit."""
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.payments import PaymentTransaction
from app.services.data_generator import PaymentDataGenerator
from app.services.data_quality import run_data_quality_audit


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_data_quality_audit_clean_data(mem_db):
    gen = PaymentDataGenerator(mem_db, seed=101)
    gen.generate_scenario(scenario="NORMAL_TRAFFIC", count=100, days_back=2)

    report = run_data_quality_audit(mem_db)
    assert report["status"] == "PASSED"
    assert report["quality_score_pct"] == 100.0
    assert report["total_checks_failed"] == 0

    check_names = [c["check_name"] for c in report["checks"]]
    assert "MDR Fee & Net Amount Reconciliation" in check_names
    assert "Payment Order Referential Integrity" in check_names
    assert "Captured Payment Timestamp Invariant" in check_names


def test_data_quality_audit_detects_corrupted_math(mem_db):
    gen = PaymentDataGenerator(mem_db, seed=202)
    gen.generate_scenario(scenario="NORMAL_TRAFFIC", count=20, days_back=1)

    # Intentionally corrupt a record's net amount
    corrupt_txn = mem_db.query(PaymentTransaction).first()
    corrupt_txn.net_amount = corrupt_txn.net_amount + Decimal("150.00")
    mem_db.commit()

    report = run_data_quality_audit(mem_db)
    assert report["total_checks_failed"] >= 1
    failed_checks = [c for c in report["checks"] if not c["passed"]]
    failed_names = [c["check_name"] for c in failed_checks]
    assert "MDR Fee & Net Amount Reconciliation" in failed_names
