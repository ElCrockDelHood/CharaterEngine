import math

import pytest

from character_engine.domain.animation.weapon_clearance import (
    Capsule,
    box_weapon,
    capsule_contact,
    frame_contacts,
    segment_closest,
    summary,
    violations,
)


def test_parallel_segments_distance():
    d, s, t = segment_closest((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0))
    assert d == pytest.approx(1.0)
    assert 0.0 <= s <= 1.0 and 0.0 <= t <= 1.0


def test_crossing_segments_touch():
    d, s, t = segment_closest((-1, 0, 0), (1, 0, 0), (0, -1, 0.2), (0, 1, 0.2))
    assert d == pytest.approx(0.2)
    assert s == pytest.approx(0.5) and t == pytest.approx(0.5)


def test_endpoint_clamping():
    d, s, t = segment_closest((0, 0, 0), (1, 0, 0), (3, 0, 0), (4, 0, 0))
    assert d == pytest.approx(2.0)
    assert (s, t) == (1.0, 0.0)


def test_degenerate_point_segments():
    assert segment_closest((0, 0, 0), (0, 0, 0), (0, 3, 4), (0, 3, 4))[0] == pytest.approx(5.0)
    assert segment_closest((0, 0, 0), (0, 0, 0), (-1, 1, 0), (1, 1, 0))[0] == pytest.approx(1.0)


def test_symmetric():
    p = ((0.1, 0.2, 0.3), (1.0, -0.4, 0.2), (0.5, 0.5, -0.5), (-0.3, 0.9, 0.4))
    assert segment_closest(*p)[0] == pytest.approx(segment_closest(p[2], p[3], p[0], p[1])[0])


def test_capsule_gap_sign():
    body = Capsule("forearm.R", (0, 0, 0), (0, 0, 0.25), 0.04)
    near = Capsule("blade", (0.05, 0, 0.1), (0.05, 0.9, 0.1), 0.0124)
    far = Capsule("blade", (0.2, 0, 0.1), (0.2, 0.9, 0.1), 0.0124)
    assert capsule_contact(near, body).gap_m == pytest.approx(0.05 - 0.04 - 0.0124)   # -2.4 mm: inside
    assert capsule_contact(far, body).gap_m > 0


def test_thickness_catches_what_the_centre_line_misses():
    """The 2026-11-15 finding: centre line 2 cm clear of the capsule, real blade still inside."""
    body = Capsule("forearm.R", (0, 0, 0), (0, 0, 0.25), 0.04)
    blade = box_weapon("blade", (0.055, -0.1, 0.1), (0.055, 0.8, 0.1), width_m=0.035)
    centre_line_gap = capsule_contact(Capsule("line", blade.a, blade.b, 0.0), body).gap_m
    assert centre_line_gap == pytest.approx(0.015)
    assert capsule_contact(blade, body).gap_m < 0


def test_box_weapon_radius_is_half_diagonal():
    assert box_weapon("b", (0, 0, 0), (1, 0, 0), 0.035).radius_m == pytest.approx(0.035 * math.sqrt(2) / 2)
    assert box_weapon("b", (0, 0, 0), (1, 0, 0), 0.03, 0.04).radius_m == pytest.approx(0.025)


def test_grip_hand_excluded_and_order():
    blade = box_weapon("blade", (0, 0, 0), (0, 0.9, 0), 0.035)
    body = [Capsule("hand.R", (0, 0, 0), (0, 0.08, 0), 0.04), Capsule("foot.L", (0.03, 0.5, 0), (0.03, 0.7, 0), 0.04),
            Capsule("head", (1, 1, 1), (1, 1, 1.2), 0.1)]
    contacts = frame_contacts([blade], body)
    assert [c.body for c in contacts] == ["foot.L", "head"]
    assert contacts[0].gap_m < 0 and 0.5 < contacts[0].t_weapon < 0.8
    assert "hand.R" in [c.body for c in frame_contacts([blade], body, grip_segments=())]


def test_summary_and_margin():
    blade = box_weapon("blade", (0, 0, 0), (0, 0.9, 0), 0.035)
    clear = Capsule("thigh.L", (0.2, 0.4, 0), (0.2, 0.6, 0), 0.06)
    inside = Capsule("thigh.L", (0.05, 0.4, 0), (0.05, 0.6, 0), 0.06)
    frames = {1: frame_contacts([blade], [clear]), 2: frame_contacts([blade], [inside]),
              3: frame_contacts([blade], [clear])}
    s = summary(frames)
    assert s["frames"] == 3 and s["frames_in_violation"] == 1 and not s["passed"]
    assert s["worst"]["frame"] == 2 and s["segments"]["thigh.L"]["frames"] == [2]
    assert [v.frame for v in violations(frames)] == [2]
    assert summary({1: frames[1]})["passed"]
    gap = frames[1][0].gap_m                      # 0.2 - 0.06 - 0.0247 ~ 0.115 m
    assert not summary({1: frames[1]}, margin_m=gap + 0.001)["passed"]


def test_deterministic():
    blade = box_weapon("blade", (0.01, 0.02, 0.03), (0.4, 0.8, 0.1), 0.035)
    body = [Capsule("leg.L", (0.1, 0.3, 0), (0.1, 0.3, 0.4), 0.05)]
    assert frame_contacts([blade], body) == frame_contacts([blade], body)
