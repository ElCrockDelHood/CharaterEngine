"""Static checks: ruff lint + architecture guard (no ``bpy`` in the domain).

    python scripts/lint.py
"""

import re
import sys

from _common import ROOT, run, venv_python

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
    code = run([venv_python(), "-m", "ruff", "check", "."], check=False)
    code |= architecture_guard()
    return code


if __name__ == "__main__":
    sys.exit(main())
