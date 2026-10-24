"""Run the test suite.

    python scripts/test.py                 # everything
    python scripts/test.py --domain        # anatomy + integration + export (fast, pure Python)
    python scripts/test.py --backend       # backend (SQLite in-memory)
    python scripts/test.py --cov           # with coverage report
    python scripts/test.py -k gltf -x      # extra args are forwarded to pytest
"""

import argparse
import sys

from _common import run, venv_python


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", action="store_true")
    parser.add_argument("--backend", action="store_true")
    parser.add_argument("--cov", action="store_true")
    args, extra = parser.parse_known_args()

    targets = []
    if args.domain:
        targets += ["tests/anatomy", "tests/unit", "tests/integration", "tests/export"]
    if args.backend:
        targets += ["tests/backend"]
    if not targets:
        targets = ["tests"]

    cmd = [venv_python(), "-m", "pytest", *targets, "-q"]
    if args.cov:
        cmd += ["--cov", "--cov-report=term-missing"]
    cmd += extra
    return run(cmd, check=False, env={"CHARACTER_ENGINE_ENV": "test"})


if __name__ == "__main__":
    sys.exit(main())
