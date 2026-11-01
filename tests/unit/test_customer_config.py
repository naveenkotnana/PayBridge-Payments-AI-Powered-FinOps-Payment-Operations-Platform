"""Unit tests for customer configuration management."""
import pytest
from app.core import customer_config as CC


def test_load_all_returns_customers():
    cfg = CC.load_all()
    assert isinstance(cfg, dict)
    assert "customer_a" in cfg
    assert "customer_b" in cfg
    assert "customer_c" in cfg


def test_get_customer_valid():
    cust = CC.get_customer("customer_a")
    assert isinstance(cust, dict)
    assert cust["customer_id"] == "CUST-A"
    assert "allowed_tools" in cust


def test_get_customer_invalid_raises_key_error():
    with pytest.raises(KeyError) as exc_info:
        CC.get_customer("non_existent_customer_xyz")
    assert "Unknown customer" in str(exc_info.value)


def test_tool_allowed():
    assert CC.tool_allowed("customer_a", "analytics_tool") is True
    assert CC.tool_allowed("customer_a", "sql_tool") is True
    assert CC.tool_allowed("customer_a", "unregistered_malicious_tool") is False


def test_requires_approval():
    assert CC.requires_approval("customer_a", "create_incident") is True
    assert CC.requires_approval("customer_a", "safe_read_query") is False
