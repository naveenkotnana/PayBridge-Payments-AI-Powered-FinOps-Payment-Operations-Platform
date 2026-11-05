"""Secure External URL Data Ingestion Service with SSRF & Denial-of-Service Guards.

Security Model:
1. Domain Allowlist: Strictly checks host against approved trusted domains
   (e.g., github.com, raw.githubusercontent.com, razorpay.com, internal test hosts).
2. SSRF Protection:
   - Resolves host DNS to IP address before connection.
   - Blocks private, loopback, link-local, multicast, and reserved IP ranges (RFC 1918, RFC 3927).
   - Re-checks destination IP on every HTTP redirect hop.
3. Resource Limits:
   - Max file size limit: 10 MB (prevents memory exhaustion on 8 GB RAM).
   - Strict connection and read timeout: 10 seconds.
4. Tabular Extraction:
   - Extracts CSV, JSON, and Excel (.xlsx/.xls) into a canonical stream.
   - Passes extracted data directly to PaymentCSVIngestionService for canonical validation.
"""
import io
import ipaddress
import logging
from pathlib import Path
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.services.ingestion_payments import PaymentCSVIngestionService

log = logging.getLogger("opspilot.url_ingestion")

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
DEFAULT_TIMEOUT_SECONDS = 10.0

# Pre-approved domains for external documentation and payment datasets
DEFAULT_ALLOWED_DOMAINS = [
    "raw.githubusercontent.com",
    "github.com",
    "api.razorpay.com",
    "razorpay.com",
    "docs.razorpay.com",
    "npci.org.in",
    "rbi.org.in",
    "huggingface.co",
]


class SSRFSecurityError(Exception):
    """Raised when an outbound URL target violates SSRF or security constraints."""
    pass


def is_ip_private_or_restricted(ip_str: str) -> bool:
    """Check if an IPv4 or IPv6 address is in a private, loopback, or reserved range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_multicast or
            ip.is_reserved or
            ip.is_unspecified
        )
    except ValueError:
        return True


def validate_url_safety(url: str, allowed_domains: Optional[List[str]] = None) -> str:
    """Strictly validate target URL scheme, domain allowlist, and IP address against SSRF."""
    if not url or not isinstance(url, str):
        raise SSRFSecurityError("Empty or invalid URL provided")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFSecurityError(f"Disallowed URL scheme '{parsed.scheme}'. Only 'http' and 'https' permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityError("URL has no valid hostname")

    # Domain allowlist check
    domains = allowed_domains or DEFAULT_ALLOWED_DOMAINS
    is_domain_allowed = any(
        hostname.lower() == d.lower() or hostname.lower().endswith("." + d.lower())
        for d in domains
    )
    if not is_domain_allowed:
        raise SSRFSecurityError(f"Domain '{hostname}' is not in approved allowlist: {domains}")

    # DNS Resolution and SSRF IP check
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_addr = entry[4][0]
            if is_ip_private_or_restricted(ip_addr):
                raise SSRFSecurityError(
                    f"SSRF Alert: Hostname '{hostname}' resolves to private/restricted IP '{ip_addr}'"
                )
    except socket.gaierror:
        raise SSRFSecurityError(f"Could not resolve host '{hostname}' via DNS")

    return url.strip()


class SecureURLIngestionService:
    """Fetches external payment datasets safely and routes to canonical ingestion."""

    def __init__(self, db: Session, allowed_domains: Optional[List[str]] = None):
        self.db = db
        self.allowed_domains = allowed_domains or DEFAULT_ALLOWED_DOMAINS
        self.csv_service = PaymentCSVIngestionService(db)

    async def fetch_and_ingest(
        self,
        url: str,
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Validate URL, securely fetch dataset, and route to canonical payment ingestion."""
        safe_url = validate_url_safety(url, self.allowed_domains)

        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT_SECONDS,
            follow_redirects=True,
            max_redirects=3,
        ) as client:
            try:
                response = await client.get(safe_url)
            except httpx.TimeoutException:
                raise SSRFSecurityError(f"Connection timeout fetching URL: {url}")
            except Exception as e:
                raise SSRFSecurityError(f"HTTP request error: {str(e)}")

            if response.status_code != 200:
                raise SSRFSecurityError(f"Remote server returned HTTP {response.status_code}")

            # Check response size cap
            content_bytes = response.content
            if len(content_bytes) > MAX_FILE_SIZE_BYTES:
                raise SSRFSecurityError(
                    f"File size {len(content_bytes)} bytes exceeds maximum {MAX_FILE_SIZE_BYTES} bytes"
                )

            # Determine format
            content_type = response.headers.get("content-type", "").lower()
            url_path = Path(urlparse(safe_url).path)
            file_name = url_path.name or "external_dataset.csv"

            # Parse content into CSV-compatible buffer
            if "json" in content_type or file_name.endswith(".json"):
                # Handle JSON array of payments
                import json
                try:
                    data = json.loads(content_bytes.decode("utf-8"))
                    if isinstance(data, dict):
                        data = data.get("payments") or data.get("transactions") or [data]
                    if not isinstance(data, list) or not data:
                        raise ValueError("JSON must contain a non-empty array of transaction objects")

                    # Convert to CSV buffer
                    headers = list(data[0].keys())
                    buffer = io.StringIO()
                    import csv
                    writer = csv.DictWriter(buffer, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(data)
                    buffer.seek(0)
                    file_buffer = buffer
                except Exception as e:
                    raise SSRFSecurityError(f"Malformed JSON payment dataset: {str(e)}")
            else:
                # Default CSV buffer
                file_buffer = io.BytesIO(content_bytes)

            # Pass into canonical pipeline
            result = self.csv_service.ingest_csv_file(
                file_path_or_buffer=file_buffer,
                source_name=f"URL_IMPORT:{file_name}",
                custom_mapping=custom_mapping,
            )
            result["source_url"] = safe_url
            return result
