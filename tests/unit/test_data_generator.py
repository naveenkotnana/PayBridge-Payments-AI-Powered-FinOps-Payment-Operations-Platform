"""Unit tests for Synthetic Data Generator and Scenario Engine."""
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.payments import (
    Merchant,
    Customer,
    PaymentTransaction,
)
from app.services.data_availability import inspect_data_availability
from app.services.data_generator import (
    MERCHANTS_MASTER,
    PaymentDataGenerator,
    calculate_fees,
    seed_merchants_and_customers,
)


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


def test_seed_merchants_and_customers(mem_db):
    res = seed_merchants_and_customers(mem_db, num_customers_per_merchant=5)
    expected_merchants = len(MERCHANTS_MASTER)
    assert res["merchants_seeded"] == expected_merchants
    assert res["customers_seeded"] == expected_merchants * 5
    assert mem_db.query(Merchant).count() == expected_merchants
    assert mem_db.query(Customer).count() == expected_merchants * 5

    # Idempotent re-run
    res2 = seed_merchants_and_customers(mem_db, num_customers_per_merchant=5)
    assert res2["merchants_seeded"] == 0
    assert res2["customers_seeded"] == 0


def test_calculate_fees_deterministic():
    # UPI: 0.35% + 18% GST on fee
    amt = Decimal("1000.00")
    fee, tax = calculate_fees(amt, "UPI")
    assert fee == Decimal("3.50")
    assert tax == Decimal("0.63")

    # Card: 1.85% + 18% GST
    fee_c, tax_c = calculate_fees(amt, "CARD")
    assert fee_c == Decimal("18.50")
    assert tax_c == Decimal("3.33")


def test_generate_scenario_normal_traffic(mem_db):
    gen = PaymentDataGenerator(mem_db, seed=123)
    res = gen.generate_scenario(scenario="NORMAL_TRAFFIC", count=100, days_back=2)

    assert res["status"] == "SUCCESS"
    assert res["records_generated"]["payments"] == 100
    assert res["records_generated"]["events"] == 200  # 1 created + 1 terminal per payment
    assert mem_db.query(PaymentTransaction).count() == 100

    # Verify mathematical invariant on every generated row
    for p in mem_db.query(PaymentTransaction).all():
        assert p.is_synthetic is True
        assert p.data_source == "SYNTHETIC"
        assert p.amount == p.net_amount + p.fee + p.tax


def test_bank_outage_scenario(mem_db):
    gen = PaymentDataGenerator(mem_db, seed=456)
    gen.generate_scenario(scenario="BANK_OUTAGE", count=150, days_back=1)

    hdfc_txns = mem_db.query(PaymentTransaction).filter(PaymentTransaction.bank == "HDFC").all()
    assert len(hdfc_txns) > 0
    hdfc_failures = [t for t in hdfc_txns if t.status == "FAILED"]
    # Bank outage forces failure rate > 60% on HDFC
    hdfc_fail_rate = len(hdfc_failures) / len(hdfc_txns)
    assert hdfc_fail_rate >= 0.50


def test_data_augmentation(mem_db):
    gen = PaymentDataGenerator(mem_db, seed=789)
    # Baseline
    gen.generate_scenario(scenario="NORMAL_TRAFFIC", count=50, days_back=1)
    # Augmentation
    aug_res = gen.augment_dataset(strategy="STRATIFIED_FAILURE_BALANCE", target_additional_records=30)

    assert aug_res["status"] == "AUGMENTATION_COMPLETE"
    assert aug_res["data_source"] == "AUGMENTED"

    augmented_txns = mem_db.query(PaymentTransaction).filter(PaymentTransaction.data_source == "AUGMENTED").all()
    assert len(augmented_txns) == 30
    for t in augmented_txns:
        assert t.augmentation_method == "STRATIFIED_FAILURE_BALANCE"
        assert t.is_synthetic is True


def test_data_availability_inspector(mem_db):
    gen = PaymentDataGenerator(mem_db, seed=999)
    gen.generate_scenario(scenario="NORMAL_TRAFFIC", count=60, days_back=2)

    report = inspect_data_availability(mem_db)
    assert "status" in report
    assert report["provenance"]["synthetic_records"] > 0
    assert "tables" in report
    assert report["tables"]["transactions"]["total"] == 60
    assert report["tables"]["merchants"]["total"] == len(MERCHANTS_MASTER)
    assert "distributions" in report
    assert report["distributions"]["failure_rate_pct"] >= 0.0
