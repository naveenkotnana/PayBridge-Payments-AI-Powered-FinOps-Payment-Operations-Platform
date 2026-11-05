# ruff: noqa: E402
"""OpsPilot Frontend Package.

Exposes Streamlit dashboard components and ensures compatibility with
`dashboard.*` import references.
"""

import sys
from pathlib import Path

_frontend_dir = Path(__file__).resolve().parent
_root_dir = _frontend_dir.parent
_backend_dir = _root_dir / "backend"

for _p in [str(_backend_dir), str(_root_dir), str(_frontend_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import backend.app as _backend_app
    sys.modules.setdefault("app", _backend_app)
except ImportError:
    pass

import frontend as _self
sys.modules.setdefault("dashboard", _self)
