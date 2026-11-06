"""One-click simulated wallet payments for the local food-order demonstration."""
import datetime as dt
import hashlib
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.ops import AuditLog
from app.models.payments import CafeOrderItems, DemoWallet, Merchant, PaymentOrder, PaymentTransaction
from app.services.cafe_menu import cart_json, price_cart


def get_wallet(db, customer_id):
    if not settings.DEMO_MODE:
        raise ValueError("The simulated wallet is available only in demo mode.")
    wallet = db.get(DemoWallet, customer_id)
    if wallet is None:
        db.add(DemoWallet(customer_id=customer_id, balance=Decimal("50000.00")))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        wallet = db.get(DemoWallet, customer_id)
    return wallet


def pay_order(db, customer_id, request_id, merchant_id="mid_rameshwaram_01", cart=None):
    """Debit the server-priced order once; persist payment and debit atomically."""
    wallet = get_wallet(db, customer_id)
    items, amount = price_cart(cart)
    if not request_id:
        raise ValueError("A payment request reference is required.")
    digest = hashlib.sha256(f"{customer_id}:{request_id}".encode()).hexdigest()[:28]
    payment_id, order_id = "wlt_" + digest, "order_wlt_" + digest
    existing = db.get(PaymentTransaction, payment_id)
    if existing:
        saved = db.get(CafeOrderItems, existing.order_id)
        if existing.amount != amount or (saved and saved.items_json != cart_json(items)):
            raise ValueError("This payment reference already belongs to a different cart.")
        return existing
    if not db.get(Merchant, merchant_id):
        raise ValueError("Merchant not found. Initialize the payment dataset first.")
    try:
        changed = db.query(DemoWallet).filter(
            DemoWallet.customer_id == customer_id,
            DemoWallet.balance >= amount,
        ).update({DemoWallet.balance: DemoWallet.balance - amount}, synchronize_session=False)
        if changed != 1:
            raise ValueError("Insufficient wallet balance. Choose another payment method.")
        db.add(PaymentOrder(order_id=order_id, customer_id=customer_id, merchant_id=merchant_id,
                            amount=amount, currency="INR", status="PAID",
                            is_synthetic=True, data_source="DEMO_WALLET"))
        db.add(CafeOrderItems(order_id=order_id, items_json=cart_json(items), total=amount))
        payment = PaymentTransaction(payment_id=payment_id, order_id=order_id,
                                     customer_id=customer_id, merchant_id=merchant_id,
                                     amount=amount, currency="INR", method="WALLET",
                                     gateway="PAYBRIDGE_DEMO_WALLET", status="CAPTURED",
                                     fee=0, tax=0, net_amount=amount,
                                     is_synthetic=True, data_source="DEMO_WALLET",
                                     captured_at=dt.datetime.now(dt.timezone.utc))
        db.add(payment)
        db.add(AuditLog(audit_id="AUD-WLT-" + digest, workflow_id=order_id,
                        user_id=customer_id, agent_node="demo_wallet", tool_name="wallet_payment",
                        input_hash=hashlib.sha256(f"{customer_id}:{request_id}:{amount}".encode()).hexdigest(),
                        result_status="SIMULATED", action="DEMO_WALLET_PAYMENT"))
        db.commit()
        db.refresh(wallet)
        return payment
    except IntegrityError:
        db.rollback()
        existing = db.get(PaymentTransaction, payment_id)
        if existing:
            return existing
        raise
    except Exception:
        db.rollback()
        raise
