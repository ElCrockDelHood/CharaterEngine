"""Head kinematics, concussion probability and stagger (domain/physics/head_kinematics.py, A16)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from character_engine.domain.physics.body_strike import LayeredBody
from character_engine.domain.physics.head_kinematics import (
    LEVER_HOOK_M,
    LEVER_STRAIGHT_M,
    P_STEP_N_S,
    ROWSON_2012_ROTATIONAL,
    STAGGER_LEVELS,
    concussion_probability,
    head_kinematics,
    knockback,
    knockback_of,
    stagger,
)
from character_engine.domain.physics.strike_model import Striker, strike_blunt
from character_engine.domain.tissue import BodyRegion

DATA = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
OLYMPIC_PUNCH = Striker(2.9, 9.14, 0.04)          # Walilko, Viano & Bir 2005 means


@pytest.fixture(scope="module")
def body():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    return LayeredBody(pts)


@pytest.fixture(scope="module")
def olympic(body):
    o = strike_blunt(body, "head", OLYMPIC_PUNCH)
    return o, knockback_of(o, OLYMPIC_PUNCH)


# --- acceptance against Walilko et al. 2005 (straight punches, Hybrid III face) -------------------------------------
def test_acceptance_peak_force_within_35_percent(olympic):
    o, _ = olympic
    assert abs(o.peak_force_n / 3427.0 - 1.0) < 0.35


def test_acceptance_linear_acceleration_within_factor_1_5(olympic):
    _, k = olympic
    assert 1 / 1.5 < k.head.linear_g / 58.0 < 1.5


def test_acceptance_rotational_acceleration_within_factor_2(olympic):
    _, k = olympic
    assert 0.5 < k.head.rotational_rad_s2 / 6343.0 < 2.0


def test_acceptance_concussion_probability_mid_range(olympic):
    _, k = olympic
    assert 0.2 <= k.head.concussion_probability <= 0.9


# --- risk table -----------------------------------------------------------------------------------------------------
def test_table_points_are_exact():
    for alpha, p in ROWSON_2012_ROTATIONAL:
        assert concussion_probability(alpha) == pytest.approx(p)


def test_probability_monotone_and_bounded():
    vals = [concussion_probability(a) for a in range(0, 12000, 250)]
    assert vals == sorted(vals)
    assert vals[0] == 0.0 and max(vals) == pytest.approx(0.99)


# --- monotonicity, conservation, determinism ------------------------------------------------------------------------
def test_monotone_in_speed(body):
    prev = None
    for v in (4.0, 6.0, 8.0, 10.0, 12.0):
        st = Striker(3.0, v, 0.04)
        k = knockback_of(strike_blunt(body, "head", st), st)
        cur = (k.head.linear_g, k.head.rotational_rad_s2, k.head.concussion_probability, k.stagger.impulse_n_s)
        if prev:
            assert all(c >= p for c, p in zip(cur, prev))
        prev = cur


def test_monotone_in_lever_arm():
    a = head_kinematics(3000.0, 5.2, LEVER_STRAIGHT_M)
    b = head_kinematics(3000.0, 5.2, LEVER_HOOK_M)
    assert b.rotational_rad_s2 > a.rotational_rad_s2
    assert b.concussion_probability >= a.concussion_probability
    assert b.linear_g == a.linear_g


def test_bracing_never_increases_stagger():
    order = {lvl: i for i, lvl in enumerate(STAGGER_LEVELS)}
    levels = [order[stagger(15.0, 6.0, 12.0, bracing=b).level] for b in (1.0, 1.3, 2.0, 3.0)]
    assert levels == sorted(levels, reverse=True)
    with pytest.raises(ValueError):
        stagger(3.0, 8.0, 12.0, bracing=0.5)


def test_stagger_thresholds():
    m_t = 12.0

    def level_for(j):                                       # very heavy striker: μ → m_t, so μ·v = j at v = j / m_t
        return stagger(1e9, j / m_t, m_t).level
    assert level_for(0.9 * P_STEP_N_S) == "none"
    assert level_for(1.1 * P_STEP_N_S) == "step"
    assert level_for(1.5 * P_STEP_N_S) == "steps"
    assert level_for(2.1 * P_STEP_N_S) == "fall"


def test_momentum_conservation():
    s = stagger(3.0, 8.0, 12.0)
    assert (3.0 + 12.0) * s.segment_speed_m_s == pytest.approx(3.0 * 8.0, rel=1e-4)
    assert s.impulse_n_s == pytest.approx(12.0 * s.segment_speed_m_s, rel=1e-4)
    assert s.impulse_n_s < s.striker_momentum_n_s


def test_head_fields_only_on_head_and_neck():
    assert knockback(BodyRegion.THORAX, 3.0, 8.0, 4000.0).head is None
    assert knockback(BodyRegion.NECK, 3.0, 8.0, 4000.0).head is not None


def test_deterministic(body):
    st = Striker.from_move(130.0, 0.05, "punch")
    a = knockback_of(strike_blunt(body, "head", st), st, LEVER_HOOK_M)
    b = knockback_of(strike_blunt(body, "head", st), st, LEVER_HOOK_M)
    assert a == b


def test_rowson_logistic_agrees_with_the_table_when_beta_is_unrounded():
    import math

    from character_engine.domain.physics.head_kinematics import ROWSON_2012_LOGISTIC
    alpha0, beta_printed = ROWSON_2012_LOGISTIC
    assert -alpha0 / beta_printed == pytest.approx(6266.0, abs=1.0)        # printed β (rounded): 50 % at 6266
    beta = -alpha0 / 6383.0                                                # unrounded β ≈ 0.001963 from the 50 % row
    for rot, p in ROWSON_2012_ROTATIONAL:
        assert 1.0 / (1.0 + math.exp(-(alpha0 + beta * rot))) == pytest.approx(p, abs=0.01)
