"""Remove generated artifacts (caches, local DBs, build outputs).

    python scripts/clean.py           # caches + local SQLite DBs
    python scripts/clean.py --builds  # also builds/gltf and builds/tmp
    python scripts/clean.py --venv    # also the virtual environment
"""

import argparse
import shutil
import sys
from pathlib import Path

from _common import ROOT, VENV_DIR

CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov"}
CACHE_FILES = {".coverage"}


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()
    print(f"removed {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--builds", action="store_true")
    parser.add_argument("--venv", action="store_true")
    args = parser.parse_args()

    for path in ROOT.rglob("*"):
        if ".git" in path.parts or ".venv" in path.parts:
            continue
        if path.is_dir() and path.name in CACHE_DIRS:
            remove(path)
        elif path.is_file() and (path.name in CACHE_FILES or path.suffix in {".pyc", ".pyo"}):
            remove(path)
    for db in ROOT.glob("*.db"):
        remove(db)
    for egg in (ROOT / "src").glob("*.egg-info"):
        remove(egg)

    if args.builds:
        for sub in ("gltf", "tmp"):
            remove(ROOT / "builds" / sub)
    if args.venv:
        remove(VENV_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
