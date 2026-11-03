"""Unit tests for the Razorpay-inspired payment simulator and canonical models."""
from decimal import Decimal
from app.models.payments import (
    Merchant,
    PaymentOrder,
    PaymentTransaction,
    ReconciliationDiscrepancy,
)
from app.services.simulator import (
    calculate_fees,
    generate_single_payment,
    seed_merchants,
)


def test_calculate_fees_upi_and_cards():
    # UPI at 0.35%
    fee_upi, tax_upi = calculate_fees(Decimal("1000.00"), "UPI")
    assert fee_upi == Decimal("3.50")
    assert tax_upi == Decimal("0.63")  # 18% of 3.50 = 0.63

    # CARD at 1.85%
    fee_card, tax_card = calculate_fees(Decimal("2000.00"), "CARD")
    assert fee_card == Decimal("37.00")
    assert tax_card == Decimal("6.66")  # 18% of 37.00 = 6.66


def test_seed_merchants(db):
    count = seed_merchants(db)
    assert count >= 0
    merchants = db.query(Merchant).all()
    assert len(merchants) >= 6
    ids = [m.merchant_id for m in merchants]
    assert "mid_swiggy_01" in ids
    assert "mid_flipkart_03" in ids


def test_generate_single_payment_lifecycle(db):
    seed_merchants(db)
    result = generate_single_payment(db, "mid_swiggy_01")
    assert result["payment_id"].startswith("pay_")
    assert result["order_id"].startswith("order_")
    assert result["merchant_id"] == "mid_swiggy_01"
    assert result["status"] in ("CAPTURED", "AUTHORIZED", "FAILED")

    # Verify database persistence
    pay = db.query(PaymentTransaction).filter(PaymentTransaction.payment_id == result["payment_id"]).first()
    assert pay is not None
    order = db.query(PaymentOrder).filter(PaymentOrder.order_id == result["order_id"]).first()
    assert order is not None

    # Verify deterministic financial arithmetic: net = amount - fee - tax
    assert pay.net_amount == pay.amount - pay.fee - pay.tax


def test_forced_gateway_outage_simulation(db):
    seed_merchants(db)
    # Force HDFC outage
    res = generate_single_payment(db, "mid_zomato_02", force_failed_gateway="HDFC_SMARTHUB")
    assert res["gateway"] == "HDFC_SMARTHUB"


def test_injected_discrepancy(db):
    seed_merchants(db)
    res = generate_single_payment(
        db,
        "mid_flipkart_03",
        inject_fee_discrepancy=True,
    )
    if res["status"] != "FAILED":
        disc = db.query(ReconciliationDiscrepancy).filter(
            ReconciliationDiscrepancy.payment_id == res["payment_id"]
        ).first()
        assert disc is not None
        assert disc.issue_type == "MDR_MISMATCH"
        assert disc.variance > Decimal("0.00")
