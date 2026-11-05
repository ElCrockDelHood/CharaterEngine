"""Whole-body layered strike: 17 capsules, one ray, one Wound (see domain/physics/body_strike.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from character_engine.domain.materials.catalog import MaterialKind
from character_engine.domain.materials.layered_capsule import OuterLayer
from character_engine.domain.physics.blunt import Impactor
from character_engine.domain.physics.body_strike import LayeredBody, sweep
from character_engine.domain.physics.cut import Blade

DATA = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"


def _points():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    p = lambda d: (d["x"], d["y"], d["z"])  # noqa: E731
    return {b["canonical_name"]: (p(b["head"]), p(b["tail"])) for b in bones}


@pytest.fixture(scope="module")
def body():
    return LayeredBody(_points())


SABRE = Blade(0.6, 10.0, 0.028)
CLUB = Impactor(1.2, 9.0, 0.03)


def test_every_segment_gets_layers(body):
    assert len(body.capsules) == 17
    for name, lc in body.capsules.items():
        assert lc.outer_radius >= lc.skin_radius > 0, name
        assert lc.shells, name


def test_central_strike_hits_its_own_segment(body):
    # since Decision 72 the neck has its real length, so a strike at the neck no longer lands on the thorax block
    for name in body.capsules:
        r = body.central_strike(name, CLUB)
        assert r is not None, name
        assert r.segment == name, name
        assert r.incidence_cos > 0.95, name


def test_deterministic(body):
    a = sweep(body, SABRE)
    b = sweep(LayeredBody(_points()), SABRE)
    assert a == b


def test_missed_ray_returns_none(body):
    assert body.strike(CLUB, (5.0, 5.0, 5.0), (0.0, 0.0, 1.0)) is None


def test_glancing_blow_loses_energy(body):
    p = body.placements["thigh.L"]
    mid = tuple((p.a[i] + p.b[i]) / 2 for i in range(3))
    r = p.radius_m
    # same ray direction, shifted sideways so the incidence angle grows
    head_on = body.strike(CLUB, (mid[0], mid[1] - 1.0, mid[2]), (0.0, 1.0, 0.0))
    off = body.strike(CLUB, (mid[0] + 0.85 * r, mid[1] - 1.0, mid[2]), (0.0, 1.0, 0.0))
    assert off.incidence_cos < head_on.incidence_cos
    assert off.energy_normal_j < head_on.energy_normal_j
    assert off.energy_normal_j == pytest.approx(off.energy_in_j * off.incidence_cos ** 2, rel=1e-3)


def test_thorax_matches_sample_two_unvested(body):
    r = body.central_strike("thorax", CLUB)
    assert r.stopped_in == "through" and r.depth_below_skin_m == pytest.approx(0.13, abs=1e-6)
    assert r.assessment.severity.name == "CRITICAL" and r.assessment.fracture


def test_vest_stops_what_the_bare_thorax_does_not():
    vested = LayeredBody(_points(), garments={"thorax": (
        OuterLayer("vest", MaterialKind.PADDED_CLOTH, 0.02, 0.004),
        OuterLayer("coat", MaterialKind.CLOTH_WOOL, 0.003, 0.008))})
    bare = LayeredBody(_points())
    a, b = bare.central_strike("thorax", CLUB), vested.central_strike("thorax", CLUB)
    assert a.assessment.fracture and not b.assessment.fracture
    assert b.assessment.severity.value < a.assessment.severity.value


def test_sabre_through_hand_but_not_through_thigh(body):
    hand = body.central_strike("hand.L", SABRE)
    thigh = body.central_strike("thigh.L", SABRE)
    assert hand.stopped_in == "through"
    assert thigh.stopped_in != "through"
    assert thigh.model == "cut" and thigh.assessment is not None


def test_harder_blow_never_hurts_less(body):
    slow = body.central_strike("abdomen", Impactor(1.2, 3.0, 0.03))
    fast = body.central_strike("abdomen", Impactor(1.2, 12.0, 0.03))
    assert fast.depth_below_skin_m >= slow.depth_below_skin_m
    assert fast.assessment.severity.value >= slow.assessment.severity.value


def test_calibrated_rigid_shell_energy_is_opt_in_and_region_specific():
    from character_engine.domain.physics.body_strike import FIGHT_RIGID_SHELL_ENERGY_J
    default = LayeredBody(_points())
    calibrated = LayeredBody(_points(), rigid_shell_energy_j=FIGHT_RIGID_SHELL_ENERGY_J)
    jab = Impactor(120.0, 1.0, 0.03)                       # 60 J
    assert default.central_strike("thorax", jab).assessment.fracture            # 25 J default breaks the ribs
    assert not calibrated.central_strike("thorax", jab).assessment.fracture    # 150 J does not
    assert calibrated.central_strike("hand.L", jab).assessment.fracture        # 20 J hand bones still do


def test_calibrated_fracture_is_monotone_in_energy():
    from character_engine.domain.physics.body_strike import FIGHT_RIGID_SHELL_ENERGY_J
    cal = LayeredBody(_points(), rigid_shell_energy_j=FIGHT_RIGID_SHELL_ENERGY_J)
    seen = False
    for e in (20.0, 60.0, 150.0, 300.0, 600.0):
        broke = cal.central_strike("thorax", Impactor(2 * e, 1.0, 0.03)).assessment.fracture
        assert broke or not seen                                   # once it breaks it stays broken
        seen = seen or broke
    assert seen
