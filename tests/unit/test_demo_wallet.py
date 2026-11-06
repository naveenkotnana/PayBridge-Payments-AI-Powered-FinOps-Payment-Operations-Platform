from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.models.ops import AuditLog
from app.models.payments import DemoWallet, Merchant, PaymentOrder, PaymentTransaction
from app.services.demo_wallet import get_wallet, pay_order


@pytest.fixture
def wallet_db(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Merchant(merchant_id="mid_rameshwaram_01", name="Cafe", email="cafe@example.com"))
        db.commit()
        yield db
    engine.dispose()


def test_starting_credit_is_not_reissued(wallet_db):
    wallet = get_wallet(wallet_db, "customer")
    assert wallet.balance == Decimal("50000.00")
    wallet.balance = Decimal("100.00")
    wallet_db.commit()
    assert get_wallet(wallet_db, "customer").balance == Decimal("100.00")


def test_payment_and_retry_debit_once(wallet_db):
    paid = pay_order(wallet_db, "customer", "same-request")
    assert paid.status == "CAPTURED"
    assert paid.method == "WALLET"
    assert paid.data_source == "DEMO_WALLET" and paid.is_synthetic
    assert paid.amount == Decimal("280.00")
    assert pay_order(wallet_db, "customer", "same-request").payment_id == paid.payment_id
    assert get_wallet(wallet_db, "customer").balance == Decimal("49720.00")
    assert wallet_db.query(PaymentTransaction).count() == 1
    assert wallet_db.query(PaymentOrder).count() == 1
    assert wallet_db.query(AuditLog).count() == 1


def test_insufficient_funds_has_no_partial_payment(wallet_db):
    wallet = get_wallet(wallet_db, "customer")
    wallet.balance = Decimal("279.99")
    wallet_db.commit()
    with pytest.raises(ValueError, match="Insufficient"):
        pay_order(wallet_db, "customer", "too-much")
    assert get_wallet(wallet_db, "customer").balance == Decimal("279.99")
    assert wallet_db.query(PaymentOrder).count() == 0
    assert wallet_db.query(PaymentTransaction).count() == 0


def test_commit_failure_rolls_back_debit(wallet_db, monkeypatch):
    get_wallet(wallet_db, "customer")
    def fail():
        raise RuntimeError("database unavailable")
    with monkeypatch.context() as patch:
        patch.setattr(wallet_db, "commit", fail)
        with pytest.raises(RuntimeError):
            pay_order(wallet_db, "customer", "failure")
    assert wallet_db.get(DemoWallet, "customer").balance == Decimal("50000.00")
    assert wallet_db.query(PaymentTransaction).count() == 0


def test_wallet_disabled_outside_demo(wallet_db, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    with pytest.raises(ValueError, match="demo mode"):
        pay_order(wallet_db, "customer", "not-demo")


def test_same_request_from_different_customers_is_separate(wallet_db):
    first = pay_order(wallet_db, "first", "request")
    second = pay_order(wallet_db, "second", "request")
    assert first.payment_id != second.payment_id
    assert get_wallet(wallet_db, "first").balance == Decimal("49720.00")
    assert get_wallet(wallet_db, "second").balance == Decimal("49720.00")


def test_custom_cart_and_changed_retry(wallet_db):
    from app.models.payments import CafeOrderItems
    from app.services.cafe_menu import SNACK_CART
    paid = pay_order(wallet_db, "customer", "snack", cart=SNACK_CART)
    assert paid.amount == Decimal("150.00")
    assert get_wallet(wallet_db, "customer").balance == Decimal("49850.00")
    assert wallet_db.get(CafeOrderItems, paid.order_id).total == Decimal("150.00")
    with pytest.raises(ValueError, match="different cart"):
        pay_order(wallet_db, "customer", "snack", cart={"tea": 1})
    assert get_wallet(wallet_db, "customer").balance == Decimal("49850.00")
