"""Unit tests for Razorpay Test Mode Webhook Gateway with HMAC-SHA256 signature verification."""
from decimal import Decimal
import hashlib
import hmac
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.payments import (
    Merchant,
    PaymentEvent,
    PaymentOrder,
    PaymentTransaction,
)
from app.api.webhooks import (
    process_webhook_payload,
    verify_razorpay_signature,
)


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed default merchant
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
        yield session
    finally:
        session.close()


def test_signature_verification_valid():
    secret = "test_webhook_secret_123"
    payload_bytes = b'{"event":"payment.captured","id":"evt_101"}'
    valid_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    assert verify_razorpay_signature(payload_bytes, valid_sig, secret) is True


def test_signature_verification_invalid():
    secret = "test_webhook_secret_123"
    payload_bytes = b'{"event":"payment.captured","id":"evt_101"}'
    fake_sig = "fake_hex_signature_abc123"

    assert verify_razorpay_signature(payload_bytes, fake_sig, secret) is False
    assert verify_razorpay_signature(payload_bytes, "", secret) is False
    assert verify_razorpay_signature(payload_bytes, None, secret) is False


def test_webhook_payment_captured_lifecycle(mem_db):
    session = mem_db
    payload = {
        "event": "payment.captured",
        "event_id": "evt_test_cap_001",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_cap_001",
                    "amount": 250000,  # 2500.00 in paise
                    "currency": "INR",
                    "status": "captured",
                    "method": "upi",
                    "bank": "SBI",
                    "order_id": "order_test_cap_001",
                    "email": "aarav.sharma@example.com",
                    "contact": "+919876543210",
                }
            }
        }
    }

    action, pid = process_webhook_payload(
        db=session,
        payload=payload,
        event_id="evt_test_cap_001",
        event_type="payment.captured",
        raw_body_str=json.dumps(payload),
    )

    assert action == "PROCESSED"
    assert pid == "pay_test_cap_001"

    # Verify transaction in database
    txn = session.query(PaymentTransaction).filter(PaymentTransaction.payment_id == "pay_test_cap_001").first()
    assert txn is not None
    assert txn.status == "CAPTURED"
    assert txn.amount == Decimal("2500.00")
    assert txn.method == "UPI"
    assert txn.bank == "SBI"
    assert txn.captured_at is not None

    # Verify order in database
    ord_obj = session.query(PaymentOrder).filter(PaymentOrder.order_id == "order_test_cap_001").first()
    assert ord_obj is not None
    assert ord_obj.status == "PAID"

    # Verify immutable event log
    evt = session.query(PaymentEvent).filter(PaymentEvent.event_id == "evt_test_cap_001").first()
    assert evt is not None
    assert evt.event_source == "RAZORPAY_WEBHOOK"


def test_webhook_deduplication_idempotency(mem_db):
    session = mem_db
    payload = {
        "event": "payment.authorized",
        "event_id": "evt_test_dup_001",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_dup_001",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "authorized",
                    "method": "card",
                    "bank": "HDFC",
                }
            }
        }
    }

    # First delivery
    action1, pid1 = process_webhook_payload(
        db=session,
        payload=payload,
        event_id="evt_test_dup_001",
        event_type="payment.authorized",
        raw_body_str=json.dumps(payload),
    )
    assert action1 == "PROCESSED"

    # Second delivery (duplicate retry from gateway)
    action2, pid2 = process_webhook_payload(
        db=session,
        payload=payload,
        event_id="evt_test_dup_001",
        event_type="payment.authorized",
        raw_body_str=json.dumps(payload),
    )
    assert action2 == "DUPLICATE_ACKNOWLEDGED"

    # Ensure only 1 event record stored
    events = session.query(PaymentEvent).filter(PaymentEvent.event_id == "evt_test_dup_001").all()
    assert len(events) == 1


def test_webhook_payment_failed_lifecycle(mem_db):
    session = mem_db
    payload = {
        "event": "payment.failed",
        "event_id": "evt_test_fail_001",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_fail_001",
                    "amount": 49900,
                    "currency": "INR",
                    "status": "failed",
                    "method": "upi",
                    "bank": "AXIS",
                    "error_code": "BAD_REQUEST_GATEWAY_DOWN",
                    "error_description": "Aggregator gateway timeout",
                }
            }
        }
    }

    action, pid = process_webhook_payload(
        db=session,
        payload=payload,
        event_id="evt_test_fail_001",
        event_type="payment.failed",
        raw_body_str=json.dumps(payload),
    )

    assert action == "PROCESSED"
    txn = session.query(PaymentTransaction).filter(PaymentTransaction.payment_id == "pay_test_fail_001").first()
    assert txn.status == "FAILED"
    assert txn.error_code == "BAD_REQUEST_GATEWAY_DOWN"
