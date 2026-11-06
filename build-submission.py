"""Build a clean, portable submission archive without secrets, caches or old databases."""
from pathlib import Path
import subprocess
import zipfile

root = Path(__file__).resolve().parent
output = root / "PayBridge-Submission.zip"
names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, text=True).splitlines()
excluded_parts = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "screenshots", ".devcontainer"}
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name in sorted(set(names)):
        path = root / name
        if not path.is_file() or excluded_parts.intersection(path.relative_to(root).parts):
            continue
        if path.name == ".env" or path.suffix.lower() in {".db", ".zip", ".pyc"}:
            continue
        if path.name.startswith(".coverage") or "ingestion_archive" in path.parts or "rejected" in path.parts:
            continue
        archive.write(path, "PayBridge/" + path.relative_to(root).as_posix())
    database = root / "backend/data/payment_data.db"
    if database.exists():
        archive.write(database, "PayBridge/backend/data/payment_data.db")
print(f"Created {output} ({output.stat().st_size / 1024 / 1024:.1f} MB)")
