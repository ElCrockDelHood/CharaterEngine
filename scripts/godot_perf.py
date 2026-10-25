"""Godot hardware benchmark on this PC (RIG-GAME-001 step 4): canonical vs game rig, face blend shapes.

    python scripts/godot_perf.py            # windowed run (needs the GPU), ~1-2 min

Opens a 1280x720 Godot window (Compatibility renderer, vsync off), runs runtime/godot/tests/ce_perf_bench.gd and
writes builds/tests/godot_perf.json. Live output + logs/<UTC>_godot_perf.log (docs/09_Debug_Consoles.md).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _logrun import run_logged, utf8_console
from engine_tests import find_godot

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "runtime" / "godot"
REPORT = ROOT / "builds" / "tests" / "godot_perf.json"


def main() -> int:
    utf8_console()
    exe = find_godot()
    if exe is None:
        print("Godot not found (set CE_GODOT)")
        return 1
    assets = PROJECT / "assets"
    assets.mkdir(exist_ok=True)
    for extra, name in ((["--pose", "tpose"], "human_adult_206_tpose.glb"),
                        (["--skeleton", "game", "--pose", "tpose"], "human_game_v1_tpose.glb")):
        code, _, _ = run_logged([sys.executable, ROOT / "scripts" / "export_gltf.py", *extra, "-o", assets / name],
                                "godot_perf_assets")
        if code:
            return code
    run_logged([exe, "--headless", "--path", PROJECT, "--import"], "godot_perf_import", timeout=600)
    if REPORT.exists():
        REPORT.unlink()
    code, secs, log = run_logged([exe, "--path", PROJECT, "--resolution", "1280x720", "--script",
                                  "res://tests/ce_perf_bench.gd", "--", "--report", REPORT], "godot_perf",
                                 timeout=900)
    if not REPORT.exists():
        print(f"no report (exit {code}); see {log}")
        return 1
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    print(f"\n{data['adapter']} | {data['api']} | {data['rendering_method']} | window {data['window']}")
    print(f"{'scenario':28s} {'bones':>5s} {'avg ms':>8s} {'p95 ms':>8s} {'fps':>7s}")
    for r in data["results"]:
        print(f"{r['scenario']:28s} {r['bones_per_character']:5d} {r['avg_ms']:8.3f} {r['p95_ms']:8.3f} "
              f"{r['fps']:7.1f}")
    print(f"report: {REPORT}  log: {log}  ({secs:.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
