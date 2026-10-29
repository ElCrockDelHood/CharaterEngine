"""Root-motion scale (domain/animation/retarget_scale.py) and toe followers in the bone maps."""

import pytest

from character_engine.domain.animation import get_bone_map, get_game_bone_map, retarget_scale
from character_engine.domain.animation.bone_map import TOE_FOLLOWERS


def _legs(hip: float, knee: float, ankle: float) -> dict:
    return {f"{b}_{s}": (0.1 if s == "L" else -0.1, 0.0, z) for s in ("L", "R")
            for b, z in (("FEMUR", hip), ("TIBIA", knee), ("TALUS", ankle))}


def test_leg_length_is_the_hip_knee_ankle_chain():
    assert retarget_scale.leg_length(_legs(0.9, 0.5, 0.1)) == pytest.approx(0.8)
    assert retarget_scale.leg_length({"FEMUR_L": (0, 0, 1)}) is None


def test_root_scale_modes():
    kw = dict(src_height_m=1.6, dst_height_m=1.8, src_leg_m=0.8, dst_leg_m=0.88)
    assert retarget_scale.root_scale("leg", **kw) == pytest.approx(1.1)
    assert retarget_scale.root_scale("stature", **kw) == pytest.approx(1.125)
    assert retarget_scale.root_scale("none", **kw) == 1.0
    # leg without a chain falls back to the stature ratio
    assert retarget_scale.root_scale("leg", src_height_m=1.6, dst_height_m=1.8) == pytest.approx(1.125)
    with pytest.raises(ValueError):
        retarget_scale.root_scale("hips", **kw)


def test_toe_followers_cover_the_four_other_toes_on_both_feet():
    assert len(TOE_FOLLOWERS) == 8
    assert set(TOE_FOLLOWERS.values()) == {"TOE_PHALANX_PROXIMAL_3_L", "TOE_PHALANX_PROXIMAL_3_R"}
    assert TOE_FOLLOWERS["TOE_PHALANX_PROXIMAL_1_L"] == "TOE_PHALANX_PROXIMAL_3_L"


@pytest.mark.parametrize("map_id", ["quaternius_ual", "mixamo", "cmu_bvh", "rokoko", "rigify_def"])
def test_maps_with_a_toe_joint_carry_the_followers_and_never_map_them(map_id):
    bm = get_bone_map(map_id)
    assert dict(bm.followers) == TOE_FOLLOWERS
    assert not set(bm.followers) & set(bm.source_to_canonical.values())   # followers stay unmapped


def test_game_maps_keep_working_with_followers():
    gm = get_game_bone_map("quaternius_ual")
    assert gm.target_rig != "canonical"
    assert gm.source_to_canonical          # replace() keeps the new field without breaking the game map
