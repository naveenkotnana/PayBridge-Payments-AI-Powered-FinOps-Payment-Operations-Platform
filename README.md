# PAYBRIDGE — Payments AI-Powered FinOps & Payment Operations Platform

**Demo mode · Synthetic payment data · Simulated actions.**

PayBridge is an interview-ready AI-powered payment operations and FinOps demonstration platform combining payment processing, data engineering, analytics, ML anomaly detection and GenAI-assisted investigation.

**The project story:** PayBridge takes payment transaction data, detects operational anomalies using ML, investigates those incidents using a LangGraph/RAG-based AI workflow, gives a human operator evidence-backed recommendations, and records the approved outcome for auditability.

The backend implements these stages. The original Customer, Merchant and Admin screens include illustrative results; complete UI-to-backend workflow wiring remains future work. This is an independent demo implementation with no Razorpay affiliation.

## Business problem

Payment operations teams investigate failed or pending payments, suspected gateway latency, abnormal transaction patterns and merchant-level incidents. They need transaction evidence, operational guidance, a reviewable recommendation and an audit trail. PayBridge organizes that work into one payment-to-decision story.

## End-to-end workflow

```text
Customer Aarav → RAMESHSWARAM CAFE → Payment transaction
    → Data ingestion → Validation / data quality
    → Database → Analytics → ML anomaly signal / alert
    → Incident investigation with LangGraph
    → RAG + named SQL + analytics evidence → Evidence bundle
    → AI recommendation → Human review
    → Simulated operational mitigation → Audit record
```

**Database scope:** SQLite is the demonstrated local database. PostgreSQL configuration and a driver are present, but loading all 50,000 records into PostgreSQL and SQL portability have not been verified. “Database” in the flow above refers to the configured store, with SQLite used for this demo.

## What is implemented?

- **IMPLEMENTED:** Admin CSV upload, ingestion-run records, rejection reports, persistent imported-data preview/download, searchable payment ledger, duplicate detection, normalization and separate data-quality audits.
- **IMPLEMENTED:** SQL analytics, Isolation Forest with deterministic severity rules, and investigation of stored alerts.
- **IMPLEMENTED:** LangGraph orchestration, local SOP retrieval, optional Ollama generation, stored approval/rejection and local action/audit records.
- **SIMPLIFIED:** evidence validation, financial fee calculations and anomaly evaluation. The detector currently fits and scores the same aggregate dataset.
- **SIMULATED:** operational mitigation, routing messages and external notification/ticket effects. No real production payment traffic is rerouted.
- **DEMO ONLY:** synthetic records and presentation persona switching. Some original UI metrics and AI responses are illustrative.
- **FUTURE WORK:** complete UI/API integration, authenticated tenant boundaries, durable execution recovery and verified PostgreSQL deployment.

## Razorpay payment flow

```text
Customer → Frontend → Backend order creation → Razorpay order
    → Checkout → Payment → Backend verification
    → HMAC-SHA256 + provider-state checks → Database records
```

`POST /api/create-order` creates an order through the Razorpay SDK and stores the provider order locally. `POST /api/verify-payment` verifies the signature, requires a matching local order, fetches the provider payment, and checks order ID, amount, currency and captured status before recording capture.

This is an actual provider integration when valid credentials are configured; test credentials use Razorpay test mode. Provider failures do not create fabricated successful orders. A browser success message alone does not confirm backend verification. Checkout returns its payment identifiers and signature to the server automatically. A captured, provider-verified payment displays a receipt; the manual verification form has been removed from the customer page. A completed browser payment remains an outstanding end-to-end check.

Payment verification is distinct from **simulated operational mitigation**. The project does not implement production traffic rerouting.

## Data engineering

```text
Synthetic CSV → Ingestion → Column / required-field validation
    → Duplicate and missing-value checks → Normalization
    → Database → Separate data-quality audit → Analytics / ML
```

The generator prepares 50,000 synthetic payments across ten merchants. Ingestion archives the input, tracks accepted/rejected/duplicate counts and records rejected-row reasons. Quality audits check relationships and financial consistency. Some unknown categorical values currently receive defaults; stricter quarantine is future work. The verified local dataset is in SQLite.

## ML and AI-assisted investigation

**ML:** payment records are grouped by gateway, method and bank. Isolation Forest scores aggregate attempts, failures, failure rate, volume and retryable failures. Rules assign severity and create alerts for qualifying findings. Merchant-specific evidence requires a separate filter; the main detector is not grouped by merchant. Latency detection is not established by these five features.

**LangGraph / GenAI:** the backend plans an investigation, runs registered SQL queries, retrieves operational SOPs, gathers analytics, validates evidence and generates a recommendation. Retrieval uses local TF-IDF and cosine similarity. Ollama provides optional local structured generation; an explicitly identified deterministic fallback is available.

RAG grounds the investigation using retrieved operational knowledge and evidence, while human review remains part of the workflow. Grounding checks are heuristic. Approved actions produce local records; audit hashes provide traceability rather than an immutable ledger.

## Demo incident: RAMESHSWARAM CAFE

Use one scenario throughout: **Aarav's payment and a suspected UPI payment failure spike at RAMESHSWARAM CAFE.**

```text
Payment → Abnormal failure pattern → ML signal / alert
    → Incident investigation → Evidence → Recommendation
    → Admin review → “Simulated mitigation approved” → Audit
```

The prepared cafe/SBI/UPI segment contains 503 captured, 133 failed and 4 pending transactions. Its terminal failure rate is `133 / (503 + 133) = 20.91%`; failed attempted amount is INR 41,360. These synthetic aggregates illustrate the investigation, rather than proving a time-local outage or confirmed revenue loss.

Select an actual backend alert to demonstrate investigation and stored review. The sample mitigation button saves a simulated approval/rejection and shows its decision in Approvals and Overview activity. It does not change payment status or execute a live routing change. The stored LangGraph workflow approvals remain a separate backend path. Setup seeds a rule-based demo alert, so its presence alone does not demonstrate that ML ran. A separate payment-incident model exists, but automatic conversion of every incident into an investigation alert is incomplete.

## Technology stack

- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy; Razorpay SDK.
- **Database:** SQLite for the local demo; PostgreSQL driver/configuration and Alembic are present.
- **Data engineering:** pandas, NumPy, CSV ingestion and validation services.
- **ML:** scikit-learn Isolation Forest and deterministic rules.
- **GenAI:** LangGraph, optional Ollama, local TF-IDF/cosine SOP retrieval.
- **Frontend:** Streamlit.
- **DevOps and quality:** Docker Compose, GitHub Actions, pytest, Ruff and Mypy.

## Run locally

Use Python 3.11 or newer from the repository root. In PowerShell, start the FastAPI backend and Streamlit frontend together:

```powershell
python -m pip install -r requirements.txt
./start-demo.ps1
```

The existing Customer, Merchant, and Admin interface opens in Streamlit at [http://127.0.0.1:8501](http://127.0.0.1:8501). FastAPI runs alongside it; open [Swagger API docs](http://127.0.0.1:8000/docs), [ReDoc](http://127.0.0.1:8000/redoc), or [health status](http://127.0.0.1:8000/health) to demonstrate the backend. The API exposes payment analytics, CSV ingestion, investigation workflows, human approval, audit, and Razorpay order/verification endpoints.

`start-demo.ps1` selects `backend/data/paybridge.db` when it exists, or the packaged `payment_data.db` otherwise, then passes that same database URL to FastAPI and Streamlit.

In Swagger, authenticate with `/auth/login`, select a returned `/alerts` ID, investigate it, inspect its workflow, and approve or reject a pending recommendation with an authorized role. Inspect `/audit` afterward. Use the locally seeded demo accounts defined in `backend/app/core/security.py`.

Configuration is documented in `.env.example`:

- `DEMO_MODE` and `DATABASE_URL`: demo initialization and shared storage.
- `JWT_SECRET`: use a unique secret; non-demo startup rejects known weak defaults.
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`: optional local inference configuration. Install the model with `ollama pull qwen2.5:3b-instruct`.
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`: required for provider checkout; keep credentials in local environment configuration.

## Scope and validation

This interview/demo implementation uses synthetic data and simulated operational actions. Streamlit persona selection is a presentation feature. Authenticated UI identities, tenant-scoped checkout and server-priced carts remain future work. Keep the current demo local. Some investigation analytics are global; state the scope when presenting merchant evidence.

The verified local test suite passed **152 tests**, with three existing datetime deprecation warnings. To run the suite, first set `DATABASE_URL` to a disposable database, then run:

```powershell
python backend/scripts/setup_all.py
python -m pytest tests/ -q
```

Docker Compose and GitHub Actions define packaging and validation steps. They do not establish a verified production deployment, real-money end-to-end testing or PostgreSQL certification.

## Current interview walkthrough

See [SUBMISSION.md](SUBMISSION.md) for the three-moment explanation and [VALIDATION.md](VALIDATION.md) for the latest verification boundaries.

## One-click wallet demo and UPI

Customer → Orders now offers PayBridge Wallet (demo), UPI (Razorpay), and Card / Wallet (Razorpay).

The local demo wallet starts once with INR 50,000 simulated credit. Clicking Pay INR 280 debits the stored balance, saves a synthetic WALLET transaction and audit record, and displays a downloadable receipt. Repeating the same payment request does not debit twice. Insufficient funds and failed database commits do not leave a partial payment. The wallet is disabled outside DEMO_MODE and never claims to move funds through Razorpay.

UPI is prioritized in provider checkout. Availability depends on the methods enabled by Razorpay for the account; this change does not activate a disabled provider method. Real UPI requires customer authorization. The local wallet gives an immediate, repeatable interview demonstration without requiring a bank or card.

## Cafe menu and merchant order updates

Customer → Orders contains five items: Masala Dosa (INR 120), Idli (INR 50), Vada (INR 70), Filter Coffee (INR 40), and Tea (INR 30). Breakfast and Snack preset combinations cost INR 280 and INR 150. Edit quantities and select Update cart before paying. Prices and totals are computed on the server; saved itemized orders flow into receipts and Merchant Orders. Merchant Overview recent-order cards and totals now read stored records.

## Payment support lookup

Admin → AI Investigation → Check a transaction reads a payment or order reference from a short question. It displays captured/failed/pending status and any saved failure reason. Unknown references are shown as not found, not failed. If no cause is recorded, the tool states that limitation. This is a deterministic read-only check against the configured database, not an unrestricted chatbot or a live bank query. The separate Incident investigation (demo) mode retains illustrative content.

## Uploaded-batch overview

Admin → Overview → Overview data can select All payments or a single import batch. Transaction counts, captured GMV, captured/failed/pending counts and success/failure rates read the selected accepted database records. Pending outcomes are excluded from the terminal success/failure denominator. Invalid and duplicate CSV rows remain ingestion rejections rather than failed payments. Demo gateway and data-quality cards are explicitly labeled illustrative.
