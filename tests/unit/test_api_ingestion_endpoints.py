"""Unit tests for payment ingestion and webhook REST API endpoints."""
import io
import uuid
from fastapi.testclient import TestClient

from app.api.main import app
from app.core.security import create_access_token, seed_demo_users
from app.db.base import Base, SessionLocal, engine
from app.models import User
from app.models.payments import PaymentIngestionRun


def setup_module():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_users(db)
    finally:
        db.close()


def get_auth_header(user_id="USR-003"):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.user_id == user_id).first()
        token = create_access_token(u)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


def test_get_ingestion_runs_endpoint():
    db = SessionLocal()
    run_id = f"run_test_{uuid.uuid4().hex[:8]}"
    try:
        db.add(PaymentIngestionRun(
            run_id=run_id,
            source_type="CSV_FILE",
            source_identifier="test_txns.csv",
            records_received=10,
            records_accepted=8,
            records_rejected=2,
            records_duplicated=0,
            status="SUCCESS"
        ))
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    response = client.get("/api/v1/ingestion/runs", headers=get_auth_header("USR-003"))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(r["run_id"] == run_id for r in data)


def test_get_payment_events_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/events", headers=get_auth_header("USR-003"))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_post_csv_ingestion_endpoint():
    client = TestClient(app)
    unique_tx_id = f"pay_api_{uuid.uuid4().hex[:8]}"
    csv_content = f"transaction_id,amount,status,method,created_at\n{unique_tx_id},1500.0,CAPTURED,UPI,2026-11-01 10:00:00\n".encode("utf-8")
    file = io.BytesIO(csv_content)

    response = client.post(
        "/api/v1/ingestion/csv",
        files={"file": ("api_test.csv", file, "text/csv")},
        headers=get_auth_header("USR-003")
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["records_received"] == 1
    assert res_data["records_accepted"] == 1
    assert res_data["records_rejected"] == 0
