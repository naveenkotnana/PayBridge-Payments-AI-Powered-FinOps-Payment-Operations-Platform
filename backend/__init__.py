"""OpsPilot Backend Package.

Exposes the FastAPI application and ensures backward compatibility for
internal `app.*` import paths.
"""

import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent
_root_dir = _backend_dir.parent
_app_dir = _backend_dir / "app"

for _p in [str(_backend_dir), str(_root_dir), str(_app_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Import and expose FastAPI instance
from backend.app.api.main import app  # noqa: E402

__all__ = ["app"]
