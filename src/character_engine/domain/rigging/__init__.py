"""Rig definition contract (control layer over the canonical deform skeleton)."""

from .block_dummy import (
    BLOCK_SEGMENTS,
    ENVELOPE_RADIUS_M,
    BlockPlacement,
    BlockSegment,
    block_placements,
)
from .game_rig import (
    GAME_BONES,
    GAME_CONTROL_RIG,
    RIG_ID,
    GameBone,
    canonical_to_game,
    game_bone_points,
    validate_game_rig,
)
from .hand_poses import (
    HAND_POSES,
    WEAPON_GRIP_POSE,
    HandPose,
    apply_hand_pose,
    grip_pose_for_weapon,
    hand_pose_rotations,
)
from .rig_definition import (
    HUMANOID_RIG,
    ControlBone,
    IKChain,
    RigDefinition,
    SplineChain,
    validate_rig_against_bones,
)
from .sockets import EQUIPMENT_SOCKETS, EquipmentSocket, socket_points, validate_sockets

__all__ = [
    "BLOCK_SEGMENTS",
    "ENVELOPE_RADIUS_M",
    "BlockPlacement",
    "BlockSegment",
    "block_placements",
    "EQUIPMENT_SOCKETS",
    "GAME_BONES",
    "GAME_CONTROL_RIG",
    "HAND_POSES",
    "HandPose",
    "WEAPON_GRIP_POSE",
    "apply_hand_pose",
    "grip_pose_for_weapon",
    "hand_pose_rotations",
    "GameBone",
    "RIG_ID",
    "canonical_to_game",
    "game_bone_points",
    "validate_game_rig",
    "HUMANOID_RIG",
    "ControlBone",
    "EquipmentSocket",
    "IKChain",
    "RigDefinition",
    "SplineChain",
    "socket_points",
    "validate_rig_against_bones",
    "validate_sockets",
]
