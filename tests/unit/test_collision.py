"""Striker / target effective mass and the inelastic energy split (domain/physics/collision.py, A14)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from character_engine.domain.physics.blunt import Impactor
from character_engine.domain.physics.body_strike import LayeredBody, sweep
from character_engine.domain.physics.collision import (
    SEGMENT_MASS_FRACTION,
    reduced_mass,
    regional_target_mass_kg,
    split,
)
from character_engine.domain.physics.cut import Blade
from character_engine.domain.tissue import BodyRegion

DATA = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
PUNCH = Impactor(2.9, 9.14, 0.04)
SABRE = Blade(0.6, 10.0, 0.028)


def _points():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    p = lambda d: (d["x"], d["y"], d["z"])  # noqa: E731
    return {b["canonical_name"]: (p(b["head"]), p(b["tail"])) for b in bones}


@pytest.fixture(scope="module")
def bodies():
    pts = _points()
    return LayeredBody(pts), LayeredBody(pts, target_mass_kg=regional_target_mass_kg())


def test_reduced_mass_limits():
    assert reduced_mass(3.0, None) == 3.0
    assert reduced_mass(3.0, math.inf) == 3.0
    assert reduced_mass(3.0, 3.0) == pytest.approx(1.5)
    assert reduced_mass(3.0, 1e9) == pytest.approx(3.0, rel=1e-6)
    with pytest.raises(ValueError):
        reduced_mass(0.0, 5.0)


def test_split_conserves_energy_and_momentum():
    s = split(2.9, 9.14, 5.0)
    assert s.deformation_j + s.momentum_j == pytest.approx(s.kinetic_j, abs=1e-5)
    assert (2.9 + 5.0) * s.target_speed_m_s == pytest.approx(2.9 * 9.14, rel=1e-5)
    assert 0.5 * 2.9 * s.deformation_speed_m_s ** 2 == pytest.approx(s.deformation_j, rel=1e-6)
    # A14 table: punch into a 5 kg head, 121 J → about 77 J of deformation
    assert s.kinetic_j == pytest.approx(121.1, abs=0.1)
    assert s.deformation_j == pytest.approx(76.7, abs=0.1)


def test_regional_target_mass_scales_and_validates():
    m = regional_target_mass_kg(75.0)
    assert set(m) == set(BodyRegion)
    assert m[BodyRegion.HEAD] == pytest.approx(75.0 * SEGMENT_MASS_FRACTION[BodyRegion.HEAD], abs=1e-3)
    assert m[BodyRegion.THIGH] > m[BodyRegion.LEG] > m[BodyRegion.FOOT] > m[BodyRegion.HAND]
    assert regional_target_mass_kg(75.0, bracing=2.0)[BodyRegion.HEAD] == pytest.approx(2 * m[BodyRegion.HEAD])
    with pytest.raises(ValueError):
        regional_target_mass_kg(75.0, bracing=0.5)


def test_default_body_is_unchanged(bodies):
    plain, _ = bodies
    r = plain.central_strike("thorax", PUNCH)
    assert r.collision is None
    assert r.energy_normal_j == pytest.approx(PUNCH.kinetic_energy_j, rel=5e-3)   # thorax tilt (Decision 72): -0.27 %
    assert all("deformation_j" not in row for row in sweep(plain, SABRE))


def test_target_mass_reduces_energy_more_on_light_segments(bodies):
    plain, reduced = bodies
    head, thorax = reduced.central_strike("head", PUNCH), reduced.central_strike("thorax", PUNCH)
    assert head.collision is not None and thorax.collision is not None
    assert head.energy_normal_j < thorax.energy_normal_j < PUNCH.kinetic_energy_j
    assert head.collision.momentum_j > thorax.collision.momentum_j
    assert head.depth_below_skin_m <= plain.central_strike("head", PUNCH).depth_below_skin_m


def test_light_blade_barely_changes(bodies):
    plain, reduced = bodies
    a, b = plain.central_strike("thorax", SABRE), reduced.central_strike("thorax", SABRE)
    assert b.collision.deformation_j / b.collision.kinetic_j > 0.95
    assert b.depth_below_skin_m == pytest.approx(a.depth_below_skin_m, abs=0.003)
    for row in sweep(reduced, SABRE):                # deformation + momentum = normal kinetic energy, per segment
        r = reduced.central_strike(row["segment"], SABRE)
        assert row["deformation_j"] + row["momentum_j"] == pytest.approx(r.collision.kinetic_j, abs=0.02)
