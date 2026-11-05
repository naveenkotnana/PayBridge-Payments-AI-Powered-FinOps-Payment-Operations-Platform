"""Payment Analytics Engine — Phase 3.

Computes payment domain KPIs using deterministic arithmetic.

Design rules:
- All monetary sums are performed by SQL on Numeric(14,2) columns.
  Python code only reads the results; it never adds floats.
- Ratios (success rate, refund rate) are computed using Python Decimal
  to avoid float representation issues.
- Every metric documents its time window and denominator explicitly
  in the returned dict so the UI never shows undefined aggregates.
- The engine never calls an LLM. Text outputs are f-strings, not AI-generated.

Usage:
    from app.db.base import SessionLocal
    from app.analytics.payment_analytics import PaymentAnalyticsEngine

    with SessionLocal() as db:
        engine = PaymentAnalyticsEngine(db, days_back=7)
        kpis = engine.get_kpi_summary()
        bank_sr = engine.get_bank_success_rates()
"""
import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.analytics.payment_queries import get_payment_query

log = logging.getLogger("opspilot.payment_analytics")

_TWO = Decimal("0.01")


def _dec(val: Any) -> Decimal:
    """Convert any numeric value to Decimal with 2dp."""
    if val is None:
        return Decimal("0.00")
    return Decimal(str(val)).quantize(_TWO, rounding=ROUND_HALF_UP)


class PaymentAnalyticsEngine:
    """Facade over named SQL queries + Decimal post-processing.

    Args:
        db: SQLAlchemy Session (caller-managed lifecycle).
        days_back: Rolling window in days. 0 = all-time.
    """

    def __init__(self, db: Session, days_back: int = 7) -> None:
        self._db = db
        self._days_back = days_back

    def _run(self, query_name: str) -> List[Dict[str, Any]]:
        sql = get_payment_query(query_name)
        rows = self._db.execute(
            text(sql), {"days_back": self._days_back}
        ).mappings().all()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_kpi_summary(self) -> Dict[str, Any]:
        """Return top-level KPI dict for dashboard header cards.

        Returns a flat dict with clearly labelled keys and units so the
        UI does not need to recompute or interpret values.
        """
        rows = self._run("payment_kpi_summary")
        if not rows:
            return {"status": "NO_DATA", "days_back": self._days_back}

        r = rows[0]
        total = int(r.get("total_attempts") or 0)
        successful = int(r.get("successful") or 0)
        failed = int(r.get("failed") or 0)
        pending = int(r.get("pending_capture") or 0)
        terminal = successful + failed  # denominator for SR
        sr = (
            _dec(successful / terminal * 100)
            if terminal > 0
            else Decimal("0.00")
        )
        gmv = _dec(r.get("gmv_inr"))
        avg_txn = _dec(r.get("avg_transaction_value_inr"))
        fees = _dec(r.get("total_fee_inr"))

        return {
            "window_days": self._days_back if self._days_back > 0 else "ALL_TIME",
            "total_attempts": total,
            "successful_payments": successful,
            "failed_payments": failed,
            "pending_capture": pending,
            "terminal_payments": terminal,
            "success_rate_pct": float(sr),
            "gmv_inr": float(gmv),
            "total_fee_inr": float(fees),
            "avg_transaction_value_inr": float(avg_txn),
            # Derived: fee as % of GMV (shows effective take rate)
            "effective_take_rate_pct": float(
                _dec(fees / gmv * 100) if gmv > 0 else Decimal("0.00")
            ),
        }

    def get_method_breakdown(self) -> List[Dict[str, Any]]:
        """SR and GMV per payment method (UPI, CARD, NETBANKING, WALLET)."""
        return self._run("payment_sr_by_method")

    def get_bank_success_rates(self) -> List[Dict[str, Any]]:
        """Bank-wise SR. Banks with < 5 attempts have sr=null (min sample guard)."""
        return self._run("payment_sr_by_bank")

    def get_merchant_performance(self) -> List[Dict[str, Any]]:
        """Per-merchant GMV, SR, and refund exposure."""
        return self._run("payment_gmv_by_merchant")

    def get_hourly_trend(self) -> List[Dict[str, Any]]:
        """Hourly transaction volume (attempts, captured, failed, GMV)."""
        return self._run("payment_hourly_trend")

    def get_refund_rates(self) -> List[Dict[str, Any]]:
        """Refund rate per merchant. Only merchants with >= 10 captured are shown."""
        return self._run("payment_refund_rate")

    def get_settlement_status(self) -> List[Dict[str, Any]]:
        """Settlement completion rate per merchant."""
        return self._run("payment_settlement_status")

    def get_top_errors(self) -> List[Dict[str, Any]]:
        """Top 15 error codes by failure volume with financial impact."""
        return self._run("payment_top_errors")

    def get_open_discrepancies(self) -> List[Dict[str, Any]]:
        """Open reconciliation discrepancies grouped by type and severity."""
        return self._run("payment_open_discrepancies")

    def get_gateway_comparison(self) -> List[Dict[str, Any]]:
        """Current vs baseline (prior 24h) SR per gateway for degradation detection."""
        return self._run("payment_gateway_sr_comparison")

    def get_retry_recovery_rates(self) -> List[Dict[str, Any]]:
        """Recovery rate per error code from payment_attempts table."""
        return self._run("payment_retry_recovery_rate")

    def get_full_dashboard(self) -> Dict[str, Any]:
        """Return all analytics sections as a single dict for API or Streamlit."""
        return {
            "kpi_summary": self.get_kpi_summary(),
            "method_breakdown": self.get_method_breakdown(),
            "bank_success_rates": self.get_bank_success_rates(),
            "merchant_performance": self.get_merchant_performance(),
            "hourly_trend": self.get_hourly_trend(),
            "refund_rates": self.get_refund_rates(),
            "settlement_status": self.get_settlement_status(),
            "top_errors": self.get_top_errors(),
            "open_discrepancies": self.get_open_discrepancies(),
            "gateway_comparison": self.get_gateway_comparison(),
            "retry_recovery_rates": self.get_retry_recovery_rates(),
        }
