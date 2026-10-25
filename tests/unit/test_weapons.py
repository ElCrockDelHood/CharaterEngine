"""Weapons in the gameplay domain: provenance, grip contract, reach / energy / wound routing."""

from __future__ import annotations

import pytest

from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.character import load_canonical_bones
from character_engine.domain.gameplay import (
    SHENMUE_MOVES,
    UNARMED,
    WEAPONS,
    CombatInput,
    Fighter,
    ShenmueCombat,
    WeaponCategory,
    gameplay_runtime_table,
    run_scenario,
    weapon,
)
from character_engine.domain.gameplay.combat import _health_cost
from character_engine.domain.gameplay.runtime_table import _scenario_scripts
from character_engine.domain.gameplay.weapons import NUMERIC_FIELDS
from character_engine.domain.rigging import EQUIPMENT_SOCKETS
from character_engine.domain.trauma import WoundType, assess_wound, blunt_impact_to_wound

UNARMED_IDS = ("jab_lands", "guard_blocks_jab", "throw_beats_guard", "elbow_command", "crescent_knockdown",
               "whiff_out_of_reach", "autoplay_180")


def _jab_at(distance_m: float, w) -> ShenmueCombat:
    sim = ShenmueCombat([Fighter("a", (0.0, 0.0, 0.0), weapon=w), Fighter("b", (0.0, -distance_m, 0.0))])
    sim.feed("a", CombatInput(punch=True))
    for _ in range(20):
        sim.step()
    return sim


def test_registry_has_unarmed_and_examples():
    assert set(WEAPONS) >= {"unarmed", "staff", "short_blade"}
    assert WEAPONS["unarmed"] is UNARMED and weapon("staff").category is WeaponCategory.BLUNT
    with pytest.raises(KeyError):
        weapon("halberd")


@pytest.mark.parametrize("wid", sorted(WEAPONS))
def test_every_numeric_value_has_a_non_proven_provenance(wid):
    w = WEAPONS[wid]
    assert set(w.provenance) == set(NUMERIC_FIELDS)
    allowed = {ProvenanceState.ESTIMATE, ProvenanceState.ASSUMED, ProvenanceState.PLACEHOLDER}
    assert set(w.provenance.values()) <= allowed
    assert w.notes


@pytest.mark.parametrize("wid", sorted(WEAPONS))
def test_grip_bone_is_canonical_and_matches_the_hand_grip_socket(wid):
    names = {b["canonical_name"] for b in load_canonical_bones()[0]}
    w = WEAPONS[wid]
    assert w.grip_bone in names
    socket = next(s for s in EQUIPMENT_SOCKETS if s.name == w.grip_socket)
    assert socket.parent_bone == w.grip_bone


def test_wound_types_map_to_trauma():
    assert UNARMED.wound_type is WoundType.BLUNT
    assert weapon("staff").wound_type is WoundType.BLUNT
    assert weapon("short_blade").wound_type is WoundType.INCISION
    assert weapon("short_blade").strike_wound("MANDIBLE", 60.0).wound_type is WoundType.INCISION
    assert weapon("staff").strike_wound("MANDIBLE", 78.0).energy_j == 78.0


def test_weapon_applies_to_hand_strikes_only():
    blade, staff = weapon("short_blade"), weapon("staff")
    applies = {mid for mid, mv in SHENMUE_MOVES.items() if blade.applies_to(mv.kind.value, mv.striking_bone)}
    assert applies == {"jab", "hook"}                       # right-hand punches; left straight, elbow excluded
    assert "straight" in {mid for mid, mv in SHENMUE_MOVES.items()
                          if staff.applies_to(mv.kind.value, mv.striking_bone)}   # two-handed
    for mv in SHENMUE_MOVES.values():
        assert not UNARMED.applies_to(mv.kind.value, mv.striking_bone)
        if mv.kind.value != "punch":
            assert not blade.applies_to(mv.kind.value, mv.striking_bone)
            assert not staff.applies_to(mv.kind.value, mv.striking_bone)


def test_unarmed_reference_fights_are_unchanged_by_the_weapon_field():
    specs = {s["scenario_id"]: s for s in _scenario_scripts()}
    for sid in UNARMED_IDS:
        assert "weapons" not in specs[sid]
        armed_spec = {**specs[sid], "weapons": {"player": "unarmed", "opponent": "unarmed"}}
        assert run_scenario(armed_spec) == run_scenario(specs[sid])


def test_blade_extends_reach_and_cuts():
    assert not _jab_at(1.0, UNARMED).hits
    sim = _jab_at(1.0, weapon("short_blade"))
    hit = sim.hits[0]
    assert hit.weapon_id == "short_blade" and hit.bone_hit == "MANDIBLE"
    assert hit.assessment.wound.wound_type is WoundType.INCISION
    assert hit.assessment.wound.depth_m == weapon("short_blade").cut_depth_m


def test_blunt_weapon_multiplies_energy_and_uses_its_contact_radius():
    staff = weapon("staff")
    sim = _jab_at(0.7, staff)
    hit = sim.hits[0]
    jab = SHENMUE_MOVES["jab"]
    assert hit.energy_j == pytest.approx(jab.energy_j * staff.energy_multiplier)
    assert hit.assessment.wound.width_m == pytest.approx(staff.contact_radius_m * 2)
    expected = assess_wound(blunt_impact_to_wound("MANDIBLE", contact_radius_m=staff.contact_radius_m,
                                                  energy_j=hit.energy_j))
    assert sim.fighters["b"].health == pytest.approx(100.0 - _health_cost(expected, jab, hit.energy_j))


def test_kicks_stay_unarmed_with_a_weapon():
    sim = ShenmueCombat([Fighter("a", (0.0, 0.0, 0.0), weapon=weapon("staff")), Fighter("b", (0.0, -1.0, 0.0))])
    sim.feed("a", CombatInput(kick=True))
    for _ in range(30):
        sim.step()
    assert sim.hits[0].weapon_id == "unarmed" and sim.hits[0].energy_j == SHENMUE_MOVES["front_kick"].energy_j


def test_table_carries_weapons_with_precomputed_impacts():
    t = gameplay_runtime_table()
    assert t["default_weapon"] == "unarmed" and set(t["weapons"]) == set(WEAPONS)
    assert t["weapons"]["unarmed"]["applies_to_moves"] == [] and t["weapons"]["unarmed"]["impacts"] == {}
    blade = t["weapons"]["short_blade"]
    assert blade["wound_type"] == "incision" and set(blade["impacts"]) == set(blade["applies_to_moves"])
    for imp in blade["impacts"]["jab"].values():
        assert imp["provenance"] == "estimate" and imp["health_cost"] > 0
    ids = [sc["spec"]["scenario_id"] for sc in t["reference_scenarios"]]
    assert set(UNARMED_IDS) < set(ids) and any("weapons" in sc["spec"] for sc in t["reference_scenarios"])


def test_staff_reference_scenario_chains_left_hand_and_kick_whiffs():
    spec = next(s for s in _scenario_scripts() if s["scenario_id"] == "staff_chain_and_kick")
    out = run_scenario(spec)
    assert [h["move_id"] for h in out["hits"]] == ["jab", "straight"]
    assert any(e["kind"] == "whiff" and e["detail"] == "front_kick" for e in out["events"])
