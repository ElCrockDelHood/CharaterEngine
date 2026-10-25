"""Bone maps onto the CE-GAME-v1 game rig (RIG-GAME-001 step 6)."""

from __future__ import annotations

import pytest

from character_engine.domain.animation import (
    BONE_MAPS,
    GAME_BONE_MAPS,
    differences_from_canonical,
    get_game_bone_map,
)
from character_engine.domain.rigging import GAME_BONES, RIG_ID

GAME_NAMES = {g.name for g in GAME_BONES}


@pytest.mark.parametrize("map_id", sorted(GAME_BONE_MAPS))
def test_targets_are_unique_game_bones_and_metadata_is_kept(map_id):
    m = get_game_bone_map(map_id)
    targets = list(m.source_to_canonical.values())
    assert m.target_rig == RIG_ID and BONE_MAPS[map_id].target_rig == "canonical"
    assert set(targets) <= GAME_NAMES and len(targets) == len(set(targets))
    src = BONE_MAPS[map_id]
    assert (m.prefix, m.forward_axis, m.up_axis, m.scale_to_m, m.root_joint) == \
        (src.prefix, src.forward_axis, src.up_axis, src.scale_to_m, src.root_joint)


def test_coverage():
    assert {k: get_game_bone_map(k).coverage() for k in GAME_BONE_MAPS} == {
        "mixamo": 52, "cmu_bvh": 52, "rokoko": 52, "quaternius_ual": 52, "rigify_def": 22}


def test_mixamo_follows_the_ue5_correspondence():
    m = get_game_bone_map("mixamo")
    assert m.canonical("mixamorig:Hips") == "pelvis"
    assert m.canonical("mixamorig:Head") == "head"
    assert m.canonical("mixamorig:LeftHandIndex1") == "index_01_l"
    assert m.canonical("mixamorig:RightHandThumb3") == "thumb_03_r"
    assert m.canonical("mixamorig:LeftToeBase") == "ball_l"
    assert m.canonical("mixamorig:LeftHandIndex4") is None          # end bones stay unmapped
    assert get_game_bone_map("cmu_bvh").canonical("LowerBack") == "spine_01"   # aliases kept


def test_quaternius_is_identity_on_game_names():
    m = get_game_bone_map("quaternius_ual")
    assert all(src.lower() == dst for src, dst in m.source_to_canonical.items())


def test_differences_from_canonical_maps_are_the_documented_pattern():
    """Canonical Mixamo-style maps put Index1..Pinky1 on metacarpals, Head on CERVICAL_1, ToeBase on a metatarsal.

    The game maps follow UE5 practice instead; the canonical maps are left unchanged (finding, owner decision).
    """
    for map_id in ("mixamo", "cmu_bvh", "rokoko", "quaternius_ual"):
        diff = differences_from_canonical(map_id)
        assert len(diff) == 27, map_id
        for src in diff:
            name = src.lower()
            assert "head" in name or "toe" in name or "ball" in name or any(
                f in name for f in ("index", "middle", "ring", "pinky")), src
            assert "thumb" not in name
    assert set(differences_from_canonical("rigify_def")) == {"spine.006", "toe.L", "toe.R"}
