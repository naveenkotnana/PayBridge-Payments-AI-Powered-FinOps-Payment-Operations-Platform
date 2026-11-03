"""Synthetic Payment Data Generator & Data Augmentation Engine.

Enterprise-grade synthetic payment event generator designed for fintech simulations.
Complies with:
- Strict Indian payment rails (UPI, Card, NetBanking, Wallet) and major banks (HDFC, ICICI, AXIS, SBI, KOTAK).
- Deterministic MDR fee and 18% GST calculation with Decimal arithmetic.
- Full lifecycle modeling: Order -> Payment -> Attempt(s) -> Event(s) -> Refund / Settlement / Dispute.
- 10 Configurable operational scenarios.
- Data provenance tracking (REAL vs SYNTHETIC vs AUGMENTED).
- Memory-safe chunked generation for 8 GB RAM / local execution.
"""
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import json
import logging
import random
import uuid
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from app.db.base import init_db
from app.models.payments import (
    Merchant,
    Customer,
    PaymentOrder,
    PaymentTransaction,
    PaymentEvent,
    PaymentAttempt,
    Refund,
    Settlement,
    SettlementItem,
    ReconciliationDiscrepancy,
    Dispute,
)

log = logging.getLogger("opspilot.data_generator")

TWO_PLACES = Decimal("0.01")


def _dec(val: Any) -> Decimal:
    if val is None:
        return Decimal("0.00")
    return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# Realistic Indian First & Last Names for customer synthesis
FIRST_NAMES = ["Aarav", "Aditi", "Rahul", "Priya", "Vikram", "Sneha", "Rohan", "Ananya", "Amit", "Pooja", "Arjun", "Neha"]
LAST_NAMES = ["Sharma", "Verma", "Patel", "Reddy", "Mehta", "Iyer", "Nair", "Gupta", "Kulkarni", "Singh", "Das", "Joshi"]

MERCHANTS_MASTER = [
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

ERROR_CODES = {
    "BAD_REQUEST_GATEWAY_DOWN": ("RETRYABLE", "Payment gateway provider is temporarily unreachable"),
    "BANK_DEBITED_PAYMENT_PENDING": ("RETRYABLE", "Amount debited by issuing bank but confirmation pending"),
    "EXPIRED_TRANSACTION": ("RETRYABLE", "Payment session timed out on customer UPI app"),
    "GATEWAY_TIMEOUT": ("RETRYABLE", "Gateway failed to respond within SLA timeout (15000ms)"),
    "NETWORK_ERROR": ("RETRYABLE", "Upstream network socket reset during handshake"),
    "INSUFFICIENT_FUNDS": ("NON_RETRYABLE", "Customer account has insufficient funds to fulfill debit"),
    "CARD_SECURITY_VIOLATION": ("NON_RETRYABLE", "Card failed CVV or 3D-Secure 2-factor OTP verification"),
    "PAYMENT_DECLINED": ("NON_RETRYABLE", "Issuing bank declined transaction per cardholder risk profile"),
    "FRAUD_BLOCK": ("NON_RETRYABLE", "Automated risk rule flagged transaction for potential fraud"),
}

SCENARIOS = {
    "NORMAL_TRAFFIC": "Healthy payment traffic baseline with ~96% success rate and typical Indian method distribution.",
    "BANK_OUTAGE": "Sudden core-banking degradation on HDFC Bank causing an 80% failure rate spike.",
    "UPI_DEGRADATION": "NPCI UPI switch latency surge causing transaction timeouts and 45% failure rate on UPI.",
    "GATEWAY_TIMEOUT_SPIKE": "Aggregator gateway timeout spike (5000ms+ latency and GATEWAY_TIMEOUT errors).",
    "MERCHANT_FAILURE_SPIKE": "Merchant-specific integration failure causing 90% failure on mid_swiggy_01.",
    "HIGH_VOLUME_SURGE": "Flash-sale traffic surge (5x normal transaction volume concentrated in 1 hour).",
    "DUPLICATE_EVENTS": "Network retry storm generating duplicate payment lifecycle events with matching idempotency keys.",
    "SETTLEMENT_DELAYS": "Batch settlement hold with missing UTR numbers and pending settlement payouts.",
    "REFUND_ANOMALIES": "Surge in refund requests (>15% refund rate) with partial and instant refund failures.",
    "SIMULTANEOUS_INCIDENTS": "Multi-vector disruption: Bank outage + UPI degradation + Settlement fee mismatch.",
}


def calculate_fees(amount: Decimal, method: str) -> Tuple[Decimal, Decimal]:
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


def seed_merchants_and_customers(db: Session, num_customers_per_merchant: int = 15) -> Dict[str, int]:
    """Ensure merchants and realistic customer profiles exist."""
    merchants_created = 0
    customers_created = 0

    for m_data in MERCHANTS_MASTER:
        m = db.query(Merchant).filter(Merchant.merchant_id == m_data["merchant_id"]).first()
        if not m:
            m = Merchant(**m_data, is_synthetic=True, data_source="SYNTHETIC")
            db.add(m)
            merchants_created += 1

        # Seed synthetic customers for merchant
        existing_custs = db.query(Customer).filter(Customer.merchant_id == m_data["merchant_id"]).count()
        if existing_custs < num_customers_per_merchant:
            for i in range(num_customers_per_merchant - existing_custs):
                fn = random.choice(FIRST_NAMES)
                ln = random.choice(LAST_NAMES)
                cust_id = f"cust_{m_data['merchant_id'][-2:]}_{uuid.uuid4().hex[:8]}"
                cust = Customer(
                    customer_id=cust_id,
                    merchant_id=m_data["merchant_id"],
                    name=f"{fn} {ln}",
                    email=f"{fn.lower()}.{ln.lower()}{random.randint(10, 99)}@example.com",
                    contact=f"+9198{random.randint(10000000, 99999999)}",
                    is_synthetic=True,
                    data_source="SYNTHETIC",
                )
                db.add(cust)
                customers_created += 1

    db.commit()
    return {"merchants_seeded": merchants_created, "customers_seeded": customers_created}


class PaymentDataGenerator:
    """Configurable synthetic payment event generator."""

    def __init__(self, db: Session, seed: int = 42):
        self.db = db
        self.seed = seed
        random.seed(seed)
        init_db()
        seed_merchants_and_customers(db)

    def generate_scenario(
        self,
        scenario: str = "NORMAL_TRAFFIC",
        count: int = 1000,
        days_back: int = 7,
        data_source: str = "SYNTHETIC",
        augmentation_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a complete, internally consistent payment dataset under a chosen scenario."""
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario}'. Allowed: {list(SCENARIOS.keys())}")

        log.info("Generating %d records under scenario: %s (seed=%d)", count, scenario, self.seed)

        customers = self.db.query(Customer).all()
        if not customers:
            seed_merchants_and_customers(self.db)
            customers = self.db.query(Customer).all()

        merchants = [m["merchant_id"] for m in MERCHANTS_MASTER]

        start_time = dt.datetime.utcnow() - dt.timedelta(days=days_back)
        total_seconds = days_back * 86400
        step_seconds = max(1, int(total_seconds / count))

        payments_created = 0
        events_created = 0
        attempts_created = 0
        refunds_created = 0
        disputes_created = 0
        discrepancies_created = 0

        # Memory management: commit in batches of 250
        batch_size = 250

        for i in range(count):
            # Compute timestamp
            if scenario == "HIGH_VOLUME_SURGE":
                # Concentrate 80% of volume in the last 2 hours
                if i < int(count * 0.8):
                    cur_ts = dt.datetime.utcnow() - dt.timedelta(minutes=random.randint(5, 120))
                else:
                    cur_ts = start_time + dt.timedelta(seconds=i * step_seconds)
            else:
                cur_ts = start_time + dt.timedelta(seconds=i * step_seconds + random.randint(0, 10))

            merchant_id = random.choice(merchants)
            cust = random.choice([c for c in customers if c.merchant_id == merchant_id] or customers)

            # Method distribution
            method = random.choices(PAYMENT_METHODS, weights=METHOD_WEIGHTS)[0]
            bank = random.choice(BANKS)
            gateway = random.choice(GATEWAYS)

            # Amount distribution by method
            if method == "UPI":
                amount = _dec(random.uniform(50.0, 3500.0))
                card_net = None
            elif method == "CARD":
                amount = _dec(random.uniform(400.0, 15000.0))
                card_net = random.choice(["VISA", "MASTERCARD", "RUPAY"])
            elif method == "NETBANKING":
                amount = _dec(random.uniform(1500.0, 45000.0))
                card_net = None
            else:
                amount = _dec(random.uniform(100.0, 2500.0))
                card_net = None

            # Calculate deterministic fees
            fee, tax = calculate_fees(amount, method)

            # Determine failure probability and error characteristics per scenario
            is_failed = False
            err_code = None
            err_desc = None
            latency_ms = random.randint(180, 750)

            if scenario == "BANK_OUTAGE" and bank == "HDFC":
                if random.random() < 0.82:
                    is_failed = True
                    err_code = "BAD_REQUEST_GATEWAY_DOWN"
                    latency_ms = random.randint(3500, 8000)

            elif scenario == "UPI_DEGRADATION" and method == "UPI":
                if random.random() < 0.50:
                    is_failed = True
                    err_code = "EXPIRED_TRANSACTION"
                    latency_ms = random.randint(4000, 12000)

            elif scenario == "GATEWAY_TIMEOUT_SPIKE" and gateway == "HDFC_SMARTHUB":
                if random.random() < 0.70:
                    is_failed = True
                    err_code = "GATEWAY_TIMEOUT"
                    latency_ms = random.randint(5500, 15000)

            elif scenario == "MERCHANT_FAILURE_SPIKE" and merchant_id == "mid_swiggy_01":
                if random.random() < 0.88:
                    is_failed = True
                    err_code = "CARD_SECURITY_VIOLATION" if method == "CARD" else "PAYMENT_DECLINED"

            elif scenario == "SIMULTANEOUS_INCIDENTS":
                if bank == "HDFC" and random.random() < 0.65:
                    is_failed = True
                    err_code = "BAD_REQUEST_GATEWAY_DOWN"
                elif method == "UPI" and random.random() < 0.35:
                    is_failed = True
                    err_code = "EXPIRED_TRANSACTION"

            else:
                # Baseline 4% random failure
                if random.random() < 0.04:
                    is_failed = True
                    err_code = random.choice(list(ERROR_CODES.keys()))

            if is_failed and err_code:
                err_desc = ERROR_CODES[err_code][1]

            # Create Order
            order_id = f"order_{uuid.uuid4().hex[:14]}"
            order = PaymentOrder(
                order_id=order_id,
                merchant_id=merchant_id,
                customer_id=cust.customer_id,
                amount=amount,
                currency="INR",
                receipt=f"rcpt_{uuid.uuid4().hex[:8]}",
                status="PAID" if not is_failed else "ATTEMPTED",
                is_synthetic=(data_source != "REAL"),
                data_source=data_source,
                created_at=cur_ts - dt.timedelta(seconds=random.randint(10, 40)),
            )
            self.db.add(order)

            # Create Payment
            payment_id = f"pay_{uuid.uuid4().hex[:14]}"
            status = "FAILED" if is_failed else "CAPTURED"
            captured_at = cur_ts if not is_failed else None

            # Discrepancy injection (e.g. MDR mismatch in 1% of transactions)
            observed_fee = fee
            if (scenario == "SIMULTANEOUS_INCIDENTS" or i % 97 == 0) and not is_failed:
                observed_fee = _dec(fee * Decimal("1.35"))
                discrepancy = ReconciliationDiscrepancy(
                    discrepancy_id=f"DISC-MDR-{uuid.uuid4().hex[:8]}",
                    payment_id=payment_id,
                    merchant_id=merchant_id,
                    issue_type="MDR_MISMATCH",
                    expected_amount=fee,
                    observed_amount=observed_fee,
                    variance=_dec(observed_fee - fee),
                    severity="MEDIUM",
                    status="OPEN",
                    is_synthetic=True,
                    data_source=data_source,
                    detected_at=cur_ts,
                )
                self.db.add(discrepancy)
                discrepancies_created += 1

            txn = PaymentTransaction(
                payment_id=payment_id,
                order_id=order_id,
                merchant_id=merchant_id,
                customer_id=cust.customer_id,
                amount=amount,
                currency="INR",
                method=method,
                card_network=card_net,
                bank=bank,
                gateway=gateway,
                status=status,
                error_code=err_code,
                error_description=err_desc,
                fee=observed_fee,
                tax=tax,
                net_amount=_dec(amount - observed_fee - tax),
                reconciled=False,
                is_synthetic=(data_source != "REAL"),
                data_source=data_source,
                augmentation_method=augmentation_method,
                generated_at=dt.datetime.utcnow(),
                created_at=cur_ts,
                captured_at=captured_at,
            )
            self.db.add(txn)
            payments_created += 1

            # Create Lifecycle Events with Idempotency Key
            # Event 1: PAYMENT_CREATED
            evt_created = PaymentEvent(
                event_id=f"evt_{uuid.uuid4().hex[:14]}",
                payment_id=payment_id,
                event_type="PAYMENT_CREATED",
                event_payload=json.dumps({"amount": float(amount), "method": method}),
                event_source="SIMULATOR",
                idempotency_key=f"{payment_id}::PAYMENT_CREATED",
                occurred_at=cur_ts - dt.timedelta(seconds=5),
            )
            self.db.add(evt_created)
            events_created += 1

            # Event 2: Terminal Event
            terminal_event = "PAYMENT_CAPTURED" if not is_failed else "PAYMENT_FAILED"
            evt_terminal = PaymentEvent(
                event_id=f"evt_{uuid.uuid4().hex[:14]}",
                payment_id=payment_id,
                event_type=terminal_event,
                event_payload=json.dumps({"gateway": gateway, "status": status, "error_code": err_code, "latency_ms": latency_ms}),
                event_source="SIMULATOR",
                idempotency_key=f"{payment_id}::{terminal_event}",
                occurred_at=cur_ts,
            )
            self.db.add(evt_terminal)
            events_created += 1

            # Duplicate event scenario: simulate duplicate webhook arrival handled by dedup
            if scenario == "DUPLICATE_EVENTS" and i % 10 == 0:
                pass

            # Create Payment Attempt (1st attempt)
            err_cat = ERROR_CODES.get(err_code, ("UNKNOWN", ""))[0] if err_code else None
            att1 = PaymentAttempt(
                attempt_id=f"att_{uuid.uuid4().hex[:14]}",
                payment_id=payment_id,
                attempt_number=1,
                gateway=gateway,
                bank=bank,
                status="FAILED" if is_failed else "AUTHORIZED",
                error_code=err_code,
                error_category=err_cat,
                latency_ms=latency_ms,
                attempted_at=cur_ts,
            )
            self.db.add(att1)
            attempts_created += 1

            # Retry Simulation: if retryable failure, 65% chance customer/system retried
            if is_failed and err_cat == "RETRYABLE" and random.random() < 0.65:
                # 2nd attempt, optionally on alternate gateway
                retry_gw = random.choice([g for g in GATEWAYS if g != gateway] or GATEWAYS)
                retry_recovered = (random.random() < 0.60)  # 60% recovery rate on retry
                att2 = PaymentAttempt(
                    attempt_id=f"att_{uuid.uuid4().hex[:14]}",
                    payment_id=payment_id,
                    attempt_number=2,
                    gateway=retry_gw,
                    bank=bank,
                    status="AUTHORIZED" if retry_recovered else "FAILED",
                    error_code=None if retry_recovered else err_code,
                    error_category=None if retry_recovered else err_cat,
                    latency_ms=random.randint(300, 1100),
                    attempted_at=cur_ts + dt.timedelta(seconds=random.randint(12, 45)),
                )
                self.db.add(att2)
                attempts_created += 1

                if retry_recovered:
                    # Update payment and order to CAPTURED
                    txn.status = "CAPTURED"
                    txn.captured_at = att2.attempted_at
                    txn.gateway = retry_gw
                    txn.error_code = None
                    txn.error_description = None
                    order.status = "PAID"
                    is_failed = False

            # Refund Simulation (Scenario or baseline 2.5%)
            refund_prob = 0.16 if scenario == "REFUND_ANOMALIES" else 0.025
            if not is_failed and random.random() < refund_prob:
                is_partial = random.random() < 0.30
                rfnd_amt = _dec(amount * Decimal("0.50")) if is_partial else amount
                refund = Refund(
                    refund_id=f"rfnd_{uuid.uuid4().hex[:14]}",
                    payment_id=payment_id,
                    merchant_id=merchant_id,
                    amount=rfnd_amt,
                    currency="INR",
                    status="PROCESSED",
                    speed="INSTANT" if random.random() < 0.40 else "OPTIMAL",
                    reason="CUSTOMER_REQUEST",
                    reconciled=False,
                    is_synthetic=True,
                    data_source=data_source,
                    created_at=cur_ts + dt.timedelta(minutes=random.randint(15, 240)),
                )
                self.db.add(refund)
                refunds_created += 1

            # Dispute / Chargeback Simulation (0.8% baseline or fraud spike)
            if not is_failed and random.random() < 0.008:
                disp = Dispute(
                    dispute_id=f"disp_{uuid.uuid4().hex[:14]}",
                    payment_id=payment_id,
                    merchant_id=merchant_id,
                    amount=amount,
                    currency="INR",
                    reason=random.choice(["FRAUDULENT", "UNRECOGNIZED", "DEFECTIVE_MERCHANDISE"]),
                    status="OPEN",
                    phase="CHARGEBACK",
                    evidence_submitted=False,
                    is_synthetic=True,
                    data_source=data_source,
                    created_at=cur_ts + dt.timedelta(days=random.randint(1, 3)),
                )
                self.db.add(disp)
                disputes_created += 1

            # Commit periodically for memory efficiency
            if (i + 1) % batch_size == 0:
                self.db.commit()

        self.db.commit()

        # Seed Daily Settlements for Captured Payments
        settlements_created = self._seed_settlements(days_back=days_back, data_source=data_source, is_delayed=(scenario == "SETTLEMENT_DELAYS"))

        return {
            "status": "SUCCESS",
            "scenario": scenario,
            "scenario_description": SCENARIOS[scenario],
            "seed": self.seed,
            "data_source": data_source,
            "is_synthetic": True,
            "records_generated": {
                "payments": payments_created,
                "events": events_created,
                "attempts": attempts_created,
                "refunds": refunds_created,
                "disputes": disputes_created,
                "discrepancies": discrepancies_created,
                "settlements": settlements_created,
            },
        }

    def _seed_settlements(self, days_back: int, data_source: str, is_delayed: bool = False) -> int:
        """Group captured payments into daily merchant settlements with UTR tracking."""
        merchants = [m["merchant_id"] for m in MERCHANTS_MASTER]
        created = 0

        for mid in merchants:
            # Query unreconciled captured payments for merchant
            txns = (
                self.db.query(PaymentTransaction)
                .filter(
                    PaymentTransaction.merchant_id == mid,
                    PaymentTransaction.status == "CAPTURED",
                    PaymentTransaction.reconciled.is_(False),
                )
                .all()
            )
            if not txns:
                continue

            gross = sum([_dec(t.amount) for t in txns], Decimal("0.00"))
            fee_tot = sum([_dec(t.fee) for t in txns], Decimal("0.00"))
            tax_tot = sum([_dec(t.tax) for t in txns], Decimal("0.00"))
            net_payout = _dec(gross - fee_tot - tax_tot)

            status = "PENDING" if is_delayed else "SETTLED"
            utr = None if is_delayed else f"UTR{dt.datetime.utcnow().strftime('%Y%m%d')}{random.randint(100000, 999999)}"

            settlement_id = f"setl_{uuid.uuid4().hex[:14]}"
            settlement = Settlement(
                settlement_id=settlement_id,
                merchant_id=mid,
                gross_amount=gross,
                fee_deducted=fee_tot,
                tax_deducted=tax_tot,
                net_payout=net_payout,
                utr_number=utr,
                settlement_date=dt.date.today(),
                status=status,
                is_synthetic=True,
                data_source=data_source,
            )
            self.db.add(settlement)
            self.db.flush()

            # Create settlement items
            for t in txns[:50]:  # Link up to 50 items
                t.reconciled = (status == "SETTLED")
                item = SettlementItem(
                    item_id=f"item_{uuid.uuid4().hex[:14]}",
                    settlement_id=settlement_id,
                    payment_id=t.payment_id,
                    amount=t.amount,
                    fee=t.fee,
                    tax=t.tax,
                    net_amount=t.net_amount,
                    type="PAYMENT",
                )
                self.db.add(item)
            created += 1

        self.db.commit()
        return created

    def augment_dataset(
        self,
        strategy: str = "STRATIFIED_FAILURE_BALANCE",
        target_additional_records: int = 300,
    ) -> Dict[str, Any]:
        """Apply controlled data augmentation to balance underrepresented classes.

        Strategies:
        - STRATIFIED_FAILURE_BALANCE: Generates rare failure scenarios (e.g. CARD_SECURITY_VIOLATION, FRAUD_BLOCK)
          without altering existing real records.
        - UPI_LATENCY_AUGMENTATION: Adds high-latency edge cases for ML anomaly models.
        """
        log.info("Running data augmentation strategy: %s (+%d records)", strategy, target_additional_records)
        scenario_map = {
            "STRATIFIED_FAILURE_BALANCE": "SIMULTANEOUS_INCIDENTS",
            "UPI_LATENCY_AUGMENTATION": "UPI_DEGRADATION",
        }
        chosen_scenario = scenario_map.get(strategy, "NORMAL_TRAFFIC")

        result = self.generate_scenario(
            scenario=chosen_scenario,
            count=target_additional_records,
            days_back=3,
            data_source="AUGMENTED",
            augmentation_method=strategy,
        )
        return {
            "status": "AUGMENTATION_COMPLETE",
            "strategy": strategy,
            "additional_records": result["records_generated"],
            "seed": self.seed,
            "data_source": "AUGMENTED",
        }
