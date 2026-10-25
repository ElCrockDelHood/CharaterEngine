"""CE-GAME-v1 game skeleton (RIG-GAME-001 step 1): definition, canonical mapping, derivation, glTF export."""

from __future__ import annotations

import json
import math
import struct

import pytest

from character_engine.domain.anatomy.pose import apply_pose
from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.character import CharacterParameters, build_character_bones, load_canonical_bones
from character_engine.domain.rigging import (
    GAME_BONES,
    RIG_ID,
    canonical_to_game,
    game_bone_points,
    validate_game_rig,
)
from character_engine.domain.rigging.game_rig import CONTAINERS
from character_engine.export.gltf import gltf_to_canonical
from character_engine.export.gltf_game import build_game_document, export_game_skeleton, game_skeleton_points


@pytest.fixture(scope="module")
def anatomical():
    return load_canonical_bones()[0]


def _by(name):
    return next(g for g in GAME_BONES if g.name == name)


def test_rig_has_66_bones_with_ue5_mannequin_names():
    names = [g.name for g in GAME_BONES]
    assert RIG_ID == "CE-GAME-v1" and len(names) == 66 == len(set(names))
    for n in ("root", "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head", "jaw", "eye_l", "eye_r",
              "clavicle_l", "upperarm_r", "lowerarm_twist_01_l", "hand_r", "thumb_03_l", "pinky_metacarpal_r",
              "ring_01_l", "thigh_twist_01_r", "calf_l", "foot_r", "ball_l"):
        assert n in names
    groups = {}
    for g in GAME_BONES:
        groups[g.group] = groups.get(g.group, 0) + 1
    assert groups == {"core": 7, "face": 3, "arm": 12, "hand": 34, "leg": 10}   # RIG-GAME-001 §3


def test_rig_validates_and_covers_every_canonical_node_exactly_once(anatomical):
    names = [b["canonical_name"] for b in anatomical]
    assert validate_game_rig(names) == []
    mapping = canonical_to_game()
    assert set(mapping) == set(names) | set(CONTAINERS) and len(mapping) == 208


def test_hands_have_three_bones_per_finger_and_ring_pinky_metacarpals():
    for s in "lr":
        for finger in ("thumb", "index", "middle", "ring", "pinky"):
            assert [_by(f"{finger}_0{i}_{s}").name for i in (1, 2, 3)]
        assert _by(f"ring_01_{s}").parent == f"ring_metacarpal_{s}"
        assert _by(f"pinky_01_{s}").parent == f"pinky_metacarpal_{s}"
        assert _by(f"index_01_{s}").parent == _by(f"middle_01_{s}").parent == f"hand_{s}"
    assert canonical_to_game()["METACARPAL_3_R"] == "hand_r"          # weapon grip bone rides on hand_r


def test_mapping_keeps_anatomical_meaning_for_hitboxes_and_face():
    m = canonical_to_game()
    assert m["RIB_08_L"] == m["STERNUM"] == "spine_03"
    assert m["MANDIBLE"] == "jaw" and m["TEMPORAL_L"] == m["CRANIUM"] == "head"
    assert m["TIBIA_L"] == m["PATELLA_L"] == "calf_l" and m["LUMBAR_3"] == "spine_01"


def test_points_are_derived_from_canonical_joints(anatomical):
    by = {b["canonical_name"]: b for b in anatomical}
    pts = game_bone_points(anatomical)

    def h(n, end="head"):
        d = by[n][end]
        return (d["x"], d["y"], d["z"]) if isinstance(d, dict) else tuple(d)

    assert pts["upperarm_l"] == (h("HUMERUS_L"), h("HUMERUS_L", "tail"))
    assert pts["hand_r"][0] == h("CAPITATE_R") and pts["jaw"][0] == h("MANDIBLE")
    hip = pts["pelvis"][0]
    assert hip == pytest.approx(tuple((a + b) / 2 for a, b in zip(h("FEMUR_L"), h("FEMUR_R"))))
    for g in GAME_BONES:
        head, tail = pts[g.name]
        assert math.dist(head, tail) > 1e-4, g.name
        if g.parent:
            assert g.parent in pts


def test_provenance_is_derived_except_assumed_rig_placements():
    assumed = {g.name for g in GAME_BONES if g.provenance is ProvenanceState.ASSUMED}
    assert assumed == {"upperarm_twist_01_l", "upperarm_twist_01_r", "lowerarm_twist_01_l", "lowerarm_twist_01_r",
                       "thigh_twist_01_l", "thigh_twist_01_r", "eye_l", "eye_r"}
    assert all(g.provenance is ProvenanceState.DERIVED for g in GAME_BONES if g.name not in assumed)


def test_left_is_plus_x_and_eyes_look_forward(anatomical):
    pts = game_bone_points(anatomical)
    assert pts["hand_l"][0][0] > 0 > pts["hand_r"][0][0]
    for s in "lr":
        head, tail = pts[f"eye_{s}"]
        assert tail[1] < head[1]                                       # -Y forward


@pytest.mark.parametrize("pose", ["tpose", "apose"])
def test_game_bones_follow_pose(anatomical, pose):
    posed = apply_pose(anatomical, pose)
    rest, moved = game_bone_points(anatomical), game_bone_points(posed, anatomical)
    assert math.dist(rest["hand_l"][0], moved["hand_l"][0]) > 0.1
    for g in ("pelvis", "spine_02", "thigh_l"):
        assert moved[g][0] == pytest.approx(rest[g][0], abs=1e-6)
    for s in "lr":   # segments stay rigid: humerus length unchanged by the pose
        assert math.dist(*moved[f"upperarm_{s}"]) == pytest.approx(math.dist(*rest[f"upperarm_{s}"]), rel=1e-5)


def test_game_bones_follow_stature(anatomical):
    params = CharacterParameters(stature_m=1.65)
    small, _ = build_character_bones(params, canonical_bones=anatomical)
    big_head = game_bone_points(anatomical)["head"][1][2]
    small_head = game_bone_points(small, anatomical)["head"][1][2]
    assert small_head < big_head


def test_glb_export_round_trips_positions(tmp_path):
    path = export_game_skeleton(tmp_path / "game.glb")
    data = path.read_bytes()
    n = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(data[20:20 + n])
    assert doc["asset"]["extras"]["rig_id"] == RIG_ID and doc["asset"]["extras"]["bone_count"] == 66
    assert len(doc["skins"][0]["joints"]) == 66 and len(doc["asset"]["extras"]["canonical_to_game"]) == 208
    nodes = {nd["name"]: nd for nd in doc["nodes"]}
    pts = game_skeleton_points()
    world = {}
    for g in GAME_BONES:                                               # accumulate local translations
        t = gltf_to_canonical(tuple(nodes[g.name]["translation"]))
        base = world[g.parent] if g.parent else (0.0, 0.0, 0.0)
        world[g.name] = tuple(b + c for b, c in zip(base, t))
        assert world[g.name] == pytest.approx(pts[g.name][0], abs=1e-5), g.name
        assert nodes[g.name]["extras"]["covers"] == list(g.covers)


def test_document_without_display_mesh():
    from character_engine.export.gltf import GltfExportOptions

    doc = build_game_document(game_skeleton_points(), GltfExportOptions(include_bone_mesh=False))
    assert "meshes" not in doc.json and len(doc.json["nodes"]) == 67   # armature + 66 joints
