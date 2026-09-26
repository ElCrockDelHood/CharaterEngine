"""Hand model for anatomical reconstruction.

This module defines the parameterized hand model supporting 27 bones per hand.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Tuple, List
from datetime import date

from ..reference import Confidence
from ..coordinate_system import LateralSide


class HandBoneType(Enum):
    """Types of bones in the hand."""
    CARPAL = "carpal"  # 8 carpal bones
    METACARPAL = "metacarpal"  # 5 metacarpal bones
    PROXIMAL_PHALANX = "proximal_phalanx"  # 5 proximal phalanges
    INTERMEDIATE_PHALANX = "intermediate_phalanx"  # 4 intermediate phalanges
    DISTAL_PHALANX = "distal_phalanx"  # 5 distal phalanges


class FingerRay(Enum):
    """Finger rays of the hand."""
    THUMB = "thumb"  # Ray 1
    INDEX = "index"  # Ray 2
    MIDDLE = "middle"  # Ray 3
    RING = "ring"  # Ray 4
    LITTLE = "little"  # Ray 5


@dataclass(frozen=True)
class HandBone:
    """Parameter for a single hand bone.
    
    Attributes:
        bone_id: Unique identifier (e.g., "SCAPHOID_L", "METACARPAL_3_L")
        bone_type: Type of bone
        finger_ray: Finger ray if applicable
        position: 3D coordinate (x, y, z) in meters
        length: Length of the bone in meters
        width: Width of the bone in meters
        height: Height of the bone in meters
        orientation: Rotation angle in degrees
        side: Lateral side (left or right hand)
        index: Index within bone type
        source_id: Reference source ID
        confidence: Confidence in values
        notes: Additional context
    """
    
    bone_id: str
    bone_type: HandBoneType
    finger_ray: Optional[FingerRay]
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
    
    def is_carpal(self) -> bool:
        """Check if bone is a carpal."""
        return self.bone_type == HandBoneType.CARPAL
    
    def is_metacarpal(self) -> bool:
        """Check if bone is a metacarpal."""
        return self.bone_type == HandBoneType.METACARPAL
    
    def is_phalanx(self) -> bool:
        """Check if bone is a phalanx."""
        return self.bone_type in [
            HandBoneType.PROXIMAL_PHALANX,
            HandBoneType.INTERMEDIATE_PHALANX,
            HandBoneType.DISTAL_PHALANX
        ]


@dataclass(frozen=True)
class HandModel:
    """Parameterized hand model (27 bones per hand).
    
    Attributes:
        model_id: Unique identifier for the hand model
        version: Version of the hand model
        side: Lateral side (left or right hand)
        bones: Dictionary of bones by ID
        total_length: Total length of hand in meters
        palm_width: Width of palm in meters
        palm_length: Length of palm in meters
        thumb_orientation: Thumb opposition angle in degrees
        finger_spacing: Average spacing between fingers in meters
        source_id: Reference source ID
        created_at: Creation timestamp
    """
    
    model_id: str
    version: str
    side: LateralSide
    bones: Dict[str, HandBone]
    total_length: float
    palm_width: float
    palm_length: float
    thumb_orientation: float
    finger_spacing: float
    source_id: Optional[str] = None
    created_at: date = field(default_factory=date.today)
    
    def get_bone(self, bone_id: str) -> Optional[HandBone]:
        """Get bone by ID."""
        return self.bones.get(bone_id)
    
    def get_bones_by_type(self, bone_type: HandBoneType) -> List[HandBone]:
        """Get all bones of a specific type."""
        return [b for b in self.bones.values() if b.bone_type == bone_type]
    
    def get_bones_by_ray(self, finger_ray: FingerRay) -> List[HandBone]:
        """Get all bones in a specific finger ray."""
        return [b for b in self.bones.values() if b.finger_ray == finger_ray]
    
    def get_carpals(self) -> List[HandBone]:
        """Get all carpal bones (should be 8)."""
        return self.get_bones_by_type(HandBoneType.CARPAL)
    
    def get_metacarpals(self) -> List[HandBone]:
        """Get all metacarpal bones (should be 5)."""
        return self.get_bones_by_type(HandBoneType.METACARPAL)
    
    def get_phalanges(self) -> List[HandBone]:
        """Get all phalanges (should be 14)."""
        return self.get_bones_by_type(HandBoneType.PROXIMAL_PHALANX) + \
               self.get_bones_by_type(HandBoneType.INTERMEDIATE_PHALANX) + \
               self.get_bones_by_type(HandBoneType.DISTAL_PHALANX)
    
    def has_complete_structure(self) -> bool:
        """Check if hand has complete 27-bone structure."""
        carpal_count = len(self.get_carpals())
        metacarpal_count = len(self.get_metacarpals())
        phalanx_count = len(self.get_phalanges())
        
        return carpal_count == 8 and metacarpal_count == 5 and phalanx_count == 14
    
    def has_uniform_bones(self) -> bool:
        """Check if bones are uniform (simplified structure)."""
        metacarpals = self.get_metacarpals()
        if len(metacarpals) < 2:
            return False
        
        # Check if all metacarpals have same length
        first_length = metacarpals[0].length
        return all(abs(m.length - first_length) < 0.001 for m in metacarpals)


class HandModelBuilder:
    """Builder for creating hand models."""
    
    def __init__(self, model_id: str, version: str, side: LateralSide):
        self.model_id = model_id
        self.version = version
        self.side = side
        self.bones: Dict[str, HandBone] = {}
        self.total_length = 0.0
        self.palm_width = 0.0
        self.palm_length = 0.0
        self.thumb_orientation = 0.0
        self.finger_spacing = 0.0
        self.source_id: Optional[str] = None
    
    def add_bone(self, bone: HandBone) -> "HandModelBuilder":
        """Add a bone to the model."""
        self.bones[bone.bone_id] = bone
        return self
    
    def set_total_length(self, length: float) -> "HandModelBuilder":
        """Set total hand length."""
        self.total_length = length
        return self
    
    def set_palm_width(self, width: float) -> "HandModelBuilder":
        """Set palm width."""
        self.palm_width = width
        return self
    
    def set_palm_length(self, length: float) -> "HandModelBuilder":
        """Set palm length."""
        self.palm_length = length
        return self
    
    def set_thumb_orientation(self, angle: float) -> "HandModelBuilder":
        """Set thumb opposition angle."""
        self.thumb_orientation = angle
        return self
    
    def set_finger_spacing(self, spacing: float) -> "HandModelBuilder":
        """Set finger spacing."""
        self.finger_spacing = spacing
        return self
    
    def set_source_id(self, source_id: str) -> "HandModelBuilder":
        """Set reference source ID."""
        self.source_id = source_id
        return self
    
    def build(self) -> HandModel:
        """Build the hand model."""
        return HandModel(
            model_id=self.model_id,
            version=self.version,
            side=self.side,
            bones=dict(self.bones),
            total_length=self.total_length,
            palm_width=self.palm_width,
            palm_length=self.palm_length,
            thumb_orientation=self.thumb_orientation,
            finger_spacing=self.finger_spacing,
            source_id=self.source_id
        )


def create_unknown_hand_bone(bone_id: str, bone_type: HandBoneType,
                              side: LateralSide, index: int,
                              finger_ray: Optional[FingerRay] = None) -> HandBone:
    """Create a placeholder unknown hand bone."""
    return HandBone(
        bone_id=bone_id,
        bone_type=bone_type,
        finger_ray=finger_ray,
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


def create_measured_hand_bone(bone_id: str, bone_type: HandBoneType,
                               side: LateralSide, index: int,
                               position: Tuple[float, float, float],
                               length: float, width: float, height: float,
                               orientation: float,
                               finger_ray: Optional[FingerRay] = None,
                               source_id: str = "UNKNOWN") -> HandBone:
    """Create a measured hand bone from reference data."""
    return HandBone(
        bone_id=bone_id,
        bone_type=bone_type,
        finger_ray=finger_ray,
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
