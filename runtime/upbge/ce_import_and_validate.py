"""CHARACTER ENGINE - UPBGE / Blender import + validation of the canonical glTF.

Runs INSIDE UPBGE or Blender (needs ``bpy``). It is deliberately kept out of
``src/character_engine`` so the domain stays free of ``bpy``.

Usage (headless, from the repository root):

    python -m character_engine.export.gltf -o builds/gltf/human_adult_206.glb
    upbge -b --python runtime/upbge/ce_import_and_validate.py -- \
        --glb builds/gltf/human_adult_206.glb --save builds/tests/upbge_validation.blend

    (or ``blender -b --python ...`` for vanilla Blender 3.6/4.x)

What it does:
1. Imports the glTF (built-in importer, Y-up -> Blender Z-up conversion is automatic).
2. Finds the imported armature and verifies the M21 runtime contract:
   208 bones, required canonical names, feet at Z~0, upright along +Z.
3. Rebuilds exact rest-bone tails from the ``extras`` written by the exporter
   (glTF only carries joint positions; the canonical head/tail are in extras).
4. Optionally saves a .blend and always prints a PASS/FAIL report;
   exits with code 1 on failure so CI can gate on it.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
except ImportError as exc:  # pragma: no cover - only runs inside UPBGE/Blender
    raise SystemExit("This script must be executed inside UPBGE/Blender: upbge -b --python ...") from exc


EXPECTED_TOTAL_NODES = 208
REQUIRED_BONES = ("ROOT_SKELETON", "CRANIUM", "SACRUM", "CERVICAL_1", "FEMUR_L", "FEMUR_R", "FRONTAL")
GROUND_TOLERANCE = 0.05


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="ce_import_and_validate")
    parser.add_argument("--glb", type=Path, default=Path("builds/gltf/human_adult_206.glb"))
    parser.add_argument("--save", type=Path, default=None, help="Optional .blend output path")
    parser.add_argument("--no-fix-tails", action="store_true", help="Skip rebuilding tails from extras")
    return parser.parse_args(argv)


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_gltf(path: Path):
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if not armatures:
        raise RuntimeError("No armature created by the glTF importer (skin missing?)")
    return armatures[0]


def read_node_extras(glb_path: Path) -> dict:
    """Read node extras straight from the .glb JSON chunk (canonical Z-up head/tail)."""
    data = glb_path.read_bytes()
    if glb_path.suffix.lower() == ".gltf":
        doc = json.loads(data.decode("utf-8"))
    else:
        import struct
        json_len = struct.unpack_from("<I", data, 12)[0]
        doc = json.loads(data[20:20 + json_len].decode("utf-8"))
    return {n["name"]: n.get("extras", {}) for n in doc.get("nodes", []) if "extras" in n}


def fix_rest_tails(armature, extras_by_name: dict) -> int:
    """Set exact head/tail from canonical extras (Z-up metres == Blender space)."""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    fixed = 0
    try:
        for ebone in armature.data.edit_bones:
            extras = extras_by_name.get(ebone.name)
            if not extras or extras.get("is_container"):
                continue
            head, tail = extras.get("head"), extras.get("tail")
            if head and tail:
                ebone.head = Vector(head)
                ebone.tail = Vector(tail)
                fixed += 1
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    return fixed


def validate(armature) -> dict:
    errors, warnings = [], []
    bones = armature.data.bones
    count = len(bones)
    if count != EXPECTED_TOTAL_NODES:
        errors.append(f"bone count {count} != expected {EXPECTED_TOTAL_NODES}")
    names = {b.name for b in bones}
    for required in REQUIRED_BONES:
        if required not in names:
            errors.append(f"missing required bone: {required}")

    matrix_world = armature.matrix_world
    zs = [(matrix_world @ b.head_local).z for b in bones]
    min_z, max_z = min(zs), max(zs)
    if abs(min_z) > GROUND_TOLERANCE:
        warnings.append(f"lowest joint at z={min_z:.3f} (expected ~0, ground plane)")
    if max_z - min_z < 1.0:
        errors.append(f"skeleton height {max_z - min_z:.3f} m along Z too small: up-axis conversion failed?")

    roots = [b for b in bones if b.parent is None]
    if not roots:
        errors.append("armature has no root bone")

    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "bone_count": count,
        "roots": len(roots),
        "height_m": max_z - min_z,
        "ground_z": min_z,
    }


def print_report(report: dict, path: Path) -> None:
    print("==== CHARACTER ENGINE runtime validation (UPBGE/Blender) ====")
    print(f"asset: {path}")
    for key in ("bone_count", "roots", "height_m", "ground_z", "tails_fixed"):
        if key in report:
            print(f"{key}: {report[key]}")
    for w in report["warnings"]:
        print(f"WARN: {w}")
    for e in report["errors"]:
        print(f"FAIL: {e}")
    print(f"RESULT: {'PASS' if report['passed'] else 'FAIL'}")


def main() -> int:
    args = parse_args()
    if not args.glb.exists():
        print(f"FAIL: glTF not found: {args.glb}")
        return 1
    reset_scene()
    armature = import_gltf(args.glb)
    report = validate(armature)
    if not args.no_fix_tails:
        report["tails_fixed"] = fix_rest_tails(armature, read_node_extras(args.glb))
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.save.resolve()))
        print(f"saved: {args.save}")
    print_report(report, args.glb)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    code = main()
    if code:
        sys.exit(code)
