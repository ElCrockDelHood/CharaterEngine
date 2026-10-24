"""Static checks: ruff lint + architecture guard (no ``bpy`` in the domain).

    python scripts/lint.py
"""

import re
import sys

from _common import ROOT, venv_python

DOMAIN_DIRS = [ROOT / "src" / "character_engine" / "domain", ROOT / "src" / "character_engine" / "export",
               ROOT / "src" / "character_engine" / "math", ROOT / "backend"]
BPY_IMPORT = re.compile(r"^\s*(import bpy|from bpy\b|import bmesh|from bmesh\b|import mathutils|from mathutils\b)", re.M)


def architecture_guard() -> int:
    """Domain, export, math and backend must never import Blender modules."""
    violations = []
    for base in DOMAIN_DIRS:
        for path in base.rglob("*.py"):
            if BPY_IMPORT.search(path.read_text(encoding="utf-8", errors="ignore")):
                violations.append(path.relative_to(ROOT))
    if violations:
        print("ARCHITECTURE VIOLATION: Blender modules imported outside infrastructure/runtime:")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("architecture guard: OK (no bpy in domain/export/math/backend)")
    return 0


def main() -> int:
    import contextlib
    import io

    from _logrun import append_log, run_logged

    code, _, log = run_logged([venv_python(), "-m", "ruff", "check", "."], "lint")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        guard = architecture_guard()
    print(out.getvalue(), end="")
    append_log(log, "lint", out.getvalue())
    return code | guard


if __name__ == "__main__":
    sys.exit(main())
