"""Run a batch export spec inside Blender (background). Launched by ``scripts/batch_export.py``.

    blender -b --factory-startup --python runtime/blender/ce_batch_export.py -- \
        --spec scripts/batch_specs/default.json --out builds/exports/batch [--only NAME,...] [--commit abc123]

Writes ``<out>/<job>.glb`` + ``<out>/<job>.provenance.json`` per job and ``<out>/manifest.json``
(rewritten after every job, so a crash still leaves the finished jobs recorded). A failing job is
recorded as FAIL and the next one runs. Exit code 0 = every job passed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

try:
    import bpy  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("run inside Blender: blender -b --python ...") from exc

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from character_engine.pipeline import batch_export  # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None, help="default: the spec's output_dir")
    ap.add_argument("--only", default="", help="comma-separated job names to run")
    ap.add_argument("--commit", default="")
    return ap.parse_args(argv)


def load_addon():
    src_addon = SRC / "character_engine" / "infrastructure" / "blender" / "addon"
    tmp = Path(tempfile.mkdtemp(prefix="ce_addon_"))
    shutil.copytree(src_addon, tmp / "character_engine_blender")
    sys.path.insert(0, str(tmp))
    import character_engine_blender  # type: ignore

    character_engine_blender.register()
    return character_engine_blender


def main() -> int:
    args = parse_args()
    spec = batch_export.load_spec(args.spec)
    jobs = batch_export.expand(spec, root=ROOT)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    if only:
        unknown = only - {j.name for j in jobs}
        if unknown:
            raise SystemExit(f"--only names not in the spec: {sorted(unknown)}")
        jobs = [j for j in jobs if j.name in only]
    out = args.out or batch_export.resolve(ROOT, spec.get("output_dir", batch_export.DEFAULT_OUTPUT_DIR))
    out.mkdir(parents=True, exist_ok=True)
    print(f"== Character Engine batch export: {len(jobs)} jobs, Blender {bpy.app.version_string} -> {out} ==",
          flush=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon = load_addon()
    meta = {"spec": str(args.spec), "spec_sha256": batch_export.sha256_file(args.spec),
            "blender_version": bpy.app.version_string, "addon_version": addon.batch.ADDON_VERSION,
            "repo_commit": args.commit, "output_dir": str(out),
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    results: dict = {}
    manifest_path = out / "manifest.json"
    t0 = time.time()
    for i, job in enumerate(jobs, 1):
        print(f"-- [{i}/{len(jobs)}] {job.name}", flush=True)
        t = time.time()
        try:
            results[job.name] = addon.batch.run_job(bpy.context, job, out, ROOT, args.commit)
            print(f"   PASS  {job.name}  {results[job.name]['bytes']} bytes in {results[job.name]['seconds']} s",
                  flush=True)
        except Exception as exc:  # noqa: BLE001 - one failing job must not stop the batch
            traceback.print_exc()
            results[job.name] = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}",
                                 "seconds": round(time.time() - t, 2)}
            print(f"   FAIL  {job.name}  {results[job.name]['error']}", flush=True)
        results[job.name]["job"] = job.to_dict()
        doc = batch_export.manifest(jobs, results, **meta, seconds=round(time.time() - t0, 1))
        manifest_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    doc = batch_export.manifest(jobs, results, **meta, seconds=round(time.time() - t0, 1))
    manifest_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"== batch: {doc['passed']} passed, {doc['failed']} failed in {doc['seconds']} s; manifest {manifest_path} ==",
          flush=True)
    return 0 if doc["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        code = 2
    sys.stdout.flush()
    sys.exit(code)
