"""Batch asset export: template x stature x pose x optional clip -> one GLB + provenance sidecar per job.

    python scripts/batch_export.py                                   # scripts/batch_specs/default.json
    python scripts/batch_export.py --spec scripts/batch_specs/ual1_local.json
    python scripts/batch_export.py --only human_male_adult_1800mm_tpose
    python scripts/batch_export.py --validate-godot                  # + Godot skeleton validator per GLB
    python scripts/batch_export.py --check                           # validate + list jobs, no Blender

The spec is validated in pure Python first (``character_engine.pipeline.batch_export``): unknown or unavailable
templates (horse, dog), poses, bone maps or missing clip files refuse the whole run (exit 2). Blender then runs
in background (``runtime/blender/ce_batch_export.py``) and writes ``<out>/<job>.glb``,
``<out>/<job>.provenance.json`` and ``<out>/manifest_<spec>_<UTC>.json`` (PASS/FAIL per job, one file per run so
earlier runs are kept; the newest is also copied to ``manifest.json``, the single file older versions overwrote).
A failing job does not stop the others. Default output ``builds/exports/batch/`` (git-ignored). Every run is
logged through ``_logrun`` (``logs/<UTC>_batch_export.log``; Godot runs in ``logs/<UTC>_batch_godot.log``).

``--validate-godot`` runs ``runtime/godot/ce_skeleton_validator.gd`` on each PASS GLB when Godot is found
(``$CE_GODOT``, ``C:/Tools/Godot``, PATH; same discovery as ``engine_tests.py``); otherwise every job is marked SKIPPED.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _logrun import _git_commit, run_logged, utf8_console
from engine_tests import find_blender, find_godot

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.pipeline import batch_export  # noqa: E402

SCRIPT = ROOT / "runtime" / "blender" / "ce_batch_export.py"
DEFAULT_SPEC = ROOT / "scripts" / "batch_specs" / "default.json"
GODOT_PROJECT = ROOT / "runtime" / "godot"


def validate_godot(doc: dict, timeout: int) -> int:
    """Add a ``godot`` verdict to every job; returns the number of Godot failures."""
    godot = find_godot()
    if godot is None:
        print("[godot] not found: validation SKIPPED")
        for row in doc["jobs"]:
            row["godot"] = {"status": "SKIPPED", "detail": "Godot not found"}
        return 0
    if not (GODOT_PROJECT / ".godot").exists():
        run_logged([godot, "--headless", "--path", GODOT_PROJECT, "--import"], "batch_godot", timeout=timeout)
    failures = 0
    for row in doc["jobs"]:
        if row.get("status") != "PASS":
            row["godot"] = {"status": "SKIPPED", "detail": "export failed"}
            continue
        code, secs, log = run_logged([godot, "--headless", "--path", GODOT_PROJECT, "--script",
                                      "res://ce_skeleton_validator.gd", "--", "--glb", Path(row["glb"]).resolve()],
                                     "batch_godot", timeout=timeout)
        row["godot"] = {"status": "PASS" if code == 0 else "FAIL", "exit_code": code, "seconds": round(secs, 1),
                        "log": str(log), "godot": str(godot)}
        failures += code != 0
    return failures


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--out", type=Path, default=None, help="output folder (default: the spec's output_dir)")
    ap.add_argument("--only", default="", help="comma-separated job names")
    ap.add_argument("--blender", default=None, help="Blender executable (default: engine_tests discovery)")
    ap.add_argument("--validate-godot", action="store_true")
    ap.add_argument("--check", action="store_true", help="validate the spec and list the jobs, then stop")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)
    utf8_console()
    try:
        spec = batch_export.load_spec(a.spec)
        jobs = batch_export.expand(spec, root=ROOT)
    except (OSError, batch_export.BatchSpecError) as exc:
        print(f"refused: {exc}")
        return 2
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    if only - {j.name for j in jobs}:
        print(f"refused: --only names not in the spec: {sorted(only - {j.name for j in jobs})}")
        return 2
    jobs = [j for j in jobs if not only or j.name in only]
    out = (a.out or batch_export.resolve(ROOT, spec.get("output_dir", batch_export.DEFAULT_OUTPUT_DIR))).resolve()
    print(f"{a.spec}: {len(jobs)} jobs -> {out}")
    for j in jobs:
        print(f"  {j.name}")
    if a.check:
        return 0
    blender = find_blender(a.blender)
    if blender is None:
        print("no Blender executable found (--blender or $CE_BLENDER)")
        return 1
    run = batch_export.run_id()
    manifest_path = out / batch_export.manifest_name(a.spec, run)
    code, secs, log = run_logged([blender, "-b", "--factory-startup", "--python", SCRIPT, "--", "--spec", a.spec,
                                  "--out", out, "--only", ",".join(only), "--commit", _git_commit(), "--run-id", run],
                                 "batch_export", env={"CHARACTER_ENGINE_SRC": str(ROOT / "src")}, timeout=a.timeout)
    results = {}
    meta = {}
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
    godot_failures = validate_godot(doc, a.timeout) if a.validate_godot else 0
    out.mkdir(parents=True, exist_ok=True)
    batch_export.write_manifest(out, manifest_path.name, doc)
    print("\n== batch export ==")
    for row in doc["jobs"]:
        g = f"  godot {row['godot']['status']}" if "godot" in row else ""
        print(f"  {row['status']:4s}  {row['name']}  {row.get('seconds', '-')} s{g}"
              + (f"  ({row['error']})" if row.get("error") else ""))
    print(f"  {doc['passed']}/{doc['jobs_total']} passed in {secs:.1f} s; manifest {manifest_path}")
    print(f"  repeat: python scripts/batch_export.py --spec {a.spec}" + (" --validate-godot" if a.validate_godot else ""))
    return 0 if doc["failed"] == 0 and godot_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
