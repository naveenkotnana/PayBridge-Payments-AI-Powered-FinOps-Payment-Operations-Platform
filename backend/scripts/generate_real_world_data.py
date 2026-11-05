# ruff: noqa: E402
"""Script to generate realistic real-world augmented data across top Indian digital brands.

Brands:
- Swiggy India (Instamart, Food, Gourmet)
- Zomato Ltd (Food Delivery, Gold, Dining)
- Zepto Quick Commerce (10-Min Groceries, Cafe)
- Dreamplug Technologies (CRED) (BillPay, Store)
- Blinkit Instant Commerce (Express Delivery, Print)
- Flipkart Commerce (Supermart, Big Billion Days)
- BookMyShow Ticketing (IMAX, Concerts)
- FSN E-Commerce (Nykaa) (Luxe, Cosmetics)
- MakeMyTrip India (Flights, Hotels)
- Tata Digital (Tata Neu) (Croma, BigBasket)

Data Provenance:
- Marked clearly as is_synthetic=True, data_source="AUGMENTED" or "SYNTHETIC".
"""
import datetime as dt
from decimal import Decimal
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.base import SessionLocal, init_db  # noqa: E402
from app.models.payments import (  # noqa: E402
    Customer,
    IncidentMerchant,
    Merchant,
    PaymentAttempt,
    PaymentEvent,
    PaymentIncident,
    PaymentOrder,
    PaymentTransaction,
    Settlement,
)
from app.services.data_generator import (  # noqa: E402
    PaymentDataGenerator,
    seed_merchants_and_customers,
)


def populate_real_world_augmented_data():
    init_db()
    db = SessionLocal()

    print("=" * 70)
    print("Generating Real-World Fintech Augmented Data (Swiggy, Zomato, Zepto, CRED, etc.)")
    print("=" * 70)

    # 1. Seed merchants and customers
    seed_res = seed_merchants_and_customers(db, num_customers_per_merchant=10)
    print(f"[1] Merchants Seeded: {seed_res['merchants_seeded']} | Customers Seeded: {seed_res['customers_seeded']}")

    gen = PaymentDataGenerator(db, seed=42)

    # 2. Generate baseline real-world traffic (500 transactions across all 10 brands)
    print("\n[2] Generating baseline realistic transaction traffic (500 records)...")
    base_res = gen.generate_scenario(scenario="NORMAL_TRAFFIC", count=500, days_back=7, data_source="SYNTHETIC")
    print(f"    Created {base_res['records_generated']['payments']} payments, {base_res['records_generated']['events']} events.")

    # 3. Augment with Store Name Orders (Swiggy, Zomato, Zepto, CRED, etc.)
    print("\n[3] Running STORE_NAME_AUGMENTATION (250 augmented retail store transactions)...")
    aug1 = gen.augment_dataset(strategy="STORE_NAME_AUGMENTATION", target_additional_records=250)
    print(f"    Augmented {aug1['additional_records']['payments']} store transactions.")

    # 4. Augment with Stratified Failure Balance (rare failures: Card Security, Fraud Block, Core Switch)
    print("\n[4] Running STRATIFIED_FAILURE_BALANCE (150 balanced edge-case records)...")
    aug2 = gen.augment_dataset(strategy="STRATIFIED_FAILURE_BALANCE", target_additional_records=150)
    print(f"    Augmented {aug2['additional_records']['payments']} edge-case records.")

    # 5. Augment with UPI Latency Spikes (UPI Degradation on SBI / HDFC switches)
    print("\n[5] Running UPI_LATENCY_AUGMENTATION (100 high-latency switch records)...")
    aug3 = gen.augment_dataset(strategy="UPI_LATENCY_AUGMENTATION", target_additional_records=100)
    print(f"    Augmented {aug3['additional_records']['payments']} UPI switch degradation records.")

    # 6. Ensure Interactive SBI UPI Demo transaction exists for Aarav Sharma on Swiggy
    demo_txn = db.query(PaymentTransaction).filter(PaymentTransaction.payment_id == "pay_sbi_upi_demo_01").first()
    if not demo_txn:
        print("\n[6] Seeding Aarav Sharma SBI UPI Demo Transaction (pay_sbi_upi_demo_01)...")
        demo_order = PaymentOrder(
            order_id="order_sbi_upi_demo_01",
            merchant_id="mid_swiggy_01",
            customer_id="cust_sw_aarav",
            amount=Decimal("2500.00"),
            currency="INR",
            receipt="SWIGGY-INSTAMART-DEMO-01",
            status="ATTEMPTED",
            is_synthetic=True,
            data_source="SYNTHETIC",
            created_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(minutes=15),
        )
        db.add(demo_order)

        demo_txn = PaymentTransaction(
            payment_id="pay_sbi_upi_demo_01",
            order_id="order_sbi_upi_demo_01",
            merchant_id="mid_swiggy_01",
            customer_id="cust_sw_aarav",
            amount=Decimal("2500.00"),
            currency="INR",
            method="UPI",
            bank="SBI",
            gateway="RAZORPAY_DIRECT",
            status="PENDING",
            fee=Decimal("8.75"),
            tax=Decimal("1.58"),
            net_amount=Decimal("2489.67"),
            error_code="BANK_DEBITED_PAYMENT_PENDING",
            error_description="Amount debited by issuing bank but confirmation pending",
            reconciled=False,
            is_synthetic=True,
            data_source="SYNTHETIC",
            created_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(minutes=12),
        )
        db.add(demo_txn)

        demo_attempt = PaymentAttempt(
            attempt_id="att_sbi_upi_demo_01",
            payment_id="pay_sbi_upi_demo_01",
            attempt_number=1,
            gateway="RAZORPAY_DIRECT",
            bank="SBI",
            status="TIMED_OUT",
            error_code="BANK_DEBITED_PAYMENT_PENDING",
            error_category="RETRYABLE",
            latency_ms=4250,
            attempted_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(minutes=11),
        )
        db.add(demo_attempt)

        demo_event = PaymentEvent(
            event_id="evt_sbi_upi_demo_01",
            payment_id="pay_sbi_upi_demo_01",
            event_type="PAYMENT_PENDING",
            event_payload='{"amount": 2500.0, "method": "UPI", "bank": "SBI", "status": "PENDING"}',
            event_source="SIMULATOR",
            idempotency_key="pay_sbi_upi_demo_01::PAYMENT_PENDING",
            occurred_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(minutes=10),
        )
        db.add(demo_event)
        db.commit()

    # 7. Check or create active SBI Incident
    inc = db.query(PaymentIncident).filter(PaymentIncident.incident_id == "INC-SBI-UPI-001").first()
    if not inc:
        inc = PaymentIncident(
            incident_id="INC-SBI-UPI-001",
            title="SBI UPI Switch Elevated Latency & Webhook Timeout",
            severity="HIGH",
            status="INVESTIGATING",
            affected_banks="SBI",
            affected_methods="UPI",
            affected_gateways="RAZORPAY_DIRECT",
            failed_transaction_count=42,
            baseline_success_rate=94.5,
            observed_success_rate=62.0,
            estimated_financial_exposure=Decimal("105000.00"),
            evidence_summary="Core switch latency surge on State Bank of India UPI rail; avg latency 4,250ms vs 450ms SLA.",
            detected_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(minutes=45),
            is_synthetic=True,
            data_source="AUGMENTED",
        )
        db.add(inc)
        db.commit()

        inc_m = IncidentMerchant(
            incident_id="INC-SBI-UPI-001",
            merchant_id="mid_swiggy_01",
            failed_count=18,
            failed_amount=Decimal("45000.00"),
        )
        db.add(inc_m)
        db.commit()

    # 8. Print Summary
    total_txns = db.query(PaymentTransaction).count()
    synth_txns = db.query(PaymentTransaction).filter(PaymentTransaction.data_source == "SYNTHETIC").count()
    aug_txns = db.query(PaymentTransaction).filter(PaymentTransaction.data_source == "AUGMENTED").count()
    merchants_count = db.query(Merchant).count()
    customers_count = db.query(Customer).count()
    settlements_count = db.query(Settlement).count()

    print("\n" + "=" * 70)
    print("DATABASE SUMMARY AFTER REAL-WORLD AUGMENTATION")
    print("=" * 70)
    print(f"Total Merchants:       {merchants_count} (Swiggy, Zomato, Zepto, CRED, Blinkit, etc.)")
    print(f"Total Customers:       {customers_count} (including Aarav Sharma)")
    print(f"Total Transactions:    {total_txns}")
    print(f"  - Synthetic Baseline: {synth_txns}")
    print(f"  - Augmented Records:  {aug_txns}")
    print(f"Total Settlements:     {settlements_count}")
    print("=" * 70)

    db.close()


if __name__ == "__main__":
    populate_real_world_augmented_data()
