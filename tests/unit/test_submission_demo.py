"""Verify the submitted payment evidence-to-approval flow in an isolated database."""
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.db.base import Base
from app.models import ActionRecord, Approval, AuditLog, User
from app.models.payments import Merchant, PaymentOrder, PaymentTransaction
from app.services.demo import payment_summary, refresh_demo_alert
from app.agent.workflow import run_investigation
from app.api.main import approve, reject
from app.schemas.api import ApprovalDecision
from app.rag.ollama_client import LLMResult


@pytest.fixture
def payment_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        db.add(Merchant(merchant_id="merchant_test", name="Test merchant", email="test@example.test"))
        for index, status in enumerate(["CAPTURED", "FAILED", "PENDING"]):
            db.add(PaymentOrder(order_id=f"order_{index}", merchant_id="merchant_test", amount=100, currency="INR"))
            db.add(PaymentTransaction(payment_id=f"payment_{index}", order_id=f"order_{index}",
                                      merchant_id="merchant_test", amount=100, net_amount=100,
                                      status=status, method="UPI", bank="SBI", gateway="TEST"))
        db.commit()
        yield db
    engine.dispose()


def test_metrics_have_no_invented_revenue(payment_db):
    result = payment_summary(payment_db)
    assert result["gmv"] == Decimal("100.00")
    assert result["failed_volume"] == Decimal("100.00")
    assert result["success_rate"] == 50
    assert result["pending"] == 1
    assert payment_summary(payment_db, "missing")["total"] == 0


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_offline_investigation_requires_stored_human_decision(payment_db, monkeypatch, decision):
    monkeypatch.setattr("app.rag.ollama_client.generate_json", lambda *a, **k: (LLMResult(ok=False, error="OFFLINE_TEST"), None))
    alert = refresh_demo_alert(payment_db)
    state = run_investigation(payment_db, alert.alert_id, "demo_operator", "ADMIN")
    assert state["recommendation"]["source"] == "DETERMINISTIC_FALLBACK"
    assert state["approval_status"] == "PENDING"
    assert payment_db.query(ActionRecord).count() == 0
    operator = User(user_id="demo_operator", role="ADMIN")
    handler = approve if decision == "approve" else reject
    result = handler(state["workflow_id"], ApprovalDecision(reason="Reviewed"), payment_db, operator)
    assert result["ok"]
    expected = "APPROVED" if decision == "approve" else "REJECTED"
    assert payment_db.query(Approval).one().decision == expected
    assert payment_db.query(ActionRecord).count() == (1 if decision == "approve" else 0)
    assert payment_db.query(AuditLog).filter_by(agent_node="human_decision", result_status=expected).count() == 1
    handler(state["workflow_id"], ApprovalDecision(reason="Retry"), payment_db, operator)
    assert payment_db.query(ActionRecord).count() == (1 if decision == "approve" else 0)
