"""Razorpay-Inspired AI Payments Domain Models.

Schema decisions:
- Natural fintech identifiers with entity prefixes (pay_, order_, rfnd_, setl_, mid_)
  matching Razorpay's production API standard.
- Numeric(14, 2) used for all monetary amounts to eliminate floating point rounding error.
- Indexes on merchant_id, status, method, bank, gateway, and created_at to support
  sub-50ms analytics and slicing.

Phase 2 additions:
- PaymentEvent: raw event log with deduplication key, enabling idempotent ingestion
  and out-of-order replay.
- PaymentAttempt: individual retry attempts within a single payment, tracks retry
  ordinal, gateway tried, and outcome.
- PaymentIncident: correlated cluster of related anomalies grouped by detection engine.
- IncidentMerchant: M:N mapping between incidents and affected merchants.
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from app.db.base import Base


class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String(30), primary_key=True)  # e.g., mid_swiggy_01
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    business_category = Column(String(40), index=True)  # E_COMMERCE, FOOD_DELIVERY, SAAS
    settlement_cycle = Column(String(10), default="T+1")  # T+1, T+2
    pricing_plan = Column(String(30), default="STANDARD_MDR")  # STANDARD_MDR, ENTERPRISE
    risk_tier = Column(String(20), index=True, default="LOW")  # LOW, MEDIUM, HIGH
    status = Column(String(20), index=True, default="ACTIVE")  # ACTIVE, SUSPENDED, SETTLEMENT_HOLD
    is_synthetic = Column(Boolean, default=True)
    data_source = Column(String(20), default="SYNTHETIC", index=True)
    created_at = Column(DateTime, server_default=func.now())


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(40), primary_key=True)  # cust_Abc123...
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    contact = Column(String(20), nullable=True)
    is_synthetic = Column(Boolean, default=True)
    data_source = Column(String(20), default="SYNTHETIC", index=True)
    created_at = Column(DateTime, server_default=func.now())


class DemoWallet(Base):
    """Persisted simulated credit. Never represents provider or bank funds."""
    __tablename__ = "demo_wallets"
    customer_id = Column(String(40), primary_key=True)
    balance = Column(Numeric(14, 2), nullable=False, default=50000)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("balance >= 0", name="ck_demo_wallet_balance"), {"extend_existing": True})


class CafeOrderItems(Base):
    __tablename__ = "cafe_order_items"
    order_id = Column(String(40), primary_key=True)
    items_json = Column(Text, nullable=False)
    total = Column(Numeric(14, 2), nullable=False)


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    order_id = Column(String(40), primary_key=True)  # e.g., order_K1a2B3c4D5e6F7
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
    customer_id = Column(String(40), nullable=True, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="INR")
    receipt = Column(String(60))
    status = Column(String(20), index=True, default="CREATED")  # CREATED, ATTEMPTED, PAID
    is_synthetic = Column(Boolean, default=True)
    data_source = Column(String(20), default="SYNTHETIC", index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)


class CheckoutRequest(Base):
    """Durable idempotency reservation for Razorpay order creation."""
    __tablename__ = "checkout_requests"

    idempotency_key = Column(String(100), primary_key=True)
    customer_id = Column(String(40), ForeignKey("customers.customer_id"), nullable=False, index=True)
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    request_fingerprint = Column(String(64), nullable=False)
    items_json = Column(Text, nullable=False)
    amount_minor = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    receipt = Column(String(60), nullable=False)
    state = Column(String(20), nullable=False, default="PROCESSING", index=True)
    provider_order_id = Column(String(40), unique=True, nullable=True, index=True)
    provider_key_id = Column(String(40), nullable=True)
    last_error_code = Column(String(40), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (
        CheckConstraint("amount_minor >= 100", name="ck_checkout_amount_minimum"),
        CheckConstraint("currency = 'INR'", name="ck_checkout_currency_inr"),
        CheckConstraint("state IN ('PROCESSING', 'UNCERTAIN', 'CREATED')", name="ck_checkout_state"),
    )


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    payment_id = Column(String(40), primary_key=True)  # e.g., pay_L1m2N3o4P5q6R7
    order_id = Column(String(40), ForeignKey("payment_orders.order_id"), index=True, nullable=False)
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
    customer_id = Column(String(40), nullable=True, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="INR")
    method = Column(String(20), index=True, nullable=False)  # UPI, CARD, NETBANKING, WALLET
    card_network = Column(String(20), nullable=True)  # VISA, MASTERCARD, RUPAY
    bank = Column(String(30), index=True, nullable=True)  # HDFC, ICICI, AXIS, SBI
    gateway = Column(String(30), index=True, nullable=False)  # RAZORPAY_DIRECT, HDFC_PG, PAYU
    status = Column(String(20), index=True, nullable=False)  # AUTHORIZED, CAPTURED, FAILED, REFUNDED
    error_code = Column(String(60), nullable=True)  # e.g., BAD_REQUEST_GATEWAY_DOWN
    error_description = Column(Text, nullable=True)
    fee = Column(Numeric(10, 2), default=0.0)  # MDR charged by payment aggregator
    tax = Column(Numeric(10, 2), default=0.0)  # 18% GST on MDR
    net_amount = Column(Numeric(14, 2), nullable=False)  # amount - fee - tax
    reconciled = Column(Boolean, default=False, index=True)
    is_synthetic = Column(Boolean, default=True, index=True)
    data_source = Column(String(20), default="SYNTHETIC", index=True)  # REAL, SYNTHETIC, AUGMENTED
    augmentation_method = Column(String(40), nullable=True)  # e.g., STRATIFIED_RESAMPLE, OUTAGE_INJECTION
    generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    captured_at = Column(DateTime, nullable=True)


Index("ix_pay_merchant_status", PaymentTransaction.merchant_id, PaymentTransaction.status)
Index("ix_pay_method_gateway", PaymentTransaction.method, PaymentTransaction.gateway)


class PaymentEvent(Base):
    """Immutable event log — each state transition is a new row.

    Deduplication key = (payment_id, event_type): the ingestion layer skips
    re-insertion of an already-recorded event so out-of-order or duplicate
    delivery from upstream is safe.
    """

    __tablename__ = "payment_events"

    event_id = Column(String(50), primary_key=True)  # evt_<uuid_hex[:14]>
    payment_id = Column(
        String(40), ForeignKey("payment_transactions.payment_id"), index=True, nullable=False
    )
    event_type = Column(String(40), index=True, nullable=False)
    # PAYMENT_CREATED, PAYMENT_AUTHORIZED, PAYMENT_CAPTURED, PAYMENT_FAILED,
    # PAYMENT_REFUNDED, RETRY_INITIATED, RETRY_SUCCEEDED, RETRY_FAILED
    event_payload = Column(Text, nullable=True)  # JSON snapshot of the event body
    event_source = Column(String(30), nullable=False, default="SIMULATOR")
    # SIMULATOR | WEBHOOK | MANUAL_RECONCILIATION
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)
    # Composite: payment_id + "::" + event_type — enforced at DB level
    occurred_at = Column(DateTime, nullable=False, index=True)
    ingested_at = Column(DateTime, server_default=func.now(), index=True)


Index("ix_event_payment_type", PaymentEvent.payment_id, PaymentEvent.event_type)


class PaymentAttempt(Base):
    """Each individual attempt at authorising a payment, including retries.

    attempt_number starts at 1 for the original attempt. Retries increment it.
    This table provides the raw data for the retry intelligence engine.
    """

    __tablename__ = "payment_attempts"

    attempt_id = Column(String(50), primary_key=True)  # att_<uuid_hex[:14]>
    payment_id = Column(
        String(40), ForeignKey("payment_transactions.payment_id"), index=True, nullable=False
    )
    attempt_number = Column(Integer, nullable=False, default=1)
    gateway = Column(String(30), index=True, nullable=False)
    bank = Column(String(30), index=True, nullable=True)
    status = Column(String(20), index=True, nullable=False)  # AUTHORIZED, FAILED, TIMED_OUT
    error_code = Column(String(60), nullable=True)
    # Retry classification: RETRYABLE, NON_RETRYABLE, UNKNOWN
    error_category = Column(String(20), index=True, nullable=True)
    latency_ms = Column(Integer, nullable=True)  # Round-trip latency to gateway
    attempted_at = Column(DateTime, nullable=False, index=True)


Index("ix_attempt_payment_num", PaymentAttempt.payment_id, PaymentAttempt.attempt_number)
Index("ix_attempt_gateway_err", PaymentAttempt.gateway, PaymentAttempt.error_code)


class PaymentIncident(Base):
    """A correlated cluster of anomalies grouped by the incident correlation engine.

    Design: one incident per operational event (e.g., 'HDFC gateway degradation').
    Many individual anomaly signals are merged here to avoid alert fatigue.
    Severity, affected_banks, affected_methods are populated by the engine —
    never by an LLM — to ensure reproducibility.
    """

    __tablename__ = "payment_incidents"

    incident_id = Column(String(50), primary_key=True)  # INC-2026-001
    title = Column(String(200), nullable=False)
    category = Column(String(40), index=True, nullable=False)
    # GATEWAY_DEGRADATION, BANK_CONNECTIVITY, HIGH_FAILURE_RATE,
    # SETTLEMENT_DELAY, FRAUD_SPIKE, RECONCILIATION_FAILURE
    severity = Column(String(10), index=True, nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(20), index=True, default="OPEN")
    # OPEN, INVESTIGATING, RESOLVED, FALSE_POSITIVE
    affected_banks = Column(String(200), nullable=True)  # comma-separated
    affected_methods = Column(String(100), nullable=True)  # comma-separated
    failed_transaction_count = Column(Integer, default=0)
    estimated_financial_exposure = Column(Numeric(14, 2), default=0)
    baseline_success_rate = Column(Numeric(5, 2), nullable=True)  # pre-incident SR %
    observed_success_rate = Column(Numeric(5, 2), nullable=True)  # during-incident SR %
    evidence_summary = Column(Text, nullable=True)
    root_cause_hypothesis = Column(Text, nullable=True)  # ranked list, never asserted as fact
    investigation_notes = Column(Text, nullable=True)
    detected_at = Column(DateTime, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    is_synthetic = Column(Boolean, default=True)
    data_source = Column(String(20), default="SYNTHETIC")
    created_at = Column(DateTime, server_default=func.now())


class IncidentMerchant(Base):
    """M:N link between incidents and affected merchants.

    Separate table so one incident can affect many merchants and a single
    merchant's exposure can be summed across all open incidents.
    """

    __tablename__ = "incident_merchants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(
        String(50), ForeignKey("payment_incidents.incident_id"), index=True, nullable=False
    )
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
    failed_amount = Column(Numeric(14, 2), default=0)  # exposure for this merchant
    failed_count = Column(Integer, default=0)


Index("ix_inc_merchant", IncidentMerchant.incident_id, IncidentMerchant.merchant_id)


class Refund(Base):
    __tablename__ = "refunds"

    refund_id = Column(String(40), primary_key=True)  # e.g., rfnd_X1y2Z3a4B5c6D7
    payment_id = Column(String(40), ForeignKey("payment_transactions.payment_id"), index=True, nullable=False)
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="INR")
    status = Column(String(20), index=True, default="PROCESSED")  # PROCESSED, PENDING, FAILED
    speed = Column(String(20), default="OPTIMAL")  # OPTIMAL, INSTANT
    reason = Column(String(60), default="CUSTOMER_REQUEST")
    reconciled = Column(Boolean, default=False)
    is_synthetic = Column(Boolean, default=True)
    data_source = Column(String(20), default="SYNTHETIC")
    created_at = Column(DateTime, server_default=func.now(), index=True)


class Settlement(Base):
    __tablename__ = "settlements"

    settlement_id = Column(String(40), primary_key=True)  # e.g., setl_A1b2C3d4E5f6G7
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
    gross_amount = Column(Numeric(14, 2), nullable=False)
    fee_deducted = Column(Numeric(14, 2), nullable=False)
    tax_deducted = Column(Numeric(14, 2), nullable=False)
    net_payout = Column(Numeric(14, 2), nullable=False)
    utr_number = Column(String(50), unique=True, index=True)
    settlement_date = Column(Date, index=True, nullable=False)
    status = Column(String(20), index=True, default="SETTLED")  # SETTLED, PENDING, BLOCKED
    is_synthetic = Column(Boolean, default=True)
    data_source = Column(String(20), default="SYNTHETIC")
    created_at = Column(DateTime, server_default=func.now())


class SettlementItem(Base):
    __tablename__ = "settlement_items"

    item_id = Column(String(40), primary_key=True)  # item_...
    settlement_id = Column(String(40), ForeignKey("settlements.settlement_id"), index=True, nullable=False)
    payment_id = Column(String(40), ForeignKey("payment_transactions.payment_id"), index=True, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    fee = Column(Numeric(10, 2), default=0.0)
    tax = Column(Numeric(10, 2), default=0.0)
    net_amount = Column(Numeric(14, 2), nullable=False)
    type = Column(String(20), default="PAYMENT")  # PAYMENT, REFUND, ADJUSTMENT
    created_at = Column(DateTime, server_default=func.now())


class Dispute(Base):
    __tablename__ = "disputes"

    dispute_id = Column(String(40), primary_key=True)  # disp_...
    payment_id = Column(String(40), ForeignKey("payment_transactions.payment_id"), index=True, nullable=False)
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="INR")
    reason = Column(String(60), default="FRAUDULENT")  # FRAUDULENT, UNRECOGNIZED, DEFECTIVE_MERCHANDISE
    status = Column(String(20), index=True, default="OPEN")  # OPEN, UNDER_REVIEW, WON, LOST
    phase = Column(String(30), default="INQUIRY")  # INQUIRY, CHARGEBACK, PRE_ARBITRATION
    evidence_submitted = Column(Boolean, default=False)
    is_synthetic = Column(Boolean, default=True)
    data_source = Column(String(20), default="SYNTHETIC")
    created_at = Column(DateTime, server_default=func.now(), index=True)


class ReconciliationDiscrepancy(Base):
    __tablename__ = "reconciliation_discrepancies"

    discrepancy_id = Column(String(40), primary_key=True)  # DISC-2026-001
    payment_id = Column(String(40), index=True, nullable=False)
    merchant_id = Column(String(30), index=True, nullable=False)
    issue_type = Column(String(40), index=True, nullable=False)
    # MDR_MISMATCH, UNCAPTURED_AUTH, MISSING_GATEWAY_SETTLEMENT, DUPLICATE_DEBIT
    expected_amount = Column(Numeric(14, 2), nullable=False)
    observed_amount = Column(Numeric(14, 2), nullable=False)
    variance = Column(Numeric(14, 2), nullable=False)
    severity = Column(String(10), index=True, nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(20), index=True, default="OPEN")  # OPEN, ESCALATED, RESOLVED
    is_synthetic = Column(Boolean, default=True)
    data_source = Column(String(20), default="SYNTHETIC")
    detected_at = Column(DateTime, server_default=func.now(), index=True)


class GatewayHealthMetric(Base):
    __tablename__ = "gateway_health_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gateway = Column(String(30), index=True, nullable=False)
    method = Column(String(20), index=True, nullable=False)
    window_start = Column(DateTime, index=True, nullable=False)
    window_end = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)
    successes = Column(Integer, default=0)
    success_rate = Column(Numeric(5, 2), nullable=False)  # e.g., 98.50
    avg_latency_ms = Column(Integer, default=0)
    status = Column(String(20), index=True, default="HEALTHY")  # HEALTHY, DEGRADED, DOWN


class PaymentIngestionRun(Base):
    """Tracks payment batch CSV, external URLs, and webhook data ingestion runs with full lineage."""

    __tablename__ = "payment_ingestion_runs"

    run_id = Column(String(50), primary_key=True)  # RUN-YYYYMMDD-UUID
    source_type = Column(String(30), nullable=False)  # CSV_IMPORT, URL_IMPORT, RAZORPAY_WEBHOOK
    source_identifier = Column(String(255), nullable=False)  # file name or URL
    status = Column(String(20), nullable=False, default="PROCESSING")  # PROCESSING, COMPLETED, FAILED
    records_received = Column(Integer, default=0)
    records_accepted = Column(Integer, default=0)
    records_rejected = Column(Integer, default=0)
    records_duplicated = Column(Integer, default=0)
    raw_file_path = Column(String(255), nullable=True)
    rejected_file_path = Column(String(255), nullable=True)
    error_summary = Column(Text, nullable=True)
    started_at = Column(DateTime, server_default=func.now(), index=True)
    completed_at = Column(DateTime, nullable=True)


class PaymentIngestionRecord(Base):
    """Audit record for individual rejected rows during payment ingestion."""

    __tablename__ = "payment_ingestion_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(50), ForeignKey("payment_ingestion_runs.run_id"), index=True, nullable=False)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(Text, nullable=False)  # JSON representation of input row
    rejection_reason = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


