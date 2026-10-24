"""Transform, GlobalTransform, LocalJointTransform y BonePivot – inmutables.

Contract: CE-Q1 CANONICAL QUATERNION AND MANIFOLD CONTRACT
Contract: CE-Q3 GLOBAL AND LOCAL MANIFOLD TRANSFORM SYSTEM

This module defines:
- GlobalTransform: Character's global configuration (p ∈ ℝ³, q ∈ S³)
- LocalJointTransform: Joint's local configuration relative to parent
- Transform: General transform with scale (backward compatibility)
- BonePivot: Local pivot for bones

All orientations use UnitQuaternion (S³ manifold).
NO Euler angles for internal calculations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict

from ....math.algebra.matrix4 import Matrix4
from ....math.algebra.quaternion import Quaternion, UnitQuaternion
from ....math.algebra.vector3 import Vector3


@dataclass(frozen=True)
class GlobalTransform:
    """Global character transform: position ∈ ℝ³, orientation ∈ S³.

    Represents the global configuration of a character or joint in world space.

    Contract: CE-Q1
    - Position: p ∈ ℝ³ (Cartesian space)
    - Orientation: q ∈ S³ (unit quaternion)
    - No Euler angles for internal calculations

    Provenance: PROVEN (CE-Q1 contract)
    """
    position: Vector3 = field(default_factory=Vector3.zero)
    orientation: UnitQuaternion = field(default_factory=UnitQuaternion.identity)

    def __post_init__(self):
        """Validate components are finite."""
        if not self.position.is_finite():
            raise ValueError(f"Position must be finite: {self.position}")
        # UnitQuaternion already validates finiteness and unit norm

    @staticmethod
    def identity() -> 'GlobalTransform':
        """Identity global transform (origin, no rotation).

        Provenance: PROVEN (standard definition)
        """
        return GlobalTransform(Vector3.zero(), UnitQuaternion.identity())

    def compose(self, local: 'LocalJointTransform') -> 'GlobalTransform':
        """Compose global transform with local joint transform.

        Formula:
        q_global = q_parent * q_local
        p_global = p_parent + q_parent ⊙ p_local

        Provenance: PROVEN (standard kinematic composition)
        """
        # Compose orientations: q_global = q_parent * q_local
        new_orientation = self.orientation * local.orientation

        # Compose positions: p_global = p_parent + q_parent ⊙ p_local
        rotated_local_pos = self.orientation.rotate(local.position)
        new_position = self.position + rotated_local_pos

        return GlobalTransform(new_position, new_orientation)

    def inverse(self) -> 'GlobalTransform':
        """Compute inverse global transform.

        Formula:
        q_inv = q⁻¹
        p_inv = -q⁻¹ ⊙ p

        Provenance: PROVEN (standard inverse)
        """
        inv_orientation = self.orientation.inverse()
        inv_position = inv_orientation.rotate(-self.position)
        return GlobalTransform(inv_position, inv_orientation)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (orientation in canonical w ≥ 0 form, Decision 28).

        Provenance: PROVEN (standard serialization)
        """
        q = self.orientation.canonical()
        return {
            "position": {"x": self.position.x, "y": self.position.y, "z": self.position.z},
            "orientation": {"w": q.w, "x": q.x, "y": q.y, "z": q.z}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalTransform':
        """Deserialize from dictionary.

        Provenance: PROVEN (standard deserialization)
        """
        pos = data.get("position", {})
        rot = data.get("orientation", {})

        position = Vector3(pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0))
        orientation = UnitQuaternion.from_quaternion(Quaternion(
            rot.get("w", 1.0),
            rot.get("x", 0.0),
            rot.get("y", 0.0),
            rot.get("z", 0.0)
        ))

        return cls(position, orientation)


@dataclass(frozen=True)
class LocalJointTransform:
    """Local joint transform relative to parent frame.

    Represents the configuration of a joint in its parent's local frame.

    Contract: CE-Q1
    - Local position: p_local ∈ ℝ³ (relative to parent)
    - Local orientation: q_local ∈ S³ (relative to parent)
    - Frame explicit: all transformations are explicit

    Provenance: PROVEN (CE-Q1 contract)
    """
    position: Vector3 = field(default_factory=Vector3.zero)
    orientation: UnitQuaternion = field(default_factory=UnitQuaternion.identity)

    def __post_init__(self):
        """Validate components are finite."""
        if not self.position.is_finite():
            raise ValueError(f"Position must be finite: {self.position}")
        # UnitQuaternion already validates finiteness and unit norm

    @staticmethod
    def identity() -> 'LocalJointTransform':
        """Identity local transform (no offset, no rotation).

        Provenance: PROVEN (standard definition)
        """
        return LocalJointTransform(Vector3.zero(), UnitQuaternion.identity())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (orientation in canonical w ≥ 0 form, Decision 28).

        Provenance: PROVEN (standard serialization)
        """
        q = self.orientation.canonical()
        return {
            "position": {"x": self.position.x, "y": self.position.y, "z": self.position.z},
            "orientation": {"w": q.w, "x": q.x, "y": q.y, "z": q.z}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LocalJointTransform':
        """Deserialize from dictionary.

        Provenance: PROVEN (standard deserialization)
        """
        pos = data.get("position", {})
        rot = data.get("orientation", {})

        position = Vector3(pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0))
        orientation = UnitQuaternion.from_quaternion(Quaternion(
            rot.get("w", 1.0),
            rot.get("x", 0.0),
            rot.get("y", 0.0),
            rot.get("z", 0.0)
        ))

        return cls(position, orientation)


@dataclass(frozen=True)
class Transform:
    """General transform with scale (backward compatibility).

    NOTE: This class uses Quaternion (not UnitQuaternion) for backward compatibility.
    New code should use GlobalTransform or LocalJointTransform instead.

    Provenance: PROVEN (legacy transform for backward compatibility)
    """
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
    """Local pivot for bones (backward compatibility).

    NOTE: This class uses Quaternion (not UnitQuaternion) for backward compatibility.
    New code should use LocalJointTransform instead.

    Provenance: PROVEN (legacy pivot for backward compatibility)
    """
    local_position: Vector3 = field(default_factory=Vector3.zero)
    local_rotation: Quaternion = field(default_factory=Quaternion.identity)

    def to_transform(self) -> Transform:
        return Transform(self.local_position, self.local_rotation)

    def to_dict(self) -> dict:
        return {
            "local_position": {"x": self.local_position.x, "y": self.local_position.y, "z": self.local_position.z},
            "local_rotation": {"w": self.local_rotation.w, "x": self.local_rotation.x, "y": self.local_rotation.y, "z": self.local_rotation.z}
        }
