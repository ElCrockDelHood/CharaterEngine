"""Face contract for CE-GAME-v1 (RIG-GAME-001 step 5): ARKit names, game subset, jaw and eye look-at."""

from __future__ import annotations

import math

import pytest

from character_engine.domain.rigging.face import (
    ARKIT_52,
    EYE_PITCH_MAX_DEG,
    EYE_YAW_MAX_DEG,
    GAME_FACE_SHAPES,
    JAW_OPEN_MAX_DEG,
    eye_look_angles,
    eye_look_rotation,
    face_contract,
    head_axes,
    jaw_rotation,
)
from character_engine.domain.rigging.hand_poses import quat_rotate
from character_engine.export.gltf_game import game_skeleton_points


@pytest.fixture(scope="module", params=["anatomical", "tpose"])
def points(request):
    return game_skeleton_points(pose=request.param)


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def test_arkit_names_and_approved_game_subset():
    assert len(ARKIT_52) == 52 == len(set(ARKIT_52))
    assert len(GAME_FACE_SHAPES) == 20 == len(set(GAME_FACE_SHAPES)) and set(GAME_FACE_SHAPES) < set(ARKIT_52)
    assert {"jawOpen", "eyeBlinkLeft", "eyeBlinkRight", "mouthSmileLeft"} <= set(GAME_FACE_SHAPES)


def test_runtime_contract_carries_only_game_data(points):
    fc = face_contract(points)
    assert fc["game_shapes"] == list(GAME_FACE_SHAPES)
    assert "arkit_52" not in fc                       # cinematic set stays in Blender (owner rule)
    assert fc["jaw_bone"] == "jaw" and fc["eye_bones"] == ["eye_l", "eye_r"]
    assert len(fc["reference"]["jaw"]) == 2 and len(fc["reference"]["eyes"]) == 3


def test_head_axes_are_orthonormal_and_anatomical(points):
    lateral, forward, up = head_axes(points)
    for a in (lateral, forward, up):
        assert math.hypot(*a) == pytest.approx(1.0)
    assert lateral[0] > 0.99 and forward[1] < -0.99 and up[2] > 0.99      # left +X, -Y forward, Z up


def test_jaw_opens_downwards_up_to_the_limit(points):
    h = points["jaw"][0]
    chin = _sub((h[0], h[1] - 0.08, h[2] - 0.05), h)
    moved = quat_rotate(jaw_rotation(points, 1.0), chin)
    assert moved[2] < chin[2]
    assert math.degrees(math.acos(max(-1.0, min(1.0, jaw_rotation(points, 1.0)[0]))) * 2) == pytest.approx(JAW_OPEN_MAX_DEG)
    assert jaw_rotation(points, 2.0) == jaw_rotation(points, 1.0) and jaw_rotation(points, 0.0) == (1.0, 0.0, 0.0, 0.0)


@pytest.mark.parametrize("eye", ["eye_l", "eye_r"])
def test_eye_aims_at_reachable_target(points, eye):
    lateral, forward, up = head_axes(points)
    head = points[eye][0]
    target = tuple(head[i] + 1.0 * forward[i] + 0.3 * lateral[i] + 0.2 * up[i] for i in range(3))
    aim = quat_rotate(eye_look_rotation(points, eye, target), forward)
    want = _sub(target, head)
    n = math.hypot(*want)
    cos = sum(a * b / n for a, b in zip(aim, want))
    assert math.degrees(math.acos(min(1.0, cos))) < 1e-6


def test_eye_angles_are_clamped(points):
    lateral, forward, up = head_axes(points)
    head = points["eye_l"][0]
    far = tuple(head[i] + 0.1 * forward[i] + 2.0 * lateral[i] + 2.0 * up[i] for i in range(3))
    yaw, pitch = eye_look_angles(points, "eye_l", far)
    assert yaw == EYE_YAW_MAX_DEG and pitch == EYE_PITCH_MAX_DEG
