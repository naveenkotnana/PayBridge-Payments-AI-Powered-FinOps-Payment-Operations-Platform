"""Provider-stubbed checkout safety tests; no test calls Razorpay's network."""
import hashlib
import hmac
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.checkout import (
    CreateOrderRequest, VerifyPaymentRequest, create_razorpay_order,
    verify_razorpay_payment,
)
from app.core.config import settings
from app.db.base import Base
from app.models.payments import (
    CafeOrderItems, CheckoutRequest, Customer, Merchant, PaymentEvent,
    PaymentOrder, PaymentTransaction,
)


@pytest.fixture
def provider_stub(monkeypatch):
    client = MagicMock()
    client.order.create.return_value = {"id": "order_unit_test"}
    client.payment.fetch.return_value = {
        "id": "pay_unit_test", "order_id": "order_unit_test",
        "amount": 28000, "currency": "INR", "status": "captured",
        "method": "upi", "bank": "HDFC",
    }
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "unit-test-secret")
    monkeypatch.setattr("app.api.checkout.razorpay.Client", lambda **kwargs: client)
    return client


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Merchant(merchant_id="mid_rameshwaram_01", name="Rameshwaram Cafe",
                 email="orders@example.com", status="ACTIVE"),
        Customer(customer_id="cust_aarav_01", merchant_id="mid_rameshwaram_01",
                 name="Aarav", email="aarav@example.com"),
    ])
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def create(db, key="key-1", items=None, customer="cust_aarav_01"):
    if items is None:
        items = {"masala_dosa": 2, "filter_coffee": 1}
    return create_razorpay_order(
        CreateOrderRequest(items=items),
        db, customer_id=customer, merchant_id="mid_rameshwaram_01",
        idempotency_key=key,
    )


def signed(order_id="order_unit_test", payment_id="pay_unit_test", secret="unit-test-secret"):
    signature = hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return VerifyPaymentRequest(razorpay_order_id=order_id,
                                razorpay_payment_id=payment_id,
                                razorpay_signature=signature)


def test_server_prices_cart_and_persists_order(mem_db, provider_stub):
    response = create(mem_db)
    assert response.amount == 28000
    assert response.currency == "INR"
    assert response.key_id == "rzp_test_unit"
    assert mem_db.get(PaymentOrder, response.order_id).amount == 280
    assert mem_db.get(CafeOrderItems, response.order_id).total == 280
    assert provider_stub.order.create.call_args.kwargs["data"]["amount"] == 28000


def test_same_idempotency_request_returns_same_order_without_second_provider_call(mem_db, provider_stub):
    first = create(mem_db)
    second = create(mem_db)
    assert second.order_id == first.order_id
    assert provider_stub.order.create.call_count == 1
    assert mem_db.query(PaymentOrder).count() == 1


def test_idempotency_key_cannot_be_reused_for_different_cart(mem_db, provider_stub):
    create(mem_db)
    with pytest.raises(HTTPException) as exc:
        create(mem_db, items={"tea": 1})
    assert exc.value.status_code == 409
    assert provider_stub.order.create.call_count == 1


@pytest.mark.parametrize("items", [{}, {"bad_item": 1}, {"tea": 11}, {"tea": -1}])
def test_invalid_cart_rejected_before_provider_call(mem_db, provider_stub, items):
    with pytest.raises(HTTPException) as exc:
        create(mem_db, items=items)
    assert exc.value.status_code == 400
    assert provider_stub.order.create.call_count == 0


def test_customer_must_belong_to_configured_merchant(mem_db, provider_stub):
    with pytest.raises(HTTPException) as exc:
        create(mem_db, customer="cust_not_present")
    assert exc.value.status_code == 403
    assert provider_stub.order.create.call_count == 0


def test_missing_credentials_fail_before_reservation_or_provider_call(mem_db, provider_stub, monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "")
    with pytest.raises(HTTPException) as exc:
        create(mem_db)
    assert exc.value.status_code == 503
    assert mem_db.query(CheckoutRequest).count() == 0
    assert provider_stub.order.create.call_count == 0


def test_provider_create_timeout_leaves_uncertain_idempotent_reservation(mem_db, provider_stub):
    provider_stub.order.create.side_effect = TimeoutError("provider timeout")
    with pytest.raises(HTTPException) as exc:
        create(mem_db)
    assert exc.value.status_code == 502
    reservation = mem_db.get(CheckoutRequest, "key-1")
    assert reservation.state == "UNCERTAIN"
    assert mem_db.query(PaymentOrder).count() == 0
    with pytest.raises(HTTPException) as repeated:
        create(mem_db)
    assert repeated.value.status_code == 409


def test_invalid_signature_never_changes_order_or_payment_state(mem_db, provider_stub):
    create(mem_db)
    req = signed()
    req.razorpay_signature = "invalid"
    with pytest.raises(HTTPException) as exc:
        verify_razorpay_payment(req, mem_db, customer_id="cust_aarav_01")
    assert exc.value.status_code == 400
    assert mem_db.get(PaymentOrder, "order_unit_test").status == "CREATED"
    assert mem_db.query(PaymentTransaction).count() == 0


def test_wrong_customer_cannot_verify_order(mem_db, provider_stub):
    create(mem_db)
    with pytest.raises(HTTPException) as exc:
        verify_razorpay_payment(signed(), mem_db, customer_id="other_customer")
    assert exc.value.status_code == 404
    assert mem_db.query(PaymentTransaction).count() == 0


@pytest.mark.parametrize("field,value", [
    ("id", "another_payment"), ("status", "authorized"),
    ("amount", 1), ("currency", "USD"), ("order_id", "another_order"),
])
def test_provider_mismatch_rejected_without_state_change(mem_db, provider_stub, field, value):
    create(mem_db)
    provider_stub.payment.fetch.return_value[field] = value
    with pytest.raises(HTTPException) as exc:
        verify_razorpay_payment(signed(), mem_db, customer_id="cust_aarav_01")
    assert exc.value.status_code == 409
    assert mem_db.query(PaymentTransaction).count() == 0
    assert mem_db.get(PaymentOrder, "order_unit_test").status == "CREATED"


def test_successful_verification_is_idempotent(mem_db, provider_stub):
    create(mem_db)
    first = verify_razorpay_payment(signed(), mem_db, customer_id="cust_aarav_01")
    second = verify_razorpay_payment(signed(), mem_db, customer_id="cust_aarav_01")
    assert first.status == second.status == "success"
    assert mem_db.get(PaymentOrder, "order_unit_test").status == "PAID"
    assert mem_db.query(PaymentTransaction).count() == 1
    assert mem_db.query(PaymentEvent).count() == 1


def test_provider_fetch_failure_does_not_mark_paid(mem_db, provider_stub):
    create(mem_db)
    provider_stub.payment.fetch.side_effect = TimeoutError("provider unavailable")
    with pytest.raises(HTTPException) as exc:
        verify_razorpay_payment(signed(), mem_db, customer_id="cust_aarav_01")
    assert exc.value.status_code == 502
    assert mem_db.get(PaymentOrder, "order_unit_test").status == "CREATED"
    assert mem_db.query(PaymentTransaction).count() == 0


def test_reconciliation_recovers_provider_order_after_local_write_failure(mem_db, provider_stub):
    from app.models.payments import CheckoutRequest
    from app.services.checkout_reconciliation import reconcile_checkout_orders

    mem_db.add(CheckoutRequest(
        idempotency_key="recover-key", customer_id="cust_aarav_01",
        merchant_id="mid_rameshwaram_01", request_fingerprint="a" * 64,
        items_json='[{"item_id":"masala_dosa","quantity":2}]',
        amount_minor=28000, currency="INR", receipt="PB-RECOVER",
        state="CREATED", provider_order_id="order_unit_test",
    ))
    mem_db.commit()
    provider_stub.order.fetch.return_value = {
        "id": "order_unit_test", "amount": 28000, "currency": "INR",
        "receipt": "PB-RECOVER", "status": "created",
    }
    assert reconcile_checkout_orders(mem_db) == {"checked": 1, "recovered": 1, "deferred": 0}
    restored = mem_db.get(PaymentOrder, "order_unit_test")
    assert restored.amount == 280
    assert restored.status == "CREATED"
    assert mem_db.get(CafeOrderItems, "order_unit_test").items_json.startswith("[")


def test_reconciliation_does_not_restore_mismatched_provider_order(mem_db, provider_stub):
    from app.models.payments import CheckoutRequest
    from app.services.checkout_reconciliation import reconcile_checkout_orders

    mem_db.add(CheckoutRequest(
        idempotency_key="recover-key", customer_id="cust_aarav_01",
        merchant_id="mid_rameshwaram_01", request_fingerprint="a" * 64,
        items_json="[]", amount_minor=28000, currency="INR",
        receipt="PB-RECOVER", state="CREATED", provider_order_id="order_unit_test",
    ))
    mem_db.commit()
    provider_stub.order.fetch.return_value = {
        "id": "order_unit_test", "amount": 1, "currency": "INR",
        "receipt": "PB-RECOVER", "status": "created",
    }
    assert reconcile_checkout_orders(mem_db) == {"checked": 1, "recovered": 0, "deferred": 1}
    assert mem_db.query(PaymentOrder).count() == 0
