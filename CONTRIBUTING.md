# Contributing to PayBridge

Thank you for your interest in contributing to **PayBridge — AI-Powered Payment Operations & FinOps Intelligence Platform**!

## Repository Architecture

The repository is organized into a clean, modern modular structure:

```
├── .github/workflows/       # Automated CI/CD pipelines (lint, test, build)
├── backend/                 # FastAPI REST API, database models, payment services, ingestion
│   ├── app/                 # Core backend application modules
│   │   ├── api/             # FastAPI routes & endpoints (v1)
│   │   ├── core/            # Config, security, JWT auth
│   │   ├── db/              # SQLAlchemy session & PostgreSQL/SQLite engine
│   │   ├── models/          # Declarative ORM models (transactions, webhooks, audit)
│   │   ├── rag/             # Vector store, hybrid retriever, grounding engine
│   │   ├── schemas/         # Pydantic schemas (canonical payment, requests, responses)
│   │   └── services/        # Webhook processor, CSV mapper, URL fetcher, FinOps
│   ├── alembic/             # Database migrations
│   ├── config/              # YAML configs & customer profiles
│   ├── data/                # Sample datasets, raw uploads, lineage archives
│   ├── scripts/             # Data bootstrapping & evaluation runners
│   ├── main.py              # Backend entrypoint (`uvicorn backend:app`)
│   └── rag_agent.py         # Standalone RAG CLI query agent
├── docs/                    # Technical architecture, API specs, governance docs
├── frontend/                # Streamlit Operations & Intelligence Dashboard
│   ├── views/               # Portal views (Overview, Transactions, Anomalies, FinOps)
│   ├── dashboard.py         # Main Streamlit application entrypoint
│   ├── components.py        # Reusable UI widgets & API client
│   ├── styles.py            # Custom CSS & design system
│   └── Dockerfile           # Frontend container definition
├── ml/                      # Machine Learning anomaly detection models
│   ├── anomaly.py           # Isolation Forest + DBSCAN anomaly detector
│   └── __init__.py          # ML package exports
├── screenshots/             # Product screenshots, architectural GIFs, and media
└── tests/                   # Automated test suite (Unit & Integration tests)
```

---

## Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Git
- Docker & Docker Compose (optional for containerized deployment)
- Ollama (optional for local LLM inference)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/naveenkotnana/Deploy-PayBridge-Razorpay-inspired-AI-FinOps-Platform.git
cd Deploy-PayBridge-Razorpay-inspired-AI-FinOps-Platform

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Bootstrap Database & Sample Data
```bash
python backend/scripts/setup_all.py
```

### 4. Running the Services

- **Backend API**:
  ```bash
  uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
  ```
  Interactive Swagger UI documentation is available at `http://localhost:8000/docs`.

- **Frontend Dashboard**:
  ```bash
  streamlit run frontend/dashboard.py
  ```
  The dashboard will open automatically at `http://localhost:8501`.

---

## Code Quality & Testing

Before submitting a Pull Request, ensure all checks pass:

```bash
# 1. Lint and format checks
ruff check backend frontend ml tests

# 2. Run unit and integration tests
pytest tests/ -v

# 3. RAG Grounding & Evaluation
python backend/scripts/run_rag_eval.py

# 4. Agent Governance & Guardrails Evaluation
python backend/scripts/run_agent_eval.py
```

---

## Submitting Pull Requests

1. Fork the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Write clean, self-documenting code with type annotations and docstrings.
3. Add corresponding unit or integration tests under `tests/`.
4. Ensure all 117+ tests pass without errors or warnings.
5. Submit your PR with a clear description of changes and test results.
