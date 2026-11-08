# -*- coding: utf-8 -*-
# ruff: noqa: E402
"""Generate and Ingest the Canonical 50,000 Transaction Payment Dataset.

10 Target Indian Merchants:
1. RAMESHSWARAM CAFE (mid_rameshwaram_01) - Food & Beverages
2. URBAN EATS (mid_urban_eats_02) - Quick Service Restaurant
3. FRESH BASKET (mid_fresh_basket_03) - Groceries
4. TECHMART (mid_techmart_04) - Consumer Electronics
5. CITY PHARMACY (mid_city_pharmacy_05) - Healthcare & Medicines
6. QUICK BITES (mid_quick_bites_06) - Cloud Kitchen
7. STYLE HUB (mid_style_hub_07) - Fashion & Apparel
8. DAILY MART (mid_daily_mart_08) - Supermarket
9. TRAVEL POINT (mid_travel_point_09) - Transit & Bookings
10. HOME NEEDS (mid_home_needs_10) - Home Improvement

Canonical CSV:
backend/data/raw/payment_platform_50000_transactions.csv
"""
import csv
import datetime as dt
from decimal import Decimal
from pathlib import Path
import random
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
for _p in [str(PROJECT_ROOT), str(BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.db.base import SessionLocal, init_db
from app.models.payments import Customer, Merchant
from app.services.ingestion_payments import PaymentCSVIngestionService

RAW_DATA_DIR = BACKEND_DIR / "data" / "raw"
TARGET_CSV_PATH = RAW_DATA_DIR / "payment_platform_50000_transactions.csv"

INDIAN_MERCHANTS = [
    {"merchant_id": "mid_rameshwaram_01", "name": "RAMESHSWARAM CAFE", "category": "FOOD_DELIVERY", "email": "finance@rameshwaramcafe.in"},
    {"merchant_id": "mid_urban_eats_02", "name": "URBAN EATS", "category": "FOOD_DELIVERY", "email": "accounts@urbaneats.in"},
    {"merchant_id": "mid_fresh_basket_03", "name": "FRESH BASKET", "category": "GROCERY", "email": "billing@freshbasket.in"},
    {"merchant_id": "mid_techmart_04", "name": "TECHMART", "category": "ELECTRONICS", "email": "finance@techmart.in"},
    {"merchant_id": "mid_city_pharmacy_05", "name": "CITY PHARMACY", "category": "HEALTHCARE", "email": "accounts@citypharmacy.in"},
    {"merchant_id": "mid_quick_bites_06", "name": "QUICK BITES", "category": "FOOD_DELIVERY", "email": "ops@quickbites.in"},
    {"merchant_id": "mid_style_hub_07", "name": "STYLE HUB", "category": "APPAREL", "email": "payments@stylehub.in"},
    {"merchant_id": "mid_daily_mart_08", "name": "DAILY MART", "category": "RETAIL", "email": "support@dailymart.in"},
    {"merchant_id": "mid_travel_point_09", "name": "TRAVEL POINT", "category": "TRAVEL", "email": "reservations@travelpoint.in"},
    {"merchant_id": "mid_home_needs_10", "name": "HOME NEEDS", "category": "HOME_IMPROVEMENT", "email": "care@homeneeds.in"},
]

PAYMENT_METHODS = ["UPI", "CARD", "NETBANKING", "WALLET"]
BANKS = ["HDFC", "ICICI", "AXIS", "SBI", "KOTAK"]
GATEWAYS = ["RAZORPAY_DIRECT", "HDFC_PG", "PAYU"]


def generate_50k_csv(csv_path: Path, total_records: int = 50000) -> Path:
    """Generate deterministic 50,000 synthetic transaction records across 10 Indian merchants."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    random.seed(42)  # Deterministic seed

    base_time = dt.datetime(2026, 11, 1, 8, 0, 0)
    print(f"Generating {total_records:,} transactions to {csv_path}...")

    fieldnames = [
        "payment_id", "order_id", "merchant_id", "merchant_name",
        "customer_id", "amount", "currency", "method", "bank",
        "gateway", "status", "fee", "tax", "net_amount", "created_at"
    ]

    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx in range(1, total_records + 1):
            mid_info = random.choice(INDIAN_MERCHANTS)
            mid = mid_info["merchant_id"]
            m_name = mid_info["name"]

            # Method distribution: 65% UPI, 22% CARD, 9% NETBANKING, 4% WALLET
            method_roll = random.random()
            if method_roll < 0.65:
                method = "UPI"
            elif method_roll < 0.87:
                method = "CARD"
            elif method_roll < 0.96:
                method = "NETBANKING"
            else:
                method = "WALLET"

            bank = random.choice(BANKS)
            gateway = "RAZORPAY_DIRECT" if random.random() < 0.70 else random.choice(GATEWAYS)

            # Amount logic by category
            if mid == "mid_rameshwaram_01":
                amount = Decimal(str(random.choice([140, 180, 220, 280, 320, 360, 420, 560])))
            elif mid_info["category"] == "ELECTRONICS":
                amount = Decimal(str(random.randint(1500, 48000)))
            elif mid_info["category"] == "TRAVEL":
                amount = Decimal(str(random.randint(1200, 18500)))
            else:
                amount = Decimal(str(random.randint(80, 2400)))

            # Status distribution: ~93% CAPTURED, ~6% FAILED, ~1% PENDING
            # If SBI UPI on Rameshwaram Cafe, inject higher failure rate for incident realism
            stat_roll = random.random()
            if bank == "SBI" and method == "UPI" and mid == "mid_rameshwaram_01" and random.random() < 0.14:
                status = "FAILED"
            elif stat_roll < 0.93:
                status = "CAPTURED"
            elif stat_roll < 0.99:
                status = "FAILED"
            else:
                status = "PENDING"

            # Fee and tax calculation
            fee_rate = Decimal("0.0035") if method == "UPI" else (Decimal("0.0185") if method == "CARD" else Decimal("0.0150"))
            fee = (amount * fee_rate).quantize(Decimal("0.01"))
            tax = (fee * Decimal("0.18")).quantize(Decimal("0.01"))
            net = amount - fee - tax

            # Time progression
            txn_time = base_time + dt.timedelta(seconds=idx * 6)
            cust_num = random.randint(1, 2500)

            writer.writerow({
                "payment_id": f"pay_{idx:07d}_{mid[:8]}",
                "order_id": f"order_{idx:07d}",
                "merchant_id": mid,
                "merchant_name": m_name,
                # Customer IDs are merchant-scoped in the source model. Prefix
                # with the merchant slug so one synthetic customer can never
                # be assigned to multiple merchants by chance.
                "customer_id": f"cust_{mid.removeprefix('mid_')}_{cust_num:05d}",
                "amount": f"{amount:.2f}",
                "currency": "INR",
                "method": method,
                "bank": bank,
                "gateway": gateway,
                "status": status,
                "fee": f"{fee:.2f}",
                "tax": f"{tax:.2f}",
                "net_amount": f"{net:.2f}",
                "created_at": txn_time.strftime("%Y-%m-%d %H:%M:%S")
            })

    print(f"Generated {total_records:,} records ({csv_path.stat().st_size / (1024*1024):.1f} MB).")
    return csv_path


def seed_10_merchants(db):
    """Ensure merchants and their scoped synthetic customers exist."""
    count = 0
    for m in INDIAN_MERCHANTS:
        existing = db.query(Merchant).filter(Merchant.merchant_id == m["merchant_id"]).first()
        if not existing:
            merchant = Merchant(
                merchant_id=m["merchant_id"],
                name=m["name"],
                email=m["email"],
                business_category=m["category"],
                settlement_cycle="T+1",
                pricing_plan="STANDARD_MDR",
                risk_tier="LOW",
                status="ACTIVE",
                is_synthetic=True,
                data_source="SYNTHETIC"
            )
            db.add(merchant)
            count += 1
    db.commit()
    print(f"Seeded {count} new Indian merchants into database.")

    customer_count = 0
    for merchant in INDIAN_MERCHANTS:
        prefix = f"cust_{merchant['merchant_id'].removeprefix('mid_')}"
        for customer_number in range(1, 2501):
            customer_id = f"{prefix}_{customer_number:05d}"
            if db.get(Customer, customer_id) is None:
                db.add(Customer(
                    customer_id=customer_id,
                    merchant_id=merchant["merchant_id"],
                    name=f"Synthetic Customer {customer_number}",
                    email=f"{customer_id}@example.invalid",
                    is_synthetic=True,
                    data_source="SYNTHETIC",
                ))
                customer_count += 1
        # Commit by merchant to bound memory while keeping each seed batch
        # consistent with the merchant foreign key.
        db.commit()
    print(f"Seeded {customer_count} new merchant-scoped synthetic customers.")


def main():
    t0 = time.time()
    init_db()
    with SessionLocal() as db:
        # 1. Seed the 10 merchants
        seed_10_merchants(db)

        # 2. Generate the 50,000 transaction CSV
        csv_file = generate_50k_csv(TARGET_CSV_PATH, total_records=50000)

        # 3. Ingest through canonical PaymentCSVIngestionService
        print("\nIngesting 50,000 transactions through Data Engineering pipeline...")
        ingest_service = PaymentCSVIngestionService(db)
        summary = ingest_service.ingest_csv(csv_file, source_name="payment_platform_50000_transactions.csv")

        print("=" * 64)
        print("Data Engineering Ingestion Lineage Summary:")
        print(f"  Run ID:        {summary.get('run_id')}")
        print(f"  Received:      {summary.get('records_received'):,}")
        print(f"  Accepted:      {summary.get('records_accepted'):,}")
        print(f"  Rejected:      {summary.get('records_rejected'):,}")
        print(f"  Duplicated:    {summary.get('records_duplicated'):,}")
        print(f"  Duration:      {time.time() - t0:.2f}s")
        print("=" * 64)


if __name__ == "__main__":
    main()
