"""Central configuration. Everything is env-overridable; nothing is hardcoded secret."""
import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
ROOT = BACKEND_DIR


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be set to true or false.")


DEVELOPMENT_JWT_SECRETS = {
    "",
    "dev-only-change-me",
    "change-me-in-your-local-env",
    "secret",
    "changeme",
}

# Determine data directory
if (BACKEND_DIR / "data").exists():
    DATA_DIR = BACKEND_DIR / "data"
else:
    DATA_DIR = PROJECT_ROOT / "data"


class Settings:
    # Fail closed: local demo use must be opted into in the environment.
    DEMO_MODE: bool = _env_bool("DEMO_MODE", False)

    # --- Database -------------------------------------------------------
    # Default SQLite in data directory so the project runs with zero setup.
    # Set DATABASE_URL to a postgresql+psycopg2://... string to use Postgres.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DATA_DIR / ('paybridge.db' if (DATA_DIR / 'paybridge.db').exists() else 'payment_data.db')}"
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
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

    # --- Razorpay Standard Web Checkout Integration ---------------------
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")

    # Comma-separated trusted browser origins. Demo defaults are local only.
    ALLOWED_ORIGINS: tuple[str, ...] = tuple(
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:8501,http://127.0.0.1:8501" if DEMO_MODE else "",
        ).split(",")
        if origin.strip()
    )

    # The demo cafe is a local-only default. Production must set this explicitly.
    CHECKOUT_MERCHANT_ID: str = os.getenv(
        "CHECKOUT_MERCHANT_ID", "mid_rameshwaram_01" if DEMO_MODE else ""
    )
    ENABLE_URL_INGESTION: bool = _env_bool("ENABLE_URL_INGESTION", DEMO_MODE)
    ENABLE_SIMULATION_ENDPOINTS: bool = _env_bool("ENABLE_SIMULATION_ENDPOINTS", DEMO_MODE)

    # --- SQL tool guardrails --------------------------------------------
    SQL_ROW_LIMIT: int = int(os.getenv("SQL_ROW_LIMIT", "200"))
    SQL_TIMEOUT_S: int = int(os.getenv("SQL_TIMEOUT_S", "10"))

    # --- Paths ----------------------------------------------------------
    RAW_DIR: Path = DATA_DIR / "raw"
    DOC_DIR: Path = DATA_DIR / "documents"
    PROC_DIR: Path = DATA_DIR / "processed"

    BILLING_MONTH: str = os.getenv("BILLING_MONTH", "2026-09")


def validate_runtime_configuration(config: Optional[Settings] = None) -> None:
    """Reject unsafe production defaults before opening the application."""
    current = config or settings
    if current.DEMO_MODE:
        return
    if current.JWT_SECRET.strip() in DEVELOPMENT_JWT_SECRETS or len(current.JWT_SECRET) < 32:
        raise RuntimeError("Production requires a unique JWT_SECRET of at least 32 characters.")
    if not current.ALLOWED_ORIGINS or "*" in current.ALLOWED_ORIGINS:
        raise RuntimeError("Production requires explicit trusted ALLOWED_ORIGINS; wildcards are forbidden.")
    if not current.CHECKOUT_MERCHANT_ID:
        raise RuntimeError("Production requires CHECKOUT_MERCHANT_ID to be configured.")
    if not current.DATABASE_URL.startswith(("postgresql://", "postgresql+")):
        raise RuntimeError("Production requires a PostgreSQL DATABASE_URL.")
    if current.ENABLE_URL_INGESTION:
        raise RuntimeError("URL ingestion must remain disabled in production until SSRF controls receive external review.")


settings = Settings()
