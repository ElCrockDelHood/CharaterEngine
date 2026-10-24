"""Auto-format and auto-fix lint issues with ruff.

    python scripts/format.py          # apply
    python scripts/format.py --check  # verify only (CI)
"""

import sys

from _common import run, venv_python


def main() -> int:
    check = "--check" in sys.argv
    py = venv_python()
    if check:
        code = run([py, "-m", "ruff", "format", "--check", "."], check=False)
        code |= run([py, "-m", "ruff", "check", "."], check=False)
        return code
    run([py, "-m", "ruff", "check", "--fix", "."], check=False)
    return run([py, "-m", "ruff", "format", "."], check=False)


if __name__ == "__main__":
    sys.exit(main())
