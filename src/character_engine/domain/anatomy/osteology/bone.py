"""Entidad Bone – inmutable, con soporte para contenedores lógicos."""

import math
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, FrozenSet, Mapping, MutableMapping, MutableSequence, Optional
from uuid import UUID, uuid4

from ....math.algebra.vector3 import Vector3
from .constants import BoneState, BoneType
from .transform import BonePivot, Transform


def _deep_freeze(value):
    """Convierte recursivamente estructuras mutables en inmutables."""
    if isinstance(value, (MutableMapping, dict, Mapping)):
        return MappingProxyType({k: _deep_freeze(v) for k, v in value.items()})
    elif isinstance(value, (MutableSequence, list, tuple)):
        return tuple(_deep_freeze(v) for v in value)
    elif isinstance(value, (set, frozenset)):
        return frozenset(_deep_freeze(v) for v in value)
    elif isinstance(value, (str, int, float, bool, type(None))):
        return value
    else:
        raise TypeError(f"Tipo no permitido en metadata: {type(value)}")

def _is_finite(v: float) -> bool:
    return math.isfinite(v)

@dataclass(frozen=True)
class Bone:
    # Campos sin default primero (requeridos)
    name: str
    canonical_name: str
    head: Vector3
    tail: Vector3

    # Campos con default después
    id: UUID = field(default_factory=uuid4)
    parent_id: Optional[UUID] = None
    child_ids: FrozenSet[UUID] = field(default_factory=frozenset)
    transform: Transform = field(default_factory=Transform.identity)
    pivot: BonePivot = field(default_factory=BonePivot)
    bone_type: BoneType = BoneType.LONG
    state: BoneState = BoneState.CREATED
    version: str = "1.0.0"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    is_container: bool = False  # Nuevo flag para contenedores lógicos

    def __post_init__(self):
        if not self.name:
            raise ValueError("El nombre no puede estar vacío")
        if not self.canonical_name:
            raise ValueError("El nombre canónico no puede estar vacío")
        if self.parent_id == self.id:
            raise ValueError("Un hueso no puede ser su propio padre")

        # Solo validar geometría si no es contenedor
        if not self.is_container:
            if not (_is_finite(self.head.x) and _is_finite(self.head.y) and _is_finite(self.head.z)):
                raise ValueError(f"head no finito: {self.head}")
            if not (_is_finite(self.tail.x) and _is_finite(self.tail.y) and _is_finite(self.tail.z)):
                raise ValueError(f"tail no finito: {self.tail}")
            if self.length <= 0:
                raise ValueError(f"Longitud inválida: {self.length}")

        # Normalizar metadata: deep freeze
        object.__setattr__(self, 'metadata', _deep_freeze(self.metadata))

    @property
    def length(self) -> float:
        if self.is_container:
            return 0.0
        return self.head.distance_to(self.tail)

    def is_root(self) -> bool:
        return self.parent_id is None

    def is_anatomical(self) -> bool:
        return not self.is_container

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "canonical_name": self.canonical_name,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "child_ids": [str(cid) for cid in self.child_ids],
            "head": {"x": self.head.x, "y": self.head.y, "z": self.head.z} if not self.is_container else {"x":0,"y":0,"z":0},
            "tail": {"x": self.tail.x, "y": self.tail.y, "z": self.tail.z} if not self.is_container else {"x":0,"y":0,"z":0},
            "transform": self.transform.to_dict(),
            "pivot": self.pivot.to_dict() if hasattr(self.pivot, 'to_dict') else {},
            "bone_type": self.bone_type.value,
            "state": self.state.value,
            "version": self.version,
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_container": self.is_container
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Bone':
        from ....math.algebra.quaternion import Quaternion
        from ....math.algebra.vector3 import Vector3
        from .transform import BonePivot, Transform
        head_data = data.get("head", {"x":0,"y":0,"z":0})
        tail_data = data.get("tail", {"x":0,"y":0.1,"z":0})
        transform_data = data.get("transform", {})
        pivot_data = data.get("pivot", {})
        pos = transform_data.get("position", {})
        rot = transform_data.get("rotation", {})
        scl = transform_data.get("scale", {})
        pivot_pos = pivot_data.get("local_position", {})
        pivot_rot = pivot_data.get("local_rotation", {})
        return cls(
            name=data["name"],
            canonical_name=data["canonical_name"],
            head=Vector3(head_data.get("x",0), head_data.get("y",0), head_data.get("z",0)),
            tail=Vector3(tail_data.get("x",0), tail_data.get("y",0.1), tail_data.get("z",0)),
            id=UUID(data["id"]) if "id" in data else uuid4(),
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None,
            child_ids=frozenset({UUID(cid) for cid in data.get("child_ids", [])}),
            transform=Transform(
                position=Vector3(pos.get("x",0), pos.get("y",0), pos.get("z",0)),
                rotation=Quaternion(rot.get("w",1), rot.get("x",0), rot.get("y",0), rot.get("z",0)),
                scale=Vector3(scl.get("x",1), scl.get("y",1), scl.get("z",1))
            ),
            pivot=BonePivot(
                local_position=Vector3(pivot_pos.get("x",0), pivot_pos.get("y",0), pivot_pos.get("z",0)),
                local_rotation=Quaternion(pivot_rot.get("w",1), pivot_rot.get("x",0), pivot_rot.get("y",0), pivot_rot.get("z",0))
            ),
            bone_type=BoneType(data.get("bone_type", "long")),
            state=BoneState(data.get("state", "created")),
            version=data.get("version", "1.0.0"),
            metadata=dict(data.get("metadata", {})),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            is_container=data.get("is_container", False)
        )
