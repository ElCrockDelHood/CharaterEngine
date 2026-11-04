"""F2 of docs/architecture/ASSET_FITTING_PROPOSAL.md: fit the BodyParts3D left femur onto the canonical rig.

    blender -b --factory-startup --python runtime/blender/ce_f2_femur_fit.py -- \
        --bp3d C:/DEV/Assets/BodyParts3D_4.0/extracted/partof_BP3D_4.0_obj_99 \
        --out  C:/DEV/Assets/BodyParts3D_4.0/out
    (or set CE_BP3D_DIR / CE_F2_OUT instead of the arguments; driven by scripts/f2_femur_fit.py)

INTERNAL USE ONLY (Decision 62): the OBJ files stay outside the repo; the .blend and the full results JSON are written
to ``--out`` (outside the repo). Only a numeric summary goes to docs/audit (written by the driver, not here).

Steps (all anchors and derived targets are ESTIMATE; see docs/architecture/FEMUR_ANCHOR_LANDMARKS_PROPOSAL.md):
1. import FJ3259 (left femur) and FJ3365 (right femur) raw: mm, Z-up, -Y front, left = +X (A18);
2. asset anchors: femoral head centre = least-squares sphere on the proximal-medial vertices (one outlier pass);
   lateral / medial epicondyle = extreme vertices along ±X in the distal 10 %;
3. canonical targets (1.80 m skeleton, read-only): head centre -> FEMUR_L.head (hip joint); knee centre ->
   FEMUR_L.tail; epicondyles -> knee centre ± half the asset's epicondylar width (scaled) along the canonical
   lateral axis. The epicondyle targets are DERIVED FROM THE ASSET (no measured canonical epicondyles exist), so they
   carry the roll and the knee centre, not an independent width;
4. similarity registration (domain/assets/registration.py) -> RMS per anchor;
5. checks: (a) canonical joints untouched (bytes + every head/tail), (b) length vs Trotter (Decision 16) and the
   along-axis stretch that would be needed, (c) roll defined by the 3 anchors, (d) right femur by mirror (x -> -x,
   winding reversed) compared with the real FJ3365, (e) anchor RMS in mm.
Nothing is fixed as a tolerance here; the proposed 2 mm RMS (ESTIMATE) is only compared against.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path

try:
    import bmesh  # type: ignore
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
    from mathutils.kdtree import KDTree  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("run inside Blender: blender -b --python ...") from exc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.anatomy.osteometry.long_bones import load_osteometry  # noqa: E402
from character_engine.domain.assets.registration import (  # noqa: E402
    determinant,
    fit_sphere,
    register,
    spread_ratio,
)

CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
LEFT, RIGHT = "FJ3259", "FJ3365"
MM = 0.001
# Region selection for the anchors (ESTIMATE, from FEMUR_ANCHOR_LANDMARKS_PROPOSAL.md)
HEAD_TOP_FRACTION = 0.12        # proximal slice searched for the femoral head
HEAD_OUTLIER_M = 0.003          # second sphere pass keeps points within 3 mm of the first sphere
DISTAL_FRACTION = 0.10          # distal slice searched for the epicondyles
PROPOSED_RMS_MM = 2.0           # proposal §5, ESTIMATE, pending owner — compared, never enforced


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--bp3d", default=os.environ.get("CE_BP3D_DIR"))
    p.add_argument("--out", default=os.environ.get("CE_F2_OUT"))
    a = p.parse_args(argv)
    if not a.bp3d or not a.out:
        raise SystemExit("need --bp3d and --out (or CE_BP3D_DIR / CE_F2_OUT)")
    return Path(a.bp3d), Path(a.out)


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _joints(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return {b["canonical_name"]: (tuple(b["head"].values()), tuple(b["tail"].values())) for b in data["bones"]}


def _header_bounds(path: Path):
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("# Bounds(mm)"):
            return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", line.split(":", 1)[1])]
    return None


def import_obj(path: Path, name: str):
    before = set(bpy.data.objects)
    # BP3D is already Z-up / -Y front: keep raw coordinates (no axis conversion, no scale)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z", global_scale=1.0)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if len(new) != 1:
        raise SystemExit(f"{path.name}: expected 1 mesh, got {len(new)}")
    obj = new[0]
    obj.name = name
    return obj


def verts_world(obj):
    mw = obj.matrix_world
    return [tuple(mw @ v.co) for v in obj.data.vertices]


def signed_volume(obj) -> float:
    """Signed volume (mesh units³); > 0 means outward-facing winding."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    vol = 0.0
    for f in bm.faces:
        a, b, c = (v.co for v in f.verts)
        vol += a.dot(b.cross(c)) / 6.0
    bm.free()
    return vol


def anchors_left_femur(v_m):
    zs = [p[2] for p in v_m]
    zmin, zmax = min(zs), max(zs)
    top = [p for p in v_m if p[2] > zmax - HEAD_TOP_FRACTION * (zmax - zmin)]
    xmed = statistics.median(p[0] for p in top)
    cand = [p for p in top if p[0] < xmed]                 # medial half (left femur: medial = towards -X)
    c1, r1, _ = fit_sphere(cand)
    kept = [p for p in cand if abs(math.dist(p, c1) - r1) < HEAD_OUTLIER_M]
    head, radius, sphere_rms = fit_sphere(kept)
    distal = [p for p in v_m if p[2] < zmin + DISTAL_FRACTION * (zmax - zmin)]
    lateral = max(distal, key=lambda p: p[0])               # left femur: lateral = +X
    medial = min(distal, key=lambda p: p[0])
    return {"head": head, "lateral": lateral, "medial": medial}, {
        "head_points": len(kept), "head_points_first_pass": len(cand), "head_radius_mm": radius / MM,
        "head_sphere_rms_mm": sphere_rms / MM, "distal_points": len(distal)}


def mirror_x(p):
    return (-p[0], p[1], p[2])


def nearest_stats(src, dst_tree):
    d = [dst_tree.find(Vector(p))[2] for p in src]
    d.sort()
    return {"mean_mm": statistics.mean(d) / MM, "rms_mm": math.sqrt(sum(x * x for x in d) / len(d)) / MM,
            "p95_mm": d[int(0.95 * (len(d) - 1))] / MM, "max_mm": d[-1] / MM}


def tree(points):
    t = KDTree(len(points))
    for i, p in enumerate(points):
        t.insert(Vector(p), i)
    t.balance()
    return t


def symmetric(a, b):
    ab, ba = nearest_stats(a, tree(b)), nearest_stats(b, tree(a))
    return {"a_to_b": ab, "b_to_a": ba, "max_mm": max(ab["max_mm"], ba["max_mm"]),
            "mean_mm": (ab["mean_mm"] + ba["mean_mm"]) / 2}


def main() -> int:
    bp3d, out = _args()
    out.mkdir(parents=True, exist_ok=True)
    fp_before, joints_before = _fingerprint(CANONICAL), _joints(CANONICAL)
    bpy.ops.wm.read_factory_settings(use_empty=True)

    paths = {LEFT: bp3d / f"{LEFT}.obj", RIGHT: bp3d / f"{RIGHT}.obj"}
    objs = {k: import_obj(p, k) for k, p in paths.items()}
    raw = {k: verts_world(o) for k, o in objs.items()}
    # import sanity: Blender coordinates == BP3D header bounds (no hidden axis swap)
    import_check = {}
    for k, p in paths.items():
        hb = _header_bounds(p)
        mn = [min(v[i] for v in raw[k]) for i in range(3)]
        mx = [max(v[i] for v in raw[k]) for i in range(3)]
        import_check[k] = max(abs(a - b) for a, b in zip(mn + mx, hb))
    if max(import_check.values()) > 0.01:
        raise SystemExit(f"imported bounds differ from the OBJ header: {import_check}")

    v_l = [tuple(c * MM for c in p) for p in raw[LEFT]]
    v_r = [tuple(c * MM for c in p) for p in raw[RIGHT]]
    anchors, anchor_info = anchors_left_femur(v_l)

    bones = joints_before
    hip, knee = Vector(bones["FEMUR_L"][0]), Vector(bones["FEMUR_L"][1])
    axis = (hip - knee).normalized()
    lateral_dir = (Vector((1.0, 0.0, 0.0)) - axis * axis.x).normalized()      # canonical lateral for _L, ⟂ axis
    a_head, a_lat, a_med = (Vector(anchors[k]) for k in ("head", "lateral", "medial"))
    a_knee = (a_lat + a_med) / 2                                          # biomechanics.json: equidistant (ASSUMED)
    s0 = (hip - knee).length / (a_head - a_knee).length
    half_w = (a_lat - a_med).length * s0 / 2
    targets = {"head": tuple(hip), "lateral": tuple(knee + lateral_dir * half_w),
               "medial": tuple(knee - lateral_dir * half_w)}
    order = ("head", "lateral", "medial")
    reg = register([anchors[k] for k in order], [targets[k] for k in order], with_scale=True)

    # apply to the left femur (canonical metres)
    fitted_l = [reg.apply(p) for p in v_l]
    me = objs[LEFT].data
    for v, p in zip(me.vertices, fitted_l):
        v.co = Vector(p)
    objs[LEFT].matrix_world.identity()
    objs[LEFT].name = "FEMUR_L_BP3D_fitted"

    # (b) length along the canonical bone axis vs Trotter
    proj = [Vector(p).dot(axis) for p in fitted_l]
    fitted_len = max(proj) - min(proj)
    trotter = load_osteometry().lengths_for_stature(1.80)["FEMUR"]
    raw_axis = (a_head - a_knee).normalized()
    raw_len = (max(Vector(p).dot(raw_axis) for p in v_l) - min(Vector(p).dot(raw_axis) for p in v_l))

    # (c) roll: angle between the fitted epicondyle axis (⟂ bone axis) and the canonical lateral direction
    f_lat, f_med = Vector(reg.apply(anchors["lateral"])), Vector(reg.apply(anchors["medial"]))
    ml = f_lat - f_med
    ml_perp = (ml - axis * ml.dot(axis)).normalized()
    roll_deg = math.degrees(math.atan2(axis.dot(lateral_dir.cross(ml_perp)), lateral_dir.dot(ml_perp)))

    # (d) mirror: raw left mirrored (x -> -x, winding reversed) vs the real right femur, both raw (BP3D frame)
    mirrored_raw = [mirror_x(p) for p in v_l]
    mir = bpy.data.objects.new("FEMUR_R_from_mirror", bpy.data.meshes.new("FEMUR_R_from_mirror"))
    bpy.context.scene.collection.objects.link(mir)
    bm = bmesh.new()
    bm.from_mesh(objs[LEFT].data)
    for v in bm.verts:
        v.co.x = -v.co.x                                    # mirror the fitted left femur across the sagittal plane
    bm.to_mesh(mir.data)
    vol_mirror_no_fix = signed_volume(mir)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(mir.data)
    bm.free()
    mir.data.update()
    vol_mirror_fixed = signed_volume(mir)
    vol_left = signed_volume(objs[LEFT])

    # real right femur registered with its own anchors onto the mirrored canonical targets
    r_anchors, r_info = anchors_left_femur([mirror_x(p) for p in v_r])     # same rule on the mirror image
    r_anchors = {k: mirror_x(p) for k, p in r_anchors.items()}
    r_targets = {k: mirror_x(p) for k, p in targets.items()}
    reg_r = register([r_anchors[k] for k in order], [r_targets[k] for k in order], with_scale=True)
    fitted_r = [reg_r.apply(p) for p in v_r]
    mirrored_fitted = [mirror_x(p) for p in fitted_l]
    for v, p in zip(objs[RIGHT].data.vertices, fitted_r):
        v.co = Vector(p)
    objs[RIGHT].matrix_world.identity()
    objs[RIGHT].name = "FEMUR_R_BP3D_fitted"

    # (a) canonical joints after everything
    fp_after, joints_after = _fingerprint(CANONICAL), _joints(CANONICAL)
    moved = [n for n in joints_before if joints_before[n] != joints_after[n]]

    blend = out / "f2_femur_fit.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))

    res = {
        "status": "F2 measured; tolerances PENDING (all ESTIMATE)",
        "blender": bpy.app.version_string,
        "inputs": {k: {"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for k, p in paths.items()},
        "import_bounds_vs_header_max_abs_mm": import_check,
        "anchors_asset_mm": {k: [c / MM for c in v] for k, v in anchors.items()},
        "anchor_extraction": anchor_info,
        "targets_m": targets,
        "target_provenance": {"head": "FEMUR_L.head (canonical hip joint, read-only)",
                              "lateral/medial": "FEMUR_L.tail ± asset epicondylar half-width × s0 along canonical "
                                                "lateral ⟂ bone axis — DERIVED from the asset, ESTIMATE"},
        "registration_left": {"scale": reg.scale, "det_rotation": determinant(reg.rotation),
                              "rotation": reg.rotation, "translation_m": reg.translation,
                              "residuals_mm": {k: e / MM for k, e in zip(order, reg.residuals)},
                              "rms_mm": reg.rms / MM, "spread_ratio": reg.spread_ratio,
                              "chirality_checked": reg.chirality_checked,
                              "meets_proposed_2mm_rms": reg.rms / MM <= PROPOSED_RMS_MM},
        "registration_right": {"scale": reg_r.scale, "rms_mm": reg_r.rms / MM,
                               "residuals_mm": {k: e / MM for k, e in zip(order, reg_r.residuals)},
                               "anchor_extraction": r_info},
        "a_joints": {"canonical_fingerprint_before": fp_before, "after": fp_after,
                     "bones_compared": len(joints_before), "moved": moved},
        "b_length": {"trotter_femur_max_length_m": trotter, "fitted_length_along_bone_axis_m": fitted_len,
                     "asset_raw_length_along_its_axis_mm": raw_len / MM,
                     "canonical_joint_segment_m": (hip - knee).length,
                     "length_error_pct_vs_trotter": 100 * (fitted_len - trotter) / trotter,
                     "along_axis_stretch_to_trotter": trotter / fitted_len,
                     "note": "stretch NOT applied: it would move the knee anchor off FEMUR_L.tail"},
        "c_roll": {"spread_ratio_anchors": spread_ratio([anchors[k] for k in order]),
                   "roll_error_deg": roll_deg,
                   "fitted_epicondyle_axis_dot_lateral": ml_perp.dot(lateral_dir)},
        "d_mirror": {"signed_volume_cm3": {"left_fitted": vol_left * 1e6, "mirror_without_winding_fix": vol_mirror_no_fix * 1e6,
                                          "mirror_with_winding_fix": vol_mirror_fixed * 1e6},
                     "raw_mirrored_left_vs_real_right": symmetric(mirrored_raw, v_r),
                     "fitted_mirror_vs_fitted_right": symmetric(mirrored_fitted, fitted_r)},
        "e_anchor_rms_mm": reg.rms / MM,
        "outputs": {"blend": str(blend)},
    }
    (out / "f2_femur_fit_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("CE_F2_RESULT " + json.dumps({"rms_mm": res["e_anchor_rms_mm"], "moved": moved,
                                         "len_err_pct": res["b_length"]["length_error_pct_vs_trotter"],
                                         "roll_deg": roll_deg,
                                         "mirror_mean_mm": res["d_mirror"]["raw_mirrored_left_vs_real_right"]["mean_mm"]}))
    return 0 if not moved and fp_before == fp_after else 1


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
