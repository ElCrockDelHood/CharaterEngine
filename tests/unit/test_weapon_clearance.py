import math

import pytest

from character_engine.domain.animation.weapon_clearance import (
    Capsule,
    Rules,
    box_weapon,
    candidate_axes,
    capsule_contact,
    clearing_angle,
    episodes,
    frame_contacts,
    plan_wrist_fix,
    ramp,
    rotate_about,
    rotate_capsule,
    rotate_parts,
    segment_closest,
    split_weapon,
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


# --------------------------------------------------------------------------- correction ----

def test_rotate_about_quarter_turn():
    assert rotate_about((1, 0, 0), (0, 0, 0), (0, 0, 1), math.pi / 2) == pytest.approx((0, 1, 0), abs=1e-12)
    assert rotate_about((2, 0, 5), (1, 0, 5), (0, 0, 1), math.pi) == pytest.approx((0, 0, 5), abs=1e-12)


def test_candidate_axes_are_perpendicular_units():
    w = Capsule("w", (0, 0, 0), (0.3, 0.8, 0.1), 0.02)
    for ax in candidate_axes([w]):
        assert sum(x * x for x in ax) == pytest.approx(1.0)
        assert sum(a * b for a, b in zip(ax, (0.3, 0.8, 0.1))) == pytest.approx(0.0, abs=1e-12)


def _blade_through_foot():
    pivot = (0.0, 0.0, 0.0)
    blade = [box_weapon("sabre", (0, 0.05, 0), (0, 0.95, 0), 0.035)]     # along +Y from the grip
    foot = Capsule("foot.L", (0.0, 0.5, -0.03), (0.0, 0.7, -0.03), 0.04)  # just under the blade's middle
    return pivot, blade, foot


def test_clearing_angle_is_minimal_and_clears():
    pivot, blade, foot = _blade_through_foot()
    up = (1.0, 0.0, 0.0)                                                  # +Y turned about +X goes up (+Z)
    a = clearing_angle(blade, pivot, up, [foot])
    assert a is not None and 0 < a < 15
    assert frame_contacts([rotate_capsule(blade[0], pivot, up, math.radians(a))], [foot])[0].gap_m >= 0
    assert frame_contacts([rotate_capsule(blade[0], pivot, up, math.radians(a - 1))], [foot])[0].gap_m < 0
    assert clearing_angle(blade, pivot, up, [foot], max_deg=1) is None


def test_episodes_and_ramp():
    assert episodes([3, 4, 5, 12, 14, 30]) == [[3, 4, 5], [12, 14], [30]]
    r = ramp({10: 8.0}, list(range(4, 17)), ramp_frames=4)
    assert r[10] == 8.0 and r[14] == pytest.approx(1.6) and r[15] == 0.0 and r[5] == 0.0
    assert [r[f] for f in range(6, 11)] == sorted(r[f] for f in range(6, 11))   # rises without a jump


def test_plan_wrist_fix_clears_with_one_axis_and_ramps():
    pivot, blade, foot = _blade_through_foot()
    frames = {f: (blade, pivot, [foot] if 10 <= f <= 12 else []) for f in range(0, 25)}
    by = {p.frame: p for p in plan_wrist_fix(frames)}
    assert set(by) == set(range(6, 17))                     # 3 bad frames + 4 frames of ramp on each side
    assert len({p.axis for p in by.values()}) == 1          # one axis for the whole episode
    assert all(p.cleared for p in by.values())
    for f in (10, 11, 12):
        moved = rotate_capsule(blade[0], pivot, by[f].axis, math.radians(by[f].angle_deg))
        assert frame_contacts([moved], [foot])[0].gap_m >= 0
    steps = [by[f].angle_deg for f in range(6, 17)]
    assert max(abs(b - a) for a, b in zip(steps, steps[1:])) <= max(steps) / 5 + 1e-9


def test_nearby_runs_share_one_turn_per_frame():
    pivot, blade, foot = _blade_through_foot()
    frames = {f: (blade, pivot, [foot] if f in (10, 17) else []) for f in range(0, 30)}
    plan = plan_wrist_fix(frames)
    assert len(plan) == len({p.frame for p in plan})


def test_ramp_never_pushes_a_clear_frame_into_the_body():
    """Regular_C, 2026-11-24: frame 28 was clear, the ramp-out turn about frame 27's axis put the blade in the foot."""
    pivot, blade, foot = _blade_through_foot()
    up = (1.0, 0.0, 0.0)
    a = clearing_angle(blade, pivot, up, [foot])
    above = Capsule("thigh.R", (0.0, 0.5, 0.075), (0.0, 0.7, 0.075), 0.04)   # clear now, hit by a turn upwards
    assert Rules().clear(blade, [above])
    assert not Rules().clear(rotate_parts(blade, pivot, up, math.radians(a * 0.8)), [above])
    frames = {f: (blade, pivot, [foot] if f == 10 else [above] if f == 11 else []) for f in range(0, 20)}
    for p in plan_wrist_fix(frames):
        w, piv, body = frames[p.frame]
        assert Rules().clear(rotate_parts(w, piv, p.axis, math.radians(p.angle_deg)), body), p


def test_plan_reports_what_cannot_be_cleared():
    pivot = (0.0, 0.0, 0.0)
    blade = [box_weapon("sabre", (0, 0.05, 0), (0, 0.95, 0), 0.035)]
    trunk = Capsule("thorax", (0, 0.5, -1), (0, 0.5, 1), 0.4)              # swallows the blade whichever way
    plan = plan_wrist_fix({1: (blade, pivot, [trunk])}, max_deg=10)
    assert [p.cleared for p in plan if p.frame == 1] == [False]
    assert plan_wrist_fix({1: (blade, pivot, [])}) == []


def test_split_weapon_and_grip_may_rest_on_the_forearm():
    sabre = box_weapon("sabre", (0, 0, 0), (0, 0.9, 0), 0.035)
    grip, blade = split_weapon(sabre, 0.1)
    assert grip.b == pytest.approx((0, 0.1, 0)) and blade.a == grip.b and blade.b == sabre.b
    assert [p.name for p in split_weapon(sabre, 1.0)] == ["grip"]
    forearm = Capsule("forearm.R", (0.03, -0.25, 0), (0.03, 0.02, 0), 0.04)   # its end cap overlaps the butt
    foot = Capsule("foot.L", (0.03, 0.5, 0), (0.03, 0.7, 0), 0.04)
    rules = Rules()
    assert rules.clear([grip, blade], [forearm])                               # the fist hides that contact
    assert not Rules(allowed={}).clear([grip, blade], [forearm])
    assert not rules.clear([grip, blade], [foot])                              # the blade still may not
    blade_into_forearm = Capsule("forearm.R", (0.03, 0.3, 0), (0.03, 0.5, 0), 0.04)
    assert not rules.clear([grip, blade], [blade_into_forearm])
