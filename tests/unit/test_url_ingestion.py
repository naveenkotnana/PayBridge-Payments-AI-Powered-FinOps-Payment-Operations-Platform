"""Unit tests for Secure URL Ingestion Service and SSRF Protection."""
import pytest

from app.services.url_ingestion import (
    SSRFSecurityError,
    is_ip_private_or_restricted,
    validate_url_safety,
)


def test_ip_private_or_restricted_detection():
    # Loopback
    assert is_ip_private_or_restricted("127.0.0.1") is True
    assert is_ip_private_or_restricted("::1") is True

    # RFC 1918 Private Ranges
    assert is_ip_private_or_restricted("10.0.0.1") is True
    assert is_ip_private_or_restricted("172.16.0.1") is True
    assert is_ip_private_or_restricted("192.168.1.1") is True

    # AWS/Cloud metadata
    assert is_ip_private_or_restricted("169.254.169.254") is True

    # Public IP
    assert is_ip_private_or_restricted("8.8.8.8") is False
    assert is_ip_private_or_restricted("142.250.190.46") is False


def test_validate_url_safety_scheme():
    # Disallowed schemes
    with pytest.raises(SSRFSecurityError, match="Disallowed URL scheme"):
        validate_url_safety("file:///etc/passwd")

    with pytest.raises(SSRFSecurityError, match="Disallowed URL scheme"):
        validate_url_safety("gopher://127.0.0.1:6379")

    with pytest.raises(SSRFSecurityError, match="Disallowed URL scheme"):
        validate_url_safety("ftp://example.com/test.csv")


def test_validate_url_safety_domain_allowlist():
    allowed = ["raw.githubusercontent.com", "api.razorpay.com"]

    # Disallowed domain
    with pytest.raises(SSRFSecurityError, match="not in approved allowlist"):
        validate_url_safety("https://malicious-site.com/payments.csv", allowed_domains=allowed)

    # Valid domain (if DNS resolves to public IP)
    url = "https://raw.githubusercontent.com/user/repo/main/payments.csv"
    res = validate_url_safety(url, allowed_domains=allowed)
    assert res == url
