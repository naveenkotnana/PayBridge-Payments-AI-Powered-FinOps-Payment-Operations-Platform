"""OpsPilot FastAPI Server Entry Point."""

import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent
_root_dir = _backend_dir.parent
for _p in [str(_backend_dir), str(_root_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend import app  # noqa: E402

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
