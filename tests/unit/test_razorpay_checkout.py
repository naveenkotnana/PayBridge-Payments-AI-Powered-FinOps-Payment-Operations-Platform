"""Unit tests for Razorpay Standard Web Checkout API endpoints."""
import hashlib
import hmac
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.checkout import create_razorpay_order, verify_razorpay_payment, CreateOrderRequest, VerifyPaymentRequest
from app.core.config import settings
from app.db.base import Base
from app.models.payments import (
    Customer,
    Merchant,
    PaymentEvent,
    PaymentOrder,
    PaymentTransaction,
)
from fastapi import HTTPException


def test_cart_prices_override_client_amount(mem_db):
    from app.models.payments import CafeOrderItems
    response = create_razorpay_order(CreateOrderRequest(amount=100, items={"tea": 2}), db=mem_db)
    assert response.amount == 6000
    assert mem_db.get(PaymentOrder, response.order_id).amount == 60
    assert mem_db.get(CafeOrderItems, response.order_id).total == 60


def test_local_payment_key_rotation(monkeypatch, tmp_path):
    from app.api import checkout
    local = tmp_path / ".env"
    monkeypatch.setattr(checkout, "PAYMENT_ENV_PATH", local)
    local.write_text("RAZORPAY_KEY_ID=rzp_test_first\nRAZORPAY_KEY_SECRET=first-secret\n")
    assert checkout._payment_credentials() == ("rzp_test_first", "first-secret")
    local.write_text("RAZORPAY_KEY_ID=rzp_test_rotated\nRAZORPAY_KEY_SECRET=rotated-secret\n")
    assert checkout._payment_credentials() == ("rzp_test_rotated", "rotated-secret")


@pytest.fixture(autouse=True)
def provider_stub(monkeypatch, tmp_path):
    """No test should contact the payment provider or depend on real credentials."""
    from unittest.mock import MagicMock
    monkeypatch.setattr("app.api.checkout.PAYMENT_ENV_PATH", tmp_path / ".env")
    client = MagicMock()
    client.order.create.return_value = {"id": "order_unit_test"}
    client.payment.fetch.return_value = {"id": "pay_test_aarav_999", "order_id": "order_test_aarav_001",
                                         "amount": 28000, "currency": "INR", "status": "captured",
                                         "method": "upi", "bank": "HDFC"}
    client.utility.verify_payment_signature.side_effect = ValueError("Invalid signature")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "unit-test-secret")
    monkeypatch.setattr("app.api.checkout.razorpay.Client", lambda **kwargs: client)
    return client


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed merchant and customer
    m = Merchant(
        merchant_id="mid_rameshwaram_01",
        name="Rameshwaram Cafe",
        email="orders@rameshwaramcafe.in",
        business_category="FOOD_DELIVERY",
        status="ACTIVE",
    )
    c = Customer(
        customer_id="cust_aarav_01",
        merchant_id="mid_rameshwaram_01",
        name="Aarav",
        email="aarav@example.com",
    )
    session.add_all([m, c])
    session.commit()

    try:
        yield session
    finally:
        session.close()


def test_create_order_success(mem_db):
    """Test successful order creation for Aarav's ₹280 order (28000 paise)."""
    req = CreateOrderRequest(
        amount=28000,
        currency="INR",
        receipt="RC-ORDER-10291",
        merchant_id="mid_rameshwaram_01",
        customer_id="cust_aarav_01"
    )
    res = create_razorpay_order(req, db=mem_db)

    assert res.amount == 28000
    assert res.currency == "INR"
    assert res.receipt == "RC-ORDER-10291"
    assert res.order_id.startswith("order_")
    assert res.key_id == settings.RAZORPAY_KEY_ID

    # Check persistence in database
    db_order = mem_db.query(PaymentOrder).filter(PaymentOrder.order_id == res.order_id).first()
    assert db_order is not None
    assert float(db_order.amount) == 280.0
    assert db_order.status == "CREATED"


def test_create_order_validation_amount_below_minimum(mem_db):
    """Orders with amount less than 100 paise must be rejected with HTTP 400."""
    req = CreateOrderRequest(
        amount=50,  # 50 paise is < 100 paise
        currency="INR",
        receipt="RC-FAIL-01"
    )
    with pytest.raises(HTTPException) as exc_info:
        create_razorpay_order(req, db=mem_db)
    assert exc_info.value.status_code == 400


def test_verify_payment_valid_signature(mem_db):
    """Payment verification with valid HMAC-SHA256 signature captures transaction and updates order."""
    # First create an order
    order_id = "order_test_aarav_001"
    order = PaymentOrder(
        order_id=order_id,
        merchant_id="mid_rameshwaram_01",
        customer_id="cust_aarav_01",
        amount=280.0,
        currency="INR",
        receipt="RC-AARAV-001",
        status="CREATED"
    )
    mem_db.add(order)
    mem_db.commit()

    # Generate authentic HMAC-SHA256 signature
    payment_id = "pay_test_aarav_999"
    key_secret = settings.RAZORPAY_KEY_SECRET
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    sig = hmac.new(key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    req = VerifyPaymentRequest(
        razorpay_payment_id=payment_id,
        razorpay_order_id=order_id,
        razorpay_signature=sig
    )

    res = verify_razorpay_payment(req, db=mem_db)
    assert res.status == "success"
    assert res.payment_id == payment_id
    assert res.order_id == order_id

    # Verify order is marked PAID
    updated_order = mem_db.query(PaymentOrder).filter(PaymentOrder.order_id == order_id).first()
    assert updated_order.status == "PAID"

    # Verify transaction captured with MDR calculations
    txn = mem_db.query(PaymentTransaction).filter(PaymentTransaction.payment_id == payment_id).first()
    assert txn is not None
    assert txn.status == "CAPTURED"
    assert float(txn.amount) == 280.0
    assert float(txn.fee) == 5.60   # 2% of 280
    assert float(txn.tax) == 1.01   # 18% GST on 5.60
    assert float(txn.net_amount) == 273.39

    # Verify immutable PaymentEvent
    event = mem_db.query(PaymentEvent).filter(PaymentEvent.payment_id == payment_id).first()
    assert event is not None
    assert event.event_type == "PAYMENT_CAPTURED"


def test_verify_payment_invalid_signature_rejected(mem_db):
    """Tampered or invalid signature must be rejected with HTTP 400."""
    req = VerifyPaymentRequest(
        razorpay_payment_id="pay_tampered_001",
        razorpay_order_id="order_tampered_001",
        razorpay_signature="invalid_forged_signature_hex"
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_razorpay_payment(req, db=mem_db)
    assert exc_info.value.status_code == 400
    assert "Invalid Razorpay payment signature" in exc_info.value.detail


def test_security_secret_never_exposed(mem_db):
    """The server-side secret must never be included in any order response."""
    req = CreateOrderRequest(
        amount=28000,
        currency="INR",
        receipt="RC-SEC-001"
    )
    res = create_razorpay_order(req, db=mem_db)
    dump = res.model_dump()
    assert "key_secret" not in dump
    assert settings.RAZORPAY_KEY_SECRET not in str(dump)


def _signed_request(order_id="order_test_aarav_001", payment_id="pay_test_aarav_999"):
    signature = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return VerifyPaymentRequest(razorpay_order_id=order_id, razorpay_payment_id=payment_id, razorpay_signature=signature)


def test_missing_local_order_rejected(mem_db):
    with pytest.raises(HTTPException) as exc:
        verify_razorpay_payment(_signed_request(), db=mem_db)
    assert exc.value.status_code == 404
    assert mem_db.query(PaymentTransaction).count() == 0


@pytest.mark.parametrize("field,value", [("status", "authorized"), ("amount", 1), ("currency", "USD"), ("order_id", "other")])
def test_provider_mismatch_rejected(mem_db, provider_stub, field, value):
    mem_db.add(PaymentOrder(order_id="order_test_aarav_001", merchant_id="mid_rameshwaram_01", amount=280, currency="INR", status="CREATED"))
    mem_db.commit()
    provider_stub.payment.fetch.return_value[field] = value
    with pytest.raises(HTTPException) as exc:
        verify_razorpay_payment(_signed_request(), db=mem_db)
    assert exc.value.status_code == 409
    assert mem_db.query(PaymentTransaction).count() == 0
    assert mem_db.get(PaymentOrder, "order_test_aarav_001").status == "CREATED"


def test_provider_failure_never_creates_fake_order(mem_db, provider_stub):
    provider_stub.order.create.side_effect = RuntimeError("provider unavailable")
    with pytest.raises(HTTPException) as exc:
        create_razorpay_order(CreateOrderRequest(amount=28000), db=mem_db)
    assert exc.value.status_code == 502
    assert mem_db.query(PaymentOrder).count() == 0
