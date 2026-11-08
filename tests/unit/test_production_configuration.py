from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import validate_runtime_configuration
from app.core.security import assert_demo_users_absent
from app.db.base import Base
from app.models import User


def production_settings(**overrides):
    values = {
        "DEMO_MODE": False,
        "JWT_SECRET": "production-test-secret-with-at-least-32-bytes",
        "ALLOWED_ORIGINS": ("https://paybridge.example",),
        "CHECKOUT_MERCHANT_ID": "merchant-prod-1",
        "DATABASE_URL": "postgresql+psycopg2://user:pass@localhost/paybridge",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def isolated_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_demo_mode_is_explicitly_allowed_for_local_demo():
    validate_runtime_configuration(production_settings(DEMO_MODE=True, JWT_SECRET=""))


@pytest.mark.parametrize(
    "overrides",
    [
        {"JWT_SECRET": ""},
        {"JWT_SECRET": "dev-only-change-me"},
        {"JWT_SECRET": "too-short"},
        {"ALLOWED_ORIGINS": ()},
        {"ALLOWED_ORIGINS": ("*",)},
        {"CHECKOUT_MERCHANT_ID": ""},
        {"DATABASE_URL": "sqlite:///local.db"},
    ],
)
def test_production_rejects_unsafe_configuration(overrides):
    with pytest.raises(RuntimeError):
        validate_runtime_configuration(production_settings(**overrides))


def test_production_startup_rejects_builtin_demo_users(isolated_db):
    isolated_db.add(
        User(
            user_id="SECURITY-TEST-ADMIN",
            username="admin",
            password_hash="not-a-real-password-hash",
            role="ADMIN",
            is_active=True,
        )
    )
    isolated_db.commit()

    with pytest.raises(RuntimeError, match="built-in demo accounts"):
        assert_demo_users_absent(isolated_db)


def test_production_startup_allows_unrelated_users(isolated_db):
    isolated_db.add(
        User(
            user_id="SECURITY-TEST-USER",
            username="production-operator-test",
            password_hash="not-a-real-password-hash",
            role="ADMIN",
            is_active=True,
        )
    )
    isolated_db.commit()
    assert_demo_users_absent(isolated_db) is None
