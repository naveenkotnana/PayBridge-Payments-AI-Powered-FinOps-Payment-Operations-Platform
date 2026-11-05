# ruff: noqa: E402
"""Generate realistic real-world 500+ Indian customer and payment records in .csv format.

Outputs:
1. data/raw/fintech_customers_500plus.csv (600 unique Indian customer profiles)
2. data/raw/fintech_transactions_500plus.csv (600+ realistic store transactions)

Features:
- Authentic Indian names across North, South, East, and West India.
- Store brands: Swiggy, Zomato, Zepto, CRED, Blinkit, Flipkart, BookMyShow, Nykaa, MakeMyTrip, Tata Neu.
- Real-world cities, PIN codes, banks, and payment rails.
- Strict financial invariants (Decimal calculations).
"""
import csv
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import random
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.base import SessionLocal, init_db  # noqa: E402
from app.models.payments import Customer, Merchant  # noqa: E402

TWO_PLACES = Decimal("0.01")


def _dec(val) -> Decimal:
    return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


MALE_FIRST_NAMES = [
    "Aarav", "Rohan", "Vikram", "Arjun", "Aditya", "Rahul", "Amit", "Siddharth",
    "Kabir", "Varun", "Kunal", "Neeraj", "Karthik", "Suresh", "Pranav", "Nikhil",
    "Dev", "Harsh", "Rakesh", "Manish", "Abhishek", "Gaurav", "Yash", "Alok",
    "Mayank", "Ankit", "Sachin", "Vivek", "Vishal", "Deepak", "Tushar", "Saurabh",
    "Tarun", "Arvind", "Rajesh", "Sunil", "Mohit", "Chirag", "Ayush", "Parth"
]

FEMALE_FIRST_NAMES = [
    "Priya", "Ananya", "Sneha", "Aditi", "Pooja", "Neha", "Riya", "Shreya",
    "Divya", "Tanvi", "Kavya", "Ishita", "Meera", "Sanya", "Simran", "Swati",
    "Deepa", "Shruti", "Radhika", "Kriti", "Aishwarya", "Niharika", "Preeti", "Payal",
    "Natasha", "Disha", "Mansi", "Vidya", "Bhavna", "Sonali", "Pallavi", "Garima",
    "Rashmi", "Ankita", "Jyoti", "Shilpa", "Trisha", "Lavanya", "Revathi", "Malini"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Patel", "Mehta", "Shah", "Reddy",
    "Rao", "Iyer", "Iyengar", "Nair", "Menon", "Kulkarni", "Deshmukh", "Joshi",
    "Bhat", "Chatterjee", "Banerjee", "Mukherjee", "Das", "Ghosh", "Sen", "Choudhury",
    "Mishra", "Pandey", "Tiwari", "Agarwal", "Bansal", "Mittal", "Jain", "Goyal",
    "Kapoor", "Malhotra", "Khanna", "Sethi", "Saxena", "Mathur", "Srivastava", "Yadav"
]

CITIES_METADATA = [
    ("Bengaluru", "Karnataka", "560001"),
    ("Mumbai", "Maharashtra", "400001"),
    ("Delhi NCR", "Delhi", "110001"),
    ("Hyderabad", "Telangana", "500001"),
    ("Chennai", "Tamil Nadu", "600001"),
    ("Pune", "Maharashtra", "411001"),
    ("Kolkata", "West Bengal", "700001"),
    ("Ahmedabad", "Gujarat", "380001"),
    ("Jaipur", "Rajasthan", "302001"),
    ("Kochi", "Kerala", "682001"),
    ("Chandigarh", "Punjab", "160017"),
    ("Indore", "Madhya Pradesh", "452001"),
    ("Lucknow", "Uttar Pradesh", "226001"),
    ("Coimbatore", "Tamil Nadu", "641001"),
    ("Bhubaneswar", "Odisha", "751001"),
]

BANKS = ["State Bank of India (SBI)", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra Bank"]
BANK_CODES = {"State Bank of India (SBI)": "SBI", "HDFC Bank": "HDFC", "ICICI Bank": "ICICI", "Axis Bank": "AXIS", "Kotak Mahindra Bank": "KOTAK"}

MERCHANTS_MAP = [
    ("mid_swiggy_01", "Swiggy India", "Food & Instamart", ["SWIGGY-INSTAMART-", "SWIGGY-FOOD-", "SWIGGY-GOURMET-"], 150.0, 3200.0),
    ("mid_zomato_02", "Zomato Ltd", "Food & Dining", ["ZOMATO-ORDER-", "ZOMATO-GOLD-", "ZOMATO-BIRYANI-"], 180.0, 2800.0),
    ("mid_zepto_06", "Zepto Quick Commerce", "10-Min Groceries", ["ZEPTO-10MIN-", "ZEPTO-CAFE-", "ZEPTO-FRESH-"], 99.0, 2400.0),
    ("mid_cred_05", "CRED (Dreamplug)", "FinTech & BillPay", ["CRED-BILLPAY-HDFC-", "CRED-STORE-", "CRED-FASTAG-"], 1000.0, 65000.0),
    ("mid_blinkit_07", "Blinkit Instant Commerce", "Quick Commerce", ["BLINKIT-EXP-", "BLINKIT-PRINT-", "BLINKIT-TECH-"], 80.0, 2200.0),
    ("mid_flipkart_03", "Flipkart Commerce", "E-Commerce", ["FK-SUPERMART-", "FK-ELECTRONICS-", "FK-BIGBILLION-"], 499.0, 48000.0),
    ("mid_bookmyshow_04", "BookMyShow Ticketing", "Movies & Events", ["BMS-IMAX-TICKET-", "BMS-CONCERT-", "BMS-STANDUP-"], 350.0, 6500.0),
    ("mid_nykaa_08", "FSN E-Commerce (Nykaa)", "Beauty & Fashion", ["NYKAA-LUXE-", "NYKAA-GLAM-", "NYKAA-MAN-"], 399.0, 9500.0),
    ("mid_makemytrip_09", "MakeMyTrip India", "Travel & Hotels", ["MMT-FLT-INDIGO-", "MMT-HOTEL-TAJ-", "MMT-CAB-"], 2400.0, 52000.0),
    ("mid_tataneu_10", "Tata Digital (Tata Neu)", "Super App & Croma", ["TATANEU-CROMA-", "TATANEU-BB-", "TATANEU-1MG-"], 450.0, 42000.0),
]

PAYMENT_METHODS = ["UPI", "CARD", "NETBANKING", "WALLET"]
METHOD_WEIGHTS = [0.65, 0.22, 0.09, 0.04]


def generate_500plus_people_dataset(target_count: int = 600):
    random.seed(42)

    data_dir = PROJECT_ROOT / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    customers_csv_path = data_dir / "fintech_customers_500plus.csv"
    txns_csv_path = data_dir / "fintech_transactions_500plus.csv"

    print("=" * 70)
    print(f"Generating {target_count} Authentic Indian Customer Records & Transactions CSV")
    print("=" * 70)

    # Prepare unique names pool
    names_pool = []
    for fn in MALE_FIRST_NAMES:
        for ln in LAST_NAMES:
            names_pool.append((fn, ln, "MALE"))
    for fn in FEMALE_FIRST_NAMES:
        for ln in LAST_NAMES:
            names_pool.append((fn, ln, "FEMALE"))

    random.shuffle(names_pool)
    selected_names = names_pool[:target_count]

    customers_rows = []
    txns_rows = []

    # First customer is always Aarav Sharma for demo consistency
    selected_names[0] = ("Aarav", "Sharma", "MALE")

    base_date = dt.date(2025, 1, 15)

    for idx, (fn, ln, gender) in enumerate(selected_names, start=1):
        cid = "cust_sw_aarav" if idx == 1 else f"CUST-IND-{idx:05d}"
        full_name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 99)}@gmail.com" if idx > 1 else "aarav.sharma@example.com"
        phone = f"+9198{random.randint(10000000, 99999999)}" if idx > 1 else "+919876543210"

        city, state, pin_prefix = random.choice(CITIES_METADATA)
        pin_code = f"{pin_prefix[:3]}{random.randint(100, 999)}"

        bank_name = random.choice(BANKS)
        bank_code = BANK_CODES[bank_name]
        method = random.choices(PAYMENT_METHODS, weights=METHOD_WEIGHTS)[0]
        kyc = random.choices(["VERIFIED", "MIN_KYC", "PENDING"], weights=[0.82, 0.14, 0.04])[0]
        risk_score = round(random.uniform(0.02, 0.35) if kyc == "VERIFIED" else random.uniform(0.35, 0.88), 3)

        # Primary merchant association
        m_tuple = MERCHANTS_MAP[0] if idx == 1 else random.choice(MERCHANTS_MAP)
        mid, m_name, category, prefixes, min_amt, max_amt = m_tuple

        orders_count = random.randint(3, 48)
        avg_spend = round(random.uniform(min_amt, max_amt), 2)
        total_spend = round(orders_count * avg_spend, 2)

        # Recent transaction
        txn_id = "pay_sbi_upi_demo_01" if idx == 1 else f"pay_{idx:05d}_{random.randint(1000, 9999)}"
        receipt_prefix = random.choice(prefixes)
        receipt_no = "SWIGGY-INSTAMART-DEMO-01" if idx == 1 else f"{receipt_prefix}{random.randint(10000, 99999)}"
        last_amt = 2500.00 if idx == 1 else round(random.uniform(min_amt, min(max_amt, 4000.0)), 2)
        last_status = "PENDING" if idx == 1 else random.choices(["CAPTURED", "FAILED", "PENDING"], weights=[0.92, 0.05, 0.03])[0]

        onboard_days = random.randint(10, 600)
        onboard_date = base_date + dt.timedelta(days=onboard_days)

        # Customer CSV row
        customers_rows.append({
            "customer_id": cid,
            "full_name": full_name,
            "gender": gender,
            "email": email,
            "phone_number": phone,
            "city": city,
            "state": state,
            "pin_code": pin_code,
            "kyc_status": kyc,
            "risk_score": risk_score,
            "primary_bank": bank_name,
            "bank_code": bank_code,
            "preferred_payment_method": method,
            "primary_merchant_app": m_name,
            "merchant_id": mid,
            "lifetime_orders_count": orders_count,
            "total_spend_inr": total_spend,
            "average_order_value_inr": avg_spend,
            "last_transaction_id": txn_id,
            "last_order_receipt": receipt_no,
            "last_order_status": last_status,
            "is_synthetic": True,
            "data_source": "AUGMENTED_SYNTHETIC",
            "onboarding_date": str(onboard_date),
        })

        # Calculate MDR fee & tax
        fee_rate = Decimal("0.0035") if method == "UPI" else (Decimal("0.0185") if method == "CARD" else Decimal("0.0150"))
        fee_dec = _dec(Decimal(str(last_amt)) * fee_rate)
        tax_dec = _dec(fee_dec * Decimal("0.18"))
        net_dec = _dec(Decimal(str(last_amt)) - fee_dec - tax_dec)

        # Transaction CSV row
        txns_rows.append({
            "payment_id": txn_id,
            "order_receipt": receipt_no,
            "customer_id": cid,
            "customer_name": full_name,
            "merchant_id": mid,
            "merchant_name": m_name,
            "gross_amount_inr": f"{last_amt:.2f}",
            "mdr_fee_inr": str(fee_dec),
            "gst_tax_inr": str(tax_dec),
            "net_payout_inr": str(net_dec),
            "payment_method": method,
            "issuing_bank": bank_code,
            "gateway": "RAZORPAY_DIRECT" if method == "UPI" else "HDFC_SMARTHUB",
            "payment_status": last_status,
            "city": city,
            "is_synthetic": True,
            "data_source": "AUGMENTED_SYNTHETIC",
            "transaction_timestamp": str(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(hours=random.randint(1, 168))),
        })

    # Write Customers CSV
    cust_fieldnames = list(customers_rows[0].keys())
    with open(customers_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cust_fieldnames)
        writer.writeheader()
        writer.writerows(customers_rows)

    # Write Transactions CSV
    txn_fieldnames = list(txns_rows[0].keys())
    with open(txns_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=txn_fieldnames)
        writer.writeheader()
        writer.writerows(txns_rows)

    print(f" Successfully generated Customers CSV:    {customers_csv_path}")
    print(f"    - Total Unique People Records:         {len(customers_rows)}")
    print(f" Successfully generated Transactions CSV: {txns_csv_path}")
    print(f"    - Total Store Transactions:            {len(txns_rows)}")

    # Sync into SQLite opspilot.db for immediate dashboard visibility
    print("\n[3] Syncing 600+ Customers into database (opspilot.db)...")
    init_db()
    with SessionLocal() as db:
        # Seed merchants if missing
        for m_tuple in MERCHANTS_MAP:
            mid, m_name, category, _, _, _ = m_tuple
            if not db.query(Merchant).filter(Merchant.merchant_id == mid).first():
                db.add(Merchant(
                    merchant_id=mid,
                    name=m_name,
                    email=f"finance@{mid}.com",
                    business_category=category,
                    settlement_cycle="T+1",
                    pricing_plan="ENTERPRISE",
                    risk_tier="LOW",
                    is_synthetic=True,
                    data_source="AUGMENTED_SYNTHETIC",
                ))
        db.commit()

        # Batch insert customers
        existing_cids = {c.customer_id for c in db.query(Customer.customer_id).all()}
        new_cust_objs = []

        for row in customers_rows:
            if row["customer_id"] not in existing_cids:
                new_cust_objs.append(Customer(
                    customer_id=row["customer_id"],
                    merchant_id=row["merchant_id"],
                    name=row["full_name"],
                    email=row["email"],
                    contact=row["phone_number"],
                    is_synthetic=True,
                    data_source="AUGMENTED_SYNTHETIC",
                ))

        if new_cust_objs:
            db.bulk_save_objects(new_cust_objs)
            db.commit()
            print(f"    - Inserted {len(new_cust_objs)} new customer accounts into database.")
        else:
            print("    - Customers already synced in database.")

        total_in_db = db.query(Customer).count()
        print(f" Total Customers in opspilot.db: {total_in_db}")
    print("=" * 70)


if __name__ == "__main__":
    generate_500plus_people_dataset(target_count=600)
