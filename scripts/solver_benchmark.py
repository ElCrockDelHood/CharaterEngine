"""Experiment 0 driver: Blender 3.6 solver benchmark on this PC (docs/product/EXPERIMENT-0-SOLVER-BENCHMARK.md).

    python scripts/solver_benchmark.py                       # all cases, sizes 0..2, light -> heavy
    python scripts/solver_benchmark.py --max-level 1         # skip the heavy (largest) sizes
    python scripts/solver_benchmark.py --levels 2 --timeout 600
    python scripts/solver_benchmark.py --smoke               # smallest sizes, 3 frames (tests)

Every case runs in its own Blender process (``runtime/blender/ce_solver_benchmark.py``) with a timeout, so a
heavy case can never freeze the run: it is recorded as ``exceeded``. Each process is logged through
``_logrun`` (``logs/<UTC>_solver_bench.log``). Results: ``builds/benchmarks/<UTC>_solver_benchmark.json`` and
``.md`` plus one Workbench PNG per case in ``builds/renders/benchmark/``. All values are ESTIMATE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from _logrun import run_logged, utf8_console
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "blender" / "ce_solver_benchmark.py"
OUT_DIR = ROOT / "builds" / "benchmarks"
RENDER_DIR = ROOT / "builds" / "renders" / "benchmark"

# Cases in order of expected cost; sizes per level 0 (light), 1 (medium), 2 (heavy).
CASES = {
    "rigid": (10, 100, 500),
    "geonodes": (1_000, 10_000, 100_000),
    "particles": (1_000, 10_000, 50_000),
    "softbody": (2, 3, 4),
    "cloth": (16, 32, 64),
    "fluid": (32, 48, 64),
}
SIZE_UNITS = {"rigid": "bodies", "geonodes": "points", "particles": "particles", "softbody": "ico subdiv",
              "cloth": "grid side", "fluid": "resolution"}
REQUIRED_OK = ("case", "size", "frames", "seed", "status", "provenance", "conditions", "sim_s_per_frame",
               "replay_s_per_frame", "render_s", "ram_peak_mb")
STATUSES = ("ok", "exceeded", "error")


def validate_result(r: dict) -> list[str]:
    """Schema check of one case result; returns a list of problems (empty = valid)."""
    problems = []
    for key in ("case", "size", "frames", "seed", "status", "provenance"):
        if key not in r:
            problems.append(f"missing {key}")
    if r.get("status") not in STATUSES:
        problems.append(f"bad status {r.get('status')!r}")
    if r.get("provenance") != "ESTIMATE":
        problems.append("provenance must be ESTIMATE")
    if r.get("case") not in CASES:
        problems.append(f"unknown case {r.get('case')!r}")
    if r.get("status") == "ok":
        problems += [f"missing {k}" for k in REQUIRED_OK if k not in r]
        for k in ("sim_s_per_frame", "replay_s_per_frame"):
            if isinstance(r.get(k), (int, float)) and r[k] < 0:
                problems.append(f"negative {k}")
    return problems


def plan(levels, cases) -> list[tuple[str, int, int]]:
    """(case, size, level), all cases of level 0 first, heavy level last."""
    return [(c, CASES[c][lv], lv) for lv in levels for c in CASES if c in cases]


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def markdown(summary: dict) -> str:
    lines = [f"# Experiment 0 — solver benchmark ({summary['started']})", "",
             f"Blender: `{summary['blender']}` · frames per case: {summary['frames']} · seed: {summary['seed']} · "
             f"timeout per case: {summary['timeout_s']} s · all values ESTIMATE (single run).", "",
             "| Case | Size | Status | Sim s/frame (mean / max) | Cached replay fps | Workbench render s | Peak RAM MB |",
             "|------|------|--------|--------------------------|-------------------|--------------------|-------------|"]
    for r in summary["results"]:
        size = f"{r['size']} {SIZE_UNITS.get(r['case'], '')}"
        if r["status"] == "ok":
            lines.append(f"| {r['case']} | {size} | ok | {r['sim_s_per_frame']} / {r.get('sim_s_per_frame_max')} | "
                         f"{r.get('replay_fps')} | {r.get('render_s')} | {r.get('ram_peak_mb')} |")
        else:
            lines.append(f"| {r['case']} | {size} | **{r['status']}** | {r.get('error', '')} | — | — | — |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", default=None, help="Blender 3.6 executable (default: CE_BLENDER / C:/DEV/Tools/Blender)")
    ap.add_argument("--cases", default=",".join(CASES), help="comma-separated subset of: " + ", ".join(CASES))
    ap.add_argument("--levels", default="0,1,2", help="size levels to run (0 light, 1 medium, 2 heavy)")
    ap.add_argument("--max-level", type=int, default=None, help="drop levels above this one")
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--timeout", type=int, default=300, help="seconds per case before it is recorded as exceeded")
    ap.add_argument("--smoke", action="store_true", help="level 0, 3 frames, short timeout (tests)")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--render-dir", type=Path, default=RENDER_DIR)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="do not echo Blender output to the console")
    a = ap.parse_args(argv)

    exe = find_blender(a.blender)
    if exe is None:
        print("[bench] Blender not found (use --blender or CE_BLENDER)")
        return 2
    levels = [0] if a.smoke else [int(x) for x in a.levels.split(",") if x.strip()]
    if a.max_level is not None:
        levels = [lv for lv in levels if lv <= a.max_level]
    frames = 3 if a.smoke else a.frames
    timeout = min(a.timeout, 120) if a.smoke else a.timeout
    cases = [c.strip() for c in a.cases.split(",") if c.strip()]
    unknown = [c for c in cases if c not in CASES]
    if unknown:
        print(f"[bench] unknown case(s): {unknown}")
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    work = a.out_dir / f"{stamp}_cases"
    results, logs = [], []
    for case, size, level in plan(levels, cases):
        out = work / f"{case}_{size}.json"
        png = None if a.no_render else a.render_dir / f"{stamp}_{case}_{size}.png"
        cmd = [exe, "-b", "--factory-startup", "--python", SCRIPT, "--", "--case", case, "--size", str(size),
               "--frames", str(frames), "--seed", str(a.seed), "--out", out]
        if png:
            cmd += ["--render", png]
        print(f"\n[bench] level {level}: {case} size {size} ({SIZE_UNITS[case]}), {frames} frames, timeout {timeout} s",
              flush=True)
        code, secs, log = run_logged(cmd, "solver_bench", timeout=timeout, echo=not a.quiet)
        logs.append(str(log))
        if code == 124:
            r = {"case": case, "size": size, "frames": frames, "seed": a.seed, "status": "exceeded",
                 "error": f"timeout {timeout} s", "provenance": "ESTIMATE"}
        elif out.exists():
            r = json.loads(out.read_text(encoding="utf-8"))
        else:
            r = {"case": case, "size": size, "frames": frames, "seed": a.seed, "status": "error",
                 "error": f"no result (exit {code})", "provenance": "ESTIMATE"}
        r["level"], r["wall_s"], r["log"] = level, round(secs, 1), str(log)
        if png:
            r["render_png"], r["render_sha256"] = str(png), sha256(png)
        results.append(r)
        print(f"[bench] -> {r['status']}  sim {r.get('sim_s_per_frame')} s/frame  "
              f"RAM peak {r.get('ram_peak_mb')} MB  render {r.get('render_s')} s", flush=True)

    summary = {"experiment": "EXPERIMENT-0 solver benchmark", "started": stamp, "blender": str(exe),
               "frames": frames, "seed": a.seed, "timeout_s": timeout, "levels": levels, "results": results}
    a.out_dir.mkdir(parents=True, exist_ok=True)
    js = a.out_dir / f"{stamp}_solver_benchmark.json"
    md = a.out_dir / f"{stamp}_solver_benchmark.md"
    js.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md.write_text(markdown(summary), encoding="utf-8")
    print("\n" + markdown(summary))
    print(f"[bench] results: {js}\n[bench] table:   {md}")

    problems = {f"{r['case']}_{r['size']}": p for r in results if (p := validate_result(r))}
    if problems:
        print(f"[bench] schema problems: {problems}")
        return 1
    return 0 if all(r["status"] != "error" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
