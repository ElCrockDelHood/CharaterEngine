"""F2 long-bone fit driver: runs runtime/blender/ce_f2_femur_fit.py in Blender 3.6 headless and writes the numeric
summary docs/audit/A20_F2_LONG_BONES_FIT.json (no geometry, no anchor coordinates).

    python scripts/f2_femur_fit.py --bp3d C:/DEV/Assets/BodyParts3D_4.0/extracted/partof_BP3D_4.0_obj_99 \
        --out C:/DEV/Assets/BodyParts3D_4.0/out [--bones FEMUR,TIBIA,...] [--blender ...] [--no-summary]
    python scripts/f2_femur_fit.py --regions --bp3d ... --out ...   # whole skeleton by regions -> A22 summary

Default: all six long bones (FEMUR, TIBIA, FIBULA, HUMERUS, RADIUS, ULNA), left and right. The summary also compares
the femur with the committed A19 result (Decision 63). ``--bones FEMUR`` re-measures the femur alone (A19 values).

BodyParts3D is INTERNAL USE ONLY (Decision 62): the OBJ files, the .blend and the full results JSON stay in --out,
outside the repo. Log: logs/<UTC>_blender.log (scripts/_logrun.py).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

from _logrun import run_logged
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "blender" / "ce_f2_femur_fit.py"
REGIONS_SCRIPT = ROOT / "runtime" / "blender" / "ce_f2_regions_fit.py"
SUMMARY = ROOT / "docs" / "audit" / "A20_F2_LONG_BONES_FIT.json"
REGIONS_SUMMARY = ROOT / "docs" / "audit" / "A22_SKELETON_REGIONS_FIT.json"
A19 = ROOT / "docs" / "audit" / "A19_F2_FEMUR_FIT.json"


def _stats(values):
    v = sorted(values)
    return {"n": len(v), "min": v[0], "median": statistics.median(v), "max": v[-1],
            "mean": statistics.mean(v), "stdev": statistics.stdev(v) if len(v) > 1 else 0.0}


def summary(res: dict) -> dict:
    rows, per_bone = [], {}
    for bone, b in res["bones"].items():
        m = b["mirror"]
        per_bone[bone] = {
            "bp3d_files": {s: b["bp3d_files"][s]["file"] for s in ("L", "R")},
            "rule": b["rule"], "anchors": b["anchor_names"], "trotter_max_length_m": b["trotter_max_length_m"],
            "mirror": {"signed_volume_cm3": m["signed_volume_cm3"],
                       "raw_mirrored_left_vs_real_right_mm": {k: m["raw_mirrored_left_vs_real_right"][k]
                                                              for k in ("mean_mm", "p95_mm", "max_mm")},
                       "fitted_mirror_vs_fitted_right_mm": {k: m["fitted_mirror_vs_fitted_right"][k]
                                                            for k in ("mean_mm", "p95_mm", "max_mm")}},
        }
        for s in ("L", "R"):
            x = b[s]
            keep = ("scale", "rms_mm", "residuals_mm", "spread_ratio", "planarity_ratio", "chirality_checked",
                    "meets_proposed_2mm_rms", "canonical_joint_segment_m", "asset_joint_distance_mm",
                    "fitted_length_along_bone_axis_m", "length_error_pct_vs_trotter",
                    "along_axis_stretch_to_trotter", "roll_error_deg", "target_provenance")
            per_bone[bone][s] = {k: x[k] for k in keep}
            per_bone[bone][s]["anchor_extraction"] = {
                n: {k: v for k, v in i.items() if k in ("points", "radius_mm", "sphere_rms_mm")}
                for n, i in x["anchor_extraction"].items()}
            rows.append({"bone": bone, "side": s, "rms_mm": x["rms_mm"], "max_residual_mm": max(x["residuals_mm"].values()),
                         "scale": x["scale"], "length_error_pct": x["length_error_pct_vs_trotter"],
                         "roll_error_deg": x["roll_error_deg"], "spread_ratio": x["spread_ratio"]})
    mirrors = [b["mirror"]["raw_mirrored_left_vs_real_right"] for b in res["bones"].values()]
    dispersion = {
        "anchor_rms_mm": _stats([r["rms_mm"] for r in rows]),
        "anchor_max_residual_mm": _stats([r["max_residual_mm"] for r in rows]),
        "abs_length_error_pct_vs_trotter": _stats([abs(r["length_error_pct"]) for r in rows]),
        "similarity_scale": _stats([r["scale"] for r in rows]),
        "abs_roll_error_deg": _stats([abs(r["roll_error_deg"]) for r in rows]),
        "mirror_mean_mm": _stats([m["mean_mm"] for m in mirrors]),
        "mirror_p95_mm": _stats([m["p95_mm"] for m in mirrors]),
        "mirror_max_mm": _stats([m["max_mm"] for m in mirrors]),
        "bone_sides_meeting_proposed_2mm_rms": sum(r["rms_mm"] <= 2.0 for r in rows),
        "bone_sides_within_proposed_1pct_length": sum(abs(r["length_error_pct"]) <= 1.0 for r in rows),
    }
    out = {"status": res["status"], "licence": "BodyParts3D 4.0, INTERNAL USE ONLY (Decision 62)",
           "blender": res["blender"], "stature_m": res["stature_m"], "joints": res["joints"],
           "failed": res["failed"], "rows": rows, "dispersion": dispersion, "bones": per_bone,
           "proposed_estimates_compared": {"anchor_rms_mm": 2.0, "length_pct": 1.0, "mirror_mm": 1.0}}
    if "FEMUR" in res["bones"] and A19.exists():
        a = json.loads(A19.read_text(encoding="utf-8"))
        f = res["bones"]["FEMUR"]
        pairs = {"left_rms_mm": (a["left"]["rms_mm"], f["L"]["rms_mm"]),
                 "left_scale": (a["left"]["scale"], f["L"]["scale"]),
                 "right_rms_mm": (a["right_own_anchors"]["rms_mm"], f["R"]["rms_mm"]),
                 "left_length_m": (a["b_length"]["fitted_length_along_bone_axis_m"],
                                   f["L"]["fitted_length_along_bone_axis_m"]),
                 "mirror_raw_mean_mm": (a["d_mirror"]["raw_mirrored_left_vs_real_right"]["mean_mm"],
                                        f["mirror"]["raw_mirrored_left_vs_real_right"]["mean_mm"])}
        out["femur_vs_A19"] = {k: {"A19": x, "now": y, "abs_diff": abs(x - y)} for k, (x, y) in pairs.items()}
    return out


def regions_summary(res: dict) -> dict:
    """A22: global registration, per-region statistics, mirror pairs and pelvis distances (no coordinates)."""
    keep = ("centroid_to_segment_mm", "head_error_mm", "tail_error_mm", "extent_over_length", "axis_angle_deg")
    mirror = res["mirror"]
    means = sorted(v["mean_mm"] for v in mirror.values())
    return {
        "status": res["status"], "licence": "BodyParts3D 4.0, INTERNAL USE ONLY (Decision 62)",
        "blender": res["blender"], "joints": res["joints"], "failed": res["failed"],
        "global_registration": res["global_registration"],
        "regions": res["regions"],
        "bones": {b: {k: m[k] for k in keep} for b, m in res["bones"].items()},
        "mirror_pairs": mirror,
        "mirror_mean_mm_over_pairs": {"n": len(means), "min": means[0], "median": statistics.median(means),
                                      "max": means[-1]},
        "pelvis": res["pelvis"],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bp3d", default=os.environ.get("CE_BP3D_DIR"))
    p.add_argument("--out", default=os.environ.get("CE_F2_OUT"))
    p.add_argument("--bones", default="FEMUR,TIBIA,FIBULA,HUMERUS,RADIUS,ULNA")
    p.add_argument("--blender")
    p.add_argument("--no-summary", action="store_true")
    p.add_argument("--regions", action="store_true", help="whole skeleton by regions (A22) instead of long bones")
    a = p.parse_args()
    if not a.bp3d or not a.out:
        p.error("need --bp3d and --out (or CE_BP3D_DIR / CE_F2_OUT)")
    out = Path(a.out).resolve()
    if ROOT in out.parents or out == ROOT:
        p.error("--out must be outside the repo (Decision 62)")
    blender = find_blender(a.blender)
    if blender is None:
        p.error("Blender not found (set CE_BLENDER or --blender)")
    if a.regions:
        cmd = [str(blender), "-b", "--factory-startup", "--python", str(REGIONS_SCRIPT), "--",
               "--bp3d", str(Path(a.bp3d)), "--out", str(out)]
        code, _, log = run_logged(cmd, "blender")
        results = out / "f2_regions_fit_results.json"
        if code != 0:
            print(f"Blender exit {code}; see {log}" + (f" and {results}" if results.exists() else ""))
            return code
        if not a.no_summary:
            res = json.loads(results.read_text(encoding="utf-8"))
            REGIONS_SUMMARY.write_text(json.dumps(regions_summary(res), indent=1) + "\n", encoding="utf-8",
                                       newline="\n")
            print(f"summary -> {REGIONS_SUMMARY.relative_to(ROOT)}")
        return 0
    cmd = [str(blender), "-b", "--factory-startup", "--python", str(SCRIPT), "--",
           "--bp3d", str(Path(a.bp3d)), "--out", str(out), "--bones", a.bones]
    code, _, log = run_logged(cmd, "blender")
    name = "f2_femur_fit" if a.bones.strip().upper() == "FEMUR" else "f2_long_bones_fit"
    results = out / f"{name}_results.json"
    if code != 0:
        print(f"Blender exit {code}; see {log}" + (f" and {results}" if results.exists() else ""))
        return code
    res = json.loads(results.read_text(encoding="utf-8"))
    if not a.no_summary and name == "f2_long_bones_fit":
        SUMMARY.write_text(json.dumps(summary(res), indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"summary -> {SUMMARY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
