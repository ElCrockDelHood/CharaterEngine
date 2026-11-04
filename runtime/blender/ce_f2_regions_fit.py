"""F2 by regions (A22): the whole BodyParts3D skeleton compared with the canonical one, region by region.

    blender -b --factory-startup --python runtime/blender/ce_f2_regions_fit.py -- \
        --bp3d C:/DEV/Assets/BodyParts3D_4.0/extracted/partof_BP3D_4.0_obj_99 \
        --out  C:/DEV/Assets/BodyParts3D_4.0/out
    (driven by ``scripts/f2_femur_fit.py --regions``)

INTERNAL USE ONLY (Decision 62): OBJ files, the .blend and the full results JSON stay in ``--out``.
Method in ``domain/assets/skeleton_regions.py``: one global similarity on the 8 measured limb joint centres
(hip, knee, shoulder, elbow; A20 anchor rules), then every bone against its canonical segment, per region; mirror of
every bilateral pair (raw left mirrored vs raw right); proposed pelvic landmarks as distances only.
Reuses the helpers of ``ce_f2_femur_fit.py`` (import, KD-tree mirror distance, fingerprint).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import bpy  # type: ignore
    from mathutils import Matrix  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("run inside Blender: blender -b --python ...") from exc

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import ce_f2_femur_fit as f2  # noqa: E402

from character_engine.domain.assets.long_bone_fit import RULES, end_point, extract_anchors  # noqa: E402
from character_engine.domain.assets.registration import determinant, register  # noqa: E402
from character_engine.domain.assets.skeleton_regions import (  # noqa: E402
    GLOBAL_ANCHORS,
    REGIONS,
    all_region_bones,
    anchor_targets,
    bone_metrics,
    pelvis_dimensions,
    pelvis_landmarks,
    region_summary,
)

MM = 0.001


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--bp3d", default=os.environ.get("CE_BP3D_DIR"))
    p.add_argument("--out", default=os.environ.get("CE_F2_OUT"))
    a = p.parse_args(argv)
    if not a.bp3d or not a.out:
        raise SystemExit("need --bp3d and --out (or CE_BP3D_DIR / CE_F2_OUT)")
    return Path(a.bp3d), Path(a.out)


def _elements(entry):
    """OBJ file ids for one canonical bone (A18): duplicates use the first file, compounds use all of them."""
    els = [e["file_id"] for e in entry["elements"]]
    return els[:1] if entry["status"] == "MAPPED_DUPLICATE" else els


def main() -> int:
    bp3d, out = _args()
    out.mkdir(parents=True, exist_ok=True)
    fp_before, joints = f2._fingerprint(f2.CANONICAL), f2._joints(f2.CANONICAL)
    a18 = {b["canonical"]: b for b in json.loads(f2.MAPPING.read_text(encoding="utf-8"))["bones"]}
    bpy.ops.wm.read_factory_settings(use_empty=True)

    raw, failed = {}, {}
    for bone in all_region_bones():
        entry = a18.get(bone)
        if not entry or not entry["elements"]:
            continue
        try:
            pts = []
            for fid in _elements(entry):
                obj = f2.import_obj(bp3d / f"{fid}.obj", f"{bone}_{fid}")
                pts += [tuple(c * MM for c in (obj.matrix_world @ v.co)) for v in obj.data.vertices]
            raw[bone] = pts
        except Exception as exc:
            failed[bone] = f"{type(exc).__name__}: {exc}"

    # 1. global similarity on the measured limb joint centres
    asset_pts, names = [], []
    for bone, end in GLOBAL_ANCHORS:
        base, side = bone[:-2], bone[-1]
        anchors, _ = extract_anchors(RULES[base], raw[bone], side)
        rule = RULES[base]
        asset_pts.append(end_point(rule.proximal if end == "proximal" else rule.distal, anchors))
        names.append(f"{bone}.{end}")
    reg = register(asset_pts, anchor_targets(joints), with_scale=True)

    # 2. every bone in the canonical frame
    metrics, fitted = {}, {}
    for bone, pts in raw.items():
        fitted[bone] = [reg.apply(p) for p in pts]
        head, tail = joints[bone]
        metrics[bone] = bone_metrics(fitted[bone], head, tail)

    # 3. mirror of every bilateral pair (raw, BP3D frame)
    mirror = {}
    for bone in raw:
        if bone.endswith("_L") and bone[:-2] + "_R" in raw:
            m = f2.symmetric([f2._mirror(p) for p in raw[bone]], raw[bone[:-2] + "_R"])
            mirror[bone[:-2]] = {k: m[k] for k in ("mean_mm", "p95_mm", "max_mm")}

    # 4. pelvis: proposed landmarks (distances only), hip centres from the femoral head spheres
    hips = {s: asset_pts[names.index(f"FEMUR_{s}.proximal")] for s in ("L", "R")}
    lm = pelvis_landmarks(raw["COXAL_L"], raw["COXAL_R"]) if "COXAL_L" in raw and "COXAL_R" in raw else None
    pelvis = None
    if lm:
        pelvis = {"asset_mm": pelvis_dimensions(lm, hips["L"], hips["R"]),
                  "asset_scaled_to_canonical_mm": {k: v * reg.scale for k, v in
                                                   pelvis_dimensions(lm, hips["L"], hips["R"]).items()},
                  "canonical_inter_hip_centre_width_mm":
                      abs(joints["FEMUR_L"][0][0] - joints["FEMUR_R"][0][0]) * 1e3}

    fp_after, joints_after = f2._fingerprint(f2.CANONICAL), f2._joints(f2.CANONICAL)
    moved = [n for n in joints if joints[n] != joints_after[n]]
    blend = out / "f2_regions_fit.blend"
    r, t, sc = reg.rotation, reg.translation, reg.scale
    m = Matrix([[sc * r[0][0] * MM, sc * r[0][1] * MM, sc * r[0][2] * MM, t[0]],
                [sc * r[1][0] * MM, sc * r[1][1] * MM, sc * r[1][2] * MM, t[1]],
                [sc * r[2][0] * MM, sc * r[2][1] * MM, sc * r[2][2] * MM, t[2]],
                [0.0, 0.0, 0.0, 1.0]])
    for obj in list(bpy.data.objects):          # the .blend shows the registered skeleton, metres, canonical frame
        if obj.type == "MESH":
            obj.data.transform(obj.matrix_world)
            obj.matrix_world.identity()
            obj.data.transform(m)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))

    res = {
        "status": "F2 regions measured; tolerances PENDING (all ESTIMATE)", "blender": bpy.app.version_string,
        "global_registration": {"anchors": names, "scale": reg.scale, "det_rotation": determinant(reg.rotation),
                                "residuals_mm": dict(zip(names, (e / MM for e in reg.residuals))),
                                "rms_mm": reg.rms / MM, "chirality_checked": reg.chirality_checked},
        "regions": {r: region_summary(metrics, bones) for r, bones in REGIONS.items()},
        "bones": metrics, "mirror": mirror, "pelvis": pelvis, "failed": failed,
        "joints": {"canonical_fingerprint_before": fp_before, "after": fp_after,
                   "bones_compared": len(joints), "moved": moved},
        "outputs": {"blend": str(blend)},
    }
    (out / "f2_regions_fit_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("CE_F2_REGIONS " + json.dumps({"fitted": len(metrics), "failed": list(failed), "moved": moved,
                                         "global_rms_mm": round(reg.rms / MM, 2)}))
    return 0 if not moved and fp_before == fp_after and not failed else 1


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
