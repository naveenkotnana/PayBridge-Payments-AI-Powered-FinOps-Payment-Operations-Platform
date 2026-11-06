"""Razorpay Standard Web Checkout API endpoints: Order creation and Payment verification."""
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import hmac
import json
import logging
import uuid
from pathlib import Path
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, StrictInt
import razorpay
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import get_db
from app.models.ops import AuditLog
from app.models.payments import (
    Merchant,
    PaymentEvent,
    PaymentOrder,
    PaymentTransaction,
    CafeOrderItems,
)
from app.services.cafe_menu import cart_json, price_cart

log = logging.getLogger("paybridge.checkout")
router = APIRouter(prefix="/api", tags=["checkout"])

TWO_PLACES = Decimal("0.01")
PAYMENT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


def _payment_credentials():
    """Read the local payment pair per request, including after key rotation."""
    from dotenv import dotenv_values
    local = dotenv_values(PAYMENT_ENV_PATH) if PAYMENT_ENV_PATH.is_file() else {}
    return (local.get("RAZORPAY_KEY_ID") or settings.RAZORPAY_KEY_ID,
            local.get("RAZORPAY_KEY_SECRET") or settings.RAZORPAY_KEY_SECRET)


def _dec(val) -> Decimal:
    return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class CreateOrderRequest(BaseModel):
    amount: int = Field(..., description="Amount in smallest currency unit (paise for INR). Must be >= 100 paise.")
    currency: str = Field(default="INR", description="Currency code (e.g. INR)")
    receipt: Optional[str] = Field(default=None, description="Internal receipt / order reference")
    merchant_id: Optional[str] = Field(default="mid_rameshwaram_01", description="Merchant ID")
    customer_id: Optional[str] = Field(default="cust_aarav_01", description="Customer ID")
    items: Optional[Dict[str, StrictInt]] = None


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    receipt: str


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    status: str
    message: str
    payment_id: str
    order_id: str


@router.post("/create-order", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
def create_razorpay_order(req: CreateOrderRequest, db: Session = Depends(get_db)):
    """Create a new Razorpay order for Standard Web Checkout."""
    cart_rows = None
    if req.items is not None:
        try:
            cart_rows, total = price_cart(req.items)
            req.amount = int(total * 100)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
    if not isinstance(req.amount, int) or req.amount < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be an integer greater than or equal to 100 paise (₹1.00)."
        )

    receipt = req.receipt or f"RC-{uuid.uuid4().hex[:8].upper()}"
    key_id, key_secret = _payment_credentials()

    if not key_id or not key_secret or key_id == "rzp_test_mock_finops_key" or key_secret == "mock_finops_secret_opspilot":
        raise HTTPException(503, "Razorpay checkout is not configured. The operations demo uses synthetic CSV payments.")
    if req.currency.upper() != "INR":
        raise HTTPException(400, "This prototype supports INR only.")
    order_id = None
    # 1. Attempt live Razorpay API order creation via official SDK
    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        order_payload = {
            "amount": req.amount,
            "currency": req.currency.upper(),
            "receipt": receipt,
            "payment_capture": 1,
        }
        rzp_order = client.order.create(data=order_payload)
        order_id = rzp_order.get("id")
    except Exception:
        log.warning("Razorpay order creation failed", exc_info=True)
        raise HTTPException(502, "Payment provider could not create an order. Please retry later.")
    if not order_id:
        raise HTTPException(502, "Payment provider returned no order identifier.")

    # 2. Persist order in local database
    order_amount_rs = _dec(Decimal(req.amount) / Decimal(100))
    existing_order = db.query(PaymentOrder).filter(PaymentOrder.order_id == order_id).first()
    if not existing_order:
        # Verify or ensure merchant exists
        merchant = db.query(Merchant).filter(Merchant.merchant_id == req.merchant_id).first()
        if not merchant:
            merchant = Merchant(
                merchant_id=req.merchant_id,
                name="Rameshwaram Cafe",
                email="accounts@rameshwaramcafe.in",
                business_category="FOOD_DELIVERY",
                status="ACTIVE",
            )
            db.add(merchant)

        db_order = PaymentOrder(
            order_id=order_id,
            merchant_id=req.merchant_id or "mid_rameshwaram_01",
            customer_id=req.customer_id or "cust_aarav_01",
            amount=order_amount_rs,
            currency=req.currency.upper(),
            receipt=receipt,
            status="CREATED",
            is_synthetic=False,
            data_source="RAZORPAY_TEST" if key_id.startswith("rzp_test_") else "REAL"
        )
        db.add(db_order)
        if cart_rows is not None:
            db.add(CafeOrderItems(order_id=order_id, items_json=cart_json(cart_rows), total=order_amount_rs))
        db.commit()

    return CreateOrderResponse(
        order_id=order_id,
        amount=req.amount,
        currency=req.currency.upper(),
        key_id=key_id,
        receipt=receipt
    )


@router.post("/verify-payment", response_model=VerifyPaymentResponse)
def verify_razorpay_payment(req: VerifyPaymentRequest, db: Session = Depends(get_db)):
    """Verify HMAC-SHA256 payment signature and capture payment transaction."""
    if not req.razorpay_payment_id or not req.razorpay_order_id or not req.razorpay_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required verification fields."
        )

    key_id, key_secret = _payment_credentials()
    if not key_secret or key_secret == "mock_finops_secret_opspilot":
        raise HTTPException(503, "Razorpay payment verification is not configured.")

    # Verify signature
    # Signature formula: hmac_sha256(order_id + "|" + payment_id, secret)
    message = f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode("utf-8")
    expected_sig = hmac.new(key_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    is_valid = False
    # Check HMAC digest in constant time using HMAC-SHA256
    if hmac.compare_digest(expected_sig.lower(), req.razorpay_signature.strip().lower()):
        is_valid = True
    else:
        # Also check with official SDK utility if available
        try:
            client = razorpay.Client(auth=(key_id, key_secret))
            client.utility.verify_payment_signature({
                "razorpay_order_id": req.razorpay_order_id,
                "razorpay_payment_id": req.razorpay_payment_id,
                "razorpay_signature": req.razorpay_signature
            })
            is_valid = True
        except Exception:
            is_valid = False

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Razorpay payment signature. Verification failed."
        )

    # A signature authenticates identifiers; capture and amount must also be checked.
    order = db.query(PaymentOrder).filter(PaymentOrder.order_id == req.razorpay_order_id).first()
    if order is None:
        raise HTTPException(404, "Local payment order not found")
    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        payment = client.payment.fetch(req.razorpay_payment_id)
    except Exception:
        raise HTTPException(502, "Could not confirm payment status with provider")
    if (payment.get("order_id") != order.order_id
            or payment.get("amount") != int(Decimal(str(order.amount)) * 100)
            or payment.get("currency") != order.currency
            or payment.get("status") != "captured"):
        raise HTTPException(409, "Payment is not captured or does not match the stored order")
    existing_txn = db.query(PaymentTransaction).filter_by(payment_id=req.razorpay_payment_id).first()
    if existing_txn:
        if existing_txn.order_id != order.order_id or existing_txn.status != "CAPTURED":
            raise HTTPException(409, "Payment conflicts with an existing transaction state")
        return VerifyPaymentResponse(status="success", message="Payment already verified", payment_id=req.razorpay_payment_id, order_id=order.order_id)
    order_amount, merchant_id, customer_id = order.amount, order.merchant_id, order.customer_id
    order.status = "PAID"

    # 2. Record or update PaymentTransaction as CAPTURED
    fee = _dec(order_amount * Decimal("0.02"))  # 2% MDR
    tax = _dec(fee * Decimal("0.18"))           # 18% GST on MDR
    net = _dec(order_amount - fee - tax)

    existing_txn = db.query(PaymentTransaction).filter(PaymentTransaction.payment_id == req.razorpay_payment_id).first()
    if not existing_txn:
        txn = PaymentTransaction(
            payment_id=req.razorpay_payment_id,
            order_id=req.razorpay_order_id,
            merchant_id=merchant_id,
            customer_id=customer_id,
            amount=order_amount,
            currency=order.currency,
            method=str(payment.get("method", "unknown")).upper(),
            bank=payment.get("bank"),
            gateway="RAZORPAY_DIRECT",
            status="CAPTURED",
            fee=fee,
            tax=tax,
            net_amount=net,
            reconciled=False,
            is_synthetic=False,
            data_source="RAZORPAY_TEST" if key_id.startswith("rzp_test_") else "REAL"
        )
        db.add(txn)
    else:
        existing_txn.status = "CAPTURED"
        existing_txn.fee = fee
        existing_txn.tax = tax
        existing_txn.net_amount = net

    # 3. Log PaymentEvent with idempotency key
    idempotency_key = f"{req.razorpay_payment_id}::PAYMENT_CAPTURED"
    existing_evt = db.query(PaymentEvent).filter(PaymentEvent.idempotency_key == idempotency_key).first()
    if not existing_evt:
        evt = PaymentEvent(
            event_id=f"evt_{uuid.uuid4().hex[:14]}",
            payment_id=req.razorpay_payment_id,
            event_type="PAYMENT_CAPTURED",
            event_source="RAZORPAY_CHECKOUT",
            idempotency_key=idempotency_key,
            event_payload=json.dumps({
                "payment_id": req.razorpay_payment_id,
                "order_id": req.razorpay_order_id,
                "merchant_id": merchant_id,
                "status": "captured",
                "method": payment.get("method", "unknown"),
                "amount": float(order_amount) * 100,
            }),
            occurred_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(evt)

    # 4. Audit Log entry with explicit UTC timestamp (prevents SQLite RETURNING syntax errors)
    db.add(AuditLog(
        audit_id=f"AUD-{uuid.uuid4().hex[:12].upper()}",
        workflow_id="RAZORPAY_STANDARD_CHECKOUT",
        user_id="CUSTOMER_AARAV",
        agent_node="checkout_gateway",
        tool_name="razorpay_verify",
        input_hash=hashlib.sha256(f"{req.razorpay_order_id}:{req.razorpay_payment_id}".encode()).hexdigest(),
        result_status="CAPTURED",
        latency_ms=88,
        action="PAYMENT_VERIFIED_AND_ORDER_CONFIRMED",
        timestamp=dt.datetime.now(dt.timezone.utc)
    ))

    db.commit()

    return VerifyPaymentResponse(
        status="success",
        message="Payment verified and recorded successfully",
        payment_id=req.razorpay_payment_id,
        order_id=req.razorpay_order_id
    )
