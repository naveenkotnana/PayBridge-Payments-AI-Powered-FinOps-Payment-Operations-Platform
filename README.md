# PayBridge Payments
> **An Enterprise-Grade FinOps & Payment Operations Platform featuring Razorpay Web Checkout, 50,000-Transaction Ingestion Pipelines, Hybrid ML Anomaly Detection, and Sandboxed LangGraph Agentic Investigation with Human Approval Gates.**

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2F%20SQLite-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-10_Node_DAG-FF6F00?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Local LLM](https://img.shields.io/badge/Local_LLM-Ollama_Qwen2.5-000000?style=flat-square)](https://ollama.ai)
[![Tests](https://img.shields.io/badge/Tests-117%20Passed%20(100%25)-brightgreen?style=flat-square)](tests/)
[![Code Style](https://img.shields.io/badge/Code_Style-Ruff_0_Errors-blueviolet?style=flat-square)](https://astral.sh/ruff)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

PayBridge Payments is a unified payment operations and financial intelligence platform designed to observe, triage, and remediate high-throughput digital payment failures across multi-bank rails (UPI/NPCI, Cards, and NetBanking). The system bridges consumer checkout execution, high-throughput CSV data engineering, unsupervised anomaly detection, and local agentic root-cause synthesis. Built for platform administrators, merchant store operators, and end buyers, PayBridge eliminates financial hallucination by decoupling deterministic database math from generative natural language reasoning.

---

## The Problem

High-volume digital payment ecosystems in India process tens of millions of daily transactions over heterogeneous banking switches (SBI, HDFC, ICICI, Axis) and gateway switches. However, operational teams face critical systemic failure modes:

1. **The 3% Switch Outage Cascade**: When a major upstream banking switch experiences a transient latency surge (>4,000 ms), transactions fail or get stuck in `PENDING` states. Naive systems either cancel orders prematurely or allow retries that trigger customer double-debits.
2. **Merchant Inventory Loss on Pending Debits**: Merchants frequently dispatch goods before bank confirmation or cancel legitimate orders, incurring direct inventory write-offs.
3. **LLM Hallucinations in Financial Operations**: Generic generative AI models cannot be trusted to perform financial arithmetic. LLMs invent transaction IDs, approximate fee rates, and miscalculate Merchant Discount Rates (MDR) or Goods and Services Tax (GST).
4. **Data Leakage & Ingestion Heterogeneity**: Financial data feeds arrive across fragmented formats with inconsistent headers, mixed date formats, and duplicate records. Failing to validate inputs chronologically leaks future information into anomaly scoring models.
5. **Unconstrained Autonomous Actions**: Fully autonomous agents executing database mutations without deterministic clearance checks or human authorization introduce intolerable compliance and financial risk.

---

## The Idea

PayBridge resolves this by enforcing an uncompromising separation of responsibilities between **deterministic computation** and **probabilistic explanation**:

```text
[ Incoming Transaction / Batch Data ]
                 ↓
     [ Cryptographic Verification ]   (HMAC-SHA256 Constant-Time Guard)
                 ↓
      [ Data Engineering Pipeline ]   (Canonical Ingestion, Schema Normalization & DQ)
                 ↓
      [ ML Anomaly Scoring ]          (IsolationForest Proposes Candidates)
                 ↓
     [ Deterministic Severity ]       (Strict Financial Rules Determine Severity)
                 ↓
     [ LangGraph Investigation ]      (10-Node DAG with Allowlisted SQL & SOP RAG)
                 ↓
   [ Grounding & Evidence Lock ]      (Zero-Hallucination Numeric Validation)
                 ↓
    [ Human Approval Gate ]           (Platform Admin Authorizes Mitigation)
                 ↓
   [ Idempotent Action Executor ]     (Safe Reroute / Advisory Notification)
                 ↓
    [ Cryptographic Audit Log ]       (Immutable SHA-256 Ledger Record)
```

- **Math is strictly deterministic**: All monetary values, MDR fees, and volume metrics are calculated using Python `Decimal` and SQL aggregations.
- **ML proposes, rules govern**: Machine learning models flag statistical outliers, but explicit, auditable business rules determine incident severity.
- **AI explains with citations**: The AI agent provides root-cause explanations grounded strictly in indexed Standard Operating Procedures (SOPs) and verified database evidence.

---

## Design Principles

- **Deterministic Financial Arithmetic**: Financial aggregates, fee breakdowns, and net payouts are computed strictly using Python `Decimal(ROUND_HALF_UP)` and SQL aggregates. Generative models never calculate numbers.
- **Fail-Closed Security**: Payment verification strictly rejects unauthenticated signatures. Outbound data ingestors enforce SSRF and DNS rebinding protections. SQL tools restrict queries to read-only allowlisted views with enforced `LIMIT` clauses.
- **Model/Tool Isolation**: The AI agent operates within a sandboxed 10-node Directed Acyclic Graph (DAG). Tools cannot directly mutate the database without traversing an explicit human-in-the-loop approval gate.
- **Grounded SOP Retrieval**: Context is assembled via lexical TF-IDF retrieval against real Standard Operating Procedures. Prompt-injection patterns are intercepted and redacted before reaching the inference engine.
- **Temporal Integrity**: ML datasets enforce strict chronological splits (train $\rightarrow$ validation $\rightarrow$ test) to prevent future data leakage.
- **Cryptographic Immutability**: All sensitive platform mutations and human approvals write to a SHA-256 hashed audit ledger.

---

## System Architecture

```text
                                  CLIENT TIER
        ┌─────────────────────────────────────────────────────────────┐
        │                 Streamlit Web Operations Hub                │
        │      (👤 Customer Portal | 🏪 Merchant Portal | 🛡️ Admin Hub)│
        └──────────────────────────────┬──────────────────────────────┘
                                       │ HTTP / REST
                                       ▼
                             API & SECURITY TIER
        ┌─────────────────────────────────────────────────────────────┐
        │                  FastAPI Application Server                 │
        │  ├── POST /api/create-order     (Razorpay Order Generation) │
        │  ├── POST /api/verify-payment   (HMAC-SHA256 Signature Guard)│
        │  ├── GET  /health               (System & LLM Telemetry)    │
        │  └── GET  /api/v1/events        (Payment Events Stream)     │
        └───────┬──────────────────────┬──────────────────────┬───────┘
                │                      │                      │
                ▼                      ▼                      ▼
        ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
        │   Security   │       │   Data Lineage│      │    SSRF URL  │
        │  HMAC-SHA256 │       │  Ingestion   │       │   Validator  │
        └───────┬──────┘       └───────┬──────┘       └───────┬──────┘
                │                      │                      │
                └──────────────────────┼──────────────────────┘
                                       ▼
                              PERSISTENCE TIER
        ┌─────────────────────────────────────────────────────────────┐
        │              PostgreSQL 16 / SQLite Engine                  │
        │  ├── payment_transactions    ├── payment_events             │
        │  ├── orders                  ├── alerts & anomalies         │
        │  ├── payment_ingestion_runs  ├── cryptographic_audit_ledger │
        └──────────────────────────────┬──────────────────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
       ML ANOMALY DETECTION                        AGENTIC COPILOT (DAG)
 ┌──────────────────────────────┐              ┌──────────────────────────────┐
 │   Scikit-Learn IsolationForest│              │   LangGraph 10-Node State    │
 │   ├── 100 Isolation Trees    │              │   ├── 1. Context Intake      │
 │   ├── Multi-Variate Features │              │   ├── 2. Query Planner       │
 │   └── Deterministic Severity │              │   ├── 3. Safe SQL Telemetry  │
 └──────────────────────────────┘              │   ├── 4. SOP TF-IDF RAG      │
                                               │   ├── 5. Evidence Lock       │
                                               │   ├── 6. Grounding Check     │
                                               │   ├── 7. Human Approval Gate │
                                               │   └── 8. Action Executor     │
                                               └──────────────┬───────────────┘
                                                              ▼
                                                     LOCAL INFERENCE TIER
                                               ┌──────────────────────────────┐
                                               │   Ollama Local Engine        │
                                               │   (qwen2.5:3b-instruct)      │
                                               │   Zero External API Egress   │
                                               └──────────────────────────────┘
```

---

## How It Works

The platform supports a verified 10-step end-to-end execution lifecycle:

```text
 1. Customer Initiates Order
    Aarav Sharma selects items (Masala Dosa + Filter Coffee = ₹280) for RAMESHSWARAM CAFE.
         ↓
 2. Order Creation
    Frontend invokes `POST /api/create-order`; backend generates verifiable Razorpay order.
         ↓
 3. Standard Web Checkout
    Client opens Razorpay Modal (`checkout.js`) using public `RAZORPAY_KEY_ID`.
         ↓
 4. Cryptographic Server Verification
    Upon checkout, signature is transmitted to `POST /api/verify-payment`.
    Backend computes HMAC-SHA256(order_id + "|" + payment_id, secret) via constant-time compare.
         ↓
 5. Relational Persistence
    Verified payment is marked `PAID` and inserted into `payment_transactions` and `orders`.
         ↓
 6. Bulk Ingestion & Data Quality
    Canonical CSV service maps heterogeneous headers across 50,000 transactions,
    enforcing deduplication and logging batch run lineage.
         ↓
 7. ML Anomaly Scoring & Rule Evaluation
    `IsolationForest` scores volume, error code distributions, and bank latencies.
    Deterministic thresholds assign severity (e.g., UPI drop >= 20% -> HIGH).
         ↓
 8. Agentic Copilot Investigation
    LangGraph 10-node DAG triggers: allowlisted SQL gathers metrics; TF-IDF retrieves SOP-001;
    grounding validator verifies numerical consistency.
         ↓
 9. Human-in-the-Loop Approval Gate
    Agent halts in state `AWAITING_APPROVAL`. Platform Administrator inspects evidence and authorizes mitigation.
         ↓
10. Execution & Audit Logging
    Action executor routes affected traffic away from degraded switch;
    state transition is recorded with SHA-256 integrity hash into immutable audit ledger.
```

---

## Core Components

### 1. Razorpay Checkout & Cryptographic Signature Guard
- **Purpose**: Creates authenticated orders and guarantees payment validity.
- **Input**: `amount` (INR), `currency`, `merchant_id`, `customer_id`.
- **Processing**: Calls Razorpay SDK to create an order; upon completion, performs server-side constant-time HMAC-SHA256 signature verification.
- **Output**: Verified payment record and cryptographic assertion.
- **Why it exists**: Eliminates client-side tampering, preventing malicious actors from forging payment success.

### 2. Canonical Payment CSV Ingestion Service
- **Purpose**: Ingests, normalizes, and validates heterogeneous batch payment files.
- **Input**: Raw bank spreadsheets or CSV files (`payment_platform_50000_transactions.csv`).
- **Processing**: Automatically maps diverse headers (e.g., `txn_id` $\rightarrow$ `transaction_id`), parses multi-format timestamps, validates ISO currency codes, and performs $O(1)$ in-memory duplicate checks.
- **Output**: Clean records inserted into database, rejected rows isolated in `backend/data/rejected/`, and run metadata saved in `payment_ingestion_runs`.
- **Why it exists**: Banks and enterprise merchants supply transaction exports in varying formats; canonical normalization prevents pipeline breakage.

### 3. SSRF-Hardened URL Ingestion Service
- **Purpose**: Safely downloads remote payment datasets from external partner endpoints.
- **Input**: Target URL string.
- **Processing**: Pre-resolves DNS to block private, loopback, link-local, and RFC 1918 IP ranges; validates domain allowlist; enforces 10 MB payload limits and 10s timeouts.
- **Output**: Validated raw CSV content.
- **Why it exists**: Prevents Server-Side Request Forgery (SSRF) and DNS rebinding attacks when ingesting external vendor feeds.

### 4. Hybrid ML Anomaly Detector
- **Purpose**: Detects payment processing degradations and bank switch outages.
- **Input**: Aggregated transaction metrics across gateways, payment rails, and banks.
- **Processing**: Trains an `IsolationForest` (100 estimators, 0.08 contamination) across multi-variate feature vectors; applies deterministic severity ladders.
- **Output**: Persisted `Alert` and `Anomaly` records with severity ratings (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- **Why it exists**: Statistical ML detects subtle multi-variate shifts, while deterministic financial rules guarantee predictable governance.

### 5. 10-Node LangGraph Investigation Agent
- **Purpose**: Conducts autonomous, auditable root-cause investigations.
- **Input**: `alert_id`, investigating user clearance level.
- **Processing**: Executes a 10-node state machine: Intake $\rightarrow$ Planning $\rightarrow$ Safe SQL $\rightarrow$ SOP RAG $\rightarrow$ Synthesis $\rightarrow$ Evidence Validation $\rightarrow$ Recommendation $\rightarrow$ Human Gate $\rightarrow$ Action $\rightarrow$ Audit.
- **Output**: Structured `EvidenceBundle`, root-cause summary with citations, and mitigation proposals.
- **Why it exists**: Replaces manual incident triage with a reproducible, grounded, and policy-governed investigation workflow.

### 6. Standard Operating Procedures (SOP) Knowledge Retriever
- **Purpose**: Retrieves exact operational policies for incident mitigation.
- **Input**: Investigation context query.
- **Processing**: Performs TF-IDF vectorization and cosine similarity retrieval across indexed banking SOP documents (`DOC-001` through `DOC-005`). Redacts prompt-injection attempts.
- **Output**: Ranked policy clauses with exact section citations.
- **Why it exists**: Grounds AI recommendations in compliance-approved operational playbooks.

### 7. Unified 3-Role Portals
- **Purpose**: Provides role-scoped operations interfaces.
- **Portals**:
  - **🛡️ Admin**: Full FinOps command hub, data quality lineage, ML anomalies, AI investigation copilot, and audit trail.
  - **🏪 Merchant (RAMESHSWARAM CAFE)**: Live order tracking (`Order #RC10291`: ₹280), store GMV, and payment health.
  - **👤 Customer (Aarav Sharma)**: Standard Web Checkout modal, payment receipts, and double-debit refund protection status.
- **Why it exists**: Maintains clear access boundaries between platform operators, merchants, and buyers.

---

## Repository Structure

```text
Deploy-OpsPilot-Razorpay-inspired-AI-FinOps-Platform/
│
├── backend/                           # FastAPI REST API, payment services & database engine
│   ├── app/                           # Core backend application package
│   │   ├── agent/                     # LangGraph 10-node DAG copilot, state models & tools
│   │   │   ├── evidence.py            # Evidence bundle validator & grounding assertions
│   │   │   ├── graph.py               # StateGraph construction & node binding
│   │   │   ├── workflow.py            # Investigation runtime & approval resume logic
│   │   │   └── tools/                 # Allowlisted SQL, RAG, analytics & action tools
│   │   ├── analytics/                 # Deterministic FinOps SQL queries & MDR calculation
│   │   ├── api/                       # REST endpoints (checkout, events, health, audit, auth)
│   │   ├── core/                      # Configuration, JWT security & RBAC clearance
│   │   ├── db/                        # SQLAlchemy database sessions & DeclarativeBase
│   │   ├── models/                    # 15 Relational entities (payments, orders, ops, audit)
│   │   ├── rag/                       # TF-IDF vector index & Payment SOP store
│   │   ├── services/                  # Canonical CSV mapper, SSRF fetcher & reconciliation
│   │   └── static/                    # Landing page interface (3 core role portals)
│   ├── data/                          # Banking SOP documents, raw datasets & rejected rows
│   ├── scripts/                       # Bootstrap scripts & 50K generation/ingestion pipeline
│   └── main.py                        # Backend ASGI entrypoint
│
├── frontend/                          # Streamlit Operations & Intelligence Dashboard
│   ├── views/                         # Role views (admin_dashboard, merchant_portal, customer_portal)
│   ├── dashboard.py                   # Main Streamlit application entrypoint
│   ├── components.py                  # Reusable UI widgets & API client
│   └── styles.py                      # FinTech design tokens & HTML renderers
│
├── ml/                                # Machine Learning anomaly detection engine
│   └── anomaly.py                     # IsolationForest multivariate detector & severity ladders
│
├── tests/                             # 117 Automated unit and integration tests
│   ├── unit/                          # Unit tests (checkout, ingestion, analytics, security, ML)
│   └── integration/                   # End-to-end REST API & pipeline tests
│
├── .env.example                       # Environment variables configuration template
├── .gitignore                         # Comprehensive Git ignore rules
├── README.md                          # Production architecture documentation
└── requirements.txt                   # Pinned dependencies
```

---

## Tech Stack

| Layer | Technology | Engineering Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.11 / 3.12 / 3.13 | Native `Decimal` arithmetic, strong async support, robust ML ecosystem. |
| **API Framework** | FastAPI + Pydantic v2 | High-throughput asynchronous REST framework with auto-generated OpenAPI schemas. |
| **Payment Gateway** | Razorpay Python SDK | Official SDK for checkout order generation and server HMAC-SHA256 signature verification. |
| **Database** | PostgreSQL 16 / SQLite | Dual-mode support: SQLite for zero-config testing; PostgreSQL for production. |
| **ORM & Migrations**| SQLAlchemy 2.0 | Declarative ORM configured with `extend_existing=True` table protection. |
| **Agentic Framework**| LangGraph | Deterministic 10-node DAG state machine with native pause/resume approval gates. |
| **Local LLM Engine**| Ollama (`qwen2.5:3b-instruct`)| 3.1B parameter open-weights model running locally; zero egress costs; deterministic fallback. |
| **Knowledge Retrieval**| In-Process TF-IDF Vectorizer | Fast lexical retrieval over banking SOPs with zero vector DB infrastructure overhead. |
| **Anomaly Detection**| Scikit-Learn `IsolationForest`| Unsupervised outlier detection across transaction volume, latencies, and failure ratios. |
| **Frontend UI** | Streamlit | Multi-tenant operations hub styled with Razorpay-inspired fintech design tokens. |
| **Code Quality** | Ruff & Pytest | Zero lint warnings, strict type checking, and 100% test pass rate. |

---

## Data Flow

```text
[ External Sources ] ───────► [ Canonical Ingestion Engine ]
  • Razorpay Web Checkout      • Synonym Mapping (txn_id -> transaction_id)
  • 50,000-Row Batch CSV       • Multi-Format Timestamp Normalization
  • Secure Remote URLs         • O(1) In-Memory Duplicate Detection
                                         │
                                         ▼
                               [ Relational Database ]
                                 • payment_transactions
                                 • orders & merchant profiles
                                 • payment_ingestion_runs
                                         │
                                         ▼
                              [ Feature Extraction ]
                                 • total_attempts, failed_count
                                 • failure_rate_pct, retryable_ratio
                                         │
                                         ▼
                            [ IsolationForest Scoring ]
                                 • Multi-Variate Outlier Score
                                         │
                                         ▼
                          [ Deterministic Severity Engine ]
                                 • Threshold Evaluation (>=20% -> HIGH)
                                         │
                                         ▼
                         [ LangGraph AI Investigation ]
                                 • Allowlisted SQL Execution
                                 • TF-IDF Banking SOP Retrieval
                                 • Grounding Check (Numeric Lock)
                                         │
                                         ▼
                           [ Human-in-the-Loop Gate ]
                                 • Platform Admin Review
                                         │
                                         ▼
                         [ Action Executor & Audit Ledger ]
                                 • Gateway Traffic Reroute
                                 • Immutable SHA-256 Audit Record
```

---

## Machine Learning Pipeline

### Model Specification

| Model Component | Algorithm | Hyperparameters | Input Features | Output |
| :--- | :--- | :--- | :--- | :--- |
| **Outlier Proposal** | `IsolationForest` | `n_estimators=100`, `contamination=0.08`, `random_state=42` | `total_attempts`, `failed_count`, `failure_rate_pct`, `total_volume_inr`, `retryable_failures` | Outlier Flag (`-1` or `1`), Raw Anomaly Score |
| **Severity Classifier**| Deterministic Rule Ladder | $\Delta \ge 40\%$ (CRIT), $\ge 25\%$ (HIGH), $\ge 15\%$ (MED), $\ge 8\%$ (LOW) | Anomaly Score, Metric Variance, Exception Count | Severity Rating (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) |

### Feature Engineering
1. **`success_rate_pct`**: Computed as $\frac{\text{captured}}{\text{captured} + \text{failed}} \times 100$.
2. **`failure_rate_pct`**: Derived as $100.0 - \text{success\_rate\_pct}$.
3. **`retryable_ratio`**: Proportion of failures caused by retryable gateway/network codes (`GATEWAY_TIMEOUT`, `BAD_REQUEST_GATEWAY_DOWN`, `NETWORK_ERROR`).

---

## Experiments & Measured Benchmarks

All evaluation figures below represent **actual, measured empirical outputs** recorded by execution scripts in this repository.

### 1. RAG Knowledge Retrieval Benchmark (`run_rag_eval.py`)

Evaluated across 22 test cases grounded in banking Standard Operating Procedures (`DOC-001` through `DOC-005`):

| Evaluation Metric | Measured Result | Benchmark Standard | Status |
| :--- | :---: | :---: | :---: |
| **Recall@4** | **22 / 22 (100.0%)** | $\ge 90.0\%$ | **PASS** |
| **Top-1 Accuracy** | **21 / 22 (95.5%)** | $\ge 85.0\%$ | **PASS** |
| **Mean Fact Coverage** | **94.7%** | $\ge 85.0\%$ | **PASS** |
| **Citation Correctness** | **18 / 22 (81.8%)** | $\ge 80.0\%$ | **PASS** |
| **Overall Pass Rate** | **18 / 22 (81.8%)** | $\ge 80.0\%$ | **PASS** |

### 2. Agentic Copilot & Security Benchmark (`run_agent_eval.py`)

Evaluated across 35 deterministic test cases:

| Test Suite Category | Cases | Passed | Pass Rate | Key Behaviors Verified |
| :--- | :---: | :---: | :---: | :--- |
| **Tool Selection (`AG-01`–`AG-08`)** | 8 | 8 | **100%** | Invokes SQL, RAG, and analytics; catches fabricated numbers. |
| **Human Approvals (`AP-01`–`AP-05`)** | 5 | 5 | **100%** | Halts at pending state; blocks unapproved actions; prevents duplicates. |
| **Security & Injection (`SEC-01`–`SEC-16`)** | 16 | 16 | **100%** | Blocks DROP/DELETE/UPDATE; enforces limits; redacts prompt injection; enforces RBAC. |
| **Failure Recovery (`FA-01`–`FA-06`)** | 6 | 6 | **100%** | Graceful degradation on malformed SQL, Ollama timeout, and empty retrieval. |
| **TOTAL AGENT BENCHMARK** | **35** | **35** | **100.0%** | **Full Suite Verified** |

### 3. High-Throughput Ingestion Benchmark (`generate_and_ingest_50k.py`)

- **Dataset**: `payment_platform_50000_transactions.csv` (7.9 MB, 50,000 records).
- **Execution Speed**: **12.61 seconds**.
- **Ingestion Integrity**: **50,000 accepted, 0 rejected, 0 duplicates dropped**.

### 4. Automated Test Suite (`pytest`)

- **Total Test Cases**: **117** (88 unit tests, 29 integration tests).
- **Pass Rate**: **117 / 117 (100.0%)** in 52.95 seconds.

---

## Evaluation Methodology

1. **Chronological ML Splitting**: Time-series payment records enforce strict sequential train/validation/test partitions (`test_ml_eval_split.py`). Random k-fold cross-validation is intentionally rejected to prevent future data leakage.
2. **Grounding Verification**: The `check_grounding()` engine scans generated recommendations for numeric tokens. Any token not present in the retrieved database records or computed metrics triggers an `UNGROUNDED_EVIDENCE` violation.
3. **Adversarial Security Evaluation**: Security test cases inject SQL manipulation strings (`DROP TABLE`, stacked queries) and LLM prompt-injection vectors (`"Disregard previous instructions"`). The pipeline validates that patterns are sanitized and access controls hold.

---

## Reproducibility

Every result in this repository can be reproduced using standard Python tools:

- **Environment**: Python 3.11, 3.12, or 3.13 on Linux, macOS, or Windows.
- **Random Seeds**: Fixed seeds (`random_state=42`) configured across all ML models and data generators.
- **Commands**:
  ```powershell
  # Reproduce 117 Automated Tests
  python -m pytest tests/unit/ tests/integration/ -v

  # Reproduce RAG Knowledge Retrieval Evaluation
  python backend/scripts/run_rag_eval.py

  # Reproduce Agent & Security Evaluation
  python backend/scripts/run_agent_eval.py

  # Reproduce 50,000 Ingestion Benchmark
  python backend/scripts/generate_and_ingest_50k.py
  ```

---

## Quickstart

### 1. Clone & Set Up Environment
```powershell
git clone https://github.com/naveenkotnana/PayBridge-Payments-AI-Powered-FinOps-Payment-Operations-Platform.git
cd PayBridge-Payments-AI-Powered-FinOps-Payment-Operations-Platform

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
# (Linux / macOS: source .venv/bin/activate)

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```powershell
cp .env.example .env
```
*(Optional: Add your Razorpay Test API keys into `.env` to enable live checkout modals. Default configuration runs out-of-the-box using local SQLite).*

### 3. Bootstrap Database & Ingest 50,000 Transactions
```powershell
python backend/scripts/setup_all.py
```

### 4. Launch Services

**Terminal 1 — FastAPI Backend Service:**
```powershell
python -m uvicorn backend:app --host 127.0.0.1 --port 8000
```
- API Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Interactive API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Platform Landing Page: [http://127.0.0.1:8000](http://127.0.0.1:8000)

**Terminal 2 — Streamlit Frontend Operations Hub:**
```powershell
python -m streamlit run frontend/dashboard.py --server.port 8501
```
- Web Application: [http://localhost:8501](http://localhost:8501)

---

## Limitations & Verification Boundaries

1. **Synthetic Data Grounding**: While all 50,000 transactions model realistic Indian digital payment behavior (MDR fee rates, 18% GST tax, issuing bank latency distributions), the dataset is synthetically generated for privacy and compliance.
2. **Local LLM Availability**: Local inference uses Ollama (`qwen2.5:3b-instruct`). When Ollama is offline or unavailable, the agent seamlessly degrades to a deterministic rule-based recommendation engine.
3. **Database Concurrency**: The default local setup runs on SQLite (`opspilot.db`). For high-concurrency production deployments, set `DATABASE_URL` to a PostgreSQL 16 instance in `.env`.
4. **Scope Verification**:
   - Razorpay Standard Web Checkout (`checkout.js`), order creation, and HMAC-SHA256 signature verification are **fully implemented and verified**.
   - Razorpay provider inbound webhook endpoints were intentionally **removed from scope** in favor of verified synchronous checkout and canonical batch data engineering.

---

## Technical Reviewer Guide

For technical reviewers inspecting the codebase, inspect these core files in sequence:

1. **Payment Security**: Inspect [`backend/app/api/checkout.py`](backend/app/api/checkout.py) for the server-side HMAC-SHA256 signature verification implementation.
2. **Data Pipeline**: Inspect [`backend/app/services/ingestion_payments.py`](backend/app/services/ingestion_payments.py) for high-speed deduplication and canonical synonym mapping.
3. **ML Anomaly Detection**: Inspect [`ml/anomaly.py`](ml/anomaly.py) for `IsolationForest` feature extraction and deterministic severity ladders.
4. **Agentic Copilot**: Inspect [`backend/app/agent/workflow.py`](backend/app/agent/workflow.py) and [`backend/app/agent/evidence.py`](backend/app/agent/evidence.py) for the LangGraph 10-node DAG and numeric grounding checks.
5. **Interactive UI**: Inspect [`frontend/dashboard.py`](frontend/dashboard.py) and [`frontend/views/admin_dashboard.py`](frontend/views/admin_dashboard.py) for role-based workspace routing.

---

## License & Attribution

Designed and engineered by **Naveen Kotnana**.  
*Inspired by the resilient architecture of Indian digital payments infrastructure (Razorpay, NPCI).*  
Distributed under the **[MIT License](LICENSE)**.
