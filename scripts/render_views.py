"""Automatic renders: front / side / back stills, contact sheet and turntable per body (Blender in background).

    python scripts/render_views.py                                   # scripts/render_specs/default.json, Workbench
    python scripts/render_views.py --check                           # validate the spec and list jobs, no Blender
    python scripts/render_views.py --engine EEVEE                    # opt-in engines: EEVEE, CYCLES
    python scripts/render_views.py --engine CYCLES --device CPU      # CYCLES device: AUTO (default) | CPU | GPU
    python scripts/render_views.py --mp4 --only human_male_adult_1800mm_tpose

The spec (``character_engine.pipeline.render_views``) takes the same body matrices as ``batch_export.py`` and is
validated before Blender starts (unavailable templates, unknown engine / device / view refuse the run, exit 2).
Outputs (git-ignored) in ``builds/renders/views/<job>/``: ``front.png``, ``side.png``, ``back.png``,
``contact_sheet.png``, ``turntable/0001.png…`` and, with ``--mp4``, ``turntable.mp4`` encoded by Blender's
bundled FFmpeg (nothing is downloaded); ``render.json`` per job, ``manifest.json`` for the run.
CYCLES ``GPU`` is refused when Cycles sees no CUDA device; ``AUTO`` falls back to CPU and says so.
Every run is logged through ``_logrun`` (``logs/<UTC>_render_views.log``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _logrun import _git_commit, run_logged, utf8_console
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.pipeline import batch_export, render_views  # noqa: E402

SCRIPT = ROOT / "runtime" / "blender" / "ce_render_views.py"
DEFAULT_SPEC = ROOT / "scripts" / "render_specs" / "default.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--out", type=Path, default=None, help="output folder (default: the spec's output_dir)")
    ap.add_argument("--only", default="", help="comma-separated job names")
    ap.add_argument("--engine", default=None, choices=sorted(render_views.ENGINES))
    ap.add_argument("--device", default=None, choices=render_views.DEVICES)
    ap.add_argument("--samples", type=int, default=None)
    ap.add_argument("--mp4", action="store_true", help="also encode turntable.mp4 (Blender's bundled FFmpeg)")
    ap.add_argument("--blender", default=None, help="Blender executable (default: engine_tests discovery)")
    ap.add_argument("--check", action="store_true", help="validate the spec and list the jobs, then stop")
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args(argv)
    utf8_console()
    overrides = {"engine": a.engine, "device": a.device, "samples": a.samples}
    try:
        raw = batch_export.load_spec(a.spec)
        if a.mp4:
            overrides["turntable"] = {**(raw.get("turntable") or {}), "mp4": True}
        spec = render_views.parse(raw, root=ROOT, overrides=overrides)
    except (OSError, batch_export.BatchSpecError) as exc:
        print(f"refused: {exc}")
        return 2
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    if only - {j.name for j in spec.jobs}:
        print(f"refused: --only names not in the spec: {sorted(only - {j.name for j in spec.jobs})}")
        return 2
    jobs = [j for j in spec.jobs if not only or j.name in only]
    out = (a.out or batch_export.resolve(ROOT, spec.output_dir)).resolve()
    print(f"{a.spec}: {len(jobs)} jobs, {json.dumps(spec.settings())} -> {out}")
    for j in jobs:
        print(f"  {j.name}: {', '.join(render_views.output_names(spec)[:4])}, ...")
    if a.check:
        return 0
    blender = find_blender(a.blender)
    if blender is None:
        print("no Blender executable found (--blender or $CE_BLENDER)")
        return 1
    manifest_path = out / "manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()
    passed = {k: v for k, v in overrides.items() if v is not None}
    code, secs, log = run_logged([blender, "-b", "--factory-startup", "--python", SCRIPT, "--", "--spec", a.spec,
                                  "--out", out, "--only", ",".join(only), "--overrides", json.dumps(passed),
                                  "--commit", _git_commit()],
                                 "render_views", env={"CHARACTER_ENGINE_SRC": str(ROOT / "src")}, timeout=a.timeout)
    results, meta = {}, {}
    if manifest_path.exists():
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        results = {r["name"]: {k: v for k, v in r.items() if k != "name"} for r in doc["jobs"]}
        meta = {k: v for k, v in doc.items() if k not in ("jobs", "jobs_total", "passed", "failed")}
    for j in jobs:   # a Blender crash leaves later jobs without a result: record why
        if j.name not in results or results[j.name].get("error") == "not run":
            results[j.name] = {"status": "FAIL", "error": f"not run (Blender exit code {code}, log {log})",
                               "job": j.to_dict()}
    doc = batch_export.manifest(jobs, results, **meta, blender_exit_code=code, blender_seconds=round(secs, 1),
                                blender_log=str(log))
    out.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print("\n== render views ==")
    for row in doc["jobs"]:
        print(f"  {row['status']:4s}  {row['name']}  {row.get('times', '')}"
              + (f"  ({row['error']})" if row.get("error") else ""))
    print(f"  {doc['passed']}/{doc['jobs_total']} passed in {secs:.1f} s; manifest {manifest_path}")
    return 0 if doc["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
