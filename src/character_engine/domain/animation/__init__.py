"""Animation contracts: bone maps for mocap retargeting (pure Python)."""

from .bone_map import BONE_MAPS, BoneMap, get_bone_map, invert
from .game_bone_map import GAME_BONE_MAPS, differences_from_canonical, get_game_bone_map

__all__ = [
    "BONE_MAPS",
    "GAME_BONE_MAPS",
    "BoneMap",
    "differences_from_canonical",
    "get_bone_map",
    "get_game_bone_map",
    "invert",
]
