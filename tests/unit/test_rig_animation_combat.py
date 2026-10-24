"""Rig definition, mocap bone maps and the Shenmue-style combat state machine."""

import json
from pathlib import Path

import pytest

from character_engine.domain.animation import BONE_MAPS, get_bone_map, invert
from character_engine.domain.gameplay import (
    GAMEPLAY_STYLES,
    SHENMUE_MOVES,
    CombatInput,
    CombatState,
    Fighter,
    MoveKind,
    ShenmueCombat,
    default_hitboxes,
)
from character_engine.domain.rigging import HUMANOID_RIG, IKChain, RigDefinition, validate_rig_against_bones

CANON = Path(__file__).resolve().parents[2] / "src/character_engine/data/anatomy/human_adult_206.json"


@pytest.fixture(scope="module")
def bone_names():
    return {b["canonical_name"] for b in json.loads(CANON.read_text(encoding="utf-8"))["bones"]}


# ------------------------------------------------------------------ rigging --------------

def test_humanoid_rig_references_only_canonical_bones(bone_names):
    assert validate_rig_against_bones(HUMANOID_RIG, bone_names) == []
    ids = {c.chain_id for c in HUMANOID_RIG.ik_chains}
    assert {"arm_L", "arm_R", "leg_L", "leg_R"} <= ids
    legs = [c for c in HUMANOID_RIG.ik_chains if c.chain_id.startswith("leg_")]
    assert all(c.foot_roll for c in legs)
    assert HUMANOID_RIG.properties["arm_ik_L"] == 1.0  # IK by default, FK switchable


def test_rig_has_spine_neck_fingers_and_breath_control():
    spline = {s.chain_id: s for s in HUMANOID_RIG.spline_chains}
    assert spline["spine"].bones[0] == "LUMBAR_5" and spline["spine"].bones[-1] == "THORACIC_1"
    assert spline["neck"].bones == tuple(f"CERVICAL_{i}" for i in range(7, 0, -1))
    assert len(spline["finger_1_L"].bones) == 3 and len(spline["finger_2_L"].bones) == 4
    breath = next(c for c in HUMANOID_RIG.controls if c.name == "CTRL-breath")
    assert "STERNUM" in breath.drives and "RIB_01_L" in breath.drives


def test_validate_reports_problems(bone_names):
    bad = RigDefinition("bad", ik_chains=(IKChain("x", ("FEMUR_L", "NOPE"), "TALUS_L", (0, 0, 0), "p"),
                                          IKChain("x", ("TIBIA_L",), "TALUS_L", (0, 0, 0), "p")),
                        spline_chains=(), controls=())
    problems = validate_rig_against_bones(bad, bone_names)
    assert any("NOPE" in p for p in problems) and any("duplicate" in p for p in problems)


# ------------------------------------------------------------------ bone maps ------------

@pytest.mark.parametrize("map_id", sorted(BONE_MAPS))
def test_bone_maps_target_canonical_bones(map_id, bone_names):
    bm = get_bone_map(map_id)
    for src, canon in bm.source_to_canonical.items():
        assert canon in bone_names, f"{map_id}: {src} -> {canon}"
    assert bm.scale_to_m > 0


def test_mixamo_prefix_and_symmetry():
    bm = get_bone_map("mixamo")
    assert bm.canonical("mixamorig:LeftArm") == "HUMERUS_L"
    assert bm.canonical("RightArm") == "HUMERUS_R"
    assert bm.canonical("mixamorig:LeftHandIndex4") == "PHALANX_DISTAL_2_L"
    assert bm.canonical("Unknown") is None
    assert bm.coverage() >= 60
    inv = invert(bm)
    assert inv["HUMERUS_L"] == "mixamorig:LeftArm"


def test_cmu_aliases():
    bm = get_bone_map("cmu_bvh")
    assert bm.canonical("LowerBack") == "LUMBAR_5"
    assert bm.canonical("Neck1") == "CERVICAL_1"
    with pytest.raises(KeyError):
        get_bone_map("vicon_xyz")


# ------------------------------------------------------------------ combat ---------------

def _sim(distance=0.7):
    return ShenmueCombat([Fighter("ryo", (0.0, 0.0, 0.0)), Fighter("dummy", (0.0, -distance, 0.0))])


def _run(sim, frames):
    for _ in range(frames):
        sim.step()


def test_move_table_is_consistent(bone_names):
    for mv in SHENMUE_MOVES.values():
        assert mv.startup > 0 and mv.active > 0 and mv.recovery > 0
        assert mv.striking_bone in bone_names and mv.target_region_bone in bone_names
        for nxt in mv.cancel_into:
            assert nxt in SHENMUE_MOVES
    assert GAMEPLAY_STYLES["shenmue"]["lock_on"] is True
    assert set(GAMEPLAY_STYLES["shenmue"]["moves"]) == set(SHENMUE_MOVES)


def test_hitboxes_scale_with_stature():
    assert default_hitboxes(1.80)["CRANIUM"] == pytest.approx(0.10)
    assert default_hitboxes(0.90)["CRANIUM"] == pytest.approx(0.05)


def test_jab_frame_data_and_hit():
    sim = _sim()
    sim.feed("ryo", CombatInput(punch=True))
    ryo, dummy = sim.fighters["ryo"], sim.fighters["dummy"]
    jab = SHENMUE_MOVES["jab"]
    assert ryo.state == CombatState.STARTUP and ryo.current_move == "jab"
    _run(sim, jab.startup + 1)
    assert ryo.state == CombatState.ACTIVE
    assert len(sim.hits) == 1 and sim.hits[0].bone_hit == "MANDIBLE" and not sim.hits[0].blocked
    assert dummy.state == CombatState.HITSTUN and dummy.health < 100.0
    assert sim.hits[0].assessment is not None and sim.hits[0].assessment.severity.value == 1
    _run(sim, jab.active + jab.recovery + 1)
    assert ryo.state == CombatState.IDLE and ryo.current_move is None


def test_command_input_selects_longest_match():
    sim = _sim()
    sim.feed("ryo", CombatInput(direction="F"))
    sim.step()
    sim.feed("ryo", CombatInput(direction="F"))
    sim.step()
    sim.feed("ryo", CombatInput(punch=True))
    assert sim.fighters["ryo"].current_move == "elbow_assault"


def test_stale_inputs_expire():
    sim = _sim()
    sim.feed("ryo", CombatInput(direction="F"))
    _run(sim, 40)
    sim.feed("ryo", CombatInput(punch=True))
    assert sim.fighters["ryo"].current_move == "jab"


def test_guard_blocks_strikes_but_not_throws():
    sim = _sim(distance=0.5)
    sim.feed("dummy", CombatInput(guard=True))
    sim.step()
    assert sim.fighters["dummy"].state == CombatState.GUARD
    sim.feed("ryo", CombatInput(punch=True))
    _run(sim, 10)
    assert sim.hits[0].blocked and sim.fighters["dummy"].health == 100.0
    _run(sim, 40)
    sim.feed("dummy", CombatInput(guard=True))
    sim.step()
    sim.feed("ryo", CombatInput(direction="F"))
    sim.step()
    sim.feed("ryo", CombatInput(throw=True))
    assert sim.fighters["ryo"].current_move == "shoulder_throw"
    _run(sim, 12)
    throw_hit = sim.hits[-1]
    assert throw_hit.move_id == "shoulder_throw" and not throw_hit.blocked and throw_hit.knockdown
    assert sim.fighters["dummy"].state == CombatState.KNOCKDOWN


def test_whiff_when_out_of_range():
    sim = _sim(distance=3.0)
    sim.feed("ryo", CombatInput(kick=True))
    _run(sim, 15)
    assert sim.hits == [] and any(e.kind == "whiff" for e in sim.events)


def test_recovery_cancel_chain():
    sim = _sim()
    sim.feed("ryo", CombatInput(punch=True))
    jab = SHENMUE_MOVES["jab"]
    _run(sim, jab.startup + jab.active + 1)
    assert sim.fighters["ryo"].state == CombatState.RECOVERY
    sim.feed("ryo", CombatInput(direction="F"))
    sim.feed("ryo", CombatInput(punch=True))
    assert sim.fighters["ryo"].current_move == "hook"


def test_repeated_jabs_eventually_ko_with_wound_log():
    sim = _sim()
    for _ in range(3000):
        if not sim.fighters["dummy"].alive:
            break
        if sim.fighters["ryo"].state == CombatState.IDLE:
            sim.feed("ryo", CombatInput(punch=True))
        sim.step()
    dummy = sim.fighters["dummy"]
    assert dummy.state == CombatState.KO and dummy.health == 0.0
    assert len(dummy.wounds) == len([h for h in sim.hits if not h.blocked])
    assert all(w.wound.wound_type.value == "blunt" for w in dummy.wounds)
    assert any(e.kind == "ko" for e in sim.events)
    # A KO'd fighter is no longer targeted
    assert sim.nearest_opponent(sim.fighters["ryo"]) is None
    assert SHENMUE_MOVES["jab"].kind == MoveKind.PUNCH
