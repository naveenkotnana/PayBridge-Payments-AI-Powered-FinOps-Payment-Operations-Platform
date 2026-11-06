from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.payments import PaymentOrder, PaymentTransaction
from app.services.payment_support import lookup_payment


@pytest.fixture
def support_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for status in ["CAPTURED", "FAILED", "PENDING"]:
            db.add(PaymentTransaction(payment_id="pay_" + status.lower(), order_id="order_" + status.lower(), merchant_id="cafe", amount=Decimal("280.00"), net_amount=280, method="UPI", gateway="TEST", status=status, data_source="SYNTHETIC"))
        db.commit()
        yield db
    engine.dispose()


def test_success_from_question(support_db):
    result = lookup_payment(support_db, "Did pay_captured complete?")
    assert result["matches"][0]["status"] == "CAPTURED"
    assert "captured" in result["matches"][0]["explanation"]


def test_failure_does_not_invent_cause(support_db):
    result = lookup_payment(support_db, "pay_failed")["matches"][0]
    assert "cause cannot be determined" in result["explanation"]


def test_recorded_failure_reason(support_db):
    row = support_db.get(PaymentTransaction, "pay_failed")
    row.error_description = "Bank declined the request"
    support_db.commit()
    assert row.error_description in lookup_payment(support_db, "pay_failed")["matches"][0]["explanation"]


def test_pending_is_not_success(support_db):
    assert "not recorded as captured" in lookup_payment(support_db, "order_pending")["matches"][0]["explanation"]


def test_missing_is_not_failed(support_db):
    result = lookup_payment(support_db, "pay_missing")
    assert not result["matches"]
    assert "does not prove" in result["message"]


def test_order_without_payment(support_db):
    support_db.add(PaymentOrder(order_id="order_unpaid", merchant_id="cafe", amount=280, status="CREATED"))
    support_db.commit()
    result = lookup_payment(support_db, "order_unpaid")
    assert result["order_status"] == "CREATED" and not result["matches"]


def test_multiple_references_rejected(support_db):
    with pytest.raises(ValueError):
        lookup_payment(support_db, "pay_failed and pay_captured")
