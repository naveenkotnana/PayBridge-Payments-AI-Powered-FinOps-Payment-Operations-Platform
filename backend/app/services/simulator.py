"""Synthetic Payment Event Simulator for Razorpay-Inspired AI Payments.

Generates realistic Indian payment transactions, orders, refunds, and gateway telemetry.
Features:
- Realistic payment method mix (UPI ~65%, Cards ~22%, NetBanking ~9%, Wallets ~4%).
- Realistic bank routing (HDFC, ICICI, Axis, SBI).
- Deterministic MDR / Fee calculation with GST.
- Controlled anomalies: Gateway SR plunges, MDR rate mismatches, uncaptured auths.
- Low-memory footprint, runs smoothly on 8 GB RAM machines.
"""
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import random
import uuid
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from app.db.base import init_db
from app.models.payments import (
    Merchant,
    PaymentOrder,
    PaymentTransaction,
    Refund,
    ReconciliationDiscrepancy,
)

MERCHANTS_SEED = [
    {"merchant_id": "mid_swiggy_01", "name": "Swiggy India", "email": "finance@swiggy.in", "business_category": "FOOD_DELIVERY", "settlement_cycle": "T+1", "pricing_plan": "ENTERPRISE", "risk_tier": "LOW"},
    {"merchant_id": "mid_zomato_02", "name": "Zomato Ltd", "email": "settlements@zomato.com", "business_category": "FOOD_DELIVERY", "settlement_cycle": "T+1", "pricing_plan": "ENTERPRISE", "risk_tier": "LOW"},
    {"merchant_id": "mid_flipkart_03", "name": "Flipkart Commerce", "email": "payments@flipkart.com", "business_category": "E_COMMERCE", "settlement_cycle": "T+1", "pricing_plan": "ENTERPRISE", "risk_tier": "LOW"},
    {"merchant_id": "mid_bookmyshow_04", "name": "BookMyShow Ticketing", "email": "accounts@bookmyshow.com", "business_category": "TICKETING", "settlement_cycle": "T+2", "pricing_plan": "STANDARD_MDR", "risk_tier": "MEDIUM"},
    {"merchant_id": "mid_cred_05", "name": "Dreamplug Technologies (CRED)", "email": "ops@cred.club", "business_category": "FINTECH", "settlement_cycle": "T+1", "pricing_plan": "ENTERPRISE", "risk_tier": "LOW"},
    {"merchant_id": "mid_zepto_06", "name": "Zepto Quick Commerce", "email": "finance@zepto.com", "business_category": "E_COMMERCE", "settlement_cycle": "T+1", "pricing_plan": "STANDARD_MDR", "risk_tier": "LOW"},
]

PAYMENT_METHODS = ["UPI", "CARD", "NETBANKING", "WALLET"]
METHOD_WEIGHTS = [0.65, 0.22, 0.09, 0.04]

BANKS = ["HDFC", "ICICI", "AXIS", "SBI", "KOTAK"]
GATEWAYS = ["HDFC_SMARTHUB", "ICICI_PAYSEAL", "AXIS_EPG", "RAZORPAY_DIRECT"]

ERROR_CODES = [
    ("BAD_REQUEST_GATEWAY_DOWN", "Payment gateway provider is temporarily unreachable"),
    ("INSUFFICIENT_FUNDS", "Customer account has insufficient funds to fulfill debit"),
    ("BANK_DEBITED_PAYMENT_PENDING", "Amount debited by issuing bank but confirmation pending"),
    ("CARD_SECURITY_VIOLATION", "Card failed CVV or 3D-Secure 2-factor OTP verification"),
    ("EXPIRED_TRANSACTION", "Payment session timed out on customer UPI app"),
]

TWO_PLACES = Decimal("0.01")


def _dec(val) -> Decimal:
    return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_fees(amount: Decimal, method: str) -> tuple[Decimal, Decimal]:
    """Calculate deterministic MDR (Merchant Discount Rate) and 18% GST."""
    if method == "UPI":
        fee_rate = Decimal("0.0035")  # 0.35% for commercial UPI
    elif method == "CARD":
        fee_rate = Decimal("0.0185")  # 1.85% for Credit / Debit Cards
    elif method == "NETBANKING":
        fee_rate = Decimal("0.0150")  # 1.50%
    else:
        fee_rate = Decimal("0.0180")  # 1.80% for Wallets

    fee = _dec(amount * fee_rate)
    tax = _dec(fee * Decimal("0.18"))  # 18% GST on processing fee
    return fee, tax


def seed_merchants(db: Session) -> int:
    """Seed benchmark merchants idempotently."""
    created = 0
    for m in MERCHANTS_SEED:
        existing = db.query(Merchant).filter(Merchant.merchant_id == m["merchant_id"]).first()
        if not existing:
            db.add(Merchant(**m))
            created += 1
    db.commit()
    return created


def generate_single_payment(
    db: Session,
    merchant_id: str,
    timestamp: Optional[dt.datetime] = None,
    force_failed_gateway: Optional[str] = None,
    inject_fee_discrepancy: bool = False,
    inject_uncaptured_auth: bool = False,
) -> Dict[str, Any]:
    """Generate a single realistic payment event, order, and potential refund/discrepancy."""
    now = timestamp or dt.datetime.now()
    method = random.choices(PAYMENT_METHODS, weights=METHOD_WEIGHTS)[0]
    bank = random.choice(BANKS)
    gateway = force_failed_gateway or random.choice(GATEWAYS)

    # Realistic transaction sizes based on payment method
    if method == "UPI":
        amount = _dec(random.uniform(50.0, 3500.0))
        card_network = None
    elif method == "CARD":
        amount = _dec(random.uniform(400.0, 15000.0))
        card_network = random.choice(["VISA", "MASTERCARD", "RUPAY"])
    elif method == "NETBANKING":
        amount = _dec(random.uniform(1500.0, 45000.0))
        card_network = None
    else:
        amount = _dec(random.uniform(100.0, 2000.0))
        card_network = None

    order_id = f"order_{uuid.uuid4().hex[:14]}"
    order = PaymentOrder(
        order_id=order_id,
        merchant_id=merchant_id,
        amount=amount,
        currency="INR",
        receipt=f"rcpt_{uuid.uuid4().hex[:8]}",
        status="ATTEMPTED",
        created_at=now - dt.timedelta(seconds=random.randint(5, 45)),
    )
    db.add(order)

    # Failure simulation
    is_gateway_outage = force_failed_gateway is not None and gateway == force_failed_gateway
    failure_chance = 0.65 if is_gateway_outage else 0.05
    is_failed = random.random() < failure_chance

    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    fee, tax = calculate_fees(amount, method)

    if inject_fee_discrepancy and not is_failed:
        # Injected tariff variance: Gateway deducted higher fee than agreed contract
        observed_fee = _dec(fee * Decimal("1.45"))
    else:
        observed_fee = fee

    net = _dec(amount - observed_fee - tax)

    if is_failed:
        err = ERROR_CODES[0] if is_gateway_outage else random.choice(ERROR_CODES)
        status = "FAILED"
        err_code, err_desc = err[0], err[1]
        captured_at = None
        order.status = "ATTEMPTED"
    else:
        if inject_uncaptured_auth:
            status = "AUTHORIZED"
            captured_at = None
            order.status = "ATTEMPTED"
        else:
            status = "CAPTURED"
            captured_at = now
            order.status = "PAID"
        err_code, err_desc = None, None

    payment = PaymentTransaction(
        payment_id=payment_id,
        order_id=order_id,
        merchant_id=merchant_id,
        amount=amount,
        currency="INR",
        method=method,
        card_network=card_network,
        bank=bank,
        gateway=gateway,
        status=status,
        error_code=err_code,
        error_description=err_desc,
        fee=observed_fee,
        tax=tax,
        net_amount=net,
        reconciled=False,
        created_at=now,
        captured_at=captured_at,
    )
    db.add(payment)

    # Controlled discrepancy injection
    if inject_fee_discrepancy and not is_failed:
        disc = ReconciliationDiscrepancy(
            discrepancy_id=f"DISC-FEE-{uuid.uuid4().hex[:8]}",
            payment_id=payment_id,
            merchant_id=merchant_id,
            issue_type="MDR_MISMATCH",
            expected_amount=fee,
            observed_amount=observed_fee,
            variance=_dec(observed_fee - fee),
            severity="MEDIUM",
            status="OPEN",
            detected_at=now,
        )
        db.add(disc)

    if inject_uncaptured_auth:
        disc = ReconciliationDiscrepancy(
            discrepancy_id=f"DISC-AUTH-{uuid.uuid4().hex[:8]}",
            payment_id=payment_id,
            merchant_id=merchant_id,
            issue_type="UNCAPTURED_AUTH",
            expected_amount=amount,
            observed_amount=Decimal("0.00"),
            variance=amount,
            severity="HIGH",
            status="OPEN",
            detected_at=now,
        )
        db.add(disc)

    # Occasional refund generation (~2% of captured transactions)
    if status == "CAPTURED" and random.random() < 0.025:
        refund_id = f"rfnd_{uuid.uuid4().hex[:14]}"
        db.add(
            Refund(
                refund_id=refund_id,
                payment_id=payment_id,
                merchant_id=merchant_id,
                amount=amount,
                currency="INR",
                status="PROCESSED",
                speed="OPTIMAL",
                reason=random.choice(["CUSTOMER_REQUEST", "DUPLICATE_PAYMENT", "GOODS_RETURNED"]),
                reconciled=False,
                created_at=now + dt.timedelta(minutes=random.randint(10, 360)),
            )
        )

    db.commit()
    return {
        "payment_id": payment_id,
        "order_id": order_id,
        "merchant_id": merchant_id,
        "amount": float(amount),
        "method": method,
        "gateway": gateway,
        "status": status,
        "error_code": err_code,
    }


def seed_synthetic_dataset(db: Session, days: int = 7, target_count: int = 1500) -> Dict[str, Any]:
    """Seed comprehensive benchmark dataset spanning 7 trailing days."""
    init_db()
    seed_merchants(db)

    # Only seed if table is sparse (< 100 rows)
    current_count = db.query(PaymentTransaction).count()
    if current_count >= 100:
        return {"status": "ALREADY_POPULATED", "payment_count": current_count}

    start_time = dt.datetime.now() - dt.timedelta(days=days)
    step_seconds = int((days * 86400) / target_count)

    merchants = [m["merchant_id"] for m in MERCHANTS_SEED]
    generated = 0

    for i in range(target_count):
        cur_ts = start_time + dt.timedelta(seconds=i * step_seconds + random.randint(0, 15))
        mid = random.choice(merchants)

        # Inject periodic gateway degradation on HDFC between day 2 and day 3
        is_hdfc_incident_window = 2.0 <= (i / (target_count / days)) <= 2.25
        failed_gw = "HDFC_SMARTHUB" if is_hdfc_incident_window else None

        # Occasional reconciliation discrepancies
        inject_fee = (i % 87 == 0)
        inject_auth = (i % 143 == 0)

        generate_single_payment(
            db=db,
            merchant_id=mid,
            timestamp=cur_ts,
            force_failed_gateway=failed_gw,
            inject_fee_discrepancy=inject_fee,
            inject_uncaptured_auth=inject_auth,
        )
        generated += 1

    return {"status": "SUCCESS", "payments_generated": generated}
