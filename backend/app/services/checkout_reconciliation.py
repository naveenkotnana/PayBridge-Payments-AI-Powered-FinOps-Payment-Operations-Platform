"""Recover local order records after Razorpay succeeded but a DB write failed.

This service only reconciles provider orders with an exact durable reservation.
It never assumes a payment was captured; capture still requires normal signed
payment verification.
"""
import logging
from decimal import Decimal

import razorpay
from sqlalchemy.orm import Session

from app.api.checkout import _credentials
from app.models.payments import CafeOrderItems, CheckoutRequest, PaymentOrder

log = logging.getLogger("paybridge.checkout.reconciliation")


def reconcile_checkout_orders(db: Session, *, limit: int = 100) -> dict[str, int]:
    """Restore missing local orders from provider order data; bounded per run."""
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    key_id, key_secret = _credentials()
    client = razorpay.Client(auth=(key_id, key_secret))
    reservations = (
        db.query(CheckoutRequest)
        .filter(CheckoutRequest.provider_order_id.is_not(None))
        .order_by(CheckoutRequest.created_at.asc())
        .limit(limit)
        .all()
    )
    result = {"checked": 0, "recovered": 0, "deferred": 0}
    for reservation in reservations:
        if db.query(PaymentOrder).filter_by(order_id=reservation.provider_order_id).first():
            continue
        result["checked"] += 1
        try:
            provider_order = client.order.fetch(reservation.provider_order_id)
            matches = (
                provider_order.get("id") == reservation.provider_order_id
                and provider_order.get("amount") == reservation.amount_minor
                and provider_order.get("currency") == reservation.currency
                and provider_order.get("receipt") == reservation.receipt
                and provider_order.get("status") in {"created", "attempted"}
            )
            if not matches:
                result["deferred"] += 1
                continue
            db.add(PaymentOrder(
                order_id=reservation.provider_order_id,
                merchant_id=reservation.merchant_id,
                customer_id=reservation.customer_id,
                amount=(Decimal(reservation.amount_minor) / Decimal(100)),
                currency=reservation.currency, receipt=reservation.receipt,
                status="ATTEMPTED" if provider_order.get("status") == "attempted" else "CREATED",
                is_synthetic=False,
                data_source="RAZORPAY_TEST" if key_id.startswith("rzp_test_") else "REAL",
            ))
            db.add(CafeOrderItems(
                order_id=reservation.provider_order_id,
                items_json=reservation.items_json,
                total=(Decimal(reservation.amount_minor) / Decimal(100)),
            ))
            db.commit()
            result["recovered"] += 1
        except Exception:
            db.rollback()
            result["deferred"] += 1
            # Avoid logging provider response bodies or credentials.
            log.warning("Deferred checkout reconciliation for one reserved order")
    return result
