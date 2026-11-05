"""Central configuration. Everything is env-overridable; nothing is hardcoded secret."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
ROOT = BACKEND_DIR

# Determine data directory
if (BACKEND_DIR / "data").exists():
    DATA_DIR = BACKEND_DIR / "data"
else:
    DATA_DIR = PROJECT_ROOT / "data"


class Settings:
    # --- Database -------------------------------------------------------
    # Default SQLite in data directory so the project runs with zero setup.
    # Set DATABASE_URL to a postgresql+psycopg2://... string to use Postgres.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DATA_DIR / ('paybridge.db' if (DATA_DIR / 'paybridge.db').exists() else 'opspilot.db')}"
    )

    # --- Ollama (local only, no paid APIs) ------------------------------
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "90"))

    # --- RAG ------------------------------------------------------------
    # 'tfidf' = pure sklearn, zero downloads, always works.
    # 'ollama' = local embedding model via Ollama (nomic-embed-text).
    EMBEDDING_MODE: str = os.getenv("EMBEDDING_MODE", "tfidf")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "4"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "80"))

    # --- Auth -----------------------------------------------------------
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-only-change-me")
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

    # --- Razorpay Checkout & Webhook Integration ------------------------
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_mock_finops_key")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "mock_finops_secret_opspilot")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "test_secret_opspilot_2026")

    # --- SQL tool guardrails --------------------------------------------
    SQL_ROW_LIMIT: int = int(os.getenv("SQL_ROW_LIMIT", "200"))
    SQL_TIMEOUT_S: int = int(os.getenv("SQL_TIMEOUT_S", "10"))

    # --- Paths ----------------------------------------------------------
    RAW_DIR: Path = DATA_DIR / "raw"
    DOC_DIR: Path = DATA_DIR / "documents"
    PROC_DIR: Path = DATA_DIR / "processed"

    BILLING_MONTH: str = os.getenv("BILLING_MONTH", "2026-09")


settings = Settings()
