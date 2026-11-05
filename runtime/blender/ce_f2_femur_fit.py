"""F2 of docs/architecture/ASSET_FITTING_PROPOSAL.md: fit BodyParts3D long bones onto the canonical rig.

    blender -b --factory-startup --python runtime/blender/ce_f2_femur_fit.py -- \
        --bp3d C:/DEV/Assets/BodyParts3D_4.0/extracted/partof_BP3D_4.0_obj_99 \
        --out  C:/DEV/Assets/BodyParts3D_4.0/out [--bones FEMUR,TIBIA,FIBULA,HUMERUS,RADIUS,ULNA]
    (or CE_BP3D_DIR / CE_F2_OUT; driven by scripts/f2_femur_fit.py). The file keeps its A19 name; it now fits
    every long bone listed (femur: A19 / Decision 63; all six: A20).

Meshes stay out of the repo (Decisions 46, 76): OBJ files, the .blend and the full results JSON stay in ``--out`` (outside the repo).

Per bone and side: import raw (mm, Z-up, −Y front, left = +X; checked against the OBJ header bounds), anchors and
targets from ``domain/assets/long_bone_fit.py`` (ESTIMATE), similarity registration
(``domain/assets/registration.py``), then: (a) canonical joints untouched, (b) length along the canonical axis vs
Trotter (Decision 16), (c) roll, (d) mirror of the left bone (x → −x, winding reversed) vs the real right bone,
(e) anchor RMS. Nothing is enforced as a tolerance.
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
from character_engine.domain.assets.long_bone_fit import (  # noqa: E402
    RULES,
    axial_extent,
    canonical_lateral,
    derive_targets,
    end_point,
    extract_anchors,
)
from character_engine.domain.assets.registration import determinant, register, spread_ratio  # noqa: E402

CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
MAPPING = ROOT / "docs" / "audit" / "A18_BP3D_BONE_MAPPING.json"
MM = 0.001
STATURE_M = 1.80
PROPOSED_RMS_MM = 2.0           # proposal §5, ESTIMATE, pending owner — compared, never enforced


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--bp3d", default=os.environ.get("CE_BP3D_DIR"))
    p.add_argument("--out", default=os.environ.get("CE_F2_OUT"))
    p.add_argument("--bones", default=",".join(RULES))
    a = p.parse_args(argv)
    if not a.bp3d or not a.out:
        raise SystemExit("need --bp3d and --out (or CE_BP3D_DIR / CE_F2_OUT)")
    bones = [b.strip().upper() for b in a.bones.split(",") if b.strip()]
    unknown = [b for b in bones if b not in RULES]
    if unknown:
        raise SystemExit(f"no anchor rule for {unknown}")
    return Path(a.bp3d), Path(a.out), bones


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
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z", global_scale=1.0)   # keep raw axes
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if len(new) != 1:
        raise RuntimeError(f"{path.name}: expected 1 mesh, got {len(new)}")
    new[0].name = name
    return new[0]


def signed_volume(obj) -> float:
    """Signed volume (mesh units³); > 0 means outward-facing winding."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    vol = sum(f.verts[0].co.dot(f.verts[1].co.cross(f.verts[2].co)) / 6.0 for f in bm.faces)
    bm.free()
    return vol


def _tree(points):
    t = KDTree(len(points))
    for i, p in enumerate(points):
        t.insert(Vector(p), i)
    t.balance()
    return t


def _nearest(src, dst):
    tree = _tree(dst)
    d = sorted(tree.find(Vector(p))[2] for p in src)
    return {"mean_mm": statistics.mean(d) / MM, "rms_mm": math.sqrt(sum(x * x for x in d) / len(d)) / MM,
            "p95_mm": d[int(0.95 * (len(d) - 1))] / MM, "max_mm": d[-1] / MM}


def symmetric(a, b):
    ab, ba = _nearest(a, b), _nearest(b, a)
    return {"a_to_b": ab, "b_to_a": ba, "max_mm": max(ab["max_mm"], ba["max_mm"]),
            "p95_mm": max(ab["p95_mm"], ba["p95_mm"]), "mean_mm": (ab["mean_mm"] + ba["mean_mm"]) / 2}


def _mirror(p):
    return (-p[0], p[1], p[2])


def _set_verts(obj, pts, name):
    for v, p in zip(obj.data.vertices, pts):
        v.co = Vector(p)
    obj.matrix_world.identity()
    obj.name = name


def _roll(rule, anchors, reg, head, tail, side):
    """Angle (deg) between the fitted lateral vector ⟂ axis and the canonical lateral direction."""
    end = rule.distal if rule.distal.pair else rule.proximal if rule.proximal.pair else None
    if end is not None:
        v = Vector(reg.apply(anchors[end.pair[0].name])) - Vector(reg.apply(anchors[end.pair[1].name]))
    else:
        p = Vector(reg.apply(anchors[rule.roll.name]))
        ax = Vector(head) - Vector(tail)
        v = p - (Vector(tail) + ax * ((p - Vector(tail)).dot(ax) / ax.dot(ax)))
    axis = (Vector(head) - Vector(tail)).normalized()
    lat = Vector(canonical_lateral(head, tail, side))
    vv = v - axis * v.dot(axis)
    if vv.length == 0:
        return float("nan")
    vv.normalize()
    return math.degrees(math.atan2(axis.dot(lat.cross(vv)), lat.dot(vv)))


def fit_bone(bone, bp3d, mapping, joints, trotter):
    rule = RULES[bone]
    names = list(rule.anchor_names())
    paths = {s: bp3d / f"{mapping[f'{bone}_{s}']}.obj" for s in ("L", "R")}
    objs = {s: import_obj(p, f"{bone}_{s}_raw") for s, p in paths.items()}
    raw = {s: [tuple(o.matrix_world @ v.co) for v in o.data.vertices] for s, o in objs.items()}
    import_check = {}
    for s, p in paths.items():
        hb = _header_bounds(p)
        mn = [min(v[i] for v in raw[s]) for i in range(3)]
        mx = [max(v[i] for v in raw[s]) for i in range(3)]
        import_check[s] = max(abs(a - b) for a, b in zip(mn + mx, hb))
    if max(import_check.values()) > 0.01:
        raise RuntimeError(f"{bone}: imported bounds differ from the OBJ header: {import_check}")
    verts = {s: [tuple(c * MM for c in p) for p in raw[s]] for s in raw}

    out = {"bp3d_files": {s: {"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for s, p in paths.items()},
           "import_bounds_vs_header_max_abs_mm": import_check, "rule": rule.note, "anchor_names": names,
           "trotter_max_length_m": trotter}
    fitted = {}
    for s in ("L", "R"):
        head, tail = joints[f"{bone}_{s}"]
        anchors, info = extract_anchors(rule, verts[s], s)
        targets, prov = derive_targets(rule, anchors, head, tail, s)
        reg = register([anchors[n] for n in names], [targets[n] for n in names], with_scale=True)
        fitted[s] = [reg.apply(p) for p in verts[s]]
        _set_verts(objs[s], fitted[s], f"{bone}_{s}_BP3D_fitted")
        length = axial_extent(fitted[s], head, tail)
        out[s] = {
            "anchor_extraction": info, "target_provenance": prov,
            "scale": reg.scale, "det_rotation": determinant(reg.rotation),
            "residuals_mm": {n: e / MM for n, e in zip(names, reg.residuals)}, "rms_mm": reg.rms / MM,
            "spread_ratio": reg.spread_ratio, "planarity_ratio": spread_ratio([anchors[n] for n in names])[1],
            "chirality_checked": reg.chirality_checked, "meets_proposed_2mm_rms": reg.rms / MM <= PROPOSED_RMS_MM,
            "canonical_joint_segment_m": math.dist(head, tail),
            "asset_joint_distance_mm": math.dist(end_point(rule.proximal, anchors),
                                                 end_point(rule.distal, anchors)) / MM,
            "fitted_length_along_bone_axis_m": length,
            "length_error_pct_vs_trotter": None if trotter is None else 100 * (length - trotter) / trotter,
            "along_axis_stretch_to_trotter": None if trotter is None else trotter / length,
            "roll_error_deg": _roll(rule, anchors, reg, head, tail, s),
        }

    # (d) mirror of the fitted left bone (winding reversed) vs the fitted right bone; raw mirror vs raw right
    mir = bpy.data.objects.new(f"{bone}_R_from_mirror", bpy.data.meshes.new(f"{bone}_R_from_mirror"))
    bpy.context.scene.collection.objects.link(mir)
    bm = bmesh.new()
    bm.from_mesh(objs["L"].data)
    for v in bm.verts:
        v.co.x = -v.co.x
    bm.to_mesh(mir.data)
    vol_no_fix = signed_volume(mir)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(mir.data)
    bm.free()
    out["mirror"] = {
        "signed_volume_cm3": {"left_fitted": signed_volume(objs["L"]) * 1e6,
                              "mirror_without_winding_fix": vol_no_fix * 1e6,
                              "mirror_with_winding_fix": signed_volume(mir) * 1e6},
        "raw_mirrored_left_vs_real_right": symmetric([_mirror(p) for p in verts["L"]], verts["R"]),
        "fitted_mirror_vs_fitted_right": symmetric([_mirror(p) for p in fitted["L"]], fitted["R"]),
    }
    return out


def main() -> int:
    bp3d, out, bones = _args()
    out.mkdir(parents=True, exist_ok=True)
    fp_before, joints_before = _fingerprint(CANONICAL), _joints(CANONICAL)
    mapping = {b["canonical"]: b["elements"][0]["file_id"]
               for b in json.loads(MAPPING.read_text(encoding="utf-8"))["bones"] if b["elements"]}
    lengths = load_osteometry().lengths_for_stature(STATURE_M)
    bpy.ops.wm.read_factory_settings(use_empty=True)

    results, failed = {}, {}
    for bone in bones:
        try:
            results[bone] = fit_bone(bone, bp3d, mapping, joints_before, lengths.get(bone))
        except Exception as exc:   # report and continue: one bone must not hide the others
            failed[bone] = f"{type(exc).__name__}: {exc}"

    fp_after, joints_after = _fingerprint(CANONICAL), _joints(CANONICAL)
    moved = [n for n in joints_before if joints_before[n] != joints_after[n]]
    name = "f2_femur_fit" if bones == ["FEMUR"] else "f2_long_bones_fit"
    blend = out / f"{name}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    res = {"status": "F2 measured; tolerances PENDING (all ESTIMATE)", "blender": bpy.app.version_string,
           "stature_m": STATURE_M, "bones": results, "failed": failed,
           "joints": {"canonical_fingerprint_before": fp_before, "after": fp_after,
                      "bones_compared": len(joints_before), "moved": moved},
           "outputs": {"blend": str(blend)}}
    (out / f"{name}_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("CE_F2_RESULT " + json.dumps({b: {s: round(r[s]["rms_mm"], 3) for s in ("L", "R")}
                                        for b, r in results.items()}) + f" moved={moved} failed={failed}")
    return 0 if not moved and fp_before == fp_after and not failed else 1


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
