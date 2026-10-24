"""Decision 17 (closed by D-13): left is +X when facing −Y with Z up.

forward × up = (0,−1,0) × (0,0,1) = (−1,0,0) is the anatomical RIGHT, so every ``*_L`` bone
must have x > 0 and every ``*_R`` bone x < 0 — the Blender / glTF / Mixamo convention.
"""

import json

import pytest

from character_engine.domain.anatomy.coordinate_system import CANONICAL_COORDINATE_SYSTEM, LateralSide
from character_engine.domain.anatomy.pose import apply_pose
from character_engine.domain.character.templates import default_canonical_json


@pytest.fixture(scope="module")
def bones():
    return json.loads(default_canonical_json().read_text(encoding="utf-8"))["bones"]


def test_left_bones_are_on_positive_x(bones):
    for b in bones:
        name = b["canonical_name"]
        for end in ("head", "tail"):
            x = b[end]["x"]
            if name.endswith("_L"):
                assert x > 0, f"{name}.{end}.x = {x} (left must be +X)"
            elif name.endswith("_R"):
                assert x < 0, f"{name}.{end}.x = {x} (right must be −X)"


def test_face_is_in_front(bones):
    by = {b["canonical_name"]: b for b in bones}
    for n in ("NASAL_L", "STERNUM", "PATELLA_L"):
        assert by[n]["head"]["y"] < 0, n          # anterior = −Y


def test_right_is_forward_cross_up():
    cs = CANONICAL_COORDINATE_SYSTEM
    f, u, r = cs.get_forward_direction(), cs.get_up_direction(), cs.get_right_direction()
    cross = (f[1] * u[2] - f[2] * u[1], f[2] * u[0] - f[0] * u[2], f[0] * u[1] - f[1] * u[0])
    assert r == cross == (-1.0, 0.0, 0.0)
    assert cs.get_side_from_x(0.2) == LateralSide.LEFT
    assert cs.get_side_from_x(-0.2) == LateralSide.RIGHT
    assert cs.get_side_from_x(0.0) == LateralSide.MIDLINE


def test_tpose_spreads_left_arm_to_positive_x(bones):
    posed = {b["canonical_name"]: b for b in apply_pose(bones, "tpose")}
    for side, sign in (("L", 1), ("R", -1)):
        hum = posed[f"HUMERUS_{side}"]
        assert sign * (hum["tail"]["x"] - hum["head"]["x"]) > 0.25
        assert abs(hum["tail"]["z"] - hum["head"]["z"]) < 0.01
