# -*- coding: utf-8 -*-
"""Streamlit App Entrypoint. Seamlessly delegates to frontend.dashboard."""
from pathlib import Path
import runpy
import sys

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"

for _p in [str(_FRONTEND_DIR), str(_PROJECT_ROOT), str(_BACKEND_DIR)]:
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

dashboard_script = _FRONTEND_DIR / "dashboard.py"
runpy.run_path(str(dashboard_script), run_name="__main__")
