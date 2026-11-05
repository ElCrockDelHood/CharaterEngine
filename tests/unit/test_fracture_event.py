"""Bone fragments of a fractured blow (domain/physics/fracture_event.py, A33)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from character_engine.domain.physics.body_strike import LayeredBody
from character_engine.domain.physics.fracture_event import (
    BUTTERFLY,
    FRAGMENT_KE_FRACTION,
    N_MAX,
    N_MIN,
    REGION_PATTERN,
    SCHEMA,
    SPIDERWEB,
    FractureEvent,
    excess_energy_j,
    fragment_count,
    strike_fracture,
)
from character_engine.domain.physics.strike_model import Striker

DATA = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
HEAVY = Striker(8.0, 12.0, 0.04)


@pytest.fixture(scope="module")
def body():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    return LayeredBody(pts)


def test_deterministic_for_the_same_seed(body):
    a = strike_fracture(body, "head", HEAVY, seed=7)[1]
    b = strike_fracture(body, "head", HEAVY, seed=7)[1]
    assert a == b
    assert strike_fracture(body, "head", HEAVY)[1] == strike_fracture(body, "head", HEAVY)[1]   # default seed too


def test_different_seeds_differ(body):
    a = strike_fracture(body, "head", HEAVY, seed=1)[1]
    b = strike_fracture(body, "head", HEAVY, seed=2)[1]
    assert a.fragments != b.fragments


def test_no_fragments_when_the_shell_holds(body):
    o, e = strike_fracture(body, "head", Striker(0.5, 6.0, 0.03))
    assert not o.fractured and not e.fractured
    assert e.fragments == () and e.patch_mass_kg == 0.0 and e.excess_energy_j == 0.0


def test_count_monotone_and_within_bounds():
    for pat in set(REGION_PATTERN.values()):
        counts = [fragment_count(pat, e) for e in (0.0, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 300.0, 1000.0, 1e5)]
        assert counts == sorted(counts)
        assert all(N_MIN <= c <= N_MAX for c in counts)
        assert counts[-1] == pat.cap


def test_skull_gives_more_fragments_than_a_long_bone_for_the_same_excess():
    for e in (10.0, 50.0, 200.0):
        assert fragment_count(SPIDERWEB, e) > fragment_count(BUTTERFLY, e)


def test_mass_sum_equals_the_patch_mass(body):
    for seg in ("head", "thorax", "thigh.L", "hand.R"):
        e = strike_fracture(body, seg, HEAVY)[1]
        assert e.fractured
        assert sum(f.mass_kg for f in e.fragments) == pytest.approx(e.patch_mass_kg, abs=1e-9)
        assert all(f.mass_kg > 0.0 and f.size_m > 0.0 for f in e.fragments)


def test_energy_and_momentum_stay_within_the_excess(body):
    for seg in ("head", "thorax", "thigh.L", "hand.R"):
        e = strike_fracture(body, seg, HEAVY)[1]
        budget = FRAGMENT_KE_FRACTION * e.excess_energy_j
        ke = sum(0.5 * f.mass_kg * sum(c * c for c in f.velocity_m_s) for f in e.fragments)
        assert ke == pytest.approx(e.fragment_kinetic_j, rel=1e-3)
        assert ke <= budget * (1.0 + 1e-3)
        p = [sum(f.mass_kg * f.velocity_m_s[i] for f in e.fragments) for i in range(3)]
        assert math.sqrt(sum(c * c for c in p)) <= math.sqrt(2.0 * e.patch_mass_kg * budget) * (1.0 + 1e-3)


def test_patch_is_never_wider_than_the_bone(body):
    e = strike_fracture(body, "thigh.L", Striker(3.7, 9.0, 0.06))[1]
    r = next(s.r_outer for s in body.capsules["thigh.L"].shells if s.material.value == "bone")
    assert all(abs(f.position_m[0]) <= 0.5 * math.pi * r + 1e-9 for f in e.fragments)
    wide = 2000.0 * math.pi * e.patch_radius_m ** 2 * e.shell_thickness_m * 0.6
    assert e.patch_mass_kg < wide


def test_no_fragment_faster_than_the_elastic_limit(body):
    e = strike_fracture(body, "hand.R", HEAVY)[1]
    assert all(math.sqrt(sum(c * c for c in f.velocity_m_s)) <= 2.0 * HEAVY.speed_m_s + 1e-6 for f in e.fragments)


def test_inner_fragments_move_inward(body):
    for seg in ("head", "thorax", "thigh.L"):
        e = strike_fracture(body, seg, HEAVY)[1]
        inner = [f for f in e.fragments if f.inner]
        assert inner
        for f in inner:
            speed = math.sqrt(sum(c * c for c in f.velocity_m_s))
            assert f.velocity_m_s[2] >= speed * math.cos(math.radians(20.0)) - 1e-6


def test_patterns_by_region(body):
    assert strike_fracture(body, "head", HEAVY)[1].pattern == "spiderweb"
    assert strike_fracture(body, "thorax", HEAVY)[1].pattern == "transverse_ribs"
    e = strike_fracture(body, "thigh.L", HEAVY)[1]
    assert e.pattern == "butterfly" and e.fragments[0].kind == "wedge"
    assert strike_fracture(body, "foot.L", HEAVY)[1].pattern == "small_pieces"


def test_excess_energy_uses_the_right_criterion(body):
    o = strike_fracture(body, "head", HEAVY)[0]
    assert excess_energy_j(o) == pytest.approx(o.dissipated_j - 23.0, abs=1e-6)     # skull: mid of 22-24 J
    o = strike_fracture(body, "thorax", HEAVY)[0]
    assert excess_energy_j(o) == pytest.approx(o.dissipated_j - 3300.0 ** 2 / (2 * 1.6e5), abs=1e-6)


def test_json_round_trip_and_key_order(body):
    e = strike_fracture(body, "thorax", HEAVY)[1]
    d = e.to_dict()
    assert d["schema"] == SCHEMA
    assert list(d)[:3] == ["schema", "segment", "region"]
    assert FractureEvent.from_dict(json.loads(json.dumps(d))) == e
    with pytest.raises(ValueError):
        FractureEvent.from_dict({**d, "schema": "other"})


def test_earlier_results_do_not_depend_on_this_module(body):
    # the strike outcome is the one strike_model gives on its own
    from character_engine.domain.physics.strike_model import strike_blunt
    assert strike_fracture(body, "thorax", HEAVY)[0] == strike_blunt(body, "thorax", HEAVY)
