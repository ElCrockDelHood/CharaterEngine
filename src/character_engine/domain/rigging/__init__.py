"""Rig definition contract (control layer over the canonical deform skeleton)."""

from .block_dummy import (
    BLOCK_SEGMENTS,
    ENVELOPE_RADIUS_M,
    BlockPlacement,
    BlockSegment,
    block_placements,
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
