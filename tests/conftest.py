import sys
import pathlib

_root_dir = pathlib.Path(__file__).resolve().parents[1]
_backend_dir = _root_dir / "backend"
_ml_dir = _root_dir / "ml"

# Put root and backend on sys.path
for _p in [str(_ml_dir), str(_root_dir), str(_backend_dir)]:
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

try:
    import backend as _backend_mod
    sys.modules.setdefault("backend", _backend_mod)
except ImportError:
    pass

try:
    import frontend as _frontend_mod
    sys.modules.setdefault("dashboard", _frontend_mod)
except ImportError:
    pass

import pytest  # noqa: E402
from app.db.base import SessionLocal, init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db_ready():
    init_db()


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.close()
