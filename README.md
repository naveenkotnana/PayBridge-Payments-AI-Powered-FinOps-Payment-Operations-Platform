# ⚡ Razorpay-Inspired AI Payments — Intelligent Payment Operations & Financial Intelligence Platform

<p align="center">
  <img src="assets/operations_overview.png" alt="Razorpay-Inspired AI Payments Operations Overview" width="900" style="border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);" />
</p>

<p align="center">
  <strong>An Enterprise-Grade Payment Operations Platform Featuring Real-Time Bank Switch Observability, Event-Driven Ingestion, Deterministic Financial Reconciliation, and Sandboxed Local AI Agent Investigation</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-Principal_Fintech_Design-00875A?style=for-the-badge&logo=shield&logoColor=white" alt="Architecture" />
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/PostgreSQL-16%20%2F%20SQLite-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/LangGraph-10_Node_DAG-FF6F00?style=for-the-badge" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Local_LLM-Ollama_Qwen2.5-000000?style=for-the-badge" alt="Ollama" />
  <img src="https://img.shields.io/badge/Tests-88%20PASSED%20%7C%20100%25-brightgreen?style=for-the-badge" alt="Tests" />
  <img src="https://img.shields.io/badge/Code_Style-Ruff_0_Errors-blueviolet?style=for-the-badge" alt="Ruff" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License" />
</p>

> [!NOTE]
> **Independent Portfolio Showcase**: This platform is an independent technical portfolio project engineered by **Naveen Kotnana**, inspired by Razorpay's Indian fintech design language, multi-bank switch routing, and high-throughput payment operations. It is **not** an official Razorpay product.
> 
> **Zero Paid API Overhead & Complete Data Privacy**: All customer profiles, transaction streams, bank latencies, and settlement records are **100% synthetically generated** and grounded in real-world Indian digital commerce benchmarks. All AI agent inference runs locally via **Ollama** (`qwen2.5:3b-instruct`) with zero external cloud egress. When Ollama is offline, a deterministic rule-based fallback seamlessly takes over.

---

## 🎯 Executive Overview & Engineering Pitch

> ### 💡 The 3% Problem
> **What happens when SBI UPI drops by just 3% during a Friday evening flash sale?**  
> **₹50 Lakhs in failed checkouts, panicking customers, and blind order cancellations.**
>
> When high-scale payment gateways process millions of transactions across heterogeneous core banking switches, even minor upstream latency surges trigger catastrophic merchant fulfillment holds. This platform demonstrates how to build an **autonomous payment operations and financial intelligence engine** that detects switch degradations in real time, alerts merchants to pause fulfillment, and automates root-cause investigations with zero-hallucination deterministic math.

In modern digital economies, payment aggregators handle billions of rupees across heterogeneous issuing bank switches (SBI, HDFC, ICICI, Axis, Kotak) and payment rails (UPI, Credit/Debit Cards, Net Banking, Wallets). When an issuing bank switch degrades, even a **1.5% drop in success rate** translates to tens of lakhs in failed transactions, merchant panic, customer double-debit confusion, and erroneous order fulfillment holds.

**OpsPilot Payments** bridges the gap between raw database transactions and operational financial intelligence:
1. **Real-Time Bank Switch Telemetry**: Distinguishes upstream Core Banking switch timeouts from gateway aggregator drops and customer drop-offs.
2. **Event-Driven Ingestion Engine**: Accepts multi-format CSV files with canonical column mapping, Razorpay Test Mode webhooks with HMAC-SHA256 verification, and external URLs with SSRF protection.
3. **Order Fulfillment Advisories**: Real-time webhook guards advising merchants to hold fulfillment for pending payments until final bank verification is established.
4. **Deterministic Math & Zero Financial Hallucination**: Generative LLMs **never** perform financial calculations. All fee structures, MDRs, GST taxes, net payouts, and blast radiuses execute strictly via SQL window functions and Python `Decimal(ROUND_HALF_UP)`.
5. **Sandboxed AI Investigation Copilot**: A 10-node **LangGraph state machine** inspects allowlisted SQL queries, cross-references Payment Standard Operating Procedures (SOPs), calculates exposure, and stops at an explicit human approval gate before triggering high-impact operational mitigations.
6. **Real-World Enterprise Scale**: Pre-seeded with 10 premier Indian digital commerce brands (**Swiggy**, **Zomato**, **Zepto**, **CRED**, **Blinkit**, **Flipkart**, **BookMyShow**, **Nykaa**, **MakeMyTrip**, **Tata Neu**) and 600+ authentic customer profiles.

---

## 💼 Recruiter & Hiring Manager Highlights

| Engineering Competency | How It Is Demonstrated in This Project |
| :--- | :--- |
| **Distributed Systems & Event Ingestion** | Event-driven pipeline handling idempotency keys, out-of-order event reconciliation, HMAC-SHA256 signature verification, and state machine validation. |
| **Data Engineering & Lineage** | Multi-schema payment CSV mapper with deterministic column synonyms, timestamp parsing, duplicate isolation, rejected record reporting, and run lineage. |
| **Security & SSRF Hardening** | Outbound URL ingestion engine with DNS rebinding protection, RFC 1918 private IP blocks, domain allowlisting, and 10 MB payload limits. |
| **Domain-Specific Fintech Architecture** | Indian payment rails (UPI / NPCI, Cards, NetBanking), MDR fee calculation ($`\text{fee} + \text{18% GST}`$), daily settlement batches ($`\text{T+1}`$ / $`\text{T+2}`$), UTR reconciliation, and chargebacks. |
| **Agentic AI & State Machines** | 10-node Directed Acyclic Graph (DAG) using **LangGraph**, RAG retrieval over Standard Operating Procedures (SOPs), prompt-injection guardrails, and human approval gates. |
| **Deterministic Financial Modeling** | Zero hallucination guarantee: Python `Decimal` and SQL aggregation handle all financial sums; LLM strictly provides root-cause explanations with citations. |
| **Full-Stack & UX Engineering** | Multi-tenant RBAC with 4 isolated role portals (Customer, Merchant, Admin, AI Operations) styled with Razorpay's modern Indian fintech design language. |
| **System Reliability & Hardware Budget** | High-performance FastAPI backend, zero-setup dual-mode database (SQLite/PostgreSQL 16), and local Ollama inference optimized for an **8 GB RAM** budget. |

---

## 📑 Table of Contents
1. [Role-Based Workspaces & Architecture](#-1-role-based-workspaces--architecture)
2. [Interactive SBI UPI Live Demonstration](#-2-interactive-sbi-upi-live-demonstration)
3. [System Architecture & Ingestion Pipeline](#-3-system-architecture--ingestion-pipeline)
4. [Enterprise Payment Ingestion & Webhooks](#-4-enterprise-payment-ingestion--webhooks)
5. [Real-World Enterprise Dataset (500+ Indian Profiles)](#-5-real-world-enterprise-dataset-500-indian-profiles)
6. [Deterministic Financial Math & Strict Evidence Rules](#-6-deterministic-financial-math--strict-evidence-rules)
7. [Payment Operations Anomaly Detection Engine](#-7-payment-operations-anomaly-detection-engine)
8. [Standard Operating Procedures (RAG Knowledge Base)](#-8-standard-operating-procedures-rag-knowledge-base)
9. [Technology Stack & Rationale](#-9-technology-stack--rationale)
10. [Quickstart & Local Setup Guide](#-10-quickstart--local-setup-guide)
11. [Default Authentication Credentials (RBAC Matrix)](#-11-default-authentication-credentials-rbac-matrix)
12. [Verification, Linting & Testing Suites](#-12-verification-linting--testing-suites)
13. [Repository Structure](#-13-repository-structure)
14. [License & Attribution](#-14-license--attribution)

---

## 🏢 1. Role-Based Workspaces & Architecture

The application enforces strict role-based navigation where each authenticated user accesses only their authorized view:

```
                            ┌─────────────────────────────────────────┐
                            │    Fintech Authentication Gateway       │
                            │      (Multi-Role Portal Selector)       │
                            └────────────────────┬────────────────────┘
                                                 │
         ┌───────────────────────┬───────────────┴───────────────┬───────────────────────┐
         ▼                       ▼                               ▼                       ▼
┌──────────────────┐   ┌───────────────────┐           ┌───────────────────┐   ┌───────────────────┐
│   Workspace 1    │   │    Workspace 2    │           │    Workspace 3    │   │    Workspace 4    │
│ Customer Portal  │   │  Merchant Portal  │           │  Admin Dashboard  │   │ AI Investigation  │
│  (Aarav Sharma)  │   │  (Swiggy India)   │           │ (Platform Admin)  │   │ (FinOps Analyst)  │
├──────────────────┤   ├───────────────────┤           ├───────────────────┤   ├───────────────────┤
│• Customer Home   │   │• Merchant Overview│           │• Executive Overview│  │• Anomaly Triage   │
│• My Transactions │   │• Scoped Txn Stream│           │• Payment Monitoring│  │• Evidence Locker  │
│• 5-Step Timeline │   │• Fulfillment Alerts│          │• Bank Switch Health│  │• Root-Cause Citations│
│• Verified Alerts │   │• Bank SR Slicing  │           │• Webhook & Pipeline│  │• Human Approvals  │
└──────────────────┘   └───────────────────┘           └───────────────────┘   └───────────────────┘
```

---

## 🎬 2. Interactive SBI UPI Live Demonstration

The platform includes a 6-step interactive walkthrough that mirrors a real-world payment incident:

```
[Step 1: Payment Initiated] ──> Aarav Sharma initiates ₹2,500 food order on Swiggy via SBI UPI.
         │
[Step 2: Delayed Bank Webhook] ─> SBI Core Banking timeout causes transaction to stall in PENDING.
         │
[Step 3: Fulfillment Hold] ───> Swiggy dashboard receives advisory: "Do not dispatch order yet".
         │
[Step 4: Incident Clustering] ──> System correlates 42 simultaneous SBI failures; flags ₹1,05,000 exposure.
         │
[Step 5: AI Root Cause] ───────> Agent attributes failure to SBI Core Switch latency (4,250 ms vs 450 ms).
         │
[Step 6: Verified Resolution] ──> Webhook resolves, status flips to CAPTURED, order is safely fulfilled.
```

---

## 🏗️ 3. System Architecture & Ingestion Pipeline

```mermaid
flowchart TD
    subgraph Ingestion ["Multi-Channel Ingestion Layer"]
        A1["Raw CSV Files<br>(Multi-Synonym Mapper)"] --> B["Canonical Validation & Lineage Engine"]
        A2["Razorpay Test Webhooks<br>(HMAC-SHA256 Verification)"] --> B
        A3["Secure External URLs<br>(SSRF Guard & Allowlist)"] --> B
        B -->|Rejected Rows| R["Rejected Records Report<br>(data/rejected/)"]
        B -->|Accepted Records| D[("PostgreSQL 16 / SQLite<br>(15 Relational Tables)")]
    end

    subgraph Analytics_Engine ["Deterministic Analytics & Telemetry"]
        D --> E["Deterministic SQL KPI Engine<br>(GMV, Success Rates, MDR Fees)"]
        D --> F["Multi-Bank Switch Telemetry<br>(SBI, HDFC, ICICI, Axis, Kotak)"]
        D --> G["Incident Correlation Engine<br>(Blast Radius & Merchant Exposure)"]
    end

    subgraph Agentic_Copilot ["LangGraph 10-Node Investigation Copilot"]
        G --> H["Node 1: Intake & Context Binding"]
        H --> I["Node 2: Dynamic Planner (Payment Queries)"]
        I --> J["Node 3: Allowlisted SQL Telemetry"]
        J --> K["Node 4: Payment SOP RAG Retrieval"]
        K --> L["Node 5: Payment Analytics Context"]
        L --> M["Node 6: Evidence Validator (Multi-Stream)"]
        M --> N["Node 7: Grounded Recommendation Generator"]
        N --> O{"Node 8: Human Approval Gate<br>(Level 2/3 Clearance Required)"}
        O -->|Awaiting Decision| P["State: PENDING_APPROVAL"]
        O -->|Approved| Q["Node 9: Action Executor"]
        Q --> S["Node 10: Cryptographic Audit Logger"]
    end

    subgraph Presentation ["Presentation Layer"]
        E & F & G & S --> T["FastAPI REST Backend (:8000)"]
        T --> U["Streamlit Role-Based Workspaces (:8501)"]
    end
```

---

## ⚡ 4. Enterprise Payment Ingestion & Webhooks

### A. Canonical Payment CSV Ingestion
- **Deterministic Synonym Auto-Detection**: Dynamically maps varied column names across banks and aggregators:
  - `txn_id`, `payment_reference`, `reference_id` ➔ `payment_id`
  - `txn_amount`, `gross_amount`, `transaction_amount` ➔ `amount`
  - `payment_status`, `txn_status` ➔ `status`
  - `payment_method`, `pay_mode` ➔ `method`
- **Data Lineage Tracking**: Every run generates a unique `run_id` (e.g., `RUN-20261105-a1b2c3`), tracking records received, accepted, rejected, and duplicated in `payment_ingestion_runs`.
- **Row-Level Rejection Audit**: Invalid records (non-positive amounts, malformed timestamps, unsupported currencies) are written to structured rejected CSVs in `data/rejected/` with explicit rejection reasons.

### B. Razorpay Test Mode Webhook Gateway (`/api/v1/webhooks/razorpay`)
- **HMAC-SHA256 Signature Verification**: Computes cryptographic HMAC-SHA256 over raw request bytes using `RAZORPAY_WEBHOOK_SECRET` and validates against `X-Razorpay-Signature`.
- **Event Deduplication & Idempotency**: Enforces `idempotency_key` (`payment_id::event_type`) to safely ignore duplicate or out-of-order webhook deliveries.
- **Payment Lifecycle FSM**: Safely transitions transactions across `payment.authorized`, `payment.captured`, and `payment.failed`.

### C. Secure External URL Ingestion with SSRF Protection
- **Domain Allowlisting**: Strictly restricts outbound requests to trusted domains (`github.com`, `raw.githubusercontent.com`, `api.razorpay.com`, `npci.org.in`, `rbi.org.in`).
- **SSRF & DNS Rebinding Guard**: Resolves host DNS before connection and rejects private, loopback, link-local, and reserved IP ranges (RFC 1918, RFC 3927).
- **Resource Constraints**: Strict 10-second timeout and 10 MB payload cap prevent memory exhaustion.

---

## 📊 5. Real-World Enterprise Dataset (500+ Indian Profiles)

To provide an authentic fintech demonstration without breaching proprietary client data, the platform generates and maintains a comprehensive real-world dataset representing India's leading digital brands:

| Enterprise Merchant | Business Category | Sample Order Receipts | Volume | Gross Value |
| :--- | :--- | :--- | :--- | :--- |
| **Swiggy India** (`mid_swiggy_01`) | Food Delivery & Instamart | `SWIGGY-INSTAMART-84920`<br>`SWIGGY-FOOD-49120` | 99 txns | ₹1,78,958.47 |
| **Zomato Ltd** (`mid_zomato_02`) | Food Delivery & Dining | `ZOMATO-BIRYANI-49210`<br>`ZOMATO-GOLD-36100` | 109 txns | ₹2,00,828.00 |
| **Zepto Quick Commerce** (`mid_zepto_06`) | 10-Minute Groceries | `ZEPTO-10MIN-48192`<br>`ZEPTO-CAFE-78494` | 103 txns | ₹1,34,316.60 |
| **Dreamplug Technologies (CRED)** (`mid_cred_05`) | FinTech & Credit Card BillPay | `CRED-BILLPAY-HDFC-9912`<br>`CRED-STORE-48201` | 97 txns | ₹10,51,712.01 |
| **Blinkit Instant Commerce** (`mid_blinkit_07`) | Quick Grocery & Essentials | `BLINKIT-EXP-77401`<br>`BLINKIT-HEALTH-39102` | 119 txns | ₹1,34,837.23 |
| **Flipkart Commerce** (`mid_flipkart_03`) | E-Commerce & Electronics | `FK-BIGBILLION-29104`<br>`FK-ELECTRONICS-88561` | 109 txns | ₹10,93,834.69 |
| **BookMyShow Ticketing** (`mid_bookmyshow_04`) | Movies & Entertainment | `BMS-IMAX-TICKET-7201`<br>`BMS-CONCERT-49281` | 101 txns | ₹2,66,664.19 |
| **FSN E-Commerce (Nykaa)** (`mid_nykaa_08`) | Beauty & Fashion | `NYKAA-LUXE-51928`<br>`NYKAA-GLAM-38192` | 103 txns | ₹2,90,569.41 |
| **MakeMyTrip India** (`mid_makemytrip_09`) | Travel & Hospitality | `MMT-FLT-INDIGO-401`<br>`MMT-HOTEL-TAJ-9821` | 85 txns | ₹10,23,110.88 |
| **Tata Digital (Tata Neu)** (`mid_tataneu_10`) | Super App & Croma | `TATANEU-CROMA-84920`<br>`TATANEU-BB-39102` | 95 txns | ₹7,54,684.58 |
| **TOTAL SYNTHESIZED PLATFORM VOLUME** | — | — | **1,020 txns** | **₹52,29,516.06** |

---

## 📐 6. Deterministic Financial Math & Strict Evidence Rules

A fundamental design requirement of this platform is **zero financial hallucination**:

1. **Deterministic Decimal Arithmetic**: LLMs are strictly forbidden from performing mathematical calculations or currency additions. All gross volumes, MDR processing fees, GST taxes, net payouts, and incident financial exposures are calculated using Python `Decimal` with `ROUND_HALF_UP` or direct SQL aggregation:
   $$\text{Net Payout} = \text{Gross Amount} - \text{MDR Fee} - \text{GST Tax}$$
   $$\text{MDR Fee} = \text{Gross Amount} \times \text{Rate}_{\text{rail}}, \quad \text{GST Tax} = \text{MDR Fee} \times 0.18$$
2. **Strict Evidence Rules**:
   - The AI Copilot never invents unobserved transactions or imaginary error codes.
   - If telemetry data is insufficient, the system explicitly reports **"INSUFFICIENT EVIDENCE"** and halts.
   - Customers are never informed that funds were debited or refunded unless verified by a corresponding ledger record.
3. **Idempotent Ingestion**: Every payment event carries a unique idempotency key (`payment_id::event_type`). Duplicate events are acknowledged without duplicating financial balances.

---

## 🤖 7. Payment Operations Anomaly Detection Engine

The anomaly detection engine (`app/ml/anomaly.py`) bridges machine learning with deterministic financial governance:
- **Design Policy**: The **ML model proposes** (IsolationForest anomaly score), but **deterministic financial rules decide severity**. Severity is never determined by an LLM.
- **Detection Areas**:
  1. *UPI failure-rate spikes* ($`\ge 20\%`$ failure rate on UPI rails).
  2. *Bank-specific transaction failures* ($`\ge 25\%`$ failure rate on SBI, HDFC, ICICI, or Axis).
  3. *Gateway latency increases & timeouts* (accumulations of retryable errors: `BAD_REQUEST_GATEWAY_DOWN`, `GATEWAY_TIMEOUT`, `NETWORK_ERROR`).
  4. *Unusual transaction volume & drop-offs*.
  5. *Payment success-rate degradation*.
- **Structured Output**: Every detected anomaly produces an Anomaly ID, entity type, observed vs expected values, severity, ranked root-cause hypothesis, and recommended operational action.

---

## 📚 8. Standard Operating Procedures (RAG Knowledge Base)

The local RAG retrieval store indexes operational payment policies (`data/documents/`):
- **SOP-001**: *UPI Bank Switch Degradation and Auto-Reroute SOP* — Latency thresholds (>3000ms), dynamic rerouting triggers, and merchant advisory notifications.
- **SOP-002**: *Fulfillment Hold Policy for Pending Bank Debits* — Suspending order fulfillment for `BANK_DEBITED_PAYMENT_PENDING` to prevent double debits.
- **SOP-003**: *Payment Reconciliation & Settlement Discrepancy SOP* — Triage for MDR fee mismatches, missing UTR numbers, and delayed T+2 batches.
- **SOP-004**: *Payment Dispute & Chargeback SLA Management Policy* — Time-bound merchant evidence SLAs (7 days inquiry, 5 days chargeback).

---

## 🛠️ 9. Technology Stack & Rationale

| Layer | Technology | Engineering Rationale |
| :--- | :--- | :--- |
| **Backend API** | **FastAPI + Pydantic v2** | Asynchronous, typed REST framework with auto-generated OpenAPI Swagger documentation. |
| **Database** | **PostgreSQL 16 / SQLite** | Dual-mode support: zero-configuration SQLite for immediate local testing, and PostgreSQL for production. |
| **ORM & Migrations** | **SQLAlchemy 2.0 + Alembic** | Schema migrations across 15 relational tables with relationships and indexes. |
| **Agentic State Machine**| **LangGraph (LangChain)** | Explicit Directed Acyclic Graph (DAG) state machine with pause/resume approval gates. |
| **Local LLM Engine** | **Ollama (`qwen2.5:3b-instruct`)** | 3.1B parameter open-weights model running locally within 2 GB VRAM; zero paid API costs. |
| **Knowledge Retrieval** | **In-Process TF-IDF Vectorizer** | Zero-memory lexical search over Standard Operating Procedures (SOPs). |
| **User Interface** | **Streamlit** | Role-based navigation with Razorpay-inspired green/slate fintech styling and glassmorphism cards. |
| **Code Quality** | **Ruff, Pytest, Mypy** | Enforces zero linting warnings, strict typing, and full automated test suite passes. |

---

## ⚡ 10. Quickstart & Local Setup Guide

### System Requirements
- **Python**: 3.11, 3.12, or 3.13
- **Git**
- **RAM**: Minimum 4 GB (8 GB recommended)
- *(Optional)* **Ollama**: For local LLM inference (`ollama run qwen2.5:3b-instruct`)

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/naveenkotnana/Deploy-OpsPilot-Razorpay-inspired-AI-FinOps-Platform.git
cd Deploy-OpsPilot-Razorpay-inspired-AI-FinOps-Platform

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```
*(Default settings run instantly using local SQLite and rule fallback without external API keys).*

### 3. Initialize Database & Run Anomaly Detection
```bash
python scripts/setup_all.py
```

### 4. Launch Services

**Terminal 1 — FastAPI Backend Service:**
```bash
python -m uvicorn backend:app --host 127.0.0.1 --port 8000
```
*Interactive Swagger Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)*

**Terminal 2 — Streamlit Frontend Dashboard:**
```bash
python -m streamlit run frontend.py --server.port 8501
```
*Web Application: [http://localhost:8501](http://localhost:8501)*

---

## 🔑 11. Default Authentication Credentials (RBAC Matrix)

| Workspace Portal | Username | Password | Role | Scoped Context |
| :--- | :--- | :--- | :--- | :--- |
| **🛡️ Admin Command** | `admin` | `admin123` | `ADMIN` | Level 3 Platform Governance & Bank Switch Control |
| **🏪 Merchant Portal** | `merchant_swiggy` *(or `merchant`)* | `merchant123` | `MERCHANT` | Scoped to Swiggy India (`mid_swiggy_01`) |
| **👤 Customer Portal** | `customer_aarav` *(or `customer`)* | `customer123` | `CUSTOMER` | Scoped to Aarav Sharma (`cust_sw_aarav`) |
| **🤖 Operations & AI** | `analyst` | `analyst123` | `ANALYST` | Level 1 Clearance (Telemetry & Investigation) |
| **🤖 Operations & AI** | `manager` | `manager123` | `MANAGER` | Level 2 Clearance (Human Approval Authority) |

---

## 🧪 12. Verification, Linting & Testing Suites

```bash
# 1. Run all unit tests
python -m pytest tests/unit -v

# 2. Run integration tests
python -m pytest tests/integration -v

# 3. Run static code quality linter
python -m ruff check app dashboard tests scripts
```

### Verified Test Results
```text
================================== Test Summary ==================================
tests/unit/test_security_unit.py ................. [18 passed]
tests/unit/test_revenue.py ....................... [10 passed]
tests/unit/test_data_generator.py ................ [7 passed]
tests/unit/test_data_quality.py .................. [5 passed]
tests/unit/test_customer_config.py ............... [5 passed]
tests/unit/test_rag_store.py ..................... [5 passed]
tests/unit/test_action_tool.py ................... [5 passed]
tests/unit/test_validation.py .................... [7 passed]
tests/unit/test_webhook_gateway.py ............... [5 passed]
tests/unit/test_payment_csv_ingestion.py ......... [4 passed]
tests/unit/test_url_ingestion.py ................. [3 passed]
tests/unit/test_payment_anomalies.py ............. [2 passed]
tests/unit/test_api_ingestion_endpoints.py ....... [3 passed]
tests/unit/test_anomaly.py ....................... [3 passed]
tests/unit/test_batch_upload.py .................. [3 passed]
tests/unit/test_payment_simulator.py ............. [3 passed]
----------------------------------------------------------------------------------
Unit Test Suite Total:                             88 PASSED (100%)
Integration Test Suite Total:                      29 PASSED (100%)
Ruff Code Quality Audit:                           0 ERRORS (All checks passed)
```

---

## 📁 13. Repository Structure

```text
Deploy-OpsPilot-Razorpay-inspired-AI-FinOps-Platform/
├── app/
│   ├── agent/                 # LangGraph 10-node DAG copilot, state models & tools
│   ├── analytics/             # Deterministic payment analytics & named SQL query engine
│   ├── api/                   # FastAPI REST endpoints, Webhook Gateway & Ingestion APIs
│   │   ├── main.py            # Main API router, lifespan, and ingestion routes
│   │   └── webhooks.py        # Dedicated Razorpay Test Mode webhook gateway
│   ├── core/                  # RBAC configuration, JWT tokens, and logging
│   ├── db/                    # SQLAlchemy database sessions and Base model
│   ├── ml/                    # IsolationForest anomaly detection models & deterministic rules
│   ├── models/                # Domain entities (15 payment tables, lineage & audit models)
│   ├── rag/                   # In-process TF-IDF vector store & Payment SOP retrieval
│   └── services/              # Canonical CSV mapper, SSRF URL fetcher, and reconciliation
├── dashboard/
│   ├── components/            # Reusable Streamlit UI components & API bridge
│   ├── styles/                # Razorpay-inspired green/slate CSS design tokens
│   └── views/                 # 4 Role-Based Workspaces & Operational Deep-Dives
│       ├── customer_portal.py          # Workspace 1: Customer Portal
│       ├── merchant_portal.py          # Workspace 2: Merchant Portal
│       ├── admin_dashboard.py          # Workspace 3: Admin Command & Ingestion Pipeline
│       ├── ai_investigation_workspace.py # Workspace 4: AI Investigation
│       ├── sbi_upi_demo.py             # Interactive 6-step SBI UPI Walkthrough
│       └── simulation.py               # Data Generation & Workbench
├── data/
│   ├── documents/             # Payment SOP text documents (SOP-001 through SOP-004)
│   ├── raw/                   # Master datasets & archived raw CSV ingestion runs
│   └── rejected/              # Lineage-tracked rejected payment records with reasons
├── scripts/
│   ├── setup_all.py           # Single-command database & synthetic bootstrap
│   ├── generate_real_world_data.py # Real-world brand data generator
│   └── generate_people_csv.py # 600+ authentic Indian customer profiles exporter
├── tests/
│   ├── unit/                  # 88 Unit tests covering all payment operations
│   └── integration/           # End-to-end pipeline & REST API tests
├── Dockerfile                 # Multi-stage production container build
├── docker-compose.yml         # Containerized PostgreSQL 16 + FastAPI + Streamlit
├── requirements.txt           # Production dependencies pinned for reproducibility
└── README.md                  # Executive architectural portfolio documentation
```

---

## 📄 14. License & Attribution

Designed and engineered as a production-grade FinOps & Payment Operations Portfolio Platform by **Naveen Kotnana**.  
*Inspired by Razorpay's modern Indian fintech design language, multi-bank switch telemetry, and operational rigor.*  
Distributed under the **[MIT License](LICENSE)**.
