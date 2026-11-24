"""Weapon clearance per clip: how far the held sabre goes into its own wielder (Blender side of weapon_clearance).

    blender -b --factory-startup --python runtime/blender/ce_weapon_clearance.py -- \
        --lib ".../UAL1_Standard.glb" --lib ".../UAL2_Standard.glb" --out builds/reports/weapon_clearance/x.json \
        [--clips Sword_Attack,Sword_Regular_C] [--margin 0.0]

Same fighter as the D1 library (``ce_fight_mockup.make_fighter``: block dummy with the Decision 83 capsules, PLACEHOLDER
sabre on ``SOCKET-hand_grip.R``, ``import_mocap`` with leg grounding, Decision 85). Per frame, every body capsule is
taken from the same placements the blocks were built from, moved by its collision object's posed matrix, and the sabre
box becomes a capsule enclosing its cross-section. The distances themselves are pure Python
(``character_engine.domain.animation.weapon_clearance``). Measurement only: nothing in the scene is corrected.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

try:
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("run inside Blender: blender -b --python ...") from exc

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ce_fight_mockup as mock  # noqa: E402
import ce_reaction_library as lib  # noqa: E402

from character_engine.domain.animation.weapon_clearance import (  # noqa: E402
    GRIP_LENGTH_M,
    RIGHT_GRIP_ALLOWED,
    RIGHT_HAND_GRIP,
    Capsule,
    Rules,
    box_weapon,
    capsule_contact,
    frame_contacts,
    plan_wrist_fix,
    split_weapon,
    summary,
)
from character_engine.domain.rigging import COLLISION_SEGMENTS, block_placements  # noqa: E402

DEFAULT_CLIPS = ("Idle_Loop,Sitting_Idle_Loop,Sword_Idle,Sword_Block,Sword_Attack,Sword_Regular_A,Sword_Regular_B,"
                 "Sword_Regular_C,Sword_Regular_Combo,Sword_Heavy_Combo,Sword_Dash")


def log(msg: str) -> None:
    print(f"[weapon_clearance] {msg}", flush=True)


def rest_placements(build, armature):
    pts = build.bone_points(armature)
    stature = float(armature.get("ce_stature_m", 1.80))
    return block_placements({n: (tuple(h), tuple(t)) for n, (h, t) in pts.items()}, stature,
                            segments=COLLISION_SEGMENTS)


def body_capsules(armature, placements):
    name = armature["ce_character"]
    out = []
    for p in placements:
        m = bpy.data.objects[f"{name}_COL_{p.name}"].matrix_world
        out.append(Capsule(p.name, tuple(m @ Vector(p.a)), tuple(m @ Vector(p.b)), p.radius_m))
    return out


def sabre_capsule(armature):
    obj = bpy.data.objects[f"{armature['ce_character']}_Sabre_PLACEHOLDER"]
    v = [obj.matrix_world @ x.co for x in obj.data.vertices]
    base, tip = sum(v[:4], Vector()) / 4, sum(v[4:], Vector()) / 4
    width, depth = (v[1] - v[0]).length, (v[2] - v[0]).length     # verts ordered (t, a, b): see build_placeholder_sabre
    return box_weapon("sabre", tuple(base), tuple(tip), width, depth), (base - tip).length, width, depth


def rest_check(armature, placements) -> float:
    """Largest distance between a collision mesh vertex and its analytic capsule surface (should be ~0)."""
    name = armature["ce_character"]
    worst = 0.0
    for p in placements:
        obj = bpy.data.objects[f"{name}_COL_{p.name}"]
        cap = Capsule(p.name, tuple(obj.matrix_world @ Vector(p.a)), tuple(obj.matrix_world @ Vector(p.b)), p.radius_m)
        for vert in obj.data.vertices:
            w = obj.matrix_world @ vert.co
            gap = capsule_contact(Capsule("pt", tuple(w), tuple(w), 0.0), cap).gap_m
            worst = max(worst, abs(gap))
    return worst


def measure(scene, fighter, placements, f0: int, f1: int, margin: float):
    """Summary of one clip as it plays now, and the raw (weapon, wrist pivot, body) per frame for the fix."""
    frames, strict, lines, raw, per_frame = {}, {}, {}, {}, []
    wrist = fighter.pose.bones["CAPITATE_R"]
    for fr in range(f0, f1 + 1):
        scene.frame_set(fr)
        bpy.context.view_layer.update()
        weapon, length, width, depth = sabre_capsule(fighter)
        body = body_capsules(fighter, placements)
        parts = split_weapon(weapon, GRIP_LENGTH_M)
        raw[fr] = (parts, tuple(fighter.matrix_world @ wrist.head), body)
        frames[fr] = frame_contacts(parts, body, RIGHT_HAND_GRIP, RIGHT_GRIP_ALLOWED)
        strict[fr] = frame_contacts([weapon], body)
        lines[fr] = frame_contacts([Capsule("centre_line", weapon.a, weapon.b, 0.0)], body)
        near = frames[fr][0]
        per_frame.append({"frame": fr, "body": near.body, "part": near.weapon, "gap_m": round(near.gap_m, 4),
                          "t_part": round(near.t_weapon, 3), "strict_gap_m": round(strict[fr][0].gap_m, 4),
                          "centre_line_gap_m": round(lines[fr][0].gap_m, 4)})
    s = summary(frames, margin)
    s["centre_line_frames_in_violation"] = summary(lines, margin)["frames_in_violation"]
    s["grip_on_forearm_frames"] = summary(strict, margin)["frames_in_violation"] - s["frames_in_violation"]
    s["weapon_m"] = {"length": round(length, 4), "width": round(width, 4), "depth": round(depth, 4),
                     "capsule_radius": round(weapon.radius_m, 4)}
    s["per_frame"] = per_frame
    return s, raw


def describe(s) -> str:
    segs = ", ".join(f"{k} {len(v['frames'])} cuadros hasta {-v['deepest_m'] * 100:.1f} cm"
                     for k, v in s["segments"].items()) or "sin cruces"
    return (f"{s['frames_in_violation']}/{s['frames']} cuadros con la hoja dentro del cuerpo "
            f"(linea central: {s['centre_line_frames_in_violation']}; empunadura apoyada en el antebrazo: "
            f"{s['grip_on_forearm_frames']}); {segs}")


def carpals(fighter):
    """The wrist bones that hang from the forearm: turning them all about one pivot moves the hand rigidly."""
    return [pb for pb in fighter.pose.bones if pb.parent is not None and pb.parent.name in ("RADIUS_R", "ULNA_R")]


def apply_fix(scene, fighter, plan) -> None:
    """Key each planned wrist turn on the clip's action (world rotation about the wrist pivot)."""
    from mathutils import Matrix  # type: ignore
    mw = fighter.matrix_world
    inv = mw.inverted()
    bones = carpals(fighter)
    wrist = fighter.pose.bones["CAPITATE_R"]
    for p in plan:
        scene.frame_set(p.frame)
        bpy.context.view_layer.update()
        pivot = mw @ wrist.head
        turn = (Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(p.angle_deg), 4, Vector(p.axis))
                @ Matrix.Translation(-pivot))
        targets = {pb.name: inv @ turn @ mw @ pb.matrix for pb in bones}
        for pb in bones:
            pb.matrix = targets[pb.name]
        bpy.context.view_layer.update()
        for pb in bones:
            pb.keyframe_insert("location", frame=p.frame)
            pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == "QUATERNION" else "rotation_euler",
                               frame=p.frame)


def shot(scene, fighter, worst, path: Path) -> None:
    """Workbench close-up of the worst contact: sabre red, light background."""
    scene.frame_set(worst["frame"])
    bpy.context.view_layer.update()
    sab = bpy.data.objects[f"{fighter['ce_character']}_Sabre_PLACEHOLDER"]
    red = bpy.data.materials.get("CE_clearance_red") or bpy.data.materials.new("CE_clearance_red")
    red.diffuse_color = (0.85, 0.1, 0.1, 1.0)
    if sab.data.materials and sab.data.materials[0] != red:
        sab.data.materials[0] = red
    elif not sab.data.materials:
        sab.data.materials.append(red)
    target = Vector(worst["point"])
    cam = bpy.data.objects.get("CE_clearance_cam")
    if cam is None:
        cam = bpy.data.objects.new("CE_clearance_cam", bpy.data.cameras.new("CE_clearance_cam"))
        scene.collection.objects.link(cam)
    cam.data.lens = 50.0
    cam.location = target + Vector((0.6, -0.6, 0.35))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.background_type, sh.background_color = "VIEWPORT", (0.82, 0.82, 0.82)
    scene.render.resolution_x, scene.render.resolution_y = 800, 600
    scene.render.image_settings.file_format = "PNG"
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    log(f"  imagen {path}")


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--clips", default=DEFAULT_CLIPS)
    ap.add_argument("--margin", type=float, default=0.0, help="required clearance in metres (PLACEHOLDER)")
    ap.add_argument("--fix", action="store_true", help="turn the wrist where the weapon enters the body, re-measure")
    ap.add_argument("--shots", type=Path, default=None, help="folder for before / after renders of the worst frame")
    a = ap.parse_args(argv)
    t0 = time.time()

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build = mock.load_addon()
    props = bpy.context.scene.character_engine
    sources = lib.clip_sources(a.lib)
    clips = [c for c in a.clips.split(",") if c]
    missing = [c for c in clips if c not in sources]
    clips = [c for c in clips if c in sources]
    if missing:
        log(f"clips not in the libraries (skipped): {missing}")
    if not clips:
        log("no clips to measure")
        return 2
    fighter = mock.make_fighter(props, build, "CE_Fighter_A", sources[clips[0]], clips[0])
    placements = rest_placements(build, fighter)
    scene = bpy.context.scene

    report = {"schema": "ce-weapon-clearance/1", "fighter": "human_male_adult 1.80 m, block dummy (Decision 83)",
              "weapon": "sabre PLACEHOLDER box on SOCKET-hand_grip.R, enclosed by a capsule (half diagonal); grip = first "
                        f"{GRIP_LENGTH_M} m (PLACEHOLDER), may rest on the gripping forearm",
              "grip_segments": list(RIGHT_HAND_GRIP), "margin_m": a.margin, "libraries": [str(p) for p in a.lib],
              "skipped": missing, "clips": {}}
    for clip in clips:
        f0, f1, _ = lib.play(props, fighter, sources[clip], clip)
        if clip == clips[0]:
            scene.frame_set(f0)
            report["capsule_mesh_check_m"] = round(rest_check(fighter, placements), 5)
            log(f"collision meshes vs analytic capsules: max {report['capsule_mesh_check_m'] * 1000:.2f} mm")
        s, raw = measure(scene, fighter, placements, f0, f1, a.margin)
        report["clips"][clip] = s
        log(f"{clip}: {describe(s)}")
        if a.fix and not s["passed"]:
            worst = s["worst"]
            if a.shots:
                shot(scene, fighter, worst, a.shots / f"{clip}_{worst['frame']}_antes.png")
            plan = plan_wrist_fix(raw, Rules(margin_m=a.margin))
            apply_fix(scene, fighter, plan)
            after, _ = measure(scene, fighter, placements, f0, f1, a.margin)
            s["fix"] = {"bone_pivot": "CAPITATE_R head (wrist); the carpals turn together, the hand follows",
                        "frames_turned": len(plan), "max_angle_deg": max(p.angle_deg for p in plan),
                        "not_cleared": [p.frame for p in plan if not p.cleared],
                        "turns": [{"frame": p.frame, "angle_deg": p.angle_deg,
                                   "axis": [round(x, 4) for x in p.axis]} for p in plan],
                        "after": {k: v for k, v in after.items() if k != "per_frame"}}
            s["passed_after_fix"] = after["passed"]
            log(f"  corregido: {len(plan)} cuadros, giro max {s['fix']['max_angle_deg']:.0f} grados -> {describe(after)}")
            if a.shots:
                shot(scene, fighter, worst, a.shots / f"{clip}_{worst['frame']}_despues.png")
    report["passed"] = all(c["passed"] for c in report["clips"].values())
    if a.fix:
        report["passed_after_fix"] = all(c.get("passed_after_fix", c["passed"]) for c in report["clips"].values())
    report["seconds"] = round(time.time() - t0, 1)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"{'OK' if report['passed'] else 'FALLA'}: informe {a.out} ({report['seconds']} s)")
    return 0


if __name__ == "__main__":
    main()
