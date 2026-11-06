# PayBridge — Payments AI-Powered FinOps & Payment Operations Platform

> **Demo mode · Synthetic payment data · Simulated operational actions**

PayBridge is a payment-operations prototype that brings payment records, data-quality checks, analytics, anomaly signals, AI-assisted investigation, human review, and audit records into one workflow. It combines a Streamlit interface with a FastAPI backend.

The project explores a practical operations question: when payments fail or become pending, how can an operator find the relevant evidence, understand the pattern, and record a reviewable next step? Some UI results are illustrative, and operational mitigations are simulated. PayBridge is an independent project and is not affiliated with Razorpay.

## Business problem

Payment operations teams may need to investigate failed or pending payments, unusual transaction patterns, merchant-level issues, and inconsistent data feeds. Investigation can require manual queries, multiple records, and separate operating procedures. PayBridge demonstrates a structured path from payment data to evidence and a human-reviewed decision.

## Key features

- Customer, Merchant, and Admin views in Streamlit.
- Razorpay Standard Checkout order creation and a FastAPI server-side verification endpoint, when valid test credentials are configured.
- CSV ingestion with column normalization, validation, duplicate handling, import history, and rejected-row reporting.
- SQL analytics and an Isolation Forest anomaly-scoring workflow with deterministic severity rules.
- LangGraph investigation orchestration using registered SQL queries, analytics evidence, and local SOP retrieval.
- Optional local Ollama structured generation with an identified deterministic fallback.
- Human approval and rejection records, plus local audit and activity records.
- Payment lookup by payment or order reference, and views for imported batches and merchant payment status.

## End-to-end workflow

```text
Payment records / CSV
        ↓
Ingestion and data-quality checks
        ↓
Configured SQL database
        ↓
Analytics and anomaly signal
        ↓
LangGraph investigation
        ↓
SQL + analytics + retrieved SOP evidence
        ↓
Recommendation for human review
        ↓
Recorded decision and audit activity
```

## Architecture

| Layer | Responsibility |
|---|---|
| Streamlit | Customer, Merchant, and Admin presentation screens |
| FastAPI | Payment, ingestion, analytics, investigation, approval, and audit APIs |
| Razorpay | Test-mode checkout and provider payment verification when configured |
| SQLAlchemy database | Payment, order, ingestion, investigation, and decision records |
| Data services | CSV normalization, validation, deduplication, and data-quality reporting |
| Analytics and ML | SQL-derived metrics, Isolation Forest scores, and deterministic severity rules |
| LangGraph and RAG | Investigation steps, allowlisted SQL tools, and local SOP retrieval |
| Human review | Operator review of a recommendation and recording of approve/reject |

The UI is not fully wired to every backend workflow. The database demonstrated locally is SQLite. PostgreSQL configuration and a driver are present, but a complete PostgreSQL migration and deployment have not been verified.

## Razorpay payment flow

```text
Customer → FastAPI creates provider order → Razorpay Checkout
         → checkout returns payment details → FastAPI verifies
         → HMAC-SHA256 + provider-state checks → database record
```

`POST /api/create-order` creates an order through the Razorpay SDK and stores its provider order reference locally. `POST /api/verify-payment` checks the signature, matching local order, provider payment, order ID, amount, currency, and captured status before recording a capture. The Razorpay secret remains on the server and must be configured outside source control.

This integration uses Razorpay test mode when test credentials are supplied. The browser success callback is not, by itself, proof of a verified payment. A completed browser checkout and receipt still require end-to-end confirmation in the target environment. Provider payment verification is separate from the simulated operational mitigation described below.

## Data engineering pipeline

```text
Synthetic or compatible CSV
        ↓
Column mapping and normalization
        ↓
Required-field and schema validation
        ↓
Duplicate checks and rejected-row report
        ↓
Configured SQL database
        ↓
Analytics and ML inputs
```

The data generator prepares synthetic payment records. CSV imports save accepted rows as structured database records and create an ingestion-run record with counts and status. The original upload and rejection report are handled separately; the system does not create a separate processed CSV. The verified local data store is SQLite.

## Data quality

The ingestion flow validates required fields, normalizes recognized values, identifies duplicate payment IDs, and reports invalid rows. Data-quality audits also check stored relationships and financial consistency. Some unrecognized categorical values may receive defaults; stricter quarantine and broader source-specific schemas remain future work. Unrelated or arbitrary files are not reliably converted into payment records.

## Analytics

Payment records feed SQL-based metrics, including transaction counts, captured volume, and status rates. Admin Overview can filter by all payments or an imported batch. Merchant payment views can filter captured, failed, and pending records. Captured GMV is payment volume, not profit. Pending records are excluded from terminal success/failure-rate denominators. Some original dashboard metrics remain illustrative; use the ledger and clearly labeled views when presenting stored records.

## ML anomaly detection

The backend groups payment attempts by gateway, payment method, and bank, then applies Isolation Forest scoring to aggregate features such as attempts, failures, failure rate, volume, and retryable failures. Deterministic rules assign severity and create qualifying alerts. The detector currently scores aggregates from the same prepared dataset; this is not evidence of a live production outage. The main detector is not merchant-specific, and latency detection is not established by these features.

## AI investigation and LangGraph

The backend LangGraph workflow plans an investigation, runs registered SQL queries, gathers analytics, retrieves operational procedures, validates evidence, and generates a recommendation. The payment-reference lookup in Admin is a separate deterministic, read-only database check; it reports saved status and failure reason when available and returns “not found” for unknown references. It is not an unrestricted chatbot or a live bank query.

## Retrieval-augmented generation (RAG)

RAG adds relevant local operating procedures to an investigation. PayBridge uses local TF-IDF and cosine-similarity retrieval over its SOP documents. Retrieved procedure text is combined with database and analytics evidence for review. Ollama can provide optional local structured generation; a deterministic fallback is available. Retrieval and grounding checks are heuristic, so recommendations still require human review. The implementation does not claim zero hallucinations or embedding-based vector search.

## Incident example

### Rameshwaram Cafe — UPI failure pattern

```text
Prepared payment records
        ↓
Failure pattern qualifies for an alert
        ↓
Investigation gathers database and SOP evidence
        ↓
Recommendation is presented to an Admin
        ↓
Admin records approve/reject decision
        ↓
Local audit/activity record
```

The prepared cafe/SBI/UPI segment contains 503 captured, 133 failed, and 4 pending transactions. Its terminal failure rate is `133 / (503 + 133) = 20.91%`; the failed attempted amount is INR 41,360. These are synthetic aggregates for an investigation example, not proof of a time-local bank outage or confirmed revenue loss. Setup also seeds a rule-based alert, so its presence alone does not show that ML ran.

## Human-in-the-loop approvals

An approval is for a proposed operational response, not for whether an individual payment succeeded. The operator reviews the evidence and records approval or rejection. In the sample incident UI, this records a simulated mitigation decision; it does not change payment status, reroute live traffic, or execute a bank-switch change. Stored backend workflow approvals are a separate path from the illustrative incident card.

## Auditability

PayBridge stores local activity and audit records for supported workflows, including decisions. Audit hashes provide traceability; they are not an immutable ledger or a guarantee of production compliance. Inspect the `/audit` API after using an authorized workflow.

## Demo disclosure

> **Demo mode · Synthetic payment data · Simulated operational actions**

- Transaction datasets used for demonstrations are synthetic.
- Some dashboard and incident content is illustrative.
- Razorpay checkout can use test credentials; test payments are not real-money payments.
- Approval records a decision; it does not route real payment traffic.
- The local demo uses SQLite; PostgreSQL migration and production deployment are unverified.
- Do not present this prototype as a production payment-routing platform.

## Portals and demo flows

- **Customer:** preset cafe menu, editable cart, demo wallet, Razorpay checkout options, and payment receipt/history. The PayBridge wallet uses simulated INR 50,000 credit and does not move funds through Razorpay.
- **Merchant:** cafe payment ledger, status filters, order summaries, and merchant-side activity. Some fulfillment/status messages are illustrative.
- **Admin:** overview, imported-batch data, payment lookup, anomaly/investigation pages, approvals, and audit activity. Some original UI investigation content is illustrative or only partially connected to backend workflows.

## Technology stack

- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Razorpay SDK.
- **Database:** SQLite for the verified local demo; PostgreSQL driver/configuration and Alembic are present but migration is unverified.
- **Data engineering:** pandas, NumPy, CSV ingestion and validation.
- **ML:** scikit-learn Isolation Forest and deterministic rules.
- **AI:** LangGraph, local TF-IDF/cosine SOP retrieval, optional Ollama.
- **Frontend:** Streamlit.
- **Quality and packaging:** pytest, Ruff, Mypy, Docker Compose, GitHub Actions.

## Repository structure

```text
backend/                 FastAPI app, APIs, database, agent, RAG, services
backend/app/agent/       LangGraph workflow and registered tools
backend/app/rag/         Local retrieval and optional Ollama client
backend/app/static/      FastAPI-served landing page and static assets
backend/data/            Local documents, generated data, and demo database files
backend/alembic/         Database migration scripts
frontend/                Streamlit entry point, views, and shared styles
ml/                      ML components
tests/                   Automated test suite
docs/                    Project and technical documentation
.env.example             Configuration template; contains no live secrets
requirements.txt         Python dependencies
start-demo.ps1           Local FastAPI and Streamlit launcher
Dockerfile               Container build
docker-compose.yml        Local compose configuration
```

## API overview

Interactive API documentation is available at `/docs` when FastAPI is running. Core routes include:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Service health |
| `POST` | `/auth/login` | Obtain an API access token |
| `GET` | `/api/v1/payments/kpis` | Payment KPIs |
| `GET` | `/api/v1/payments/dashboard` | Payment dashboard data |
| `POST` | `/api/v1/ingestion/csv` | Upload a payment CSV |
| `GET` | `/api/v1/ingestion/runs` | List ingestion runs |
| `GET` | `/alerts` | List investigation alerts |
| `POST` | `/alerts/{alert_id}/investigate` | Investigate an alert |
| `POST` | `/workflows/{workflow_id}/approve` | Record workflow approval |
| `POST` | `/workflows/{workflow_id}/reject` | Record workflow rejection |
| `GET` | `/audit` | Read audit events |
| `POST` | `/api/create-order` | Create a Razorpay order |
| `POST` | `/api/verify-payment` | Verify a Razorpay payment |

## Security considerations

Razorpay secrets are read from environment configuration and used server-side. Payment verification checks the signature and provider state before recording capture. API authentication and role permissions exist for backend workflows, but Streamlit persona selection is a presentation feature and is not a secure user identity. Authenticated UI identities, complete tenant isolation, and production deployment hardening remain future work. Never commit `.env` or real credentials; use `.env.example` as a template.

## Getting started

Use Python 3.11 or newer from the repository root. In PowerShell:

```powershell
python -m pip install -r requirements.txt
./start-demo.ps1
```

Open Streamlit at `http://127.0.0.1:8501`, FastAPI Swagger at `http://127.0.0.1:8000/docs`, or health at `http://127.0.0.1:8000/health`. The launcher selects the local PayBridge database when present, otherwise the packaged payment database, and passes the same database URL to both processes.

Configuration is documented in `.env.example`. Set `DATABASE_URL` and `DEMO_MODE` as needed. Razorpay checkout requires `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`; keep the secret local or in a deployment secret manager. Optional local generation uses `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.

## Testing and validation

The latest local validation recorded in this README was **152 passing tests**, with three datetime deprecation warnings. This does not verify a production deployment, completed real-money payment, or PostgreSQL migration. To run the suite safely, point `DATABASE_URL` at a disposable database, then run:

```powershell
python backend/scripts/setup_all.py
python -m pytest tests/ -q
```

## Limitations and future work

- Complete the Streamlit-to-API integration for all screens and workflows.
- Verify PostgreSQL migration, schema setup, and deployment persistence.
- Connect anomaly results consistently to investigation records and UI views.
- Add authenticated UI identities and enforce tenant-scoped data access.
- Evaluate anomaly detection and AI recommendation quality on representative, approved data.
