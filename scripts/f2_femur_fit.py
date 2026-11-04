"""F2 femur fit driver: runs runtime/blender/ce_f2_femur_fit.py in Blender 3.6 headless and writes the numeric
summary docs/audit/A19_F2_FEMUR_FIT.json (no geometry, no anchor coordinates).

    python scripts/f2_femur_fit.py --bp3d C:/DEV/Assets/BodyParts3D_4.0/extracted/partof_BP3D_4.0_obj_99 \
        --out C:/DEV/Assets/BodyParts3D_4.0/out [--blender C:/DEV/Tools/Blender/blender.exe] [--no-summary]

BodyParts3D is INTERNAL USE ONLY (Decision 62): the OBJ files, the .blend and the full results JSON stay in --out,
outside the repo. Log: logs/<UTC>_blender.log (scripts/_logrun.py).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from _logrun import run_logged
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "blender" / "ce_f2_femur_fit.py"
SUMMARY = ROOT / "docs" / "audit" / "A19_F2_FEMUR_FIT.json"


def summary(res: dict) -> dict:
    left, right = res["registration_left"], res["registration_right"]
    return {
        "status": res["status"],
        "licence": "BodyParts3D 4.0, INTERNAL USE ONLY (Decision 62)",
        "blender": res["blender"],
        "inputs_sha256": {k: v["sha256"] for k, v in res["inputs"].items()},
        "import_bounds_vs_header_max_abs_mm": res["import_bounds_vs_header_max_abs_mm"],
        "anchor_extraction": res["anchor_extraction"],
        "target_provenance": res["target_provenance"],
        "left": {k: left[k] for k in ("scale", "det_rotation", "residuals_mm", "rms_mm", "spread_ratio",
                                       "chirality_checked", "meets_proposed_2mm_rms")},
        "right_own_anchors": {k: right[k] for k in ("scale", "residuals_mm", "rms_mm")},
        "a_joints": res["a_joints"],
        "b_length": res["b_length"],
        "c_roll": res["c_roll"],
        "d_mirror": res["d_mirror"],
        "e_anchor_rms_mm": res["e_anchor_rms_mm"],
        "proposed_rms_mm_estimate": 2.0,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bp3d", default=os.environ.get("CE_BP3D_DIR"))
    p.add_argument("--out", default=os.environ.get("CE_F2_OUT"))
    p.add_argument("--blender")
    p.add_argument("--no-summary", action="store_true")
    a = p.parse_args()
    if not a.bp3d or not a.out:
        p.error("need --bp3d and --out (or CE_BP3D_DIR / CE_F2_OUT)")
    out = Path(a.out).resolve()
    if ROOT in out.parents or out == ROOT:
        p.error("--out must be outside the repo (Decision 62)")
    blender = find_blender(a.blender)
    if blender is None:
        p.error("Blender not found (set CE_BLENDER or --blender)")
    cmd = [str(blender), "-b", "--factory-startup", "--python", str(SCRIPT), "--",
           "--bp3d", str(Path(a.bp3d)), "--out", str(out)]
    code, _, log = run_logged(cmd, "blender")
    if code != 0:
        print(f"Blender exit {code}; see {log}")
        return code
    res = json.loads((out / "f2_femur_fit_results.json").read_text(encoding="utf-8"))
    if not a.no_summary:
        SUMMARY.write_text(json.dumps(summary(res), indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"summary -> {SUMMARY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
