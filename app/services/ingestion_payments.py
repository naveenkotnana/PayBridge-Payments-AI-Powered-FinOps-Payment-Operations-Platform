"""Payment Event Ingestion Service.

Responsibilities:
- Accept raw payment event dicts and write them to the payment_events table.
- Enforce idempotency: duplicate event delivery is detected via the
  idempotency_key column (payment_id + '::' + event_type). Duplicates are
  silently skipped — never raise an error for re-delivery.
- Handle out-of-order events: events are stored with their occurred_at
  timestamp; the analytics layer queries by occurred_at, not ingested_at,
  so late arrivals do not corrupt time-series windows.
- Emit PaymentAttempt rows for PAYMENT_FAILED / PAYMENT_AUTHORIZED events so
  the retry intelligence engine has per-attempt detail.

Error classification for retry intelligence:
- RETRYABLE: transient gateway / network failures worth retrying.
- NON_RETRYABLE: permanent failures (fraud, stolen card, auth declined).
- UNKNOWN: unclassified codes — treated conservatively as NON_RETRYABLE.
"""
import datetime as dt
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.payments import PaymentAttempt, PaymentEvent, PaymentTransaction

log = logging.getLogger("opspilot.ingestion_payments")

# Error code classification used by retry engine.
# RETRYABLE = worth attempting again (transient failures).
# NON_RETRYABLE = permanent rejection (no point retrying without change).
_ERROR_CATEGORY: Dict[str, str] = {
    "BAD_REQUEST_GATEWAY_DOWN": "RETRYABLE",
    "BANK_DEBITED_PAYMENT_PENDING": "RETRYABLE",
    "EXPIRED_TRANSACTION": "RETRYABLE",
    "GATEWAY_TIMEOUT": "RETRYABLE",
    "NETWORK_ERROR": "RETRYABLE",
    "INSUFFICIENT_FUNDS": "NON_RETRYABLE",
    "CARD_SECURITY_VIOLATION": "NON_RETRYABLE",
    "PAYMENT_DECLINED": "NON_RETRYABLE",
    "FRAUD_BLOCK": "NON_RETRYABLE",
    "INVALID_ACCOUNT": "NON_RETRYABLE",
}


def classify_error(error_code: Optional[str]) -> str:
    """Return RETRYABLE, NON_RETRYABLE, or UNKNOWN for a gateway error code."""
    if not error_code:
        return "UNKNOWN"
    return _ERROR_CATEGORY.get(error_code, "UNKNOWN")


def ingest_event(
    db: Session,
    payment_id: str,
    event_type: str,
    occurred_at: dt.datetime,
    payload: Optional[Dict[str, Any]] = None,
    event_source: str = "SIMULATOR",
) -> Dict[str, Any]:
    """Ingest a single payment lifecycle event with idempotency guarantee.

    Returns a dict with 'status' = 'INSERTED' | 'DUPLICATE_SKIPPED' and
    the 'event_id' (existing or newly created).

    Raises:
        ValueError: if payment_id does not exist in payment_transactions.
    """
    idempotency_key = f"{payment_id}::{event_type}"
    existing = (
        db.query(PaymentEvent)
        .filter(PaymentEvent.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        log.debug("Duplicate event skipped: %s", idempotency_key)
        return {"status": "DUPLICATE_SKIPPED", "event_id": existing.event_id}

    # Validate payment exists before inserting event
    txn = (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.payment_id == payment_id)
        .first()
    )
    if txn is None:
        raise ValueError(f"Payment '{payment_id}' not found — cannot ingest event.")

    event_id = f"evt_{uuid.uuid4().hex[:14]}"
    event = PaymentEvent(
        event_id=event_id,
        payment_id=payment_id,
        event_type=event_type,
        event_payload=json.dumps(payload or {}),
        event_source=event_source,
        idempotency_key=idempotency_key,
        occurred_at=occurred_at,
    )
    try:
        db.add(event)
        db.flush()
    except IntegrityError:
        # Race-condition duplicate — another thread inserted concurrently
        db.rollback()
        log.debug("Concurrent duplicate for %s — skipping", idempotency_key)
        existing = (
            db.query(PaymentEvent)
            .filter(PaymentEvent.idempotency_key == idempotency_key)
            .first()
        )
        return {"status": "DUPLICATE_SKIPPED", "event_id": existing.event_id if existing else ""}

    # Emit a PaymentAttempt row for failure / authorization events
    if event_type in ("PAYMENT_FAILED", "PAYMENT_AUTHORIZED", "PAYMENT_CAPTURED"):
        error_code = (payload or {}).get("error_code")
        _record_attempt(
            db=db,
            payment_id=payment_id,
            gateway=txn.gateway,
            bank=txn.bank,
            status="FAILED" if event_type == "PAYMENT_FAILED" else "AUTHORIZED",
            error_code=error_code,
            latency_ms=(payload or {}).get("latency_ms"),
            occurred_at=occurred_at,
        )

    db.commit()
    return {"status": "INSERTED", "event_id": event_id}


def _record_attempt(
    db: Session,
    payment_id: str,
    gateway: str,
    bank: Optional[str],
    status: str,
    error_code: Optional[str],
    latency_ms: Optional[int],
    occurred_at: dt.datetime,
) -> None:
    """Write a PaymentAttempt row; attempt_number is auto-incremented."""
    current_max = (
        db.query(PaymentAttempt)
        .filter(PaymentAttempt.payment_id == payment_id)
        .count()
    )
    db.add(
        PaymentAttempt(
            attempt_id=f"att_{uuid.uuid4().hex[:14]}",
            payment_id=payment_id,
            attempt_number=current_max + 1,
            gateway=gateway,
            bank=bank,
            status=status,
            error_code=error_code,
            error_category=classify_error(error_code),
            latency_ms=latency_ms,
            attempted_at=occurred_at,
        )
    )


def ingest_batch(
    db: Session,
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Ingest a list of event dicts. Each dict must contain:
        payment_id, event_type, occurred_at (ISO-8601 str or datetime),
        and optionally: payload (dict), event_source (str).

    Returns aggregate counters for observability.
    """
    inserted = 0
    skipped = 0
    errors = []
    for raw in events:
        occurred = raw.get("occurred_at")
        if isinstance(occurred, str):
            occurred = dt.datetime.fromisoformat(occurred)
        try:
            result = ingest_event(
                db=db,
                payment_id=raw["payment_id"],
                event_type=raw["event_type"],
                occurred_at=occurred,
                payload=raw.get("payload"),
                event_source=raw.get("event_source", "BATCH_IMPORT"),
            )
            if result["status"] == "INSERTED":
                inserted += 1
            else:
                skipped += 1
        except (ValueError, KeyError) as exc:
            errors.append({"payment_id": raw.get("payment_id"), "error": str(exc)})
            log.warning("Event ingestion failed for %s: %s", raw.get("payment_id"), exc)

    return {
        "total": len(events),
        "inserted": inserted,
        "skipped_duplicates": skipped,
        "errors": len(errors),
        "error_detail": errors[:10],  # cap at 10 to avoid huge payloads
    }


def seed_events_for_existing_payments(db: Session) -> Dict[str, Any]:
    """Backfill lifecycle events for all existing payment_transactions rows.

    Safe to re-run: idempotency_key constraint skips already-inserted events.
    Used during database initialisation so the event log is populated for
    analytics and the retry engine without requiring a live event stream.
    """
    payments = db.query(PaymentTransaction).all()
    total_inserted = 0
    total_skipped = 0

    for txn in payments:
        # PAYMENT_CREATED: always exists
        events_to_ingest = [
            {
                "payment_id": txn.payment_id,
                "event_type": "PAYMENT_CREATED",
                "occurred_at": txn.created_at - dt.timedelta(seconds=30),
                "payload": {"amount": float(txn.amount), "method": txn.method},
                "event_source": "SIMULATOR",
            }
        ]
        # Terminal event based on payment status
        if txn.status == "CAPTURED":
            events_to_ingest.append({
                "payment_id": txn.payment_id,
                "event_type": "PAYMENT_CAPTURED",
                "occurred_at": txn.captured_at or txn.created_at,
                "payload": {
                    "amount": float(txn.amount),
                    "gateway": txn.gateway,
                    "latency_ms": 450,
                },
                "event_source": "SIMULATOR",
            })
        elif txn.status == "FAILED":
            events_to_ingest.append({
                "payment_id": txn.payment_id,
                "event_type": "PAYMENT_FAILED",
                "occurred_at": txn.created_at + dt.timedelta(seconds=15),
                "payload": {
                    "error_code": txn.error_code,
                    "gateway": txn.gateway,
                    "latency_ms": 1200,
                },
                "event_source": "SIMULATOR",
            })
        elif txn.status == "AUTHORIZED":
            events_to_ingest.append({
                "payment_id": txn.payment_id,
                "event_type": "PAYMENT_AUTHORIZED",
                "occurred_at": txn.created_at + dt.timedelta(seconds=10),
                "payload": {"gateway": txn.gateway},
                "event_source": "SIMULATOR",
            })

        result = ingest_batch(db, events_to_ingest)
        total_inserted += result["inserted"]
        total_skipped += result["skipped_duplicates"]

    return {
        "payments_processed": len(payments),
        "events_inserted": total_inserted,
        "events_skipped": total_skipped,
    }
