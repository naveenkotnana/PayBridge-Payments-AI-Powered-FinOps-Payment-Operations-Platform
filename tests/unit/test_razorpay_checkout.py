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
