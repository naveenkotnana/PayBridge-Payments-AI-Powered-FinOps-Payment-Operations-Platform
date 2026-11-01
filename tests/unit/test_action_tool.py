"""Unit tests for action tool execution and idempotency verification."""
from app.agent.tools.action_tool import (
    ACTION_REGISTRY,
    idempotency_key,
    create_incident,
    create_ticket,
    send_notification,
)
from app.models import ActionRecord


def test_action_registry_contains_standard_actions():
    assert "create_incident" in ACTION_REGISTRY
    assert "create_ticket" in ACTION_REGISTRY
    assert "send_notification" in ACTION_REGISTRY


def test_idempotency_key_is_deterministic():
    key1 = idempotency_key("WF-100", "create_incident", {"title": "leak detected"})
    key2 = idempotency_key("WF-100", "create_incident", {"title": "leak detected"})
    assert key1 == key2

    key3 = idempotency_key("WF-100", "create_incident", {"title": "different title"})
    assert key1 != key3


def test_create_incident_and_idempotency(db):
    wid = "WF-UNIT-TEST-ACTION"
    db.query(ActionRecord).filter(ActionRecord.workflow_id == wid).delete()
    db.commit()

    # First execution should succeed with status EXECUTED
    res1 = create_incident(db, wid, "Test Incident", "HIGH", "Unit test details")
    assert res1["ok"] is True
    assert res1["status"] == "EXECUTED"

    # Second execution with identical payload should be DUPLICATE_SKIPPED
    res2 = create_incident(db, wid, "Test Incident", "HIGH", "Unit test details")
    assert res2["ok"] is True
    assert res2["status"] == "DUPLICATE_SKIPPED"
    assert res2["action_id"] == res1["action_id"]

    # Clean up test artifact
    db.query(ActionRecord).filter(ActionRecord.workflow_id == wid).delete()
    db.commit()


def test_create_ticket_execution(db):
    wid = "WF-UNIT-TEST-TICKET"
    db.query(ActionRecord).filter(ActionRecord.workflow_id == wid).delete()
    db.commit()

    res = create_ticket(db, wid, "Meter Replacement", queue="HARDWARE", detail="Hardware offline")
    assert res["ok"] is True
    assert res["status"] == "EXECUTED"

    db.query(ActionRecord).filter(ActionRecord.workflow_id == wid).delete()
    db.commit()


def test_send_notification_execution(db):
    wid = "WF-UNIT-TEST-NOTIF"
    db.query(ActionRecord).filter(ActionRecord.workflow_id == wid).delete()
    db.commit()

    res = send_notification(db, wid, "SLACK", "Automated alert for cluster")
    assert res["ok"] is True
    assert res["status"] == "EXECUTED"

    db.query(ActionRecord).filter(ActionRecord.workflow_id == wid).delete()
    db.commit()

