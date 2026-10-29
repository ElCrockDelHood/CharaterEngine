"""Experiment 001 (D1 experiment library): contact threshold of one attack against one stance over spacing.

    blender -b --factory-startup --python runtime/blender/ce_experiment_contact_threshold.py -- \
        --lib ".../UAL1_Standard.glb" --lib ".../UAL2_Standard.glb"

Same fighters, clips and contact measure as the reaction library (``ce_reaction_library.py``): for each spacing
the attack is scanned frame by frame and the minimum signed sabre-to-body distance (negative = penetration) says
whether the blade reaches the body. A grid of spacings (default 10 between 0.7 and 1.1 m) brackets the threshold;
bisection between the last contact and the first miss refines it to ``--tolerance`` (a measurement resolution).
No reactions are played: only the attack and the stance clips. Writes a Godot-readable JSON record (domain
``experiments``), one Workbench render at the last contact spacing and a log line per spacing.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy  # type: ignore

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ce_fight_mockup as mock  # noqa: E402
import ce_reaction_library as lib  # noqa: E402

ROOT = mock.ROOT


def measure(scene, build, attacker, defender, f0: int, f1: int, distance: float) -> dict:
    """Scan the attack at ``distance``: minimum signed distance, its frame, first contact frame and bone."""
    attacker.location = (0.0, -distance, 0.0)
    best, best_frame, first, bone = None, None, None, None
    for fr in range(f0, f1 + 1):
        scene.frame_set(fr)
        bpy.context.view_layer.update()
        gap, _, point = mock.closest_sabre_contact(attacker, defender)
        if best is None or gap < best:
            best, best_frame = gap, fr
        if first is None and gap <= 0.0:
            first = fr
            bone, _ = build.nearest_canonical_bone(defender, point, posed=True)
    m = round(best, 4)
    return {"distance_m": distance, "min_signed_distance_m": m, "contact": m <= 0.0,
            "first_contact_frame": first if m <= 0.0 else None, "bone": bone if m <= 0.0 else None,
            "min_frame": best_frame}


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", type=Path, action="append", required=True, help="glTF animation library (repeatable)")
    ap.add_argument("--attack", default="Sword_Attack")
    ap.add_argument("--stance", default="Sword_Idle")
    ap.add_argument("--min", type=float, default=0.7)
    ap.add_argument("--max", type=float, default=1.1)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--tolerance", type=float, default=0.001, help="bisection resolution in metres")
    ap.add_argument("--godot", type=Path,
                    default=ROOT / "runtime/godot/addons/character_engine/data/experiments_d1.json")
    ap.add_argument("--renders", type=Path, default=ROOT / "builds/renders/experiments")
    a = ap.parse_args(argv)

    from character_engine.domain.gameplay.experiments import (
        EXPERIMENT_SCHEMA_VERSION,
        bisect_threshold,
        bracket,
        grid,
        interpolate_zero,
        record_sha256,
        threshold_from,
        validate_experiments,
    )

    bpy.ops.wm.read_factory_settings(use_empty=True)
    build = mock.load_addon()
    scene = bpy.context.scene
    props = scene.character_engine
    sources = lib.clip_sources(a.lib)
    for clip in (a.attack, a.stance):
        if clip not in sources:
            print(f"[experiment] clip {clip} not found in the libraries", flush=True)
            return 1
    defender = mock.make_fighter(props, build, "CE_Fighter_A", sources[a.stance], a.stance)
    attacker = mock.make_fighter(props, build, "CE_Fighter_B", sources[a.attack], a.attack)
    attacker.rotation_euler = (0.0, 0.0, math.pi)
    lib.play(props, defender, sources[a.stance], a.stance)
    f0, f1, act_name = lib.play(props, attacker, sources[a.attack], a.attack)
    bpy.ops.mesh.primitive_plane_add(size=12.0)
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    a.renders.mkdir(parents=True, exist_ok=True)

    points = []
    for d in grid(a.min, a.max, a.count):
        p = measure(scene, build, attacker, defender, f0, f1, d)
        points.append(p)
        print(f"[experiment] grid {d:.4f} m: min {p['min_signed_distance_m']} m at f{p['min_frame']}, "
              f"contact {p['contact']} (f{p['first_contact_frame']}, {p['bone']})", flush=True)
    last, miss, monotonic = bracket(points)
    steps = []
    interpolated = None
    if last is not None and miss is not None:
        by_d = {p["distance_m"]: p for p in points}
        interpolated = interpolate_zero(last, by_d[last]["min_signed_distance_m"],
                                        miss, by_d[miss]["min_signed_distance_m"])

        def contact(d: float) -> bool:
            p = measure(scene, build, attacker, defender, f0, f1, d)
            steps.append(p)
            print(f"[experiment] bisect {d:.4f} m: min {p['min_signed_distance_m']} m, contact {p['contact']}",
                  flush=True)
            return p["contact"]

        bisect_threshold(contact, last, miss, a.tolerance)
    threshold = threshold_from(points, steps)
    threshold.update({"interpolated_m": round(interpolated, 4) if interpolated is not None else None,
                      "grid_monotonic": monotonic})
    if threshold["contact_up_to_m"] is not None:
        attacker.location = (0.0, -threshold["contact_up_to_m"], 0.0)
        hit = next(p for p in points + steps if p["distance_m"] == threshold["contact_up_to_m"])
        scene.frame_set(hit["min_frame"])
        lib.render_sample(scene, a.renders / f"exp001_{a.attack}__vs__{a.stance}__"
                          f"{threshold['contact_up_to_m']:.4f}m_f{hit['min_frame']:03d}.png",
                          threshold["contact_up_to_m"])

    record = {
        "id": f"exp001_contact_threshold__{a.attack}__vs__{a.stance}",
        "title": "Contact threshold over spacing",
        "question": "Up to which spacing does this attack reach the defender's body?",
        "conditions": {
            "attack_clip": a.attack, "attack_action": act_name, "defender_stance": a.stance,
            "frames": [f0, f1], "spacing_axis": "attacker root at (0, -d, 0) facing +Y; defender at origin",
            "spacing_provenance": "ESTIMATE",
            "measure": "minimum over the clip of the signed distance from the attacker's PLACEHOLDER sabre "
                       "(40 samples on the blade centre line) to the defender's collision capsules",
            "sabre": "PLACEHOLDER 0.90 x 0.035 m on SOCKET-hand_grip.R (Decision 48)",
            "capsules": "block-dummy envelope radii ESTIMATE", "bone_map": "quaternius_ual",
            "sources": [{"file": p.name, "sha256": lib.file_sha256(p), "licence": "CC0 1.0 (Quaternius)"}
                        for p in a.lib],
            "generated_by": "runtime/blender/ce_experiment_contact_threshold.py (Blender "
                            + bpy.app.version_string + ")",
        },
        "grid": points,
        "bisection": {"tolerance_m": a.tolerance, "tolerance_provenance": "measurement resolution (choice)",
                      "steps": steps},
        "threshold": threshold,
        "provenance": "estimate",
        "limitations": ["one attack, one stance, one facing; spacing only along the facing axis",
                        "defender does not react; contact = blade inside an envelope capsule (ESTIMATE radii)",
                        "frame sampling at the clip's frames: a contact between two frames is not seen",
                        "PLACEHOLDER sabre; no energy or wound assessed in this experiment"],
    }
    record["sha256"] = record_sha256(record)
    doc = {"schema_version": EXPERIMENT_SCHEMA_VERSION,
           "library": "D1 experiment library (offline, Blender)",
           "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "experiments": [record]}
    problems = validate_experiments(doc)
    if problems:
        print(f"[experiment] INVALID {problems[:5]}", flush=True)
        return 1
    a.godot.parent.mkdir(parents=True, exist_ok=True)
    a.godot.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"[experiment] threshold {json.dumps(threshold)} sha256 {record['sha256']}", flush=True)
    print(f"[experiment] wrote {a.godot}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
