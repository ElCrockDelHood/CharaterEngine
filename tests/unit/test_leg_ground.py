"""Leg grounding (domain/animation/leg_ground.py, Decision 85): ankle heights from the source, support foot."""

import pytest

from character_engine.domain.animation.leg_ground import ankle_targets, knee_pole, plan

SRC_REST = {"L": 0.08, "R": 0.08}
DST_REST = {"L": 0.07, "R": 0.07}


def test_planted_feet_go_back_to_their_rest_height():
    # idle: both source ankles at rest; ours sink 2.5 cm -> the whole body rises 2.5 cm, no leg change
    g = plan({"L": 0.08, "R": 0.08}, SRC_REST, {"L": 0.045, "R": 0.045}, DST_REST, 1.0)
    assert g.root_dz == pytest.approx(0.025)
    assert g.foot("L") == pytest.approx(0.0) and g.foot("R") == pytest.approx(0.0)


def test_crouch_hover_is_removed_by_the_pelvis():
    # crouch: source feet planted, ours hover 23 cm -> body drops, legs untouched
    g = plan({"L": 0.08, "R": 0.08}, SRC_REST, {"L": 0.30, "R": 0.30}, DST_REST, 0.95)
    assert g.root_dz == pytest.approx(-0.23)
    assert g.foot("L") == pytest.approx(0.0)


def test_support_is_the_lower_source_foot_and_the_swing_foot_keeps_its_lift():
    # walk: right foot planted, left lifted 10 cm in the source (scale 0.9 -> 9 cm on ours)
    g = plan({"L": 0.18, "R": 0.08}, SRC_REST, {"L": 0.12, "R": 0.05}, DST_REST, 0.9)
    assert g.support == "R"
    assert g.root_dz == pytest.approx(0.02)
    assert g.foot("L") == pytest.approx(0.07 + 0.09 - 0.12 - 0.02)
    assert ankle_targets({"L": 0.18}, {"L": 0.08}, {"L": 0.07}, 0.9)["L"] == pytest.approx(0.16)


def test_jump_keeps_the_scaled_lift():
    g = plan({"L": 0.58, "R": 0.60}, SRC_REST, {"L": 0.50, "R": 0.52}, DST_REST, 0.9)
    assert g.support == "L"
    assert g.root_dz == pytest.approx(0.07 + 0.5 * 0.9 - 0.50)


def test_source_ground_error_in_contact_is_not_copied():
    """Decision 89 amendment 3: a source support foot floating 1.1 cm (or sinking 1 cm) is in contact; ours rests."""
    base = plan({"L": 0.08, "R": 0.08}, SRC_REST, {"L": 0.07, "R": 0.07}, DST_REST, 1.37)
    floats = plan({"L": 0.091, "R": 0.091}, SRC_REST, {"L": 0.07, "R": 0.07}, DST_REST, 1.37,
                  {"L": 0.011, "R": 0.011})
    assert floats.root_dz == pytest.approx(base.root_dz) and floats.foot("L") == pytest.approx(0.0)
    sinks = plan({"L": 0.07, "R": 0.07}, SRC_REST, {"L": 0.07, "R": 0.07}, DST_REST, 1.0, {"L": -0.01, "R": -0.01})
    assert sinks.root_dz == pytest.approx(0.0)


def test_landing_body_goes_low_enough_for_both_feet_in_contact():
    """Both source feet in contact: the body follows the foot that needs it lower; the other leg bends."""
    # source: both ankles at rest; ours: left ankle 3 cm higher than the right (left leg straight, cannot go down)
    g = plan({"L": 0.08, "R": 0.08}, SRC_REST, {"L": 0.10, "R": 0.07}, DST_REST, 1.0, {"L": 0.0, "R": 0.0})
    assert g.root_dz == pytest.approx(-0.03)                     # body down 3 cm: the left foot reaches
    assert g.foot("L") == pytest.approx(0.0) and g.foot("R") == pytest.approx(0.03)   # the right leg bends


def test_source_ground_error_beyond_the_band_is_a_lift():
    g = plan({"L": 0.58, "R": 0.60}, SRC_REST, {"L": 0.50, "R": 0.52}, DST_REST, 0.9, {"L": 0.45, "R": 0.47})
    assert g.root_dz == pytest.approx(0.07 + 0.5 * 0.9 - 0.50)     # a jump is unchanged


def test_knee_pole_copies_the_source_knee_direction():
    pole = knee_pole((0, 0, 1.0), (0.05, -0.1, 0.55), (0, 0, 0.1), (0.2, 0.0, 0.95))
    assert pole == pytest.approx((0.25, -0.1, 0.95 - 0.0))
