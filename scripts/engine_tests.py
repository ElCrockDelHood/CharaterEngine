"""Run the engine-side test suites in order: Blender → UPBGE → Godot.

    python scripts/engine_tests.py                 # all three, stop at first failing engine
    python scripts/engine_tests.py blender upbge   # subset
    python scripts/engine_tests.py --keep-going

Executable discovery (first hit wins):
  Blender : $CE_BLENDER, C:/Program Files/Blender Foundation/Blender */blender.exe, `blender` on PATH
  UPBGE   : $CE_UPBGE,   C:/Tools/UPBGE/**/blender.exe,                          `upbge` on PATH
  Godot   : $CE_GODOT,   C:/Tools/Godot/Godot_v4*_console.exe,                    `godot` on PATH
If vanilla Blender is not installed, the Blender suite runs on UPBGE's bundled Blender
(it *is* Blender 5.0.1 + BGE) and the report says so.

Blender runs headless (-b). UPBGE runs with a small window (UPBGE 0.50 cannot register
Python components in background mode) and closes itself; that run also launches
blenderplayer.exe for an autoplay combat smoke test. Godot runs --headless.
Each engine is closed (process exit) before the next one starts. Reports:
builds/tests/<engine>_addon_report.json (Blender/UPBGE), builds/tests/godot_report.json.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "builds" / "tests"
ENGINES = ("blender", "upbge", "godot")


def _first(paths):
    for p in paths:
        if p and Path(p).exists():
            return Path(p)
    return None


def find_blender() -> Path | None:
    return _first([os.environ.get("CE_BLENDER"),
                   *sorted(glob.glob(r"C:/Program Files/Blender Foundation/Blender*/blender.exe"), reverse=True),
                   *sorted(glob.glob(r"C:/Tools/Blender/**/blender.exe", recursive=True), reverse=True),
                   shutil.which("blender")])


def find_upbge() -> Path | None:
    return _first([os.environ.get("CE_UPBGE"),
                   *sorted(glob.glob(r"C:/Tools/UPBGE/**/blender.exe", recursive=True), reverse=True),
                   shutil.which("upbge")])


def find_godot() -> Path | None:
    return _first([os.environ.get("CE_GODOT"),
                   *sorted(glob.glob(r"C:/Tools/Godot/Godot_v4*_console.exe"), reverse=True),
                   *sorted(glob.glob(r"C:/Tools/Godot/Godot_v4*.exe"), reverse=True),
                   shutil.which("godot")])


def run(cmd, timeout: int, log: Path) -> tuple[int, float]:
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    t = time.time()
    with log.open("w", encoding="utf-8", errors="replace") as fh:
        try:
            proc = subprocess.run([str(c) for c in cmd], stdout=fh, stderr=subprocess.STDOUT, timeout=timeout,
                                  cwd=str(ROOT), env={**os.environ, "CHARACTER_ENGINE_SRC": str(ROOT / "src")})
            code = proc.returncode
        except subprocess.TimeoutExpired:
            fh.write(f"\n!! timeout after {timeout} s\n")
            code = 124
    text = log.read_text(encoding="utf-8", errors="replace")
    tail = "\n".join(text.splitlines()[-40:])
    print(tail)
    return code, time.time() - t


def run_blender_like(engine: str, exe: Path, timeout: int, ui: bool) -> int:
    """Run runtime/blender/ce_addon_headless_test.py inside Blender or UPBGE.

    Blender runs in background mode (``-b``).  UPBGE 0.50 crashes when registering Python
    components or logic bricks in background mode, so its suite runs with a real (small)
    window and quits itself; that also allows the blenderplayer autoplay smoke test.
    The verdict comes from the JSON report: UPBGE 0.50 may still exit with a non-zero code
    while tearing down the window *after* the report has been written.
    """
    report = OUT / f"{engine}_addon_report.json"
    save = OUT / f"{engine}_addon.blend"
    log = OUT / f"{engine}_addon.log"
    if report.exists():
        report.unlink()
    mode = ["--window-geometry", "0", "0", "800", "600"] if ui else ["-b", "--python-exit-code", "1"]
    code, secs = run([exe, *mode, "--factory-startup",
                      "--python", ROOT / "runtime" / "blender" / "ce_addon_headless_test.py", "--",
                      "--engine", engine, "--report", report, "--save", save], timeout, log)
    if report.exists():
        data = json.loads(report.read_text(encoding="utf-8"))
        print(f"[{engine}] {data['passed']} passed, {data['failed']} failed "
              f"({data['blender_version']}, {'UI' if ui else 'background'}, {secs:.0f} s, exit {code})")
        for r in data["results"]:
            if r["status"] == "FAIL":
                print(f"   FAIL {r['check']}: {r['detail']}")
        if data["failed"] == 0 and code != 0:
            print(f"[{engine}] note: all checks passed but the process exited with {code} "
                  f"(known UPBGE 0.50 teardown crash in UI mode)" if ui else f"[{engine}] exit code {code}")
        return 0 if data["failed"] == 0 and (ui or code == 0) else 1
    print(f"[{engine}] no report produced (exit {code}); see {log}")
    return 1


def run_godot(exe: Path, timeout: int) -> int:
    project = ROOT / "runtime" / "godot"
    log = OUT / "godot.log"
    report = OUT / "godot_report.json"
    if report.exists():
        report.unlink()
    # Godot consumes exported artefacts only: regenerate the GLBs and the gameplay table first.
    assets = project / "assets"
    assets.mkdir(exist_ok=True)
    py = sys.executable
    for extra, name in (([], "human_adult_206.glb"), (["--pose", "tpose"], "human_adult_206_tpose.glb")):
        code, _ = run([py, ROOT / "scripts" / "export_gltf.py", *extra, "-o", assets / name], timeout, OUT / "godot_assets.log")
        if code:
            print(f"[godot] glTF export failed for {name}; see {OUT / 'godot_assets.log'}")
            return 1
    code, _ = run([py, ROOT / "scripts" / "export_gameplay_data.py"], timeout, OUT / "godot_assets.log")
    if code:
        return 1
    # Import pass first (creates .godot cache for GLB / scripts), then the headless test runner.
    run([exe, "--headless", "--path", project, "--import"], timeout, OUT / "godot_import.log")
    code, secs = run([exe, "--headless", "--path", project, "--script", "res://tests/ce_test_runner.gd",
                      "--", "--report", report], timeout, log)
    if report.exists():
        data = json.loads(report.read_text(encoding="utf-8"))
        print(f"[godot] {data['passed']} passed, {data['failed']} failed ({data.get('godot_version')}, {secs:.0f} s)")
        for r in data["results"]:
            if r["status"] == "FAIL":
                print(f"   FAIL {r['check']}: {r['detail']}")
        return 0 if data["failed"] == 0 else 1
    print(f"[godot] no report produced (exit {code}); see {log}")
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("engines", nargs="*", metavar="{blender,upbge,godot}")
    ap.add_argument("--keep-going", action="store_true")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--upbge-background", action="store_true",
                    help="run the UPBGE suite with -b (no window; component/blenderplayer checks are deferred/skipped)")
    a = ap.parse_args(argv)
    if not a.engines:
        a.engines = list(ENGINES)
    bad = [e for e in a.engines if e not in ENGINES]
    if bad:
        ap.error(f"unknown engine(s) {bad}; choose from {', '.join(ENGINES)}")
    OUT.mkdir(parents=True, exist_ok=True)

    blender, upbge, godot = find_blender(), find_upbge(), find_godot()
    summary = {}
    for engine in a.engines:
        if engine == "blender":
            exe = blender or upbge
            if exe is None:
                print("[blender] no Blender/UPBGE executable found"); summary[engine] = "missing"; continue
            if blender is None:
                print(f"[blender] vanilla Blender not installed; running the Blender suite on UPBGE's Blender: {exe}")
            summary[engine] = run_blender_like("blender", exe, a.timeout, ui=False)
        elif engine == "upbge":
            if upbge is None:
                print("[upbge] UPBGE not found"); summary[engine] = "missing"; continue
            summary[engine] = run_blender_like("upbge", upbge, a.timeout, ui=not a.upbge_background)
        elif engine == "godot":
            if godot is None:
                print("[godot] Godot not found"); summary[engine] = "missing"; continue
            summary[engine] = run_godot(godot, a.timeout)
        if summary[engine] not in (0, "missing") and not a.keep_going:
            print(f"stopping: {engine} failed")
            break
    print("\n== engine tests ==")
    for k, v in summary.items():
        print(f"  {k:8s} {'PASS' if v == 0 else v}")
    return 0 if all(v == 0 for v in summary.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
