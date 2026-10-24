"""Animation contracts: bone maps for mocap retargeting (pure Python)."""

from .bone_map import BONE_MAPS, BoneMap, get_bone_map, invert

__all__ = ["BONE_MAPS", "BoneMap", "get_bone_map", "invert"]
