"""Foot model for anatomical reconstruction.

This module defines the parameterized foot model supporting 26 bones per foot.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..coordinate_system import LateralSide
from ..reference import Confidence


class FootBoneType(Enum):
    """Types of bones in the foot."""
    TARSAL = "tarsal"  # 7 tarsal bones
    METATARSAL = "metatarsal"  # 5 metatarsal bones
    PROXIMAL_PHALANX = "proximal_phalanx"  # 5 proximal phalanges
    INTERMEDIATE_PHALANX = "intermediate_phalanx"  # 4 intermediate phalanges
    DISTAL_PHALANX = "distal_phalanx"  # 5 distal phalanges


class ToeRay(Enum):
    """Toe rays of the foot."""
    GREAT_TOE = "great_toe"  # Ray 1 (hallux)
    SECOND_TOE = "second_toe"  # Ray 2
    THIRD_TOE = "third_toe"  # Ray 3
    FOURTH_TOE = "fourth_toe"  # Ray 4
    LITTLE_TOE = "little_toe"  # Ray 5


@dataclass(frozen=True)
class FootBone:
    """Parameter for a single foot bone.

    Attributes:
        bone_id: Unique identifier (e.g., "CALCANEUS_L", "METATARSAL_3_L")
        bone_type: Type of bone
        toe_ray: Toe ray if applicable
        position: 3D coordinate (x, y, z) in meters
        length: Length of the bone in meters
        width: Width of the bone in meters
        height: Height of the bone in meters
        orientation: Rotation angle in degrees
        side: Lateral side (left or right foot)
        index: Index within bone type
        source_id: Reference source ID
        confidence: Confidence in values
        notes: Additional context
    """

    bone_id: str
    bone_type: FootBoneType
    toe_ray: Optional[ToeRay]
    position: Tuple[float, float, float]
    length: float
    width: float
    height: float
    orientation: float
    side: LateralSide
    index: int
    source_id: Optional[str] = None
    confidence: Confidence = Confidence.UNKNOWN
    notes: str = ""

    def is_known(self) -> bool:
        """Check if bone parameters are known."""
        return self.length > 0.0 or self.source_id is not None

    def is_tarsal(self) -> bool:
        """Check if bone is a tarsal."""
        return self.bone_type == FootBoneType.TARSAL

    def is_metatarsal(self) -> bool:
        """Check if bone is a metatarsal."""
        return self.bone_type == FootBoneType.METATARSAL

    def is_phalanx(self) -> bool:
        """Check if bone is a phalanx."""
        return self.bone_type in [
            FootBoneType.PROXIMAL_PHALANX,
            FootBoneType.INTERMEDIATE_PHALANX,
            FootBoneType.DISTAL_PHALANX
        ]


@dataclass(frozen=True)
class FootModel:
    """Parameterized foot model (26 bones per foot).

    Attributes:
        model_id: Unique identifier for the foot model
        version: Version of the foot model
        side: Lateral side (left or right foot)
        bones: Dictionary of bones by ID
        total_length: Total length of foot in meters
        foot_width: Width of foot in meters
        arch_height: Height of longitudinal arch in meters
        heel_width: Width of heel in meters
        toe_spacing: Average spacing between toes in meters
        source_id: Reference source ID
        created_at: Creation timestamp
    """

    model_id: str
    version: str
    side: LateralSide
    bones: Dict[str, FootBone]
    total_length: float
    foot_width: float
    arch_height: float
    heel_width: float
    toe_spacing: float
    source_id: Optional[str] = None
    created_at: date = field(default_factory=date.today)

    def get_bone(self, bone_id: str) -> Optional[FootBone]:
        """Get bone by ID."""
        return self.bones.get(bone_id)

    def get_bones_by_type(self, bone_type: FootBoneType) -> List[FootBone]:
        """Get all bones of a specific type."""
        return [b for b in self.bones.values() if b.bone_type == bone_type]

    def get_bones_by_ray(self, toe_ray: ToeRay) -> List[FootBone]:
        """Get all bones in a specific toe ray."""
        return [b for b in self.bones.values() if b.toe_ray == toe_ray]

    def get_tarsals(self) -> List[FootBone]:
        """Get all tarsal bones (should be 7)."""
        return self.get_bones_by_type(FootBoneType.TARSAL)

    def get_metatarsals(self) -> List[FootBone]:
        """Get all metatarsal bones (should be 5)."""
        return self.get_bones_by_type(FootBoneType.METATARSAL)

    def get_phalanges(self) -> List[FootBone]:
        """Get all phalanges (should be 14)."""
        return self.get_bones_by_type(FootBoneType.PROXIMAL_PHALANX) + \
               self.get_bones_by_type(FootBoneType.INTERMEDIATE_PHALANX) + \
               self.get_bones_by_type(FootBoneType.DISTAL_PHALANX)

    def has_complete_structure(self) -> bool:
        """Check if foot has complete 26-bone structure."""
        tarsal_count = len(self.get_tarsals())
        metatarsal_count = len(self.get_metatarsals())
        phalanx_count = len(self.get_phalanges())

        return tarsal_count == 7 and metatarsal_count == 5 and phalanx_count == 14

    def has_uniform_bones(self) -> bool:
        """Check if bones are uniform (simplified structure)."""
        metatarsals = self.get_metatarsals()
        if len(metatarsals) < 2:
            return False

        # Check if all metatarsals have same length
        first_length = metatarsals[0].length
        return all(abs(m.length - first_length) < 0.001 for m in metatarsals)

    def has_longitudinal_arch(self) -> bool:
        """Check if foot has longitudinal arch (not flat)."""
        return self.arch_height > 0.05  # Minimum arch height threshold


class FootModelBuilder:
    """Builder for creating foot models."""

    def __init__(self, model_id: str, version: str, side: LateralSide):
        self.model_id = model_id
        self.version = version
        self.side = side
        self.bones: Dict[str, FootBone] = {}
        self.total_length = 0.0
        self.foot_width = 0.0
        self.arch_height = 0.0
        self.heel_width = 0.0
        self.toe_spacing = 0.0
        self.source_id: Optional[str] = None

    def add_bone(self, bone: FootBone) -> "FootModelBuilder":
        """Add a bone to the model."""
        self.bones[bone.bone_id] = bone
        return self

    def set_total_length(self, length: float) -> "FootModelBuilder":
        """Set total foot length."""
        self.total_length = length
        return self

    def set_foot_width(self, width: float) -> "FootModelBuilder":
        """Set foot width."""
        self.foot_width = width
        return self

    def set_arch_height(self, height: float) -> "FootModelBuilder":
        """Set longitudinal arch height."""
        self.arch_height = height
        return self

    def set_heel_width(self, width: float) -> "FootModelBuilder":
        """Set heel width."""
        self.heel_width = width
        return self

    def set_toe_spacing(self, spacing: float) -> "FootModelBuilder":
        """Set toe spacing."""
        self.toe_spacing = spacing
        return self

    def set_source_id(self, source_id: str) -> "FootModelBuilder":
        """Set reference source ID."""
        self.source_id = source_id
        return self

    def build(self) -> FootModel:
        """Build the foot model."""
        return FootModel(
            model_id=self.model_id,
            version=self.version,
            side=self.side,
            bones=dict(self.bones),
            total_length=self.total_length,
            foot_width=self.foot_width,
            arch_height=self.arch_height,
            heel_width=self.heel_width,
            toe_spacing=self.toe_spacing,
            source_id=self.source_id
        )


def create_unknown_foot_bone(bone_id: str, bone_type: FootBoneType,
                              side: LateralSide, index: int,
                              toe_ray: Optional[ToeRay] = None) -> FootBone:
    """Create a placeholder unknown foot bone."""
    return FootBone(
        bone_id=bone_id,
        bone_type=bone_type,
        toe_ray=toe_ray,
        position=(0.0, 0.0, 0.0),
        length=0.0,
        width=0.0,
        height=0.0,
        orientation=0.0,
        side=side,
        index=index,
        confidence=Confidence.UNKNOWN,
        notes="Bone parameters not yet determined"
    )


def create_measured_foot_bone(bone_id: str, bone_type: FootBoneType,
                               side: LateralSide, index: int,
                               position: Tuple[float, float, float],
                               length: float, width: float, height: float,
                               orientation: float,
                               toe_ray: Optional[ToeRay] = None,
                               source_id: str = "UNKNOWN") -> FootBone:
    """Create a measured foot bone from reference data."""
    return FootBone(
        bone_id=bone_id,
        bone_type=bone_type,
        toe_ray=toe_ray,
        position=position,
        length=length,
        width=width,
        height=height,
        orientation=orientation,
        side=side,
        index=index,
        source_id=source_id,
        confidence=Confidence.HIGH,
        notes="Measured from reference data"
    )
