import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.login_rate_limit import (
    MAX_FAILURES, check_login_allowed, clear_login_failures,
    identity_digest, record_login_failure,
)
from app.models.ops import LoginRateLimit
from app.db.base import Base


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_login_failures_are_shared_and_block_after_threshold(mem_db):
    key = identity_digest("192.0.2.10", "ExampleUser")
    assert key == identity_digest("192.0.2.10", "exampleuser")
    for _ in range(MAX_FAILURES):
        record_login_failure(mem_db, key)
    assert mem_db.query(LoginRateLimit).filter_by(identity_digest=key).one().attempts == MAX_FAILURES
    with pytest.raises(HTTPException) as exc:
        check_login_allowed(mem_db, key)
    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"]


def test_successful_login_clears_failure_counter(mem_db):
    key = identity_digest("192.0.2.11", "naveen")
    record_login_failure(mem_db, key)
    clear_login_failures(mem_db, key)
    check_login_allowed(mem_db, key)
    assert mem_db.query(LoginRateLimit).filter_by(identity_digest=key).count() == 0


def test_login_rate_limit_key_does_not_store_raw_credentials(mem_db):
    key = identity_digest("192.0.2.12", "sensitive-user")
    record_login_failure(mem_db, key)
    row = mem_db.query(LoginRateLimit).one()
    assert row.identity_digest == key
    assert "sensitive-user" not in row.identity_digest
    assert "192.0.2.12" not in row.identity_digest
