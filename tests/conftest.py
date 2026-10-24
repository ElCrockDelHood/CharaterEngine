"""Shared pytest configuration for CHARACTER ENGINE.

- Forces ``CHARACTER_ENGINE_ENV=test`` so backend services pick the TEST
  profile (SQLite database, reduced Argon2 work factor). Individual tests that
  need another environment override the variable with ``monkeypatch``.
- Makes ``src/`` and the repository root importable without installing the
  package (``pyproject.toml`` also sets ``pythonpath`` for pytest; this is a
  fallback for IDE runners that ignore it).
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("CHARACTER_ENGINE_ENV", "test")

_ROOT = Path(__file__).resolve().parent.parent
for _path in (_ROOT / "src", _ROOT):
    _str_path = str(_path)
    if _str_path not in sys.path:
        sys.path.insert(0, _str_path)
