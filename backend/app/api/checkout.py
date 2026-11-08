"""Razorpay Standard Checkout with server-priced, authenticated, idempotent orders."""
import datetime as dt
from decimal import Decimal
import hashlib
import hmac
import json
import logging
import uuid
from typing import Dict

import razorpay
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import require
from app.db.base import get_db
from app.models import User
from app.models.ops import AuditLog
from app.models.payments import (
    CafeOrderItems, CheckoutRequest, Customer, Merchant, PaymentEvent,
    PaymentOrder, PaymentTransaction,
)
from app.services.cafe_menu import cart_json, price_cart

log = logging.getLogger("paybridge.checkout")
router = APIRouter(prefix="/api", tags=["checkout"])
TWO_PLACES = Decimal("0.01")


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: Dict[str, StrictInt]
    currency: str = Field(default="INR", min_length=3, max_length=3)


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    receipt: str


class VerifyPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    razorpay_payment_id: str = Field(min_length=1, max_length=40)
    razorpay_order_id: str = Field(min_length=1, max_length=40)
    razorpay_signature: str = Field(min_length=1, max_length=128)


class VerifyPaymentResponse(BaseModel):
    status: str
    message: str
    payment_id: str
    order_id: str


def _amount_minor(amount: Decimal) -> int:
    return int((amount * 100).to_integral_exact())


def _credentials() -> tuple[str, str]:
    """Use centrally loaded environment settings; never read a secret file per request."""
    key_id = settings.RAZORPAY_KEY_ID.strip()
    key_secret = settings.RAZORPAY_KEY_SECRET.strip()
    if not key_id or not key_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Razorpay checkout is not configured on this service.")
    return key_id, key_secret


def _idempotency_fingerprint(customer_id: str, merchant_id: str,
                             items: Dict[str, int], amount_minor: int,
                             currency: str) -> str:
    payload = {"customer_id": customer_id, "merchant_id": merchant_id,
               "items": dict(sorted(items.items())), "amount_minor": amount_minor,
               "currency": currency}
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def create_razorpay_order(req: CreateOrderRequest, db: Session, *,
                          customer_id: str, merchant_id: str,
                          idempotency_key: str) -> CreateOrderResponse:
    """Internal service. Identity must be supplied by a trusted caller, never the request body."""
    if not idempotency_key or len(idempotency_key) > 100:
        raise HTTPException(400, "A valid Idempotency-Key header is required.")
    if req.currency != "INR":
        raise HTTPException(400, "This checkout supports INR only.")
    try:
        cart_rows, total = price_cart(req.items)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    amount_minor = _amount_minor(total)
    if not 100 <= amount_minor <= 1_000_000_00:
        raise HTTPException(400, "Order amount must be between ₹1 and ₹10,00,000.")
    key_id, key_secret = _credentials()

    merchant = db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()
    customer = db.query(Customer).filter(Customer.customer_id == customer_id,
                                         Customer.merchant_id == merchant_id).first()
    if not merchant or merchant.status != "ACTIVE" or not customer:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Customer is not authorized for this merchant.")

    fingerprint = _idempotency_fingerprint(customer_id, merchant_id, req.items,
                                           amount_minor, req.currency)
    reservation = db.query(CheckoutRequest).filter_by(idempotency_key=idempotency_key).first()
    if reservation:
        if reservation.customer_id != customer_id or reservation.request_fingerprint != fingerprint:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "Idempotency key was already used for a different checkout request.")
        if (reservation.state == "CREATED" and reservation.provider_order_id
                and db.query(PaymentOrder).filter_by(order_id=reservation.provider_order_id).first()):
            return CreateOrderResponse(order_id=reservation.provider_order_id,
                                       amount=reservation.amount_minor,
                                       currency=reservation.currency,
                                       key_id=reservation.provider_key_id or settings.RAZORPAY_KEY_ID,
                                       receipt=reservation.receipt)
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "This checkout request is still processing or needs reconciliation. Retry with the same key later.")

    receipt = f"PB-{uuid.uuid4().hex[:20].upper()}"
    reservation = CheckoutRequest(
        idempotency_key=idempotency_key, customer_id=customer_id,
        merchant_id=merchant_id, request_fingerprint=fingerprint,
        amount_minor=amount_minor, currency=req.currency,
        receipt=receipt, items_json=cart_json(cart_rows), state="PROCESSING",
    )
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "A request with this idempotency key is already being processed.") from exc

    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        result = client.order.create(data={
            "amount": amount_minor, "currency": req.currency,
            "receipt": receipt, "payment_capture": 1,
        })
        provider_order_id = result.get("id")
        if not provider_order_id or len(provider_order_id) > 40:
            raise RuntimeError("provider response missing valid order identifier")
    except Exception as exc:
        db.query(CheckoutRequest).filter_by(idempotency_key=idempotency_key).update(
            {"state": "UNCERTAIN", "last_error_code": "PROVIDER_CREATE_UNCERTAIN"})
        db.commit()
        log.warning("Razorpay order request failed or returned an uncertain result")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            "Payment provider could not confirm order creation. Reconciliation is required before retrying.") from exc

    # Save the provider reference first. If the following local-order transaction
    # fails, a reconciler still has the provider identifier needed to query state.
    reservation = db.query(CheckoutRequest).filter_by(idempotency_key=idempotency_key).one()
    reservation.provider_order_id = provider_order_id
    reservation.provider_key_id = key_id
    reservation.state = "CREATED"
    try:
        db.commit()
        db.add(PaymentOrder(
            order_id=provider_order_id, merchant_id=merchant_id,
            customer_id=customer_id, amount=total, currency=req.currency,
            receipt=receipt, status="CREATED", is_synthetic=False,
            data_source="RAZORPAY_TEST" if key_id.startswith("rzp_test_") else "REAL",
        ))
        db.add(CafeOrderItems(order_id=provider_order_id,
                              items_json=cart_json(cart_rows), total=total))
        db.commit()
    except Exception as exc:
        db.rollback()
        log.exception("Local persistence failed for provider order reference")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Provider order exists but local persistence needs reconciliation. Do not create another payment.") from exc

    return CreateOrderResponse(order_id=provider_order_id, amount=amount_minor,
                               currency=req.currency, key_id=key_id, receipt=receipt)


def verify_razorpay_payment(req: VerifyPaymentRequest, db: Session, *,
                            customer_id: str, user_id: str | None = None) -> VerifyPaymentResponse:
    """Verify provider signature/state then atomically persist the local result."""
    key_id, key_secret = _credentials()
    expected_sig = hmac.new(key_secret.encode(),
                            f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode(),
                            hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, req.razorpay_signature.strip().lower()):
        raise HTTPException(400, "Invalid Razorpay payment signature. Verification failed.")

    order = db.query(PaymentOrder).filter_by(order_id=req.razorpay_order_id,
                                             customer_id=customer_id).with_for_update().first()
    if order is None:
        raise HTTPException(404, "Payment order not found for this customer.")
    existing = db.query(PaymentTransaction).filter_by(payment_id=req.razorpay_payment_id).first()
    if existing:
        if existing.order_id == order.order_id and existing.status == "CAPTURED" and order.status == "PAID":
            return VerifyPaymentResponse(status="success", message="Payment already verified",
                                         payment_id=req.razorpay_payment_id, order_id=order.order_id)
        raise HTTPException(409, "Payment identifier conflicts with an existing transaction.")
    if order.status not in {"CREATED", "ATTEMPTED"}:
        raise HTTPException(409, "Order is not in a state that can be verified.")

    try:
        payment = razorpay.Client(auth=(key_id, key_secret)).payment.fetch(req.razorpay_payment_id)
    except Exception as exc:
        log.warning("Razorpay payment status lookup failed")
        raise HTTPException(502, "Could not confirm payment status with provider.") from exc
    if (payment.get("id") != req.razorpay_payment_id
            or payment.get("order_id") != order.order_id
            or payment.get("amount") != _amount_minor(Decimal(str(order.amount)))
            or payment.get("currency") != order.currency
            or payment.get("status") != "captured"):
        raise HTTPException(409, "Provider payment is not captured or does not match the stored order.")

    amount = Decimal(str(order.amount)).quantize(TWO_PLACES)
    fee = (amount * Decimal("0.02")).quantize(TWO_PLACES)
    tax = (fee * Decimal("0.18")).quantize(TWO_PLACES)
    now = dt.datetime.now(dt.timezone.utc)
    order.status = "PAID"
    db.add(PaymentTransaction(
        payment_id=req.razorpay_payment_id, order_id=order.order_id,
        merchant_id=order.merchant_id, customer_id=order.customer_id,
        amount=amount, currency=order.currency,
        method=str(payment.get("method", "unknown")).upper(), bank=payment.get("bank"),
        gateway="RAZORPAY_DIRECT", status="CAPTURED", fee=fee, tax=tax,
        net_amount=amount - fee - tax, reconciled=False, is_synthetic=False,
        data_source="RAZORPAY_TEST" if key_id.startswith("rzp_test_") else "REAL",
    ))
    db.add(PaymentEvent(
        event_id=f"evt_{uuid.uuid4().hex[:14]}", payment_id=req.razorpay_payment_id,
        event_type="PAYMENT_CAPTURED", event_source="RAZORPAY_CHECKOUT",
        idempotency_key=f"{req.razorpay_payment_id}::PAYMENT_CAPTURED",
        event_payload=json.dumps({"payment_id": req.razorpay_payment_id,
                                  "order_id": order.order_id,
                                  "status": "captured", "method": payment.get("method"),
                                  "amount_minor": _amount_minor(amount)}, sort_keys=True),
        occurred_at=now,
    ))
    db.add(AuditLog(
        audit_id=f"AUD-{uuid.uuid4().hex[:12].upper()}",
        workflow_id="RAZORPAY_STANDARD_CHECKOUT", user_id=user_id or customer_id,
        agent_node="checkout_gateway", tool_name="razorpay_verify",
        input_hash=hashlib.sha256(f"{order.order_id}:{req.razorpay_payment_id}".encode()).hexdigest(),
        result_status="CAPTURED", latency_ms=0,
        action="PAYMENT_VERIFIED_AND_ORDER_CONFIRMED", timestamp=now,
    ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        prior = db.query(PaymentTransaction).filter_by(payment_id=req.razorpay_payment_id).first()
        current_order = db.query(PaymentOrder).filter_by(order_id=order.order_id,
                                                         customer_id=customer_id).first()
        if prior and prior.order_id == order.order_id and prior.status == "CAPTURED" and current_order and current_order.status == "PAID":
            return VerifyPaymentResponse(status="success", message="Payment already verified",
                                         payment_id=req.razorpay_payment_id, order_id=order.order_id)
        raise HTTPException(409, "Payment verification conflicted with another update.") from exc
    return VerifyPaymentResponse(status="success", message="Payment verified and recorded successfully",
                                 payment_id=req.razorpay_payment_id, order_id=req.razorpay_order_id)


@router.post("/create-order", response_model=CreateOrderResponse,
             status_code=status.HTTP_201_CREATED)
def create_order_endpoint(
    req: CreateOrderRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=100),
    user: User = Depends(require("customer_checkout")),
    db: Session = Depends(get_db),
):
    if not user.customer_id or not settings.CHECKOUT_MERCHANT_ID:
        raise HTTPException(403, "Authenticated customer is not configured for checkout.")
    return create_razorpay_order(req, db, customer_id=user.customer_id,
                                 merchant_id=settings.CHECKOUT_MERCHANT_ID,
                                 idempotency_key=idempotency_key)


@router.post("/verify-payment", response_model=VerifyPaymentResponse)
def verify_payment_endpoint(
    req: VerifyPaymentRequest,
    user: User = Depends(require("customer_checkout")),
    db: Session = Depends(get_db),
):
    if not user.customer_id:
        raise HTTPException(403, "Authenticated user is not a customer.")
    return verify_razorpay_payment(req, db, customer_id=user.customer_id, user_id=user.user_id)
