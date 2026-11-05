"""Worker batch job: recompute revenue and re-run anomaly detection."""
import sys
import pathlib
_backend_dir = pathlib.Path(__file__).resolve().parents[1]
_root_dir = _backend_dir.parent
for _p in [str(_root_dir), str(_backend_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
from app.core.logging_config import setup_logging
from app.db.base import SessionLocal, init_db
from app.services.revenue import compute_month
from app.ml.anomaly import detect
import logging

setup_logging()
log = logging.getLogger("opspilot.worker")
MONTHS = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]

init_db()
db = SessionLocal()
try:
    for m in MONTHS:
        log.info("revenue recomputed", extra={"node": "batch", "status": "OK",
                                              **{"tool": m}})
        compute_month(db, m)
    log.info(f"anomaly detection: {detect(db)}",
             extra={"node": "batch", "tool": "isolation_forest", "status": "OK"})
finally:
    db.close()
