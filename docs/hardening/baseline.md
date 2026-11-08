# PayBridge hardening baseline

Captured on 2026-11-08 before hardening edits.

## Source state and environment

- Branch created for this work: `production-hardening`.
- Starting commit: `b756c8b21be299c271426c61d40041990de4b883` (`build: pin Ruff version for reproducible CI`).
- The checkout contained pre-existing untracked user files, including the submission ZIP and generated Word/PPT files. They were preserved.
- System Python: 3.13.9 (Anaconda). Project `.venv`: Python 3.14.3 and did not contain pytest.
- Ruff 0.12.0 and Mypy 1.17.1 were available from the system Python environment.
- Docker CLI was not available in this shell; Docker and Compose checks could not be run at baseline.
- A local `.env` file exists and is ignored by Git. Its contents were not read or recorded.
- Tests and bootstrap used a disposable SQLite database under `.paybridge_interview_build/`; the configured/local project database was not selected for those checks.

## Baseline commands and results

| Check | Result |
| --- | --- |
| `ruff check backend frontend ml tests` | Pass, no findings. |
| `mypy backend/app/models backend/app/core backend/app/schemas backend/app/services --ignore-missing-imports` | Pass, 29 source files. |
| `python backend/scripts/setup_all.py` with isolated SQLite URL and `DEMO_MODE=true` | Completed. It reported 50,000 received, 50,000 accepted, 0 rejected, 0 duplicated for its generated payment batch. |
| SQLite count query after bootstrap | 50,004 payment rows total and 3 ingestion runs in the isolated database. The total includes non-generator rows written by bootstrap/evaluation. |
| `pytest tests/ -v --cov=backend/app --cov=ml --cov-report=term-missing` after bootstrap | 151 passed, 1 skipped, 19 warnings in 19.65 seconds; 71% total coverage. |
| Same pytest command before bootstrap | 136 passed, 16 failed. Integration failures were caused by the empty isolated DB lacking the seeded users/data expected by the integration tests. |
| `python backend/scripts/run_rag_eval.py` | 22 cases; Recall@4 22/22; top-1 21/22; mean fact coverage 0.947; overall/citation pass 18/22 (0.818). |
| `python backend/scripts/run_agent_eval.py` with isolated DB and `OLLAMA_TIMEOUT=10` | 35/35 passed. |
| `alembic upgrade head` on a fresh isolated SQLite database | Command returned success, but created only `alembic_version`; the initial migration contains no schema operations. |
| Docker build / Docker Compose | Not run: Docker executable unavailable. |

The setup script generated or refreshed `backend/data/raw/payment_platform_50000_transactions.csv`. It was not deleted. The repository also contains ignored and untracked files from earlier work; those are outside the baseline change set.

## Initial architecture and security observations

- Configuration is centralized in `backend/app/core/config.py`, but demo mode defaults to true, the JWT secret has a known development default, and Razorpay credentials have mock defaults.
- FastAPI startup rejects a known weak JWT only when demo mode is false. It still calls `seed_demo_users`; the helper returns without seeding in production, but startup does not refuse to run if demo users already exist.
- CORS permits every origin. Request metrics are process-local counters.
- Checkout routes in `backend/app/api/checkout.py` do not currently require an authenticated customer. The checkout module reads `.env` from inside request handling and accepts customer and merchant IDs from its request model.
- Role permissions exist in `backend/app/core/security.py`, but payment tenant isolation and end-to-end authenticated Streamlit API use require additional review.
- Streamlit code imports `SessionLocal` and ORM models directly in dashboard, Customer, Merchant, Admin, and investigation views. This bypasses FastAPI authorization for those paths.
- SQLite is the default; PostgreSQL URL support exists. `docker-compose.yml` runs API and dashboard against the same shared SQLite volume, not PostgreSQL.
- `backend/app/db/base.py:init_db()` uses `Base.metadata.create_all()`. The checked-in initial Alembic revision is empty, so a fresh Alembic upgrade does not create application tables.
- API surface includes `/auth/login`, `/auth/me`, `/alerts`, `/workflows`, `/revenue`, `/analytics/queries`, `/anomalies`, `/data-quality`, `/incidents`, `/audit`, `/metrics`, `/evaluation`, `/api/v1/simulation/*`, `/api/v1/payments/*`, `/api/v1/ingestion/*`, `/api/v1/events`, and Razorpay `/api/create-order` and `/api/verify-payment`.
- Current RAG defaults to local TF-IDF. An Ollama model was visible during bootstrap, but model availability is environment-specific and not a production guarantee.

## Baseline failure/limitation ledger

- The single skipped test is conditional; its exact reason is preserved in `.paybridge_interview_build/baseline-ci-pytest.log` and should be checked before making claims about provider/LLM verification.
- The agent evaluation is a small deterministic suite, not a comprehensive security or quality benchmark.
- There is no PostgreSQL integration result, live Razorpay sandbox transaction result, backup/restore smoke test, or Docker/Compose result from this environment.
- The 50K generator result is synthetic and does not establish production ingestion performance or correctness under concurrent/restart conditions.
- Passing lint and the bootstrapped test suite do not mean the app is production-ready.
