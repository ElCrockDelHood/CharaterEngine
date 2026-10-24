"""Shared helpers for the developer scripts (stdlib only)."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"


def venv_python() -> Path:
    """Path to the interpreter inside the project venv (or the current one as fallback)."""
    candidates = [VENV_DIR / "Scripts" / "python.exe", VENV_DIR / "bin" / "python"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def run(cmd, check: bool = True, env: dict | None = None, tool: str | None = None) -> int:
    """Run a command from the repository root, echoing it first.

    With ``tool`` the output is also teed live to ``logs/<UTC>_<tool>.log`` (scripts/_logrun.py).
    """
    merged_env = os.environ.copy()
    # Make `src/` and the repo root importable for every tool we launch.
    merged_env["PYTHONPATH"] = os.pathsep.join(
        p for p in [str(ROOT / "src"), str(ROOT), merged_env.get("PYTHONPATH", "")] if p
    )
    if env:
        merged_env.update(env)
    if tool:
        from _logrun import run_logged
        code, _, _ = run_logged(cmd, tool, env=merged_env)
    else:
        print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)
        code = subprocess.run([str(c) for c in cmd], cwd=ROOT, env=merged_env).returncode
    if check and code != 0:
        sys.exit(code)
    return code
