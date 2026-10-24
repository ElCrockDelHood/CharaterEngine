"""Equipment sockets (CINE-GR-001 step 1): pure data, follow their parent bone in any pose."""

import math

import pytest

from character_engine.domain.anatomy.pose import apply_pose
from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.character import CharacterParameters, build_character_bones, load_canonical_bones
from character_engine.domain.rigging import EQUIPMENT_SOCKETS, socket_points, validate_sockets


@pytest.fixture(scope="module")
def anatomical():
    return load_canonical_bones()[0]


def _by(s):
    return {x.name: x for x in EQUIPMENT_SOCKETS}[s]


def test_sockets_are_valid_assumed_data(anatomical):
    assert validate_sockets(EQUIPMENT_SOCKETS, [b["canonical_name"] for b in anatomical]) == []
    assert {s.name for s in EQUIPMENT_SOCKETS} == {"SOCKET-sabre_hip.L", "SOCKET-hand_grip.R"}
    for s in EQUIPMENT_SOCKETS:
        assert s.provenance == ProvenanceState.ASSUMED and s.notes


def test_sabre_socket_is_on_the_left_hip_behind_the_arm(anatomical):
    head, tail = socket_points(_by("SOCKET-sabre_hip.L"), anatomical, anatomical)
    coxal = {b["canonical_name"]: b for b in anatomical}["COXAL_L"]
    assert head[0] > coxal["tail"]["x"] > 0                 # left = +X (Decision 17), lateral to the hip
    assert head[1] > 0                                       # behind the coronal plane of the arms
    assert head[2] == pytest.approx(coxal["tail"]["z"])
    assert tail[2] < head[2]                                 # hangs down


def test_hand_grip_is_palmar_on_the_right_hand(anatomical):
    head, _ = socket_points(_by("SOCKET-hand_grip.R"), anatomical, anatomical)
    mc = {b["canonical_name"]: b for b in anatomical}["METACARPAL_3_R"]
    assert head[0] == pytest.approx(mc["head"]["x"]) and head[0] < 0      # right = −X
    assert head[1] < mc["head"]["y"]                                       # palm faces −Y
    assert mc["tail"]["z"] < head[2] < mc["head"]["z"]


@pytest.mark.parametrize("name", ["SOCKET-sabre_hip.L", "SOCKET-hand_grip.R"])
def test_socket_keeps_its_offset_relative_to_the_parent_in_tpose(anatomical, name):
    s = _by(name)
    posed = apply_pose(anatomical, "tpose")
    ref_head, _ = socket_points(s, anatomical, anatomical)
    head, tail = socket_points(s, posed, anatomical)
    A = {b["canonical_name"]: b for b in anatomical}[s.parent_bone]
    P = {b["canonical_name"]: b for b in posed}[s.parent_bone]

    def dist(p, b):
        return [math.dist(p, (b[e]["x"], b[e]["y"], b[e]["z"])) for e in ("head", "tail")]
    assert dist(head, P) == pytest.approx(dist(ref_head, A), abs=1e-9)    # rigidly attached
    assert math.dist(head, tail) == pytest.approx(s.length_m, abs=1e-9)


def test_offsets_scale_with_stature(anatomical):
    s = _by("SOCKET-sabre_hip.L")
    small, _ = build_character_bones(CharacterParameters(stature_m=1.65, pose="anatomical"), anatomical)
    h180, t180 = socket_points(s, anatomical, anatomical)
    h165, t165 = socket_points(s, small, anatomical)
    assert math.dist(h165, t165) < math.dist(h180, t180)
