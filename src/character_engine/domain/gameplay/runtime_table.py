"""Engine-neutral gameplay table consumed by runtimes that cannot import Python (Godot).

The Python domain stays the single source of truth: this module flattens the move set,
the pre-computed blunt-impact assessments for every (move, hitbox bone) pair and a set of
*reference scenarios* (scripted fights run with :class:`ShenmueCombat`) into a plain
JSON-serialisable dict. ``scripts/export_gameplay_data.py`` writes it to
``runtime/godot/addons/character_engine/data/gameplay_shenmue.json``; the GDScript port
replays the same scenarios and must reproduce frame numbers, health and states exactly.
"""

from __future__ import annotations

from typing import Dict, List, Mapping

from ..trauma import assess_wound, blunt_impact_to_wound
from .combat import (
    FRAME_RATE,
    GAMEPLAY_STYLES,
    SHENMUE_MOVES,
    CombatInput,
    Fighter,
    Move,
    ShenmueCombat,
    _health_cost,
    default_hitboxes,
)

SCHEMA = "ce-gameplay/1"


def _impact(bone: str, mv: Move) -> Dict[str, object]:
    a = assess_wound(blunt_impact_to_wound(bone, contact_radius_m=mv.contact_radius_m, energy_j=mv.energy_j))
    return {
        "severity": a.severity.value,
        "lethality": round(a.lethality, 4),
        "bleeding_rate": round(a.bleeding_rate, 4),
        "fracture": a.fracture,
        "incapacitating": a.incapacitating,
        "is_lethal": a.is_lethal,
        "region": a.region.value,
        "deepest_layer": a.deepest_layer.value,
        "health_cost": _health_cost(a, mv),
        "provenance": a.provenance.value,
    }


def _move_entry(mv: Move, hitbox_bones: List[str]) -> Dict[str, object]:
    return {
        "move_id": mv.move_id,
        "label": mv.label,
        "kind": mv.kind.value,
        "command": list(mv.command),
        "startup": mv.startup,
        "active": mv.active,
        "recovery": mv.recovery,
        "energy_j": mv.energy_j,
        "contact_radius_m": mv.contact_radius_m,
        "striking_bone": mv.striking_bone,
        "target_region_bone": mv.target_region_bone,
        "reach_m": mv.reach_m,
        "hitstun": mv.hitstun,
        "knockdown": mv.knockdown,
        "cancel_into": list(mv.cancel_into),
        "impacts": {bone: _impact(bone, mv) for bone in hitbox_bones},
    }


# Scripted fights: (scenario_id, distance_m, script) where script maps frame -> {fighter: input kwargs}.
def _scenario_scripts() -> List[Dict[str, object]]:
    return [
        {"scenario_id": "jab_lands", "distance_m": 0.7, "frames": 40,
         "script": {1: {"player": {"punch": True}}}},
        {"scenario_id": "guard_blocks_jab", "distance_m": 0.7, "frames": 40,
         "script": {1: {"player": {"punch": True}, "opponent": {"guard": True}},
                    2: {"opponent": {"guard": True}}, 3: {"opponent": {"guard": True}},
                    4: {"opponent": {"guard": True}}, 5: {"opponent": {"guard": True}},
                    6: {"opponent": {"guard": True}}, 7: {"opponent": {"guard": True}}}},
        {"scenario_id": "throw_beats_guard", "distance_m": 0.5, "frames": 60,
         "script": {1: {"player": {"direction": "F"}, "opponent": {"guard": True}},
                    2: {"player": {"throw": True}, "opponent": {"guard": True}},
                    **{fr: {"opponent": {"guard": True}} for fr in range(3, 15)}}},
        {"scenario_id": "elbow_command", "distance_m": 0.6, "frames": 60,
         "script": {1: {"player": {"direction": "F"}}, 3: {"player": {"direction": "F"}},
                    5: {"player": {"punch": True}}}},
        {"scenario_id": "crescent_knockdown", "distance_m": 1.0, "frames": 120,
         "script": {1: {"player": {"direction": "F"}}, 2: {"player": {"kick": True}}}},
        {"scenario_id": "whiff_out_of_reach", "distance_m": 2.5, "frames": 30,
         "script": {1: {"player": {"punch": True}}}},
        {"scenario_id": "autoplay_180", "distance_m": 0.7, "frames": 180,
         "script": {fr: {"player": {"punch": fr % 40 == 1, "kick": fr % 40 == 21}} for fr in range(1, 181)
                    if fr % 40 in (1, 21)}},
    ]


def run_scenario(spec: Mapping[str, object], moves: Mapping[str, Move] = SHENMUE_MOVES) -> Dict[str, object]:
    d = float(spec["distance_m"])
    player = Fighter("player", position=(0.0, 0.0, 0.0), facing=(0.0, -1.0, 0.0))
    opponent = Fighter("opponent", position=(0.0, -d, 0.0), facing=(0.0, 1.0, 0.0))
    sim = ShenmueCombat([player, opponent], moves=moves,
                        input_buffer_frames=int(GAMEPLAY_STYLES["shenmue"]["input_buffer_frames"]))
    script: Mapping[int, Mapping[str, Mapping[str, object]]] = spec["script"]  # type: ignore[assignment]
    for _ in range(int(spec["frames"])):
        for fid, kwargs in script.get(sim.frame + 1, {}).items():
            sim.feed(fid, CombatInput(**kwargs))
        sim.step()
    return {
        "scenario_id": spec["scenario_id"],
        "frames": sim.frame,
        "hits": [{"frame": h.frame, "attacker": h.attacker, "defender": h.defender, "move_id": h.move_id,
                  "bone_hit": h.bone_hit, "blocked": h.blocked, "knockdown": h.knockdown,
                  "severity": h.assessment.severity.value if h.assessment else 0} for h in sim.hits],
        "events": [{"frame": e.frame, "fighter": e.fighter, "kind": e.kind, "detail": e.detail} for e in sim.events],
        "fighters": {fid: {"health": f.health, "state": f.state.value, "wounds": len(f.wounds)}
                     for fid, f in sim.fighters.items()},
    }


def gameplay_runtime_table() -> Dict[str, object]:
    hitboxes = default_hitboxes(1.80)
    bones = sorted(hitboxes)
    scenarios = []
    for spec in _scenario_scripts():
        result = run_scenario(spec)
        scenarios.append({"spec": {**spec, "script": {str(k): v for k, v in spec["script"].items()}},
                          "expected": result})
    return {
        "schema": SCHEMA,
        "frame_rate": FRAME_RATE,
        "styles": {sid: {**dict(s), "moves": list(s["moves"]), "guard_absorbs": list(s["guard_absorbs"])}
                   for sid, s in GAMEPLAY_STYLES.items()},
        "moves": {mid: _move_entry(mv, bones) for mid, mv in SHENMUE_MOVES.items()},
        "hitboxes_1p80": hitboxes,
        "fallback_bone": "STERNUM",
        "knockdown_frames": 60,
        "reference_scenarios": scenarios,
        "notes": "Generated by character_engine.domain.gameplay.runtime_table; do not edit by hand. "
                 "Energy values are gameplay tuning constants; wound assessments are ESTIMATE provenance.",
    }
