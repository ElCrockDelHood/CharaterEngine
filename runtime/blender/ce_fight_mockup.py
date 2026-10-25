"""D1-2 — fight mock-up in Workbench (docs/product/DELIVERABLE-1-GRANADEROS-FIGHT.md §3.1).

    blender -b --factory-startup --python runtime/blender/ce_fight_mockup.py -- \
        --anim "C:/DEV/Assets/descargas/quaternius_ual1/extracted/.../UAL1_Standard.glb" \
        --reference "C:/DEV/Assets/Imagenes Para Libertadores, Bocetar y dibujar/<levita sheet>.png"

Two canonical 1.80 m skeletons face each other, each with the block dummy (+ collision capsules) and the
PLACEHOLDER sabre on the right-hand grip socket (blade through the fist, Decision 48). One plays a guard clip, the other an attack clip, both
retargeted from a glTF animation library (e.g. Quaternius UAL, CC0) through the ``quaternius_ual`` bone map.
An owner reference sheet is shown as an image plane beside them. Renders Workbench frames, reports the
closest sabre-to-body distance per frame and saves a .blend to open in Blender.

Everything that is not canonical data is marked: distance between fighters, reference scale and the sabre
are ESTIMATE / PLACEHOLDER. The reference images and animation files are read in place (outside the repo).
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import tempfile
import time
from pathlib import Path

try:
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("run inside Blender: blender -b --python ...") from exc

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_addon():
    tmp = Path(tempfile.mkdtemp(prefix="ce_addon_"))
    shutil.copytree(SRC / "character_engine" / "infrastructure" / "blender" / "addon", tmp / "character_engine_blender")
    sys.path.insert(0, str(tmp))
    import character_engine_blender  # type: ignore
    character_engine_blender.register()
    from character_engine_blender import build  # type: ignore
    return build


def make_fighter(props, build, name: str, anim: Path, clip: str):
    props.armature_name = name
    props.template, props.pose, props.use_template_stature = "human_male_adult", "tpose", True
    assert bpy.ops.character_engine.generate_body() == {"FINISHED"}
    arm = bpy.data.objects[name]
    assert bpy.ops.character_engine.block_dummy(with_collision=True) == {"FINISHED"}
    assert bpy.ops.character_engine.add_equipment_sockets(with_sabre=False) == {"FINISHED"}
    build.build_placeholder_sabre(bpy.context, arm, "SOCKET-hand_grip.R")   # blade along the grip axis (Decision 48)
    props.bone_map, props.bvh_path, props.mocap_action = "quaternius_ual", str(anim), clip
    assert bpy.ops.character_engine.import_mocap() == {"FINISHED"}
    return arm


def reference_plane(image: Path, height_m: float, location, rotation_z: float):
    img = bpy.data.images.load(str(image), check_existing=True)
    w, h = img.size
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=location, rotation=(math.radians(90), 0.0, rotation_z))
    plane = bpy.context.active_object
    plane.name = "REF_" + image.stem[:40]
    plane.scale = (height_m * w / h, height_m, 1.0)
    mat = bpy.data.materials.new("REF_mat")
    mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mat.node_tree.links.new(tex.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    plane.data.materials.append(mat)
    plane["ce_role"], plane["ce_provenance"] = "reference", "USER_INPUT + AI_GENERATED (scale ESTIMATE)"
    return plane


def world_verts(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [obj.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts


def closest_sabre_contact(attacker, defender, samples: int = 40):
    """Signed distance from the blade centre line to the defender's collision capsules.

    Negative = the blade is inside a capsule (penetration depth). Returns (distance, capsule name, world point
    on the blade where that distance occurs).
    """
    sabre = bpy.data.objects[f"{attacker.name}_Sabre_PLACEHOLDER"]
    v = world_verts(sabre)
    base, tip = sum(v[:4], Vector()) / 4, sum(v[4:], Vector()) / 4
    line = [base.lerp(tip, i / (samples - 1)) for i in range(samples)]
    best, where, at = math.inf, "", None
    for o in bpy.data.objects:
        if o.get("ce_character") != defender.name or o.get("ce_role") != "collision":
            continue
        inv = o.matrix_world.inverted()
        for p in line:
            ok, loc, normal, _ = o.closest_point_on_mesh(inv @ p)
            if not ok:
                continue
            lp = inv @ p
            d = (lp - loc).length * (1 if (lp - loc).dot(normal) >= 0 else -1)
            d *= o.matrix_world.to_scale()[0]
            if d < best:
                best, where, at = d, o.name.split("_COL_")[-1], p.copy()
    return best, where, at


def wound_from_contact(build, defender, point, penetration_m: float, frame: int, context: dict) -> dict:
    """Layer-1 wound for a blade contact: same domain code (assess_wound) the Godot table is generated from."""
    import hashlib

    from character_engine.domain.trauma import assess_wound, blade_contact_to_wound
    bone, bone_dist = build.nearest_canonical_bone(defender, point, posed=True)
    w = blade_contact_to_wound(bone, penetration_m, build.SABRE_PLACEHOLDER_WIDTH_M, entry_point=tuple(point))
    a = assess_wound(w)
    build.apply_wound(bpy.context, defender, point, w.wound_type.value, w.depth_m, w.width_m, None, bone,
                      provenance=w.provenance)
    record = {
        "frame": frame, "defender": defender.name, "bone": bone, "bone_distance_m": round(bone_dist, 4),
        "region": a.region.value, "type": w.wound_type.value,
        "penetration_m": w.depth_m, "penetration_basis": "blade centre line inside the block-dummy capsule "
                                                         "(envelope radius ESTIMATE)",
        "width_m": w.width_m, "width_basis": "PLACEHOLDER sabre width",
        "energy_j": None, "energy_basis": "UNKNOWN - not used by the INCISION assessment; no cited model",
        "entry_point": [round(c, 4) for c in point],
        "layers_breached": [layer.value for layer in a.layers_breached], "severity": a.severity.value,
        "lethality": a.lethality, "bleeding_rate": a.bleeding_rate, "fracture": a.fracture,
        "incapacitating": a.incapacitating, "provenance": a.provenance.value,
        "seed": None, "determinism": "no randomness: fixed clips, frame, spacing and geometry",
        **context,
    }
    record["sha256"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode("utf-8")).hexdigest()
    return record


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--anim", type=Path, required=True, help="glTF/FBX animation library (e.g. Quaternius UAL1)")
    ap.add_argument("--guard-clip", default="Sword_Idle")
    ap.add_argument("--attack-clip", default="Sword_Attack")
    ap.add_argument("--distance", type=float, default=1.6, help="fighter spacing in metres (ESTIMATE)")
    ap.add_argument("--reference", type=Path, default=None, help="owner reference sheet (image plane)")
    ap.add_argument("--reference-height", type=float, default=1.4, help="plane height in metres (ESTIMATE)")
    ap.add_argument("--frames", default="", help="comma-separated frames to render (default: start, middle, end)")
    ap.add_argument("--out", type=Path, default=ROOT / "builds" / "renders")
    ap.add_argument("--save", type=Path, default=ROOT / "builds" / "tests" / "D1-2_fight_mockup.blend")
    a = ap.parse_args(argv)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    build = load_addon()
    scene = bpy.context.scene
    props = scene.character_engine
    guard = make_fighter(props, build, "CE_Fighter_A", a.anim, a.guard_clip)
    attacker = make_fighter(props, build, "CE_Fighter_B", a.anim, a.attack_clip)
    # Canonical fighters face -Y. B goes to y = -distance and turns around to face A (+Y).
    attacker.location = (0.0, -a.distance, 0.0)
    attacker.rotation_euler = (0.0, 0.0, math.pi)
    for arm in (guard, attacker):
        arm["ce_mockup_distance_m"] = a.distance
        arm["ce_mockup_distance_provenance"] = "ESTIMATE"

    bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0.0, -a.distance / 2, 0.0))
    if a.reference and a.reference.exists():
        reference_plane(a.reference, a.reference_height, (-1.6, -a.distance / 2, a.reference_height / 2 + 0.05),
                        math.radians(90))
    cam = bpy.data.objects.new("MockupCam", bpy.data.cameras.new("MockupCam"))
    scene.collection.objects.link(cam)
    cam.data.lens = 35.0
    cam.location = (4.6, -a.distance / 2 - 1.2, 1.4)
    cam.rotation_euler = (Vector((-0.4, -a.distance / 2, 0.95)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE"
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.image_settings.file_format = "PNG"

    act = attacker.animation_data.action
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    frames = [int(x) for x in a.frames.split(",") if x.strip()] or [f0, (f0 + f1) // 2, f1]
    scene.frame_start, scene.frame_end = f0, f1
    report = {"anim": str(a.anim), "guard_clip": guard.animation_data.action.name, "attack_clip": act.name,
              "distance_m": a.distance, "distance_provenance": "ESTIMATE", "sabre": "PLACEHOLDER", "frames": []}
    a.out.mkdir(parents=True, exist_ok=True)
    for fr in frames:
        scene.frame_set(fr)
        bpy.context.view_layer.update()
        gap, region, point = closest_sabre_contact(attacker, guard)
        if gap <= 0.0 and not report.get("wounds"):
            report["wounds"] = [wound_from_contact(build, guard, point, -gap, fr, {
                "attack_clip": act.name, "distance_m": a.distance, "anim_file": a.anim.name})]
            print(f"[mockup] wound {json.dumps(report['wounds'][0])}", flush=True)
            bpy.context.view_layer.update()
        path = a.out / f"D1-2_fight_mockup_f{fr:03d}.png"
        scene.render.filepath = str(path)
        t = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        entry = {"frame": fr, "render": str(path), "render_s": round(time.perf_counter() - t, 2),
                 "attacker_sabre_to_guard_body_m": round(gap, 3), "closest_segment": region,
                 "contact": gap <= 0.0}
        if report.get("wounds") and report["wounds"][0]["frame"] == fr:
            # close-up of the contact so the colour-coded wound marker is readable
            close = bpy.data.objects.new("WoundCloseUp", bpy.data.cameras.new("WoundCloseUp"))
            scene.collection.objects.link(close)
            close.data.lens = 50.0
            hit = Vector(report["wounds"][0]["entry_point"])
            close.location = hit + Vector((0.9, -0.5, 0.25))
            close.rotation_euler = (hit - close.location).to_track_quat("-Z", "Y").to_euler()
            scene.camera = close
            scene.render.filepath = str(a.out / f"D1-2_wound_closeup_f{fr:03d}.png")
            shading = scene.display.shading
            shading.show_xray, shading.xray_alpha = True, 0.35      # the marker sits inside the block proxy
            bpy.ops.render.render(write_still=True)
            shading.show_xray = False
            entry["wound_closeup"] = scene.render.filepath
            scene.camera = cam
        report["frames"].append(entry)
        print(f"[mockup] {json.dumps(entry)}", flush=True)
    a.save.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(a.save.resolve()))
    report["blend"] = str(a.save.resolve())
    (a.out / "D1-2_fight_mockup.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[mockup] {json.dumps({k: v for k, v in report.items() if k != 'frames'})}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
