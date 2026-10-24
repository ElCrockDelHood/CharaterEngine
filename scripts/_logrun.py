"""Run a command with its output live on the console AND in a timestamped log (stdlib only).

Daily debug-console workflow (docs/09_Debug_Consoles.md): every developer run leaves

* ``logs/<UTC yyyymmddTHHMMSSZ>_<tool>.log`` — header (command, cwd, git commit, Python),
  every line prefixed with the UTC time, footer with exit code and duration;
* ``logs/latest_<tool>.log`` — a copy of the newest one, to follow with
  ``Get-Content logs\\latest_<tool>.log -Wait -Tail 50``;
* at most ``KEEP`` dated logs per tool (older ones are deleted).

Console output is forced to UTF-8 so non-ASCII characters (Δ, ≤, accents) never crash a run; log
files are UTF-8 with BOM so Windows PowerShell 5.1 reads them correctly.
Not used by the pure domain (no logging there by design).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
KEEP = 50


def utf8_console() -> None:
    """Make this process's stdout/stderr UTF-8 (Windows consoles default to cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _stamp(fmt: str = "%Y%m%dT%H%M%SZ") -> str:
    return datetime.now(timezone.utc).strftime(fmt)


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _prune(tool: str, logs_dir: Path, keep: int) -> None:
    dated = sorted(p for p in logs_dir.glob(f"*_{tool}.log") if not p.name.startswith("latest_"))
    for old in dated[:-keep] if keep > 0 else []:
        old.unlink(missing_ok=True)


def run_logged(cmd, tool: str, *, cwd: Path = ROOT, env: dict | None = None, timeout: float | None = None,
               copy_to: Path | None = None, logs_dir: Path | None = None, keep: int = KEEP,
               echo: bool = True) -> tuple[int, float, Path]:
    """Run ``cmd``; tee output to the console and ``logs/``. Returns (exit code, seconds, log path).

    ``copy_to`` also writes the plain output (no timestamps) to a legacy path such as
    ``builds/tests/godot.log``. A timeout kills the process and returns exit code 124.
    """
    utf8_console()
    logs_dir = Path(logs_dir) if logs_dir else LOGS
    logs_dir.mkdir(parents=True, exist_ok=True)
    log = logs_dir / f"{_stamp()}_{tool}.log"
    n = 1
    while log.exists():
        log = logs_dir / f"{_stamp()}_{n}_{tool}.log"
        n += 1
    full_env = {**os.environ, **(env or {}), "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    printable = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd)
    header = [f"# tool    : {tool}", f"# command : {printable}", f"# cwd     : {cwd}",
              f"# commit  : {_git_commit()}", f"# python  : {sys.version.split()[0]}",
              f"# started : {_stamp('%Y-%m-%d %H:%M:%S UTC')}", ""]
    if echo:
        print(f"\n$ {printable}\n  (log: {log})", flush=True)
    t0 = time.time()
    plain = copy_to.open("w", encoding="utf-8", errors="replace") if copy_to else None
    # UTF-8 with BOM so Windows PowerShell 5.1 (Get-Content -Wait) shows non-ASCII text correctly
    with log.open("w", encoding="utf-8-sig", errors="replace") as fh:
        fh.write("\n".join(header) + "\n")
        fh.flush()
        proc = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd), env=full_env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                                encoding="utf-8", errors="replace", bufsize=1)

        def pump() -> None:
            for line in proc.stdout:
                fh.write(f"[{_stamp('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d}] {line}")
                fh.flush()
                if plain:
                    plain.write(line)
                if echo:
                    sys.stdout.write(line)
                    sys.stdout.flush()

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            code = 124
            fh.write(f"!! timeout after {timeout} s - process killed\n")
        reader.join(timeout=10)
        secs = time.time() - t0
        fh.write(f"\n# exit code: {code} | duration: {secs:.1f} s | ended {_stamp('%Y-%m-%d %H:%M:%S UTC')}\n")
    if plain:
        plain.close()
    shutil.copyfile(log, logs_dir / f"latest_{tool}.log")
    _prune(tool, logs_dir, keep)
    if echo:
        print(f"  (exit {code}, {secs:.1f} s, log: {log})", flush=True)
    return code, secs, log


def append_log(log: Path, tool: str, text: str) -> None:
    """Append in-process output (e.g. a check done by the calling script) to a run log and its latest copy."""
    lines = "".join(f"[{_stamp('%H:%M:%S')}] {line}\n" for line in text.splitlines())
    for target in (log, log.parent / f"latest_{tool}.log"):
        with target.open("a", encoding="utf-8", errors="replace") as fh:
            fh.write(lines)
