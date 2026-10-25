"""Hand controls and pose library for the CE-GAME-v1 hands (RIG-GAME-001 step 3)."""

from __future__ import annotations

import math

import pytest

from character_engine.domain.anatomy.pose import apply_pose
from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.character import load_canonical_bones
from character_engine.domain.gameplay import WEAPONS
from character_engine.domain.rigging import (
    GAME_BONES,
    GAME_CONTROL_RIG,
    HAND_POSES,
    WEAPON_GRIP_POSE,
    HandPose,
    apply_hand_pose,
    game_bone_points,
    grip_pose_for_weapon,
    hand_pose_rotations,
)
from character_engine.domain.rigging.hand_poses import FINGERS, hand_frame
from character_engine.domain.rigging.rig_definition import validate_rig_against_bones


@pytest.fixture(scope="module", params=["anatomical", "tpose"])
def points(request):
    anat = load_canonical_bones()[0]
    bones = anat if request.param == "anatomical" else apply_pose(anat, "tpose")
    return game_bone_points(bones, anat)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def test_library_and_weapon_grips():
    assert {"rest", "relaxed", "open", "fist", "point", "grip_staff", "grip_blade"} <= set(HAND_POSES)
    assert set(WEAPON_GRIP_POSE) == set(WEAPONS)
    assert grip_pose_for_weapon("short_blade").name == "grip_blade"
    assert grip_pose_for_weapon("staff").name == "grip_staff"
    assert all(p.provenance is ProvenanceState.ASSUMED for p in HAND_POSES.values())


def test_control_rig_targets_game_bones():
    names = [g.name for g in GAME_BONES]
    assert validate_rig_against_bones(GAME_CONTROL_RIG, names) == []
    assert {c.target_bone for c in GAME_CONTROL_RIG.ik_chains} == {"hand_l", "hand_r", "foot_l", "foot_r"}


@pytest.mark.parametrize("side", ["L", "R"])
def test_palm_faces_forward_in_anatomical_and_down_in_tpose(points, side):
    _, _, palm = hand_frame(points, side.lower())
    assert palm == pytest.approx((0.0, -1.0, 0.0), abs=1e-6) or palm == pytest.approx((0.0, 0.0, -1.0), abs=1e-6)


@pytest.mark.parametrize("side", ["L", "R"])
def test_rest_pose_is_identity(points, side):
    out = apply_hand_pose(points, hand_pose_rotations(HAND_POSES["rest"], points, side))
    for bone, (h, t) in points.items():
        assert out[bone][0] == pytest.approx(h, abs=1e-12) and out[bone][1] == pytest.approx(t, abs=1e-12)


@pytest.mark.parametrize("side", ["L", "R"])
def test_curl_moves_fingers_towards_the_palm_and_thumb_across(points, side):
    s = side.lower()
    _, across, palm = hand_frame(points, s)
    out = apply_hand_pose(points, hand_pose_rotations(HandPose("t", {f: 0.3 for f in FINGERS}), points, side))
    for finger in ("index", "middle", "ring", "pinky"):
        tip = f"{finger}_03_{s}"
        move = tuple(a - b for a, b in zip(out[tip][1], points[tip][1]))
        assert _dot(move, palm) > 0.01, finger
    thumb = tuple(a - b for a, b in zip(out[f"thumb_03_{s}"][1], points[f"thumb_03_{s}"][1]))
    assert _dot(thumb, tuple(-c for c in across)) > 0.01


@pytest.mark.parametrize("side", ["L", "R"])
def test_fist_closes_and_keeps_segment_lengths(points, side):
    s = side.lower()
    out = apply_hand_pose(points, hand_pose_rotations(HAND_POSES["fist"], points, side))
    knuckle = points[f"hand_{s}"][1]
    for finger in ("index", "middle", "ring", "pinky"):
        tip = f"{finger}_03_{s}"
        assert math.dist(out[tip][1], knuckle) < 0.5 * math.dist(points[tip][1], knuckle)
    for bone, (h, t) in points.items():          # rigid bones
        assert math.dist(*out[bone]) == pytest.approx(math.dist(h, t), rel=1e-9)
    other = "r" if s == "l" else "l"
    assert out[f"index_03_{other}"] == points[f"index_03_{other}"]   # the other hand does not move


def test_left_and_right_fists_mirror(points):
    left = apply_hand_pose(points, hand_pose_rotations(HAND_POSES["fist"], points, "L"))
    right = apply_hand_pose(points, hand_pose_rotations(HAND_POSES["fist"], points, "R"))
    for finger in FINGERS:
        lt, rt = left[f"{finger}_03_l"][1], right[f"{finger}_03_r"][1]
        assert lt == pytest.approx((-rt[0], rt[1], rt[2]), abs=1e-6)          # left = +X mirror


def test_point_keeps_the_index_straight(points):
    out = apply_hand_pose(points, hand_pose_rotations(HAND_POSES["point"], points, "R"))
    assert out["index_03_r"] == points["index_03_r"]
    assert out["middle_03_r"] != points["middle_03_r"]
