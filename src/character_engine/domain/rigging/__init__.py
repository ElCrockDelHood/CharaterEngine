"""Rig definition contract (control layer over the canonical deform skeleton)."""

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
