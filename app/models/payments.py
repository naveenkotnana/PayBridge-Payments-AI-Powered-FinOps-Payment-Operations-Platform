"""Razorpay-Inspired AI Payments Domain Models.

Schema decisions:
- Natural fintech identifiers with entity prefixes (pay_, order_, rfnd_, setl_, mid_)
  matching Razorpay's production API standard.
- Numeric(14, 2) used for all monetary amounts to eliminate floating point rounding error.
- Indexes on merchant_id, status, method, bank, gateway, and created_at to support
  sub-50ms analytics and slicing.
"""
from sqlalchemy import (
    Boolean,
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
    created_at = Column(DateTime, server_default=func.now())


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    order_id = Column(String(40), primary_key=True)  # e.g., order_K1a2B3c4D5e6F7
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="INR")
    receipt = Column(String(60))
    status = Column(String(20), index=True, default="CREATED")  # CREATED, ATTEMPTED, PAID
    created_at = Column(DateTime, server_default=func.now(), index=True)


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    payment_id = Column(String(40), primary_key=True)  # e.g., pay_L1m2N3o4P5q6R7
    order_id = Column(String(40), ForeignKey("payment_orders.order_id"), index=True, nullable=False)
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
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
    created_at = Column(DateTime, server_default=func.now(), index=True)
    captured_at = Column(DateTime, nullable=True)


Index("ix_pay_merchant_status", PaymentTransaction.merchant_id, PaymentTransaction.status)
Index("ix_pay_method_gateway", PaymentTransaction.method, PaymentTransaction.gateway)


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
    created_at = Column(DateTime, server_default=func.now())


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
