# PayBridge production readiness matrix

Status is based on repository code and checks run on 2026-11-08. “Implemented” means the stated behavior exists in this branch; it does not imply production certification.

| Capability | Status | Evidence / limitation |
|---|---|---|
| Fail-closed production config | IMPLEMENTED AND TESTED | `DEMO_MODE` defaults false; production requires PostgreSQL, a strong JWT secret, explicit origins, and a checkout merchant. 10 focused config/security tests passed. |
| Demo credentials and demo seeding | IMPLEMENTED AND TESTED | Seed path is restricted to `DEMO_MODE=true`; production startup checks for built-in demo usernames. |
| API authorization and current-user lookup | IMPLEMENTED BUT NOT FULLY TESTED | JWT expiry and active-user checks, role permissions, and protected endpoints exist. Full cross-tenant coverage of every endpoint remains incomplete. |
| Login throttling | IMPLEMENTED AND TESTED | Failed attempts are stored in SQL shared by app workers; eight failures in a 15-minute window block for 15 minutes. 3 focused tests passed. Proxy identity configuration still needs deployment review. |
| Production Streamlit identity and page calls | NOT IMPLEMENTED | Production Streamlit is deliberately stopped by a fail-closed guard because the current screens still directly access services/database and role state. It must be migrated to authenticated APIs before production UI use. |
| Razorpay Standard Checkout | IMPLEMENTED AND TESTED | Server prices canonical cart, checks configured credentials, uses idempotency reservations, authenticates customer route, validates HMAC and provider capture state, and commits local payment/order/event/audit atomically. 21 checkout tests are included in suite. Provider is stubbed in tests; no real sandbox payment was run in this phase. |
| Checkout recovery | IMPLEMENTED BUT NOT FULLY TESTED | Bounded reconciliation service restores a missing local order only after matching provider order ID, amount, currency, receipt, and status. It does not mark payments captured. Scheduling and live provider recovery are not verified. |
| PostgreSQL production configuration | IMPLEMENTED BUT NOT FULLY TESTED | Docker Compose has a PostgreSQL production API profile; CI is configured with PostgreSQL. PostgreSQL service/build/integration could not run locally because Docker and `psql` are unavailable. |
| Alembic schema lifecycle | IMPLEMENTED BUT NOT FULLY TESTED | Versioned schema and additive revisions exist. Fresh and legacy SQLite upgrades reached head; a legacy copy retained 50,004 payment rows. PostgreSQL migration and data-preserving upgrade are not verified. |
| Payment CSV validation and batch behavior | IMPLEMENTED BUT NOT FULLY TESTED | Required fields, strict category handling, UTC timestamps, merchant/customer existence, order consistency, separate duplicate counts, file limits, and one transaction per batch. Unit/API checks passed. Interruption and concurrent import tests remain. |
| 50K canonical CSV ingestion | IMPLEMENTED AND TESTED | The bundled 50,000-row CSV was processed by `PaymentCSVIngestionService` against an isolated SQLite DB: received 50,000, accepted 50,000, rejected 0, duplicates 0; SQL count confirmed 50,000 rows. This is not PostgreSQL evidence. |
| Anomaly and alert history | IMPLEMENTED BUT NOT FULLY TESTED | Fingerprints, first/last seen and occurrence counts prevent repeated runs from deleting/recreating the same monthly signal. Time-windowed merchant features, resolution history, and benchmark metrics remain incomplete. |
| RAG evidence workflow | IMPLEMENTED BUT NOT FULLY TESTED | Evaluation: Recall@4 22/22, top-1 21/22, mean fact coverage 0.947, citation correctness 18/22, overall pass 18/22. Four evaluation cases did not pass. |
| Agent/security evaluation | IMPLEMENTED AND TESTED | 35/35 scripted agent, approval, SQL guardrail, prompt-injection, and failure-mode cases passed. This does not prove general model safety. |
| URL ingestion | DEMO ONLY | Disabled by default in production configuration and production startup rejects it if enabled before external SSRF review. |
| Synthetic-data simulation endpoints | DEMO ONLY | Controlled by a feature flag defaulting off outside demo mode. |
| Metrics and request tracing | NOT IMPLEMENTED | Current request counters are process-local; trace IDs are not propagated end to end. |
| Docker image hardening and Compose runtime | BLOCKED BY EXTERNAL REVIEW | Docker CLI/Compose are unavailable in this environment; image build, non-root behavior, health, and PostgreSQL startup were not verified. |
| Backup/restore | NOT IMPLEMENTED | A command runbook is provided, but no PostgreSQL backup/restore smoke test was possible here. |
| Payment routing / mitigation | SIMULATED | Approval records a decision only. It does not reroute production traffic or move funds. |
| Razorpay / PCI / regulatory compliance | BLOCKED BY EXTERNAL REVIEW | No compliance audit or qualified payment-security review was performed. |

## Overall assessment

PayBridge remains a portfolio and demo system. This branch hardens several high-risk paths and introduces production-oriented configuration and migrations, but it has not passed a defined production-readiness review. The production Streamlit UI is intentionally unavailable until the authentication migration is completed. PostgreSQL, Docker, deployment, and payment-provider checks still require an equipped environment and external operational review.
