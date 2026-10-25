"""Souls-like style (STYLE-SOULS-001 step 1): rules, Sentinel and the 9 reference scenarios."""

from __future__ import annotations

import pytest

from character_engine.domain.gameplay import WEAPONS
from character_engine.domain.gameplay.souls import (
    SOULS_MOVES,
    SOULS_TUNING,
    Sentinel,
    SoulsCombat,
    SoulsFighter,
    SoulsInput,
    SoulsState,
    run_souls_scenario,
    souls_reference_specs,
)
from character_engine.domain.trauma import WoundType

SPECS = {s["scenario_id"]: s for s in souls_reference_specs()}


@pytest.fixture(scope="module")
def runs():
    return {sid: run_souls_scenario(spec) for sid, spec in SPECS.items()}


def _kinds(run, fighter=None):
    return [e["kind"] for e in run["events"] if fighter is None or e["fighter"] == fighter]


def test_nine_reference_scenarios_and_determinism(runs):
    assert set(SPECS) == {"light_chain_lands", "dodge_through_heavy", "dodge_too_late", "stamina_exhausted",
                          "guard_break", "poise_break", "hyper_armour_trade", "sentinel_cycle_600",
                          "sentinel_punished"}
    for sid, spec in SPECS.items():
        assert run_souls_scenario(spec) == runs[sid], sid


def test_move_sets_per_weapon():
    for wid in ("unarmed", "staff", "short_blade"):
        light, heavy = SOULS_MOVES[f"{wid}_light"], SOULS_MOVES[f"{wid}_heavy"]
        assert heavy.startup > light.startup and heavy.poise_damage > light.poise_damage
        assert heavy.armour_from is not None and light.armour_from is None
        assert heavy.stamina_cost == 2 * light.stamina_cost


def test_light_chain_lands_three_times_and_stamina_regenerates(runs):
    r = runs["light_chain_lands"]
    assert [h["move_id"] for h in r["hits"]] == ["staff_light"] * 3
    starts = [e["detail"] for e in r["events"] if e["kind"] == "move_start"]
    assert starts == ["staff_light#1", "staff_light#2", "staff_light#3"]
    assert r["fighters"]["player"]["stamina"] > 100.0 - 45.0       # spent 45, then regenerated


def test_dodge_iframes(runs):
    through, late = runs["dodge_through_heavy"], runs["dodge_too_late"]
    assert "dodged" in _kinds(through, "player") and through["hits"] == []
    assert through["fighters"]["player"]["health"] == 100.0
    assert "dodged" not in _kinds(late) and late["hits"][0]["defender"] == "player"


def test_stamina_exhaustion_drops_inputs(runs):
    r = runs["stamina_exhausted"]
    assert _kinds(r, "player").count("move_start") == 6                # 6 × 15 = 90 of 100
    assert "no_stamina" in _kinds(r, "player")
    assert r["fighters"]["player"]["stamina"] >= 0.0


def test_guard_break_then_punished(runs):
    r = runs["guard_break"]
    kinds = _kinds(r, "opponent")
    assert kinds.index("blocked") < kinds.index("guard_break") < kinds.index("hit")
    assert r["hits"][0]["move_id"] == "staff_heavy"


def test_poise_break_on_second_heavy(runs):
    r = runs["poise_break"]
    assert len(r["hits"]) == 2 and _kinds(r, "opponent").count("poise_break") == 1
    assert r["events"][-1]["kind"] == "poise_break"


def test_hyper_armour_trade(runs):
    r = runs["hyper_armour_trade"]
    assert "armoured" in _kinds(r, "opponent")
    assert [h["defender"] for h in r["hits"]] == ["opponent", "player"]   # the light lands, the heavy still lands


def test_sentinel_pattern_is_telegraphed_and_repeats(runs):
    r = runs["sentinel_cycle_600"]
    starts = [e["detail"] for e in r["events"] if e["kind"] == "move_start" and e["fighter"] == "opponent"]
    assert starts[:6] == ["staff_light#1", "staff_light#2", "staff_heavy"] * 2
    tele = [e["frame"] for e in r["events"] if e["kind"] == "telegraph"]
    first_attack = next(e["frame"] for e in r["events"] if e["kind"] == "move_start")
    assert len(tele) >= 2 and first_attack - tele[0] >= SOULS_TUNING["telegraph_frames"]
    assert r["fighters"]["opponent"]["health"] == 100.0                  # the passive player never hits back


def test_sentinel_is_punished_in_its_recovery_window(runs):
    r = runs["sentinel_punished"]
    heavy_end = max(h["frame"] for h in r["hits"] if h["move_id"] == "staff_heavy" and h["defender"] == "player")
    punish = [h for h in r["hits"] if h["defender"] == "opponent"]
    assert punish and heavy_end < punish[0]["frame"] < heavy_end + SOULS_MOVES["staff_heavy"].recovery + \
        SOULS_TUNING["punish_window"] + SOULS_MOVES["staff_light"].startup + 2


def test_blade_cuts_and_staff_bruises():
    sim = SoulsCombat([SoulsFighter("a", (0.0, 0.0, 0.0), WEAPONS["short_blade"]),
                       SoulsFighter("b", (0.0, -0.9, 0.0), WEAPONS["staff"])])
    sim.feed("a", SoulsInput(light=True))
    for _ in range(15):
        sim.step()
    assert sim.hits[0].assessment.wound.wound_type is WoundType.INCISION
    sim.feed("b", SoulsInput(light=True))
    for _ in range(20):
        sim.step()
    assert sim.hits[-1].assessment.wound.wound_type is WoundType.BLUNT


def test_no_dodge_during_attack_startup():
    sim = SoulsCombat([SoulsFighter("a"), SoulsFighter("b", (0.0, -3.0, 0.0))])
    sim.feed("a", SoulsInput(heavy=True))
    sim.step()
    sim.feed("a", SoulsInput(dodge=True))
    sim.step()
    assert sim.fighters["a"].state == SoulsState.STARTUP


def test_held_inputs_last_one_frame():
    sim = SoulsCombat([SoulsFighter("a"), SoulsFighter("b", (0.0, -3.0, 0.0))])
    sim.feed("a", SoulsInput(direction="F"))
    sim.step()
    y = sim.fighters["a"].position[1]
    sim.step()
    assert sim.fighters["a"].position[1] == y and sim.fighters["a"].state == SoulsState.IDLE


def test_sentinel_stays_out_of_combat_when_target_is_dead():
    sim = SoulsCombat([SoulsFighter("p"), SoulsFighter("s", (0.0, -3.0, 0.0), WEAPONS["staff"])])
    sim.fighters["p"].state = SoulsState.KO
    assert Sentinel("s").decide(sim) == SoulsInput()


def test_tuning_is_placeholder_and_shenmue_untouched():
    from character_engine.domain.gameplay import gameplay_runtime_table
    from character_engine.domain.gameplay.souls import PROVENANCE

    assert PROVENANCE.value == "placeholder"
    table = gameplay_runtime_table()
    assert "souls_like" in table["styles"] and table["styles"]["souls_like"]["moves"] == []   # JSON is step 2
