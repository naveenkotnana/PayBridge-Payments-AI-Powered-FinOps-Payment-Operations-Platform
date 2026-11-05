"""Unit tests for Canonical Payment CSV Ingestion Pipeline & Data Lineage."""
from decimal import Decimal
import io
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.payments import (
    Merchant,
    PaymentIngestionRecord,
    PaymentIngestionRun,
    PaymentTransaction,
)
from app.services.ingestion_payments import (
    PaymentCSVIngestionService,
    detect_column_mapping,
    parse_timestamp,
)


@pytest.fixture
def mem_db(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-seed default merchant
    m = Merchant(
        merchant_id="mid_swiggy_01",
        name="Swiggy India",
        email="finance@swiggy.in",
        business_category="FOOD_DELIVERY",
        settlement_cycle="T+1",
        pricing_plan="ENTERPRISE",
        risk_tier="LOW",
        is_synthetic=True,
    )
    session.add(m)
    session.commit()

    try:
        yield session, tmp_path
    finally:
        session.close()


def test_detect_column_mapping_varied_headers():
    headers_1 = ["txn_id", "txn_amount", "currency_code", "payment_mode", "payment_status"]
    mapping_1 = detect_column_mapping(headers_1)
    assert mapping_1["payment_id"] == "txn_id"
    assert mapping_1["amount"] == "txn_amount"
    assert mapping_1["currency"] == "currency_code"
    assert mapping_1["method"] == "payment_mode"
    assert mapping_1["status"] == "payment_status"

    headers_2 = ["payment_reference", "gross_amount", "bank_name", "date"]
    mapping_2 = detect_column_mapping(headers_2)
    assert mapping_2["payment_id"] == "payment_reference"
    assert mapping_2["amount"] == "gross_amount"
    assert mapping_2["bank"] == "bank_name"
    assert mapping_2["timestamp"] == "date"


def test_parse_timestamp():
    dt1 = parse_timestamp("2026-05-10 14:30:00")
    assert dt1.year == 2026
    assert dt1.month == 5
    assert dt1.day == 10
    assert dt1.hour == 14

    dt2 = parse_timestamp("2026-05-10T14:30:00Z")
    assert dt2.year == 2026


def test_ingest_valid_csv(mem_db):
    session, tmp_path = mem_db
    service = PaymentCSVIngestionService(session, archive_dir=tmp_path / "archive", rejected_dir=tmp_path / "rejected")

    csv_data = """transaction_id,amount,currency,payment_method,status,bank,date
pay_test_001,1500.00,INR,UPI,CAPTURED,SBI,2026-05-10 12:00:00
pay_test_002,2400.50,INR,CARD,SUCCESS,HDFC,2026-05-10 12:05:00
pay_test_003,300.00,INR,NETBANKING,FAILED,ICICI,2026-05-10 12:10:00
"""
    buffer = io.StringIO(csv_data)
    result = service.ingest_csv_file(buffer, source_name="test_payments.csv")

    assert result["status"] == "COMPLETED"
    assert result["records_received"] == 3
    assert result["records_accepted"] == 3
    assert result["records_rejected"] == 0
    assert result["records_duplicated"] == 0

    # Verify persisted in database
    txns = session.query(PaymentTransaction).all()
    assert len(txns) == 3

    t1 = session.query(PaymentTransaction).filter(PaymentTransaction.payment_id == "pay_test_001").first()
    assert t1.amount == Decimal("1500.00")
    assert t1.method == "UPI"
    assert t1.status == "CAPTURED"
    assert t1.bank == "SBI"
    # Mathematical invariant
    assert t1.amount == t1.net_amount + t1.fee + t1.tax

    # Verify IngestionRun lineage
    runs = session.query(PaymentIngestionRun).all()
    assert len(runs) == 1
    assert runs[0].records_accepted == 3
    assert Path(runs[0].raw_file_path).exists()


def test_ingest_csv_with_rejected_rows_and_duplicates(mem_db):
    session, tmp_path = mem_db
    service = PaymentCSVIngestionService(session, archive_dir=tmp_path / "archive", rejected_dir=tmp_path / "rejected")

    csv_data = """txn_id,txn_amount,currency,payment_mode,payment_status
pay_dup_001,500.00,INR,UPI,CAPTURED
pay_dup_001,500.00,INR,UPI,CAPTURED
pay_invalid_amt,-200.00,INR,UPI,CAPTURED
pay_bad_curr,1000.00,USD,UPI,CAPTURED
,750.00,INR,UPI,CAPTURED
pay_valid_002,1200.00,INR,CARD,PAID
"""
    buffer = io.StringIO(csv_data)
    result = service.ingest_csv_file(buffer, source_name="mixed_batch.csv")

    assert result["status"] == "COMPLETED"
    assert result["records_received"] == 6
    assert result["records_accepted"] == 2  # pay_dup_001 (first occurrence) & pay_valid_002
    assert result["records_rejected"] == 4  # 1 duplicate + 1 negative + 1 USD + 1 missing ID
    assert result["records_duplicated"] == 1

    # Check rejected report file was generated
    assert result["rejected_file_generated"] is not None
    rej_path = Path(result["rejected_file_generated"])
    assert rej_path.exists()

    # Verify rejected audit records in database
    rej_records = session.query(PaymentIngestionRecord).all()
    assert len(rej_records) == 4
    reasons = [r.rejection_reason for r in rej_records]
    assert any("Duplicate" in r for r in reasons)
    assert any("Non-positive" in r for r in reasons)
    assert any("Unsupported currency" in r for r in reasons)
    assert any("Missing payment_id" in r for r in reasons)
