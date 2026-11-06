"""Bootstrap only the payment dataset needed for the submission demo."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "backend"))

from app.core.config import settings  # noqa: E402
from app.core.security import seed_demo_users  # noqa: E402
from app.db.base import SessionLocal, init_db  # noqa: E402
from app.models.payments import PaymentTransaction  # noqa: E402
from app.services.demo import refresh_demo_alert  # noqa: E402


def main():
    if not settings.DEMO_MODE:
        raise RuntimeError("Set DEMO_MODE=true to initialize synthetic demo data.")
    init_db()
    with SessionLocal() as db:
        seed_demo_users(db)
        count = db.query(PaymentTransaction).count()
    if not count:
        from backend.scripts.generate_and_ingest_50k import main as generate
        generate()
    with SessionLocal() as db:
        refresh_demo_alert(db)
        print(f"Demo ready: {db.query(PaymentTransaction).count():,} payment transactions.")
    print("Start the FastAPI backend and Streamlit dashboard: ./start-demo.ps1")


if __name__ == "__main__":
    main()
