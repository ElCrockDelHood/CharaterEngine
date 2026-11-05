"""Weapon rigid-body dynamics behind a cut: effective mass, inertia, impact point (A34, domain/physics/cut.py)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.physics.body_strike import LayeredBody, sweep
from character_engine.domain.physics.cut import (
    P1796_MEASURED,
    Blade,
    BladeBody,
    BladeSwing,
    blade_body_from_balance,
    blade_impact,
    coupled_arm_mass_kg,
    effective_mass_at,
    p1796_sabre_body,
    swing_from_tip_speed,
)

DATA = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
M, L = 0.9, 0.9
ROD = BladeBody(M, L / 2.0, M * L * L / 12.0, L)     # uniform rod held at its end: textbook closed forms


def test_rod_closed_forms():
    assert ROD.inertia_about_kg_m2(0.0) == pytest.approx(M * L * L / 3.0)
    assert ROD.center_of_percussion_m() == pytest.approx(2.0 * L / 3.0)
    assert effective_mass_at(ROD, L) == pytest.approx(M / 4.0)                    # free rod, struck at its end
    assert effective_mass_at(ROD, L, math.inf) == pytest.approx(M / 3.0)          # pinned at the other end
    assert effective_mass_at(ROD, L / 2.0) == pytest.approx(M)                    # at the CG it is the whole mass


def test_coupled_mass_runs_from_free_to_pinned():
    for x in (0.7, 0.8, 0.9):                                                     # past the centre of percussion
        masses = [effective_mass_at(ROD, x, c) for c in (0.0, 0.5, 5.0, 1.0e9)]
        assert masses == sorted(masses)
        assert masses[-1] == pytest.approx(effective_mass_at(ROD, x, math.inf), rel=1e-6)


def test_coupling_at_the_centre_of_percussion_changes_nothing():
    # the grip does not move when struck there, so what is attached to the grip cannot matter
    cop = ROD.center_of_percussion_m()
    assert effective_mass_at(ROD, cop, 1.7) == pytest.approx(effective_mass_at(ROD, cop))


def test_grip_jolt_changes_sign_at_the_centre_of_percussion():
    cop = ROD.center_of_percussion_m()
    assert ROD.pivot_velocity_change_per_impulse(cop) == pytest.approx(0.0)
    assert ROD.pivot_velocity_change_per_impulse(cop - 0.1) > 0.0
    assert ROD.pivot_velocity_change_per_impulse(cop + 0.1) < 0.0


def test_balance_fit_keeps_mass_and_balance_and_rejects_the_impossible():
    b = blade_body_from_balance(0.93, 0.17, 0.82)
    assert (b.mass_kg, b.cg_m, b.tip_m) == pytest.approx((0.93, 0.24, 0.89))
    # a uniform blade with no hilt offset and the balance at mid-blade is a plain rod
    rod = blade_body_from_balance(1.0, 0.41, 0.82, 1.0, 0.0, 0.0)
    assert rod.inertia_cg_kg_m2 == pytest.approx(0.82 ** 2 / 12.0)
    with pytest.raises(ValueError):
        blade_body_from_balance(0.93, 0.60, 0.82)         # beyond the blade's own centroid
    with pytest.raises(ValueError):
        blade_body_from_balance(0.93, 0.17, 0.82, tip_density_ratio=0.0)


def test_p1796_uses_the_median_of_the_measured_sabres_and_stays_an_estimate():
    assert len(P1796_MEASURED) == 6
    b = p1796_sabre_body()
    assert b.mass_kg == pytest.approx(0.9375)
    assert b.cg_m == pytest.approx(0.07 + 0.1675)
    assert b.tip_m == pytest.approx(0.07 + 0.82)
    assert b.provenance is ProvenanceState.ESTIMATE


def test_a_blade_heavier_towards_the_tip_has_more_inertia_and_a_farther_percussion_centre():
    light, heavy = p1796_sabre_body(0.25), p1796_sabre_body(0.7)
    assert light.inertia_cg_kg_m2 < heavy.inertia_cg_kg_m2
    assert light.center_of_percussion_m() < heavy.center_of_percussion_m()


def test_contact_never_takes_more_than_the_swing_has():
    b = p1796_sabre_body()
    for frac in (0.0, 0.3, 0.6):
        s = swing_from_tip_speed(b, 15.0, frac)
        for x in (0.2, 0.4, 0.6, 0.8, b.tip_m):
            hit = blade_impact(b, s, x, 0.028)
            assert hit.contact_energy_j <= hit.swing_energy_j + 1e-9


def test_pure_rotation_about_a_pinned_grip_gives_the_same_energy_all_along_the_blade():
    b = p1796_sabre_body()
    s = swing_from_tip_speed(b, 15.0)
    e = [blade_impact(b, s, x, 0.028, math.inf).contact_energy_j for x in (0.3, 0.5, 0.7, b.tip_m)]
    assert e == pytest.approx([0.5 * b.inertia_about_kg_m2(0.0) * s.angular_speed_rad_s ** 2] * 4)


def test_free_blade_peaks_at_the_centre_of_percussion_in_pure_rotation():
    b = p1796_sabre_body()
    s = swing_from_tip_speed(b, 15.0)
    cop = b.center_of_percussion_m()
    at_cop = blade_impact(b, s, cop, 0.028)
    assert at_cop.contact_energy_j > blade_impact(b, s, b.tip_m, 0.028).contact_energy_j
    assert at_cop.contact_energy_j > blade_impact(b, s, cop - 0.25, 0.028).contact_energy_j
    assert at_cop.effective_mass_kg > blade_impact(b, s, b.tip_m, 0.028).effective_mass_kg


def test_swing_from_tip_speed_and_validation():
    b = p1796_sabre_body()
    s = swing_from_tip_speed(b, 15.0, 0.3)
    assert s.speed_at(0.0) == pytest.approx(4.5)
    assert s.speed_at(b.tip_m) == pytest.approx(15.0)
    with pytest.raises(ValueError):
        swing_from_tip_speed(b, 15.0, 1.0)
    with pytest.raises(ValueError):
        blade_impact(b, BladeSwing(0.0, 10.0), b.tip_m + 0.01, 0.028)
    with pytest.raises(ValueError):
        effective_mass_at(b, 0.5, -1.0)


def test_coupled_arm_mass_uses_the_segment_fractions():
    assert coupled_arm_mass_kg(75.0) == pytest.approx(75.0 * 0.0061)
    assert coupled_arm_mass_kg(75.0, include_forearm=True) == pytest.approx(75.0 * (0.0061 + 0.0162))


def test_the_impact_feeds_the_existing_cut_and_changes_no_default():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    p = lambda d: (d["x"], d["y"], d["z"])  # noqa: E731
    body = LayeredBody({x["canonical_name"]: (p(x["head"]), p(x["tail"])) for x in bones})
    sabre = p1796_sabre_body()
    hit = blade_impact(sabre, swing_from_tip_speed(sabre, 15.0), sabre.center_of_percussion_m(), 0.028)
    assert hit.blade.mass_provenance is ProvenanceState.ESTIMATE
    assert hit.blade.kinetic_energy_j == pytest.approx(hit.contact_energy_j)
    r = body.central_strike(next(iter(body.capsules)), hit.blade)
    assert r is not None and r.model == "cut"
    placeholder = Blade(0.6, 10.0, 0.028)                # the shipped placeholder keeps its energy and provenance
    assert placeholder.kinetic_energy_j == pytest.approx(30.0)
    assert placeholder.mass_provenance is ProvenanceState.PLACEHOLDER
    assert len(sweep(body, placeholder)) == len(body.capsules)
