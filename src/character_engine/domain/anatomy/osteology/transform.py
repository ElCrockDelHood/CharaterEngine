"""Transform y BonePivot – inmutables."""

from dataclasses import dataclass, field
from typing import Dict, Any
from ....math.algebra.vector3 import Vector3
from ....math.algebra.quaternion import Quaternion
from ....math.algebra.matrix4 import Matrix4

@dataclass(frozen=True)
class Transform:
    position: Vector3 = field(default_factory=Vector3.zero)
    rotation: Quaternion = field(default_factory=Quaternion.identity)
    scale: Vector3 = field(default_factory=lambda: Vector3(1.0, 1.0, 1.0))

    def __post_init__(self):
        if self.scale.x <= 0 or self.scale.y <= 0 or self.scale.z <= 0:
            raise ValueError("Escala debe ser positiva")

    def to_matrix(self) -> Matrix4:
        return Matrix4.translation(self.position) @ Matrix4.rotation(self.rotation) @ Matrix4.scale(self.scale)

    def inverse(self) -> 'Transform':
        inv_scale = Vector3(1.0/self.scale.x, 1.0/self.scale.y, 1.0/self.scale.z)
        inv_rot = self.rotation.inverse()
        inv_pos = inv_rot.rotate(-self.position)
        return Transform(inv_pos, inv_rot, inv_scale)

    def compose(self, other: 'Transform') -> 'Transform':
        new_pos = self.position + self.rotation.rotate(other.position * self.scale)
        new_rot = self.rotation * other.rotation
        new_scale = self.scale * other.scale
        return Transform(new_pos, new_rot, new_scale)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": {"x": self.position.x, "y": self.position.y, "z": self.position.z},
            "rotation": {"w": self.rotation.w, "x": self.rotation.x, "y": self.rotation.y, "z": self.rotation.z},
            "scale": {"x": self.scale.x, "y": self.scale.y, "z": self.scale.z}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transform':
        pos = data.get("position", {})
        rot = data.get("rotation", {})
        scl = data.get("scale", {})
        return cls(
            position=Vector3(pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0)),
            rotation=Quaternion(rot.get("w", 1.0), rot.get("x", 0.0), rot.get("y", 0.0), rot.get("z", 0.0)),
            scale=Vector3(scl.get("x", 1.0), scl.get("y", 1.0), scl.get("z", 1.0))
        )

    @staticmethod
    def identity() -> 'Transform':
        return Transform()

@dataclass(frozen=True)
class BonePivot:
    local_position: Vector3 = field(default_factory=Vector3.zero)
    local_rotation: Quaternion = field(default_factory=Quaternion.identity)

    def to_transform(self) -> Transform:
        return Transform(self.local_position, self.local_rotation)

    def to_dict(self) -> dict:
        return {
            "local_position": {"x": self.local_position.x, "y": self.local_position.y, "z": self.local_position.z},
            "local_rotation": {"w": self.local_rotation.w, "x": self.local_rotation.x, "y": self.local_rotation.y, "z": self.local_rotation.z}
        }
