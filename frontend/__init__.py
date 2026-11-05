"""OpsPilot Frontend Package.

Exposes Streamlit dashboard components and ensures compatibility with
`dashboard.*` import references.
"""

import sys
from pathlib import Path

_frontend_dir = Path(__file__).resolve().parent
_root_dir = _frontend_dir.parent

for _p in [str(_frontend_dir), str(_root_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
