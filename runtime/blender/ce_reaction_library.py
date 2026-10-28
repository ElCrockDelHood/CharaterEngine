"""Deliverable 1 reaction library: attack clip x defender stance x spacing -> contact -> wound -> reaction.

    blender -b --factory-startup --python runtime/blender/ce_reaction_library.py -- \
        --lib "C:/DEV/Assets/descargas/quaternius_ual1/.../UAL1_Standard.glb" \
        --lib "C:/DEV/Assets/descargas/quaternius_ual2/.../UAL2_Standard.glb"

Builds the two D1-2 fighters (``ce_fight_mockup.py``), then for every attack clip and defender stance found
in the given glTF animation libraries and every spacing, scans all frames of the attack: signed distance from
the attacker's PLACEHOLDER sabre to the defender's collision capsules (negative = penetration). The first
contact becomes a wound (domain ``blade_contact_to_wound`` + ``assess_wound``, layer 1) and the wound picks a
reaction clip (domain ``reaction_for``, ASSUMED). Writes a JSON document Godot reads, renders one Workbench
sample per contacting (attack, stance) pair and logs one line per entry.

Not physics: the defender plays its stance clip up to the first contact and then its reaction clip (schema 2,
pose switch without blending); it does not react to the attack before contact. A stance shorter than the attack
holds its last pose. Spacing, envelope radii and the sabre are ESTIMATE / PLACEHOLDER; no energy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ce_fight_mockup as mock  # noqa: E402

ROOT = mock.ROOT
ATTACKS = ("Sword_Attack", "Sword_Regular_A", "Sword_Regular_B", "Sword_Regular_C", "Sword_Regular_Combo",
           "Sword_Heavy_Combo", "Sword_Dash")
STANCES = ("Sword_Idle", "Sword_Block")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clip_sources(libs):
    """clip short name -> library file, from the clip names inside each glTF (no scene changes)."""
    found = {}
    for lib in libs:
        before = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=str(lib))
        for act in set(bpy.data.actions) - before:
            short = act.name.rsplit("_Armature", 1)[0]
            found.setdefault(short, lib)
        for obj in [o for o in bpy.data.objects if o.get("ce_role") is None and o.type in ("ARMATURE", "MESH")
                    and not o.name.startswith("CE_")]:
            bpy.data.objects.remove(obj, do_unlink=True)
        for act in set(bpy.data.actions) - before:
            bpy.data.actions.remove(act)
    return found


def play(props, fighter, lib: Path, clip: str):
    """Retarget ``clip`` from ``lib`` onto ``fighter`` (removes the previous source rig)."""
    for o in list(bpy.data.objects):
        if o.get("ce_role") == "mocap_source" and o.get("ce_character") == fighter.name:
            bpy.data.objects.remove(o, do_unlink=True)
    props.armature_name, props.bone_map, props.bvh_path, props.mocap_action = (
        fighter.name, "quaternius_ual", str(lib), clip)
    assert bpy.ops.character_engine.import_mocap() == {"FINISHED"}, clip
    act = fighter.animation_data.action
    return int(act.frame_range[0]), int(act.frame_range[1]), act.name


RENDER_AFTER_FRAMES = 8          # second sample render, this many frames into the reaction


def render_sample(scene, path: Path, distance: float) -> None:
    camera_for(distance)
    # each clip import can switch the scene back to EEVEE (black without lights)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "MATERIAL"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def play_back_stance(*fighters) -> None:
    """Undo the reaction set-up: drop the NLA tracks and put each fighter's base action back."""
    for fighter in fighters:
        ad = fighter.animation_data
        if not ad.nla_tracks:
            continue                       # nothing was layered on this fighter
        for t in list(ad.nla_tracks):
            ad.nla_tracks.remove(t)
        ad.action = bpy.data.actions[fighter["ce_base_action"]]
    for o in list(bpy.data.objects):
        if o.get("ce_role") == "wound":
            bpy.data.objects.remove(o, do_unlink=True)


def layer_reaction(props, sources, fighter, clip: str, start: int, blend_in: int):
    """Base action (held) underneath, ``clip`` retargeted onto ``fighter`` on top from ``start``.

    Returns (reaction action name, reaction length in frames). ``blend_in`` frames of NLA blend (ASSUMED).
    """
    base = fighter.animation_data.action
    base.use_fake_user = True
    fighter["ce_base_action"] = base.name
    _, _, react_name = play(props, fighter, sources[clip], clip)
    react = fighter.animation_data.action
    react.use_fake_user = True
    ad = fighter.animation_data
    ad.action = None
    base_strip = ad.nla_tracks.new().strips.new("base", int(base.frame_range[0]), base)
    base_strip.extrapolation = "HOLD"
    react_strip = ad.nla_tracks.new().strips.new("reaction", start, react)
    react_strip.extrapolation = "HOLD_FORWARD"
    react_strip.use_auto_blend = False
    react_strip.blend_in = float(blend_in)
    return react_name, int(react.frame_range[1] - react.frame_range[0])


def reaction_playback(build, props, sources, scene, attacker, defender, first, hit_point, wound, clip: str,
                      attack_end: int, renders: Path, render_tag, distance: float, blend_in: int,
                      attacker_reaction: bool, defender_stance: str) -> dict:
    """Defender plays ``clip`` from the frame after the first contact; re-measure until every clip ends.

    NLA per fighter: base strip (held) underneath, reaction strip on top from contact + 1 with ``blend_in``
    frames (ASSUMED). With ``attacker_reaction`` the attacker switches to its recovery clip the same way.
    The wound point is carried by the wounded bone from the contact pose.
    """
    from character_engine.domain.gameplay.reaction_library import attacker_reaction_for
    f_contact = first["frame"]
    react_name, react_len = layer_reaction(props, sources, defender, clip, f_contact + 1, blend_in)
    att = None
    end = max(attack_end, f_contact + 1 + react_len)
    if attacker_reaction:
        a_clip, a_rule = attacker_reaction_for(defender_stance, wound_region(wound))
        a_name, a_len = layer_reaction(props, sources, attacker, a_clip, f_contact + 1, blend_in)
        att = {"clip": a_clip, "clip_action": a_name, "rule": a_rule, "starts_frame": f_contact + 1,
               "blend_in_frames": blend_in, "provenance": "ASSUMED"}
        end = max(end, f_contact + 1 + a_len)

    scene.frame_set(f_contact)
    bpy.context.view_layer.update()
    pb = defender.pose.bones[first["bone"]]
    local = (defender.matrix_world @ pb.matrix).inverted() @ hit_point
    build.apply_wound(bpy.context, defender, hit_point, wound.wound_type.value, wound.depth_m, wound.width_m, None,
                      wound.bone_hit, provenance=wound.provenance)
    if render_tag:
        render_sample(scene, renders / f"{render_tag}_f{f_contact:03d}_contact.png", distance)

    frames, signed, consistent = [], [], 0
    for fr in range(f_contact, end + 1):
        scene.frame_set(fr)
        bpy.context.view_layer.update()
        gap, _, _ = mock.closest_sabre_contact(attacker, defender)
        frames.append(fr)
        signed.append(round(gap, 4))
        carried = (defender.matrix_world @ pb.matrix) @ local
        nearest, _ = build.nearest_canonical_bone(defender, carried, posed=True)
        consistent += nearest == first["bone"]
        if render_tag and fr == f_contact + RENDER_AFTER_FRAMES:
            render_sample(scene, renders / f"{render_tag}_f{fr:03d}_reaction.png", distance)
    after = signed[1:]
    separated = next((f for f, g in zip(frames[1:], after) if g > 0.0), None)
    return {
        "start_frame": f_contact, "clip": clip, "clip_action": react_name, "reaction_starts_frame": f_contact + 1,
        "blend_in_frames": blend_in, "frames": frames, "signed_distance_m": signed, "separated_at_frame": separated,
        "max_penetration_after_m": round(max([0.0] + [-g for g in after]), 4),
        "penetrating_at_end": signed[-1] <= 0.0,
        "wound_bone_consistent_ratio": round(consistent / len(frames), 4),
        "provenance": "ASSUMED",
        "attacker_reaction": att,
        "note": f"NLA blend-in {blend_in} frames; "
                + ("attacker switches to its recovery clip" if att else "attacker keeps playing its clip unchanged"),
    }


def wound_region(wound) -> str:
    from character_engine.domain.trauma import assess_wound
    return assess_wound(wound).region.value


def camera_for(distance: float):
    cam = bpy.data.objects.get("LibCam") or bpy.data.objects.new("LibCam", bpy.data.cameras.new("LibCam"))
    if cam.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = 35.0
    cam.location = (4.6, -distance / 2 - 1.2, 1.4)
    cam.rotation_euler = (Vector((-0.4, -distance / 2, 0.95)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", type=Path, action="append", required=True, help="glTF animation library (repeatable)")
    ap.add_argument("--distances", default="0.9,1.2,1.6", help="fighter spacings in metres (ESTIMATE)")
    ap.add_argument("--attacks", default=",".join(ATTACKS))
    ap.add_argument("--stances", default=",".join(STANCES))
    ap.add_argument("--out", type=Path, default=ROOT / "builds" / "reactions" / "reaction_library_d1.json")
    ap.add_argument("--godot", type=Path,
                    default=ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data"
                    / "reaction_library_d1.json")
    ap.add_argument("--renders", type=Path, default=ROOT / "builds" / "renders" / "reactions")
    ap.add_argument("--save", type=Path, default=None, help="optional .blend of the final scene (inspection)")
    ap.add_argument("--blend-in", type=int, default=4, help="NLA blend-in frames into the reactions (ASSUMED)")
    ap.add_argument("--no-attacker-reaction", action="store_true", help="attacker keeps playing its clip after a hit")
    a = ap.parse_args(argv)

    from character_engine.domain.gameplay.reaction_library import (
        SCHEMA_VERSION,
        entry_sha256,
        reaction_for,
        summary,
        validate_library,
    )
    from character_engine.domain.trauma import assess_wound, blade_contact_to_wound

    bpy.ops.wm.read_factory_settings(use_empty=True)
    build = mock.load_addon()
    scene = bpy.context.scene
    props = scene.character_engine
    sources = clip_sources(a.lib)
    attacks = [c for c in a.attacks.split(",") if c in sources]
    stances = [c for c in a.stances.split(",") if c in sources]
    missing = [c for c in a.attacks.split(",") + a.stances.split(",") if c not in sources]
    print(f"[reactions] attacks {attacks} stances {stances} missing {missing}", flush=True)
    distances = [float(x) for x in a.distances.split(",")]

    defender = mock.make_fighter(props, build, "CE_Fighter_A", sources[stances[0]], stances[0])
    attacker = mock.make_fighter(props, build, "CE_Fighter_B", sources[attacks[0]], attacks[0])
    attacker.rotation_euler = (0.0, 0.0, math.pi)
    bpy.ops.mesh.primitive_plane_add(size=12.0)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    a.renders.mkdir(parents=True, exist_ok=True)

    entries = []
    for stance in stances:
        play(props, defender, sources[stance], stance)
        for attack in attacks:
            f0, f1, act_name = play(props, attacker, sources[attack], attack)
            rendered = False
            for d in distances:
                attacker.location = (0.0, -d, 0.0)
                frames, signed, first = [], [], None
                for fr in range(f0, f1 + 1):
                    scene.frame_set(fr)
                    bpy.context.view_layer.update()
                    gap, seg, point = mock.closest_sabre_contact(attacker, defender)
                    frames.append(fr)
                    signed.append(round(gap, 4))
                    if first is None and gap <= 0.0:
                        bone, _ = build.nearest_canonical_bone(defender, point, posed=True)
                        first = {"frame": fr, "segment": seg, "bone": bone, "penetration_m": round(-gap, 4),
                                 "entry_point": [round(c, 4) for c in point]}
                        hit_point = point
                wound = reaction = playback = None
                if first:
                    w = blade_contact_to_wound(first["bone"], first["penetration_m"], build.SABRE_PLACEHOLDER_WIDTH_M)
                    asm = assess_wound(w)
                    wound = {"type": w.wound_type.value, "bone": w.bone_hit, "region": asm.region.value,
                             "depth_m": w.depth_m, "width_m": w.width_m,
                             "layers_breached": [x.value for x in asm.layers_breached],
                             "severity": asm.severity.value, "lethality": asm.lethality,
                             "bleeding_rate": asm.bleeding_rate, "fracture": asm.fracture,
                             "incapacitating": asm.incapacitating, "provenance": asm.provenance.value}
                    clip, rule = reaction_for(wound["region"], wound["severity"], wound["lethality"],
                                              wound["incapacitating"])
                    reaction = {"clip": clip, "rule": rule, "provenance": "ASSUMED",
                                "note": "placeholder for a baked L2/L3 manifestation (Decisions 44-45)"}
                    render_tag = None if rendered else f"{attack}__vs__{stance}__{d:.1f}m"
                    playback = reaction_playback(build, props, sources, scene, attacker, defender, first, hit_point,
                                                 w, clip, f1, a.renders, render_tag, d, a.blend_in,
                                                 not a.no_attacker_reaction, stance)
                    rendered = rendered or render_tag is not None
                    play_back_stance(defender, attacker)
                entry = {
                    "id": f"{attack}__vs__{stance}__{d:.1f}m", "attack_clip": attack, "attack_action": act_name,
                    "defender_stance": stance, "distance_m": d, "distance_provenance": "ESTIMATE",
                    "frames": frames, "signed_distance_m": signed, "min_distance_m": min(signed),
                    "first_contact": first, "wound": wound, "reaction": reaction, "reaction_playback": playback,
                    "energy_j": None, "energy_basis": "UNKNOWN - no cited cutting-energy model; incision assessed "
                                                      "from depth and width only",
                    "seed": None, "determinism": "no randomness: fixed clips, frames, spacing and geometry",
                    "sabre": "PLACEHOLDER 0.90 x 0.035 m on SOCKET-hand_grip.R (Decision 48)",
                    "provenance": "estimate",
                }
                entry["sha256"] = entry_sha256(entry)
                entries.append(entry)
                after = (f", after: separated {playback['separated_at_frame']}, max pen "
                         f"{playback['max_penetration_after_m']}, at end {playback['penetrating_at_end']}, wound-bone "
                         f"{playback['wound_bone_consistent_ratio']}") if playback else ""
                print(f"[reactions] {entry['id']}: min {entry['min_distance_m']} m, "
                      f"contact {first['frame'] if first else None}, "
                      f"reaction {reaction['clip'] if reaction else None}{after}, sha256 {entry['sha256'][:12]}",
                      flush=True)

    doc = {
        "schema_version": SCHEMA_VERSION,
        "library": "D1 reaction library (Granaderos fight mock-up)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_by": "runtime/blender/ce_reaction_library.py (Blender " + bpy.app.version_string + ")",
        "bone_map": "quaternius_ual",
        "sources": [{"file": p.name, "sha256": file_sha256(p), "licence": "CC0 1.0 (Quaternius)"}
                    for p in a.lib],
        "rule": "reaction_for (ASSUMED): lethal -> Death01; incapacitating/severe -> Hit_Knockback; "
                "head/neck -> Hit_Head; else Hit_Chest",
        "settings": {"blend_in_frames": a.blend_in, "attacker_reaction": not a.no_attacker_reaction,
                     "provenance": "ASSUMED"},
        "limitations": ["defender reacts only after the first contact (no anticipation, no parry)",
                        "reactions start the frame after contact with a fixed NLA blend-in (ASSUMED)",
                        "blade-on-blade contact (parry) is not detected: every contact is a body hit",
                        "attacker reaction is one recovery clip for every hit (ASSUMED)",
                        "stance shorter than the attack holds its last pose",
                        "contact measured against block-dummy capsules (envelope radii ESTIMATE)",
                        "PLACEHOLDER sabre; no energy model"],
        "entries": entries,
    }
    problems = validate_library(doc)
    if problems:
        print(f"[reactions] INVALID {problems[:5]}", flush=True)
        return 1
    for path in (a.out, a.godot):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=1, sort_keys=False), encoding="utf-8")
    if a.save:
        a.save.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(a.save.resolve()))
    print(f"[reactions] summary {json.dumps(summary(doc))}", flush=True)
    print(f"[reactions] wrote {a.out} and {a.godot}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
