"""Per-move striker records (domain/physics/move_strikers.py, A17)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from character_engine.domain.physics.body_strike import LayeredBody
from character_engine.domain.physics.move_strikers import ENERGY_TOLERANCE, MOVE_STRIKERS, move_striker
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


def test_flagged_moves_are_the_kicks_and_the_throw():
    flagged = {r.move for r in MOVE_STRIKERS.values() if r.energy_flag}
    assert flagged == {"front_kick", "crescent_kick", "sweep", "shoulder_throw"}


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
