"""Per-move striker records (domain/physics/move_strikers.py, A17)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from character_engine.domain.physics.body_strike import LayeredBody
from character_engine.domain.physics.head_kinematics import concussion_probability
from character_engine.domain.physics.move_strikers import (
    ENERGY_TOLERANCE,
    FRONT_KICK_SPEEDS,
    MOVE_STRIKERS,
    ROUNDHOUSE_IMPACT,
    SEOI_NAGE_HEAD,
    SHOULDER_THROW_FALL,
    FallLanding,
    foot_referred_mass_kg,
    leg_chain_energy_j,
    momentum_mass_fraction,
    move_striker,
)
from character_engine.domain.physics.strike_model import Striker, strike_blunt

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data" / "gameplay_shenmue.json"
DATA = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
MOVES = json.loads(TABLE.read_text(encoding="utf-8"))["moves"]
PROVENANCE = {"SOURCED", "ESTIMATE", "ASSUMED"}


def test_every_move_has_a_record():
    assert set(MOVES) == set(MOVE_STRIKERS)


def test_records_copy_the_table_energy_and_radius():
    for mid, mv in MOVES.items():
        r = move_striker(mid)
        assert r.table_energy_j == mv["energy_j"]
        assert r.contact_radius_m == mv["contact_radius_m"]


def test_nominal_energy_within_tolerance_or_flagged():
    for r in MOVE_STRIKERS.values():
        within = abs(r.energy_ratio - 1.0) <= ENERGY_TOLERANCE
        assert within == (r.energy_flag is None), r.move


def test_flagged_moves_are_the_front_and_crescent_kicks():
    flagged = {r.move for r in MOVE_STRIKERS.values() if r.energy_flag}
    assert flagged == {"front_kick", "crescent_kick"}
    assert MOVE_STRIKERS["front_kick"].energy_ratio > 1.0 > MOVE_STRIKERS["crescent_kick"].energy_ratio


def test_ranges_are_ordered_and_provenance_is_labelled():
    for r in MOVE_STRIKERS.values():
        for rng in (r.mass_kg, r.speed_m_s, r.lever_arm_m):
            assert rng[0] <= rng[1] <= rng[2], r.move
            assert rng[0] > 0.0
        assert set(r.provenance.values()) <= PROVENANCE
        assert r.note


def test_unknown_move_raises():
    with pytest.raises(KeyError):
        move_striker("haymaker")


def test_from_move_and_strike_model_unchanged():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    body = LayeredBody(pts)
    st = Striker.from_move(130.0, 0.05, "punch")
    assert (st.effective_mass_kg, st.speed_m_s) == pytest.approx((2.0 * 130.0 / 7.5 ** 2, 7.5))
    o = strike_blunt(body, "head", st)
    assert o.peak_force_n == pytest.approx(3711.0, abs=1.0)        # A16 move table, hook row


def test_deterministic():
    assert move_striker("jab") == move_striker("jab")
    assert MOVE_STRIKERS["hook"].nominal_energy_j == pytest.approx(0.5 * 2.9 * 9.14 ** 2)


def test_leg_chain_energy_by_hand():
    thigh, shank, foot = 0.1416 * 75, 0.0433 * 75, 0.0137 * 75
    expected = 0.5 * (thigh * 3.86 ** 2 + shank * 6.94 ** 2 + foot * 8.56 ** 2)
    assert leg_chain_energy_j(2.4, 5.32, 8.56) == pytest.approx(expected)
    assert leg_chain_energy_j(2.4, 5.32, 8.56) == pytest.approx(195.0, abs=0.5)


def test_front_kick_mass_is_the_leg_energy_at_the_foot_speed():
    r = move_striker("front_kick")
    hip, knee, foot = FRONT_KICK_SPEEDS["sub_elite"]
    assert r.speed_m_s[1] == foot
    assert r.mass_kg[1] == pytest.approx(foot_referred_mass_kg(hip, knee, foot), abs=0.01)
    assert r.nominal_energy_j == pytest.approx(leg_chain_energy_j(hip, knee, foot), rel=0.002)
    assert r.range_energy_j()[0] < r.table_energy_j < r.range_energy_j()[1]


def test_roundhouse_momentum_mass_agrees_across_groups():
    masses = [j / v for j, v, _ in ROUNDHOUSE_IMPACT.values()]
    assert min(masses) == pytest.approx(5.28, abs=0.01)
    assert max(masses) == pytest.approx(6.10, abs=0.01)
    assert momentum_mass_fraction() == pytest.approx(0.0700, abs=0.0005)
    assert move_striker("sweep").mass_kg == move_striker("crescent_kick").mass_kg


def test_table_energies_sit_inside_every_kick_range():
    for move in ("front_kick", "crescent_kick", "sweep"):
        lo, hi = move_striker(move).range_energy_j()
        assert lo < move_striker(move).table_energy_j < hi, move


def test_fall_energy_splits_into_trunk_and_the_rest():
    fall = SHOULDER_THROW_FALL
    h = fall.release_com_height_m[1]
    assert fall.total_energy_j(h) == pytest.approx(75.0 * 9.81 * (0.99 - 0.12))
    assert fall.trunk_mass_kg == pytest.approx(0.4346 * 75.0)
    assert fall.trunk_energy_j(h) + fall.limbs_and_head_energy_j(h) == pytest.approx(fall.total_energy_j(h))
    assert FallLanding(rest_com_height_m=0.12).impact_speed_m_s(0.05) == 0.0


def test_throw_record_is_the_trunk_landing():
    r = move_striker("shoulder_throw")
    h = SHOULDER_THROW_FALL.release_com_height_m[1]
    assert r.mass_kg[1] == pytest.approx(SHOULDER_THROW_FALL.trunk_mass_kg, abs=0.01)
    assert r.speed_m_s[1] == pytest.approx(SHOULDER_THROW_FALL.impact_speed_m_s(h), abs=0.01)
    assert r.energy_flag is None


def test_measured_seoi_nage_head_loads_sit_below_the_ten_percent_risk():
    for m in SEOI_NAGE_HEAD:
        assert m.angular_rad_s2[0] <= m.angular_rad_s2[1] <= m.angular_rad_s2[2]
        assert concussion_probability(m.angular_rad_s2[2]) < 0.10, m.source
    no_ukemi, ukemi = SEOI_NAGE_HEAD
    assert not no_ukemi.ukemi and ukemi.ukemi
    assert ukemi.angular_rad_s2[1] < no_ukemi.angular_rad_s2[1]
