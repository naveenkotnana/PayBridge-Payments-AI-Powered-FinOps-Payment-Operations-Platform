"""Database-backed login throttling shared by application workers."""
import datetime as dt
import hashlib
import hmac

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ops import LoginRateLimit

WINDOW = dt.timedelta(minutes=15)
BLOCK = dt.timedelta(minutes=15)
MAX_FAILURES = 8


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def identity_digest(client_host: str, username: str) -> str:
    material = f"{client_host.strip().lower()}\0{username.strip().lower()}".encode()
    return hmac.new(settings.JWT_SECRET.encode(), material, hashlib.sha256).hexdigest()


def check_login_allowed(db: Session, digest: str) -> None:
    now = _now()
    row = db.query(LoginRateLimit).filter_by(identity_digest=digest).with_for_update().first()
    if row is None:
        return
    if row.blocked_until and row.blocked_until > now:
        retry_after = max(1, int((row.blocked_until - now).total_seconds()))
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many failed sign-in attempts. Try again later.",
                            headers={"Retry-After": str(retry_after)})
    if row.window_started_at + WINDOW <= now:
        row.window_started_at = now
        row.attempts = 0
        row.blocked_until = None
        db.commit()


def record_login_failure(db: Session, digest: str) -> None:
    now = _now()
    row = db.query(LoginRateLimit).filter_by(identity_digest=digest).with_for_update().first()
    if row is None:
        row = LoginRateLimit(identity_digest=digest, window_started_at=now, attempts=1)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            # A parallel first failure inserted the unique digest first.
            db.rollback()
            record_login_failure(db, digest)
        return
    if row.window_started_at + WINDOW <= now:
        row.window_started_at = now
        row.attempts = 0
    row.attempts += 1
    if row.attempts >= MAX_FAILURES:
        row.blocked_until = now + BLOCK
    db.commit()


def clear_login_failures(db: Session, digest: str) -> None:
    db.query(LoginRateLimit).filter_by(identity_digest=digest).delete(synchronize_session=False)
    db.commit()
