# Security review notes

Review date: 2026-11-08. This is an engineering review of the current branch, not a penetration test, compliance assessment, or independent security certification.

## Controls added

- Production mode defaults to off for demo behavior: missing/weak JWT secret, missing trusted CORS origins, non-PostgreSQL database, missing checkout merchant, demo usernames, and unreviewed URL ingestion fail closed.
- Built-in demo account seeding runs only with explicit `DEMO_MODE=true`.
- Production Streamlit startup is blocked while the pages still use direct database/service access and widget-backed role state.
- Customer checkout API endpoints require the customer checkout permission. Customer and merchant identity is derived from the authenticated database user, never the order request body.
- Checkout uses menu prices from server code, a unique durable idempotency reservation, constant-time HMAC comparison, provider-side payment lookup, customer/order ownership checks, state checks, and an atomic local write.
- Missing Razorpay keys return service unavailable; the request handler no longer reads `.env` or uses mock keys.
- Login failures use a SQL-backed counter shared between workers. The key is an HMAC digest of the client address and normalized username; raw password and token data are not stored.
- Production URL ingestion remains disabled. Simulation endpoints can be disabled through the runtime feature flag.
- CSV imports reject unknown/missing categories instead of filling them with plausible defaults, require source timestamps, and normalize offsets to UTC.
- Ingestion responses expose archived/rejected file names, not server filesystem paths.

## Remaining security work

1. Convert the Streamlit application to authenticated API calls and remove direct database imports for all production pages. The current production guard is intentional; do not remove it as a presentation shortcut.
2. Complete a route-by-route authorization and tenant-isolation audit, including customer-owned reads and merchant-scoped operations. Current changes primarily cover checkout and protected admin/analyst routes.
3. Review reverse-proxy configuration, trusted forwarding headers, TLS, request/body limits, and deployment-level network rules. The login limiter uses `request.client.host`; proxy behavior must be verified in the selected host.
4. Add shared rate limits for expensive investigation, analytics, upload, and simulation paths. Login throttling does not cover those endpoints.
5. Secure stored CSV archives and rejection files with access controls, encryption at rest, retention limits, and deletion policy. Existing local archive handling is not a managed object store.
6. Run PostgreSQL concurrency, constraints, migration, backup/restore, and failure-injection tests. PostgreSQL and Docker were not available for verification here.
7. Arrange a qualified review of Razorpay integration, key management, payment-data handling, and any regulatory obligations. Hosted checkout reduces card-data handling in this app, but no PCI DSS claim is made.
8. Add alert resolution history and time-windowed merchant-aware features; current anomaly aggregation still includes broad historical data.

## Threat boundary

Razorpay Standard Checkout handles the browser payment UI. PayBridge receives the returned provider identifiers and signature, verifies the HMAC, then checks Razorpay's payment state before recording a captured transaction. A test order is not a captured payment. Human mitigation approval is an audit decision and does not alter live gateway routing.

Do not store card numbers or CVV in PayBridge. Never put provider secrets in frontend code, logs, Git, or image build arguments. The `.env` file remains a local development secret source and must not be committed.
