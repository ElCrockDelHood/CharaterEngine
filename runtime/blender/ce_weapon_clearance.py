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
    RIGHT_HAND_GRIP,
    Capsule,
    box_weapon,
    capsule_contact,
    frame_contacts,
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


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--clips", default=DEFAULT_CLIPS)
    ap.add_argument("--margin", type=float, default=0.0, help="required clearance in metres (PLACEHOLDER)")
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
              "weapon": "sabre PLACEHOLDER box on SOCKET-hand_grip.R, enclosed by a capsule (half diagonal)",
              "grip_segments": list(RIGHT_HAND_GRIP), "margin_m": a.margin, "libraries": [str(p) for p in a.lib],
              "skipped": missing, "clips": {}}
    for clip in clips:
        f0, f1, _ = lib.play(props, fighter, sources[clip], clip)
        if clip == clips[0]:
            scene.frame_set(f0)
            report["capsule_mesh_check_m"] = round(rest_check(fighter, placements), 5)
            log(f"collision meshes vs analytic capsules: max {report['capsule_mesh_check_m'] * 1000:.2f} mm")
        frames, lines, per_frame = {}, {}, []
        for fr in range(f0, f1 + 1):
            scene.frame_set(fr)
            bpy.context.view_layer.update()
            weapon, length, width, depth = sabre_capsule(fighter)
            body = body_capsules(fighter, placements)
            frames[fr] = frame_contacts([weapon], body)
            lines[fr] = frame_contacts([Capsule("centre_line", weapon.a, weapon.b, 0.0)], body)
            near = frames[fr][0]
            per_frame.append({"frame": fr, "body": near.body, "gap_m": round(near.gap_m, 4),
                              "t_weapon": round(near.t_weapon, 3), "centre_line_gap_m": round(lines[fr][0].gap_m, 4)})
        s = summary(frames, a.margin)
        s["centre_line_frames_in_violation"] = summary(lines, a.margin)["frames_in_violation"]
        s["weapon_m"] = {"length": round(length, 4), "width": round(width, 4), "depth": round(depth, 4),
                         "capsule_radius": round(weapon.radius_m, 4)}
        s["per_frame"] = per_frame
        report["clips"][clip] = s
        segs = ", ".join(f"{k} {len(v['frames'])} cuadros hasta {-v['deepest_m'] * 100:.1f} cm"
                         for k, v in s["segments"].items()) or "sin cruces"
        log(f"{clip}: {s['frames_in_violation']}/{s['frames']} cuadros con el arma dentro del cuerpo "
            f"(linea central: {s['centre_line_frames_in_violation']}); {segs}")
    report["passed"] = all(c["passed"] for c in report["clips"].values())
    report["seconds"] = round(time.time() - t0, 1)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"{'OK' if report['passed'] else 'FALLA'}: informe {a.out} ({report['seconds']} s)")
    return 0


if __name__ == "__main__":
    main()
