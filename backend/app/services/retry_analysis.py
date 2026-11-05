"""Payment Retry Intelligence Engine — Phase 5.

Analyses payment retry behaviour to answer:
1. Which error codes are worth retrying? (recovery rate)
2. What is the optimal retry window? (time-to-recovery analysis)
3. Which gateways have the best retry success rates?
4. How many retries are typically needed before recovery?
5. Are we over-retrying non-retryable errors (wasting latency budget)?

Design rules:
- Never recommends retry for NON_RETRYABLE errors (confirmed failures).
- All arithmetic uses Decimal; percentages are Python-computed, not estimated.
- Minimum sample guard: < MIN_SAMPLE retried payments → return no recommendation.
- Output is structured data, not free-form text. The LLM layer in the agent
  workflow receives this as evidence and generates the human-readable summary.
"""
import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.ingestion_payments import classify_error

log = logging.getLogger("opspilot.retry_analysis")

_TWO = Decimal("0.01")
MIN_SAMPLE = 3   # Minimum payments with that error for a recommendation
MAX_RETRIES_RETRYABLE = 3    # Recommended max retries for RETRYABLE errors
MAX_RETRIES_UNKNOWN = 1       # 1 speculative retry for UNKNOWN errors


def _dec(val: Any) -> Decimal:
    if val is None:
        return Decimal("0.00")
    return Decimal(str(val)).quantize(_TWO, rounding=ROUND_HALF_UP)


class RetryAnalysisEngine:
    """Retry intelligence analysis over payment_attempts data.

    Args:
        db: SQLAlchemy Session (caller owns lifecycle).
        days_back: Rolling window. 0 = all-time.
    """

    def __init__(self, db: Session, days_back: int = 7) -> None:
        self._db = db
        self._days_back = days_back

    # ------------------------------------------------------------------
    # Core analysis methods
    # ------------------------------------------------------------------

    def get_error_recovery_rates(self) -> List[Dict[str, Any]]:
        """Return per-error-code recovery stats from payment_attempts.

        Recovery = payment eventually reached CAPTURED status after a failed attempt.
        """
        sql = text("""
            SELECT
                pa.error_code,
                pa.error_category,
                COUNT(DISTINCT pa.payment_id)                               AS retried_count,
                SUM(CASE WHEN pt.status='CAPTURED' THEN 1 ELSE 0 END)      AS recovered_count,
                AVG(pa.latency_ms)                                          AS avg_latency_ms,
                MIN(pa.attempted_at)                                        AS first_seen,
                MAX(pa.attempted_at)                                        AS last_seen
            FROM payment_attempts pa
            JOIN payment_transactions pt ON pt.payment_id = pa.payment_id
            WHERE pa.status = 'FAILED'
              AND pa.error_code IS NOT NULL
              AND (:days_back = 0 OR pa.attempted_at >= DATETIME('now', '-' || :days_back || ' days'))
            GROUP BY pa.error_code, pa.error_category
            HAVING COUNT(DISTINCT pa.payment_id) >= :min_sample
            ORDER BY retried_count DESC
        """)
        rows = self._db.execute(
            sql, {"days_back": self._days_back, "min_sample": MIN_SAMPLE}
        ).mappings().all()

        results = []
        for r in rows:
            retried = int(r["retried_count"] or 0)
            recovered = int(r["recovered_count"] or 0)
            recovery_rate = (
                _dec(Decimal(recovered) / Decimal(retried) * 100)
                if retried > 0
                else Decimal("0.00")
            )
            results.append({
                "error_code": r["error_code"],
                "error_category": r["error_category"] or classify_error(r["error_code"]),
                "retried_count": retried,
                "recovered_count": recovered,
                "recovery_rate_pct": float(recovery_rate),
                "avg_latency_ms": round(float(r["avg_latency_ms"] or 0)),
                "retry_recommendation": self._build_recommendation(
                    r["error_code"], r["error_category"], float(recovery_rate), retried
                ),
            })
        return results

    def get_gateway_retry_performance(self) -> List[Dict[str, Any]]:
        """SR comparison per gateway for retried payments."""
        sql = text("""
            SELECT
                pa.gateway,
                COUNT(DISTINCT pa.payment_id)                               AS retried_payments,
                SUM(CASE WHEN pt.status='CAPTURED' THEN 1 ELSE 0 END)      AS recovered,
                AVG(pa.latency_ms)                                          AS avg_retry_latency_ms,
                SUM(CASE WHEN pa.attempt_number > 1 THEN 1 ELSE 0 END)     AS multi_attempt_count
            FROM payment_attempts pa
            JOIN payment_transactions pt ON pt.payment_id = pa.payment_id
            WHERE pa.status = 'FAILED'
              AND (:days_back = 0 OR pa.attempted_at >= DATETIME('now', '-' || :days_back || ' days'))
            GROUP BY pa.gateway
            ORDER BY retried_payments DESC
        """)
        rows = self._db.execute(
            sql, {"days_back": self._days_back}
        ).mappings().all()

        results = []
        for r in rows:
            retried = int(r["retried_payments"] or 0)
            recovered = int(r["recovered"] or 0)
            recovery_rate = (
                _dec(Decimal(recovered) / Decimal(retried) * 100)
                if retried > 0
                else Decimal("0.00")
            )
            results.append({
                "gateway": r["gateway"],
                "retried_payments": retried,
                "recovered": recovered,
                "recovery_rate_pct": float(recovery_rate),
                "avg_retry_latency_ms": round(float(r["avg_retry_latency_ms"] or 0)),
                "multi_attempt_count": int(r["multi_attempt_count"] or 0),
            })
        return results

    def get_over_retry_waste(self) -> Dict[str, Any]:
        """Identify NON_RETRYABLE errors being retried (wasted latency budget).

        These are confirmed-permanent errors where retries cannot succeed but
        add latency to the customer checkout flow.
        """
        sql = text("""
            SELECT
                pa.error_code,
                COUNT(DISTINCT pa.payment_id)                               AS payments_retried,
                SUM(pa.latency_ms)                                          AS total_wasted_latency_ms,
                AVG(pa.latency_ms)                                          AS avg_latency_ms
            FROM payment_attempts pa
            WHERE pa.error_category = 'NON_RETRYABLE'
              AND pa.attempt_number > 1
              AND (:days_back = 0 OR pa.attempted_at >= DATETIME('now', '-' || :days_back || ' days'))
            GROUP BY pa.error_code
            ORDER BY payments_retried DESC
        """)
        rows = self._db.execute(
            sql, {"days_back": self._days_back}
        ).mappings().all()
        wasted = [dict(r) for r in rows]
        total_wasted_ms = sum(int(r.get("total_wasted_latency_ms") or 0) for r in wasted)
        return {
            "wasted_retries": wasted,
            "total_wasted_latency_ms": total_wasted_ms,
            "total_wasted_latency_seconds": round(total_wasted_ms / 1000, 1),
        }

    def get_retry_depth_distribution(self) -> List[Dict[str, Any]]:
        """Show how many payments needed N retries to reach terminal state."""
        sql = text("""
            SELECT
                attempt_number,
                COUNT(DISTINCT payment_id)                                  AS payment_count
            FROM payment_attempts
            WHERE (:days_back = 0 OR attempted_at >= DATETIME('now', '-' || :days_back || ' days'))
            GROUP BY attempt_number
            ORDER BY attempt_number ASC
        """)
        rows = self._db.execute(
            sql, {"days_back": self._days_back}
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_full_analysis(self) -> Dict[str, Any]:
        """Return complete retry intelligence report as a single dict."""
        error_rates = self.get_error_recovery_rates()
        gateway_perf = self.get_gateway_retry_performance()
        over_retry = self.get_over_retry_waste()
        depth = self.get_retry_depth_distribution()

        # Derive summary insight strings (deterministic logic, not LLM)
        best_recovery = max(error_rates, key=lambda x: x["recovery_rate_pct"]) if error_rates else None
        worst_recovery = min(error_rates, key=lambda x: x["recovery_rate_pct"]) if error_rates else None

        return {
            "window_days": self._days_back if self._days_back > 0 else "ALL_TIME",
            "error_recovery_rates": error_rates,
            "gateway_retry_performance": gateway_perf,
            "over_retry_waste": over_retry,
            "retry_depth_distribution": depth,
            "insights": {
                "best_recovery_error": best_recovery["error_code"] if best_recovery else None,
                "best_recovery_rate_pct": best_recovery["recovery_rate_pct"] if best_recovery else None,
                "worst_recovery_error": worst_recovery["error_code"] if worst_recovery else None,
                "worst_recovery_rate_pct": worst_recovery["recovery_rate_pct"] if worst_recovery else None,
                "total_wasted_retry_seconds": over_retry["total_wasted_latency_seconds"],
            },
        }

    # ------------------------------------------------------------------
    # Recommendation logic (deterministic rules, not LLM)
    # ------------------------------------------------------------------

    def _build_recommendation(
        self,
        error_code: str,
        error_category: str,
        recovery_rate: float,
        sample_size: int,
    ) -> Dict[str, Any]:
        """Return a structured retry recommendation based on error classification.

        Never produces a recommendation for NON_RETRYABLE errors.
        Confidence is 'LOW' when sample_size is marginal (< 10).
        """
        category = error_category or classify_error(error_code)

        if category == "NON_RETRYABLE":
            return {
                "action": "DO_NOT_RETRY",
                "max_retries": 0,
                "rationale": (
                    f"{error_code} is a permanent failure. "
                    "Retrying wastes latency budget without improving SR."
                ),
                "confidence": "HIGH",
            }

        if category == "RETRYABLE":
            if recovery_rate >= 50:
                action = "RETRY_RECOMMENDED"
                max_ret = MAX_RETRIES_RETRYABLE
                rationale = (
                    f"{recovery_rate:.1f}% recovery rate observed. "
                    f"Up to {max_ret} retries recommended with exponential backoff."
                )
            else:
                action = "RETRY_WITH_CAUTION"
                max_ret = 1
                rationale = (
                    f"Low recovery rate ({recovery_rate:.1f}%). "
                    "Single speculative retry only; consider alternative gateway."
                )
            return {
                "action": action,
                "max_retries": max_ret,
                "rationale": rationale,
                "confidence": "HIGH" if sample_size >= 10 else "LOW",
            }

        # UNKNOWN
        return {
            "action": "RETRY_WITH_CAUTION",
            "max_retries": MAX_RETRIES_UNKNOWN,
            "rationale": (
                f"{error_code} is unclassified. "
                "One speculative retry allowed; classify error before further retries."
            ),
            "confidence": "LOW",
        }
