"""Foot locking (domain/animation/foot_lock.py): contact plan with heel/ball pivots and two-bone IK."""

import math

import pytest

from character_engine.domain.animation import foot_lock as fl

REST = {"heel": 0.0, "ball": 0.0}


def sliding_foot(n: int, slide: float, lift_after: int):
    """Foot on the ground sliding forward ``slide`` m per frame, lifted 10 cm from frame ``lift_after``."""
    heel, ball = [], []
    for i in range(n):
        z = 0.0 if i < lift_after else 0.1
        heel.append((0.1, 0.03 + slide * i, z))
        ball.append((0.1, -0.15 + slide * i, z))
    return {"heel": heel, "ball": ball}


def test_correction_holds_the_pivot_on_its_mean_anchor():
    pts = sliding_foot(12, 0.01, lift_after=6)
    plan = fl.plan_locks(pts, REST, 0.0, 12)
    assert all(p is not None and p.weight == 1.0 for p in plan[:6])
    # corrected pivot positions all equal the anchor (no residual slide)
    pivot = min(("heel", "ball"), key=lambda n: pts[n][0][2])
    corrected = [pts[pivot][i][1] + plan[i].dy for i in range(6)]
    assert max(corrected) - min(corrected) == pytest.approx(0.0, abs=1e-12)
    assert corrected[0] == pytest.approx(sum(pts[pivot][i][1] for i in range(6)) / 6)


def test_blend_ramps_after_the_phase_and_frees_the_swing():
    plan = fl.plan_locks(sliding_foot(12, 0.01, lift_after=6), REST, 0.0, 12)
    assert plan[6].weight == pytest.approx(2 / 3)
    assert plan[7].weight == pytest.approx(1 / 3)
    assert all(p is None for p in plan[8:])


def test_a_phase_needing_a_large_correction_is_left_alone():
    # ground slide of 5 cm per frame over 12 frames: corrections up to ~0.28 m > max_correction_m
    plan = fl.plan_locks(sliding_foot(14, 0.05, lift_after=12), REST, 0.0, 14)
    assert all(p is None for p in plan)
    loose = fl.plan_locks(sliding_foot(14, 0.05, lift_after=12), REST, 0.0, 14, fl.LockSettings(max_correction_m=1.0))
    assert loose[0] is not None


def test_short_contacts_are_not_locked():
    plan = fl.plan_locks(sliding_foot(6, 0.01, lift_after=1), REST, 0.0, 6)
    assert plan[0] is None


def test_heel_to_ball_roll_uses_the_pivots_on_the_ground():
    heel = [(0, 0.0, 0.0), (0, 0.0, 0.0), (0, 0.0, 0.05), (0, 0.0, 0.08)]
    ball = [(0, -0.2, 0.06), (0, -0.2, 0.04), (0, -0.21, 0.0), (0, -0.22, 0.0)]
    plan = fl.plan_locks({"heel": heel, "ball": ball}, REST, 0.0, 4)
    assert plan[0].dy == pytest.approx(0.0) and plan[1].dy == pytest.approx(0.0)    # heel carries
    assert plan[2].dy == pytest.approx(-0.215 + 0.21) and plan[3].dy == pytest.approx(-0.215 + 0.22)  # ball


def test_both_pivots_on_the_ground_average_their_corrections():
    heel = [(0, 0.00, 0.0), (0, 0.02, 0.0), (0, 0.04, 0.0)]
    ball = [(0, -0.20, 0.0), (0, -0.20, 0.0), (0, -0.20, 0.0)]     # ball planted, heel sliding
    plan = fl.plan_locks({"heel": heel, "ball": ball}, REST, 0.0, 3)
    # heel anchor 0.02, ball anchor -0.20: frame 0 correction = mean(+0.02, 0.0)
    assert plan[0].dy == pytest.approx(0.01)
    assert plan[2].dy == pytest.approx(-0.01)


def test_loop_wrap_merges_the_cut_phase_into_one_anchor():
    # 12-frame loop, root advances 1 m along -Y per cycle; one contact runs over the wrap (frames 9-11, 0-2)
    # while the ball slides 1 cm per frame. Frame 12 would be frame 0 shifted by the cycle.
    n, shift = 12, (0.0, -1.0)
    ys = {i: -0.01 * i for i in (0, 1, 2)} | {i: -1.0 - 0.01 * (i - 12) for i in (9, 10, 11)}
    ball = [(0.0, ys.get(i, -0.5), 0.0 if i in ys else 0.1) for i in range(n)]
    looped = fl.plan_locks({"ball": ball}, {"ball": 0.0}, 0.0, n, loop_shift=shift)
    # in one cycle's coordinates (tail shifted back by +1 m) every contact frame lands on the same anchor
    pinned = {round(ball[i][1] + looped[i].dy + (1.0 if i >= 9 else 0.0), 9) for i in ys}
    assert len(pinned) == 1
    # without the loop shift the two halves get two different anchors
    plain = fl.plan_locks({"ball": ball}, {"ball": 0.0}, 0.0, n)
    assert len({round(ball[i][1] + plain[i].dy + (1.0 if i >= 9 else 0.0), 9) for i in ys}) == 2


def test_locked_target_moves_xy_only_by_weight():
    assert fl.locked_target((1.0, 2.0, 0.3), fl.Lock(0.2, -0.4, 0.5)) == pytest.approx((1.1, 1.8, 0.3))


def test_two_bone_ik_reaches_and_keeps_lengths_and_bend_side():
    hip, knee, ankle = (0, 0, 1.0), (0, -0.1, 0.5), (0, 0, 0.0)
    r = fl.two_bone_ik(hip, knee, ankle, (0, 0.2, 0.1))
    assert r.reached
    assert r.ankle == pytest.approx((0, 0.2, 0.1))
    assert math.dist(hip, r.knee) == pytest.approx(math.dist(hip, knee))
    assert math.dist(r.knee, r.ankle) == pytest.approx(math.dist(knee, ankle))
    assert r.knee[1] < 0.2 * (1.0 - r.knee[2]) / 0.9 + 1e-9    # knee stays on the forward (−Y) side


def test_two_bone_ik_clamps_an_unreachable_target():
    r = fl.two_bone_ik((0, 0, 1.0), (0, -0.05, 0.5), (0, 0, 0.0), (0, 0, -1.0))
    assert not r.reached
    assert math.dist((0, 0, 1.0), r.ankle) < math.dist((0, 0, 1.0), (0, -0.05, 0.5)) * 2 + 1e-3
