"""Payment Analytics Named Queries — Phase 3.

These are the ONLY SQL statements the agent's SQL tool may execute against
payment domain tables. The agent selects by name; it never writes SQL.

All monetary aggregations use SUM/ROUND on Numeric columns, which SQLite and
PostgreSQL handle with decimal precision. Python-side Decimal arithmetic is
used for any post-query ratio calculations.

Time window convention: queries accept a :days_back bind parameter (integer)
defaulting to 7 so the dashboard always shows a rolling 7-day window unless
overridden. A zero value means 'all time'.
"""

PAYMENT_QUERIES = {
    # P1 — Executive overview KPIs.
    # Success rate numerator: CAPTURED. Denominator: all terminal states
    # (CAPTURED + FAILED). AUTHORIZED is excluded — capture hasn't completed.
    "payment_kpi_summary": """
SELECT
    COUNT(*)                                                       AS total_attempts,
    SUM(CASE WHEN status = 'CAPTURED' THEN 1 ELSE 0 END)          AS successful,
    SUM(CASE WHEN status = 'FAILED'   THEN 1 ELSE 0 END)          AS failed,
    SUM(CASE WHEN status = 'AUTHORIZED' THEN 1 ELSE 0 END)        AS pending_capture,
    ROUND(
        100.0 * SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN status IN ('CAPTURED','FAILED') THEN 1 ELSE 0 END), 0),
        2
    )                                                              AS success_rate_pct,
    ROUND(SUM(CASE WHEN status='CAPTURED' THEN CAST(amount AS REAL) ELSE 0 END), 2)
                                                                   AS gmv_inr,
    ROUND(SUM(CASE WHEN status='CAPTURED' THEN CAST(fee AS REAL) ELSE 0 END), 2)
                                                                   AS total_fee_inr,
    ROUND(AVG(CASE WHEN status='CAPTURED' THEN CAST(amount AS REAL) ELSE NULL END), 2)
                                                                   AS avg_transaction_value_inr
FROM payment_transactions
WHERE (:days_back = 0 OR created_at >= DATETIME('now', '-' || :days_back || ' days'))
""",

    # P2 — Success rate sliced by payment method.
    # Minimum sample size: 5 attempts. Methods with fewer attempts return NULL
    # for SR so the UI can show '—' rather than a misleading 0% or 100%.
    "payment_sr_by_method": """
SELECT
    method,
    COUNT(*)                                                       AS attempts,
    SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)            AS captured,
    SUM(CASE WHEN status='FAILED'   THEN 1 ELSE 0 END)            AS failed,
    CASE
        WHEN SUM(CASE WHEN status IN ('CAPTURED','FAILED') THEN 1 ELSE 0 END) >= 5
        THEN ROUND(
            100.0 * SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN status IN ('CAPTURED','FAILED') THEN 1 ELSE 0 END), 0), 2)
        ELSE NULL
    END                                                            AS success_rate_pct,
    ROUND(SUM(CASE WHEN status='CAPTURED' THEN CAST(amount AS REAL) ELSE 0 END), 2)
                                                                   AS gmv_inr
FROM payment_transactions
WHERE (:days_back = 0 OR created_at >= DATETIME('now', '-' || :days_back || ' days'))
GROUP BY method
ORDER BY gmv_inr DESC
""",

    # P3 — Bank-wise success rate (HDFC, ICICI, AXIS, SBI, KOTAK).
    # Key differentiator: shows which banks are degrading so on-call can
    # reroute traffic before an incident escalates.
    "payment_sr_by_bank": """
SELECT
    bank,
    COUNT(*)                                                       AS attempts,
    SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)            AS captured,
    SUM(CASE WHEN status='FAILED'   THEN 1 ELSE 0 END)            AS failed,
    CASE
        WHEN SUM(CASE WHEN status IN ('CAPTURED','FAILED') THEN 1 ELSE 0 END) >= 5
        THEN ROUND(
            100.0 * SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN status IN ('CAPTURED','FAILED') THEN 1 ELSE 0 END), 0), 2)
        ELSE NULL
    END                                                            AS success_rate_pct,
    ROUND(AVG(CASE WHEN status='CAPTURED' THEN CAST(amount AS REAL) ELSE NULL END), 2)
                                                                   AS avg_txn_value_inr
FROM payment_transactions
WHERE bank IS NOT NULL
  AND (:days_back = 0 OR created_at >= DATETIME('now', '-' || :days_back || ' days'))
GROUP BY bank
ORDER BY attempts DESC
""",

    # P4 — Merchant-level GMV, SR, and refund exposure.
    # Allows merchant health monitoring and SLA reporting.
    "payment_gmv_by_merchant": """
SELECT
    pt.merchant_id,
    m.name                                                         AS merchant_name,
    m.business_category,
    COUNT(*)                                                       AS attempts,
    ROUND(SUM(CASE WHEN pt.status='CAPTURED' THEN CAST(pt.amount AS REAL) ELSE 0 END), 2)
                                                                   AS gmv_inr,
    CASE
        WHEN SUM(CASE WHEN pt.status IN ('CAPTURED','FAILED') THEN 1 ELSE 0 END) >= 5
        THEN ROUND(
            100.0 * SUM(CASE WHEN pt.status='CAPTURED' THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN pt.status IN ('CAPTURED','FAILED') THEN 1 ELSE 0 END), 0), 2)
        ELSE NULL
    END                                                            AS success_rate_pct,
    ROUND(COALESCE((
        SELECT SUM(CAST(r.amount AS REAL))
        FROM refunds r
        WHERE r.merchant_id = pt.merchant_id
          AND (:days_back = 0 OR r.created_at >= DATETIME('now', '-' || :days_back || ' days'))
    ), 0), 2)                                                      AS refund_amount_inr
FROM payment_transactions pt
LEFT JOIN merchants m ON m.merchant_id = pt.merchant_id
WHERE (:days_back = 0 OR pt.created_at >= DATETIME('now', '-' || :days_back || ' days'))
GROUP BY pt.merchant_id, m.name, m.business_category
ORDER BY gmv_inr DESC
""",

    # P5 — Hourly transaction volume trend.
    # Drives the live feed sparkline and anomaly baseline comparison.
    # Uses strftime for SQLite compatibility; PostgreSQL uses date_trunc.
    "payment_hourly_trend": """
SELECT
    STRFTIME('%Y-%m-%dT%H:00:00', created_at)                     AS hour,
    COUNT(*)                                                       AS attempts,
    SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)            AS captured,
    SUM(CASE WHEN status='FAILED'   THEN 1 ELSE 0 END)            AS failed,
    ROUND(SUM(CASE WHEN status='CAPTURED' THEN CAST(amount AS REAL) ELSE 0 END), 2)
                                                                   AS gmv_inr
FROM payment_transactions
WHERE (:days_back = 0 OR created_at >= DATETIME('now', '-' || :days_back || ' days'))
GROUP BY STRFTIME('%Y-%m-%dT%H:00:00', created_at)
ORDER BY hour ASC
""",

    # P6 — Refund rate analysis.
    # Numerator: PROCESSED refunds count. Denominator: CAPTURED payment count.
    # A refund rate > 5% triggers an operational alert.
    "payment_refund_rate": """
SELECT
    pt.merchant_id,
    m.name                                                         AS merchant_name,
    SUM(CASE WHEN pt.status='CAPTURED' THEN 1 ELSE 0 END)         AS captured_count,
    COUNT(r.refund_id)                                             AS refund_count,
    CASE
        WHEN SUM(CASE WHEN pt.status='CAPTURED' THEN 1 ELSE 0 END) > 0
        THEN ROUND(
            100.0 * COUNT(r.refund_id)
            / SUM(CASE WHEN pt.status='CAPTURED' THEN 1 ELSE 0 END), 2)
        ELSE NULL
    END                                                            AS refund_rate_pct,
    ROUND(COALESCE(SUM(CAST(r.amount AS REAL)), 0), 2)            AS total_refund_inr
FROM payment_transactions pt
LEFT JOIN merchants m ON m.merchant_id = pt.merchant_id
LEFT JOIN refunds r
       ON r.payment_id = pt.payment_id
      AND r.status = 'PROCESSED'
      AND (:days_back = 0 OR r.created_at >= DATETIME('now', '-' || :days_back || ' days'))
WHERE (:days_back = 0 OR pt.created_at >= DATETIME('now', '-' || :days_back || ' days'))
GROUP BY pt.merchant_id, m.name
HAVING SUM(CASE WHEN pt.status='CAPTURED' THEN 1 ELSE 0 END) >= 10
ORDER BY refund_rate_pct DESC
""",

    # P7 — Settlement completion rate.
    # Identifies merchants with delayed or blocked settlements.
    "payment_settlement_status": """
SELECT
    s.merchant_id,
    m.name                                                         AS merchant_name,
    m.settlement_cycle,
    COUNT(*)                                                       AS settlement_count,
    SUM(CASE WHEN s.status='SETTLED'  THEN 1 ELSE 0 END)          AS settled,
    SUM(CASE WHEN s.status='PENDING'  THEN 1 ELSE 0 END)          AS pending,
    SUM(CASE WHEN s.status='BLOCKED'  THEN 1 ELSE 0 END)          AS blocked,
    ROUND(SUM(CAST(s.net_payout AS REAL)), 2)                     AS total_net_payout_inr,
    ROUND(SUM(CAST(s.fee_deducted AS REAL)), 2)                   AS total_fees_deducted_inr
FROM settlements s
LEFT JOIN merchants m ON m.merchant_id = s.merchant_id
WHERE (:days_back = 0 OR s.created_at >= DATETIME('now', '-' || :days_back || ' days'))
GROUP BY s.merchant_id, m.name, m.settlement_cycle
ORDER BY pending DESC, blocked DESC
""",

    # P8 — Top error codes by volume and financial impact.
    # Drives root-cause triage: GATEWAY_DOWN errors → infra team;
    # INSUFFICIENT_FUNDS → not actionable.
    "payment_top_errors": """
SELECT
    error_code,
    COUNT(*)                                                       AS failure_count,
    ROUND(SUM(CAST(amount AS REAL)), 2)                           AS blocked_gmv_inr,
    COUNT(DISTINCT merchant_id)                                   AS affected_merchants,
    COUNT(DISTINCT bank)                                          AS affected_banks,
    ROUND(AVG(CAST(amount AS REAL)), 2)                           AS avg_blocked_amount_inr
FROM payment_transactions
WHERE status = 'FAILED'
  AND error_code IS NOT NULL
  AND (:days_back = 0 OR created_at >= DATETIME('now', '-' || :days_back || ' days'))
GROUP BY error_code
ORDER BY failure_count DESC
LIMIT 15
""",

    # P9 — Open reconciliation discrepancies with financial exposure.
    "payment_open_discrepancies": """
SELECT
    rd.issue_type,
    rd.severity,
    COUNT(*)                                                       AS discrepancy_count,
    ROUND(SUM(CAST(rd.variance AS REAL)), 2)                      AS total_variance_inr,
    COUNT(DISTINCT rd.merchant_id)                                AS affected_merchants,
    MIN(rd.detected_at)                                           AS oldest_open,
    MAX(rd.detected_at)                                           AS newest_open
FROM reconciliation_discrepancies rd
WHERE rd.status = 'OPEN'
GROUP BY rd.issue_type, rd.severity
ORDER BY
    CASE rd.severity WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1
                     WHEN 'MEDIUM' THEN 2 ELSE 3 END,
    total_variance_inr DESC
""",

    # P10 — Gateway-wise SR comparison (current 1h vs prior 24h baseline).
    # When current_sr drops > 10pp vs baseline, the incident engine creates
    # a GATEWAY_DEGRADATION incident. This query provides the raw numbers.
    "payment_gateway_sr_comparison": """
WITH current_window AS (
    SELECT gateway,
           COUNT(*)                                               AS attempts,
           SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)    AS captured,
           ROUND(100.0 * SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)
                 / NULLIF(COUNT(*), 0), 2)                       AS sr_pct
    FROM payment_transactions
    WHERE created_at >= DATETIME('now', '-1 hours')
    GROUP BY gateway
),
baseline_window AS (
    SELECT gateway,
           COUNT(*)                                               AS attempts,
           SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)    AS captured,
           ROUND(100.0 * SUM(CASE WHEN status='CAPTURED' THEN 1 ELSE 0 END)
                 / NULLIF(COUNT(*), 0), 2)                       AS sr_pct
    FROM payment_transactions
    WHERE created_at >= DATETIME('now', '-25 hours')
      AND created_at  < DATETIME('now', '-1 hours')
    GROUP BY gateway
)
SELECT
    COALESCE(c.gateway, b.gateway)                                AS gateway,
    b.sr_pct                                                      AS baseline_sr_pct,
    c.sr_pct                                                      AS current_sr_pct,
    ROUND(COALESCE(c.sr_pct, 0) - COALESCE(b.sr_pct, 0), 2)     AS sr_delta_pp,
    c.attempts                                                    AS current_attempts,
    b.attempts                                                    AS baseline_attempts
FROM current_window c
FULL OUTER JOIN baseline_window b ON b.gateway = c.gateway
ORDER BY sr_delta_pp ASC
""",

    # P11 — Retry analysis: recovery rate by error code.
    # Counts payments that eventually CAPTURED after initially FAILING.
    # Multi-attempt payments have > 1 row in payment_attempts.
    "payment_retry_recovery_rate": """
SELECT
    pa.error_code,
    pa.error_category,
    COUNT(DISTINCT pa.payment_id)                                 AS payments_with_error,
    SUM(CASE WHEN pt.status='CAPTURED' THEN 1 ELSE 0 END)        AS eventually_captured,
    ROUND(
        100.0 * SUM(CASE WHEN pt.status='CAPTURED' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(DISTINCT pa.payment_id), 0), 2
    )                                                             AS recovery_rate_pct,
    ROUND(AVG(pa.latency_ms), 0)                                  AS avg_attempt_latency_ms
FROM payment_attempts pa
JOIN payment_transactions pt ON pt.payment_id = pa.payment_id
WHERE pa.status = 'FAILED'
  AND pa.error_code IS NOT NULL
  AND (:days_back = 0 OR pa.attempted_at >= DATETIME('now', '-' || :days_back || ' days'))
GROUP BY pa.error_code, pa.error_category
HAVING COUNT(DISTINCT pa.payment_id) >= 3
ORDER BY payments_with_error DESC
""",
}


def get_payment_query(name: str) -> str:
    """Return a named payment analytics query SQL string.

    Raises:
        KeyError: if the name is not in the allowlist.
    """
    if name not in PAYMENT_QUERIES:
        raise KeyError(
            f"Unknown payment query '{name}'. "
            f"Allowed: {sorted(PAYMENT_QUERIES)}"
        )
    return PAYMENT_QUERIES[name]
