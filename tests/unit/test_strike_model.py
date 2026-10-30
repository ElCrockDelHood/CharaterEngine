"""Reduced-mass strike with a force-based fracture criterion (domain/physics/strike_model.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from character_engine.domain.physics.body_strike import LayeredBody
from character_engine.domain.physics.strike_model import (
    REGION_RESPONSE,
    TARGET_MASS_KG,
    Striker,
    fracture_probability,
    peak_force,
    reduced_mass,
    strike_blunt,
)
from character_engine.domain.tissue import BodyRegion

DATA = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"


@pytest.fixture(scope="module")
def body():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    return LayeredBody(pts)


def test_reduced_mass_limits():
    assert reduced_mass(2.0, 1e9) == pytest.approx(2.0, rel=1e-6)       # immovable target: all of m
    assert reduced_mass(1e9, 5.0) == pytest.approx(5.0, rel=1e-6)       # huge striker: the target's mass
    assert reduced_mass(3.0, 3.0) == pytest.approx(1.5)


def test_energy_is_split_between_tissue_and_knockback(body):
    st = Striker(2.9, 9.1, 0.04)                                        # Walilko-like olympic boxer punch
    o = strike_blunt(body, "head", st)
    assert o.dissipated_j + o.knockback_j == pytest.approx(o.striker_energy_j, abs=1e-2)
    assert 0.0 < o.dissipated_j < o.striker_energy_j
    assert o.dissipated_j == pytest.approx(0.5 * o.reduced_mass_kg * 9.1 ** 2, rel=1e-3)


def test_free_head_takes_less_than_a_fixed_torso(body):
    st = Striker(3.0, 8.0, 0.04)
    head = strike_blunt(body, "head", st)
    torso = strike_blunt(body, "thorax", st)
    assert head.dissipated_j / head.striker_energy_j < torso.dissipated_j / torso.striker_energy_j


def test_cadaver_thorax_peak_forces_within_a_factor_two():
    r = REGION_RESPONSE[BodyRegion.THORAX]
    for m, v, measured in ((0.14, 20.0, 3383.0), (0.14, 40.0, 10602.0), (0.04, 60.0, 3158.0)):
        f = peak_force(v, r.stiffness_n_per_m, reduced_mass(m, TARGET_MASS_KG[BodyRegion.THORAX]))
        assert 0.5 < f / measured < 2.0, (m, v, f)


def test_fracture_probability_is_monotone_and_hits_the_range_ends():
    rng = (1000.0, 2000.0, 4000.0)
    assert fracture_probability(500.0, rng) == 0.0
    assert fracture_probability(2000.0, rng) == pytest.approx(0.5)
    assert fracture_probability(9000.0, rng) == 1.0
    vals = [fracture_probability(f, rng) for f in range(0, 5000, 250)]
    assert vals == sorted(vals)


def test_harder_blow_never_gives_a_lower_fracture_probability(body):
    for seg in ("thorax", "forearm.L", "thigh.L"):
        probs = [strike_blunt(body, seg, Striker(3.0, v, 0.045)).fracture_probability for v in (3.0, 5.0, 7.5, 10.0)]
        assert probs == sorted(probs), seg


def test_skull_needs_both_force_and_energy(body):
    weak = strike_blunt(body, "head", Striker(0.5, 6.0, 0.03))          # low energy
    assert not weak.fractured
    assert weak.energy_criterion_met is False


def test_fracture_breaches_the_bone_layer(body):
    o = strike_blunt(body, "thorax", Striker(6.0, 9.0, 0.05))
    assert o.fractured
    assert o.assessment.fracture
    assert o.layers.affected_depth_m >= body.capsules["thorax"].profile.depth_to_layer(
        __import__("character_engine.domain.tissue", fromlist=["TissueLayer"]).TissueLayer.BONE)


def test_deterministic(body):
    st = Striker.from_move(130.0, 0.05, "punch")
    a, b = strike_blunt(body, "forearm.R", st), strike_blunt(body, "forearm.R", st)
    assert (a.peak_force_n, a.assessment.severity, a.layers.affected_depth_m) == \
           (b.peak_force_n, b.assessment.severity, b.layers.affected_depth_m)


def test_from_move_keeps_the_table_energy():
    st = Striker.from_move(220.0, 0.06, "kick")
    assert st.kinetic_energy_j == pytest.approx(220.0)


def test_target_masses_are_the_collision_table():
    from character_engine.domain.physics.collision import regional_target_mass_kg
    assert dict(TARGET_MASS_KG) == regional_target_mass_kg()
