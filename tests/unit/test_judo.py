"""Judo throw model and key poses (domain/physics/judo.py, domain/animation/judo_clips.py, A36)."""

from __future__ import annotations

import json
import math

import pytest

from character_engine.domain.animation.judo_clips import (
    JUDO_CLIPS,
    STAND,
    Root,
    clip_reference,
    place,
    pose_rotations,
    solve_clip,
    v,
)
from character_engine.domain.physics.head_kinematics import P_STEP_N_S, concussion_probability
from character_engine.domain.physics.judo import (
    KUZUSHI_DIRECTIONS,
    SCHEMA,
    THROWS,
    centre_of_mass,
    kuzushi,
    resolve_throw,
    resolve_ukemi,
    support_points,
)
from character_engine.domain.rigging.hand_poses import apply_hand_pose
from character_engine.export.gltf_game import game_skeleton_points

PHASES = ("kumikata", "kuzushi", "tsukuri", "kake", "fall", "landing", "end")


@pytest.fixture(scope="module")
def points():
    return game_skeleton_points(pose="anatomical")


@pytest.fixture(scope="module")
def solved(points):
    return {tid: solve_clip(points, c) for tid, c in JUDO_CLIPS.items()}


def test_centre_of_mass_of_the_standing_body(points):
    com = centre_of_mass(points)
    assert abs(com[0]) < 1e-6
    assert 0.52 < com[2] / 1.80 < 0.60                 # the usual 0.55-0.57 of stature, not asserted tighter


def test_standing_body_is_balanced_in_all_eight_directions(points):
    assert len(support_points(points)) == 8
    for d in KUZUSHI_DIRECTIONS:
        k = kuzushi(points, d)
        assert k.margin_m > 0 and not k.broken, d
        assert kuzushi(points, d, k.impulse_to_break_n_s + 0.1).broken


def test_impulse_to_break_matches_the_inverted_pendulum_by_hand(points):
    k = kuzushi(points, "forward")
    com = centre_of_mass(points)
    toe = min(points["ball_l"][1][1], points["ball_r"][1][1])          # forward is -Y
    expected = (com[1] - toe) * math.sqrt(9.81 / com[2]) * 75.0
    assert k.impulse_to_break_n_s == pytest.approx(expected)
    assert 0.5 * P_STEP_N_S < k.impulse_to_break_n_s < 4.0 * P_STEP_N_S   # same order as the step threshold (A16)


def test_margin_falls_linearly_with_impulse(points):
    a, b, c = (kuzushi(points, "back", j).margin_m for j in (0.0, 10.0, 20.0))
    assert a - b == pytest.approx(b - c)
    assert a > b > c


def test_reaped_foot_makes_the_throw_cheaper(points):
    for tid in ("o_soto_gari", "o_uchi_gari", "de_ashi_barai"):
        t = THROWS[tid]
        both = kuzushi(points, t.kuzushi)
        one = kuzushi(points, t.kuzushi, removed=(t.removed_foot,))
        assert one.impulse_to_break_n_s < both.impulse_to_break_n_s, tid
    assert not kuzushi(points, "back", removed=("l", "r")).supported


def test_throw_fails_with_a_weak_pull_and_succeeds_with_a_strong_one(points):
    t = THROWS["seoi_nage"]
    need = kuzushi(points, t.kuzushi).impulse_to_break_n_s
    weak, strong = resolve_throw(t, points, need * 0.5), resolve_throw(t, points, need * 1.5)
    assert not weak.thrown and weak.to_dict()["fall"] is None and weak.to_dict()["ukemi"] is None
    assert strong.thrown and strong.impact_speed_m_s > 0
    assert strong.fall_energy_j == pytest.approx(75.0 * 9.81 * (strong.release_com_height_m - 0.12))


def test_ukemi_decides_the_head(points):
    t = THROWS["o_soto_gari"]
    good = resolve_throw(t, points, 200.0, ukemi_skill=1.0)
    bad = resolve_throw(t, points, 200.0, ukemi_skill=0.2)
    tired = resolve_throw(t, points, 200.0, ukemi_skill=0.8, fatigue=0.5)
    assert good.ukemi.correct and good.head_hits_ground is False
    assert not bad.ukemi.correct and bad.head_hits_ground is True
    assert not tired.ukemi.correct
    assert good.head.angular_rad_s2 < bad.head.angular_rad_s2
    assert concussion_probability(good.head.angular_rad_s2) < concussion_probability(bad.head.angular_rad_s2)
    assert resolve_ukemi(t, 1.0, attempted=False).correct is False


def test_unread_data_stays_unknown(points):
    ev = resolve_throw(THROWS["o_goshi"], points, 200.0, ukemi_skill=0.0)
    assert ev.head is None and ev.head_hits_ground is None
    assert ev.to_dict()["provenance"]["head"] == "UNKNOWN"


def test_event_is_json_and_deterministic(points):
    for t in THROWS.values():
        a = json.dumps(resolve_throw(t, points, 150.0).to_dict(), sort_keys=True)
        assert a == json.dumps(resolve_throw(t, points, 150.0).to_dict(), sort_keys=True)
        d = json.loads(a)
        assert d["schema"] == SCHEMA and d["throw"] == t.throw_id
        assert {g["bone"] for g in d["grips"]} <= set(points)


def test_every_throw_has_a_clip_with_the_seven_phases():
    assert set(JUDO_CLIPS) == set(THROWS)
    for c in JUDO_CLIPS.values():
        assert tuple(k.phase for k in c.keys) == PHASES
        frames = [k.frame for k in c.keys]
        assert frames == sorted(set(frames)) and frames[0] == 0


def test_pose_rotations_point_the_bones_where_asked(points):
    rot = pose_rotations(points, STAND)
    body = apply_hand_pose(points, rot)
    for bone, want in (("thigh_l", v(0.12, 0.14, -1)), ("lowerarm_r", v(1, 0.1, 0.2)), ("calf_l", v(-0.12, 0, -1))):
        h, t = body[bone]
        n = math.dist(h, t)
        got = tuple((t[i] - h[i]) / n for i in range(3))
        assert got == pytest.approx(want, abs=1e-6), bone
    for bone, (h, t) in body.items():                                    # bone lengths are kept
        assert math.dist(h, t) == pytest.approx(math.dist(*points[bone]), abs=1e-9), bone


def test_root_puts_the_body_on_the_ground_or_at_a_height(points):
    lying = place(points, points, Root(0.3, -1.0, (("x", 90.0),), clearance=0.11))
    assert min(min(h[2], t[2]) for h, t in lying.values()) == pytest.approx(0.11)
    assert lying["pelvis"][0][:2] == pytest.approx((0.3, -1.0))
    assert lying["head"][1][1] < lying["pelvis"][0][1]                   # a turn of +90 about X lays the head towards -Y
    assert place(points, points, Root(z=0.5))["pelvis"][0][2] == pytest.approx(0.5)


def test_nobody_goes_through_the_floor(solved):
    for tid, keys in solved.items():
        for s in keys:
            low = min(min(h[2], t[2]) for pts in (s.tori, s.uke) for h, t in pts.values())
            assert low > -0.08, (tid, s.phase, low)


def test_grips_touch_until_the_throw(solved):
    for tid, keys in solved.items():
        for s in keys:
            if s.phase in ("kumikata", "kuzushi", "tsukuri", "kake"):
                for limb, miss in s.miss_m.items():
                    assert miss < 0.15, (tid, s.phase, limb, miss)


def test_uke_starts_balanced_is_broken_at_kake_and_ends_on_the_mat(solved):
    for tid, keys in solved.items():
        t = THROWS[tid]
        by = {s.phase: s for s in keys}
        assert kuzushi(by["kumikata"].uke, t.kuzushi).margin_m > 0, tid
        assert kuzushi(by["kake"].uke, t.kuzushi, removed=(t.removed_foot,) if t.removed_foot else ()).broken, tid
        end = by["end"].uke
        assert end["pelvis"][0][2] < 0.40, tid
        assert abs(end["head"][0][2] - end["pelvis"][0][2]) < 0.40, tid      # lying, not sitting
        assert by["end"].tori["head"][1][2] > 1.5, tid                       # tori ends standing


def test_clip_reference_is_stable_json(points):
    a = json.dumps(clip_reference(points), sort_keys=True)
    assert a == json.dumps(clip_reference(points), sort_keys=True)
    d = json.loads(a)
    assert d["schema"] == "ce-judo-clips/1" and d["provenance"] == "placeholder"
    q = d["clips"]["seoi_nage"]["keys"][3]["uke"]["root"]["rotation_wxyz"]
    assert sum(c * c for c in q) == pytest.approx(1.0, abs=1e-5)


@pytest.fixture(scope="module")
def seoi_frames(points):
    from character_engine.domain.animation.judo_clips import frame_table, solve_frames

    clip = JUDO_CLIPS["seoi_nage"]
    return clip, solve_frames(points, clip), frame_table(points, clip)


def test_every_frame_is_solved_and_keys_are_kept(points, seoi_frames):
    clip, frames, _ = seoi_frames
    assert [s.frame for s in frames] == list(range(clip.frames + 1))
    keyed = {s.frame: s for s in solve_clip(points, clip)}
    for s in frames:
        if s.frame in keyed:
            assert s.tori["head"] == keyed[s.frame].tori["head"] and s.uke["pelvis"] == keyed[s.frame].uke["pelvis"]


def test_in_betweens_stay_above_the_mat_and_keep_the_grips(seoi_frames):
    _, frames, _ = seoi_frames
    for s in frames:
        low = min(min(h[2], t[2]) for pts in (s.tori, s.uke) for h, t in pts.values())
        assert low > -1e-6, (s.frame, low)
        if s.phase in ("kumikata", "kuzushi"):
            assert max(s.miss_m.values()) < 0.10, (s.frame, s.miss_m)


def test_motion_is_continuous(seoi_frames):
    _, frames, _ = seoi_frames
    for a, b in zip(frames, frames[1:]):
        for who in ("tori", "uke"):
            for bone in ("head", "hand_l", "hand_r", "foot_l", "foot_r"):
                step = math.dist(getattr(a, who)[bone][1], getattr(b, who)[bone][1])
                # 0.30 m per frame = 18 m/s. The fastest points are the thrown body's feet as it turns over tori (about
                # 17.5 m/s) and tori's reaping foot (about 17 m/s): above the fastest kick measured, 14.3 m/s (Vagner
                # 2023, A17). A jump in the in-betweens (a grip switching target) gave 22-28 m/s and fails here.
                assert step < 0.30, (who, bone, a.frame, step)


def test_frame_table_rebuilds_the_solved_world(points, seoi_frames):
    from character_engine.domain.rigging.hand_poses import quat_rotate

    _, frames, table = seoi_frames
    for s, row in zip(frames[::7], table[::7]):
        for who in ("tori", "uke"):
            d = row[who]
            body = apply_hand_pose(points, d["bones_wxyz"])
            for b in ("head", "hand_l", "foot_r"):
                got = tuple(quat_rotate(d["rotation_wxyz"], body[b][1])[i] + d["location"][i] for i in range(3))
                assert got == pytest.approx(getattr(s, who)[b][1], abs=1e-6), (who, b, s.frame)


def test_slerp_takes_the_short_arc():
    from character_engine.domain.animation.judo_clips import ease, slerp
    from character_engine.domain.rigging.hand_poses import quat_axis_angle

    a, b = quat_axis_angle((1, 0, 0), math.radians(-170)), quat_axis_angle((1, 0, 0), math.radians(90))
    mid = slerp(a, b, 0.5)
    assert abs(mid[0]) == pytest.approx(abs(math.cos(math.radians(-220) / 2)), abs=1e-9)   # through -220, not through -40
    assert ease(0.0) == 0.0 and ease(1.0) == 1.0 and ease(0.5) == 0.5
