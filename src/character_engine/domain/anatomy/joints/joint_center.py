"""Joint center model for anatomical reconstruction.

This module defines the data structures for representing joint centers
with clear distinction between anatomical joint centers and bone endpoints.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from datetime import date

from ..coordinate_system import LateralSide
from ..reference import Confidence


class JointType(Enum):
    """Types of joints."""
    SHOULDER = "shoulder"
    ELBOW = "elbow"
    WRIST = "wrist"
    HIP = "hip"
    KNEE = "knee"
    ANKLE = "ankle"


class JointCenterType(Enum):
    """Types of joint center representations."""
    ANATOMICAL_CENTER = "anatomical_center"  # True anatomical joint center
    BONE_ENDPOINT = "bone_endpoint"  # Geometric bone endpoint
    ARTICULAR_SURFACE = "articular_surface"  # Articular surface center
    GEOMETRIC_REPRESENTATION = "geometric_representation"  # Simplified geometric center


@dataclass(frozen=True)
class JointCenter:
    """Joint center with full anatomical and geometric information.
    
    Attributes:
        id: Unique identifier for the joint center
        name: Human-readable joint center name
        canonical_name: Canonical joint center name
        joint_type: Type of joint
        center_type: Type of center representation
        coordinate: 3D coordinate (x, y, z) in meters
        bilateral: Whether joint is bilateral (left/right)
        side: Lateral side if bilateral
        parent_bone: Parent bone name
        child_bone: Child bone name
        source_id: Reference to source ID
        confidence: Confidence in coordinate accuracy
        notes: Additional context
        metadata: Additional metadata
        version: Joint center version
        created_at: Creation timestamp
    """
    
    id: str
    name: str
    canonical_name: str
    joint_type: JointType
    center_type: JointCenterType
    coordinate: Tuple[float, float, float]
    bilateral: bool = False
    side: Optional[LateralSide] = None
    parent_bone: Optional[str] = None
    child_bone: Optional[str] = None
    source_id: Optional[str] = None
    confidence: Confidence = Confidence.UNKNOWN
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: date = field(default_factory=date.today)
    
    def is_anatomical_center(self) -> bool:
        """Check if this is an anatomical joint center."""
        return self.center_type == JointCenterType.ANATOMICAL_CENTER
    
    def is_bone_endpoint(self) -> bool:
        """Check if this is a bone endpoint."""
        return self.center_type == JointCenterType.BONE_ENDPOINT
    
    def is_bilateral(self) -> bool:
        """Check if joint is bilateral."""
        return self.bilateral
    
    def is_left(self) -> bool:
        """Check if joint is on left side."""
        return self.side == LateralSide.LEFT
    
    def is_right(self) -> bool:
        """Check if joint is on right side."""
        return self.side == LateralSide.RIGHT
    
    def get_x(self) -> float:
        """Get X coordinate."""
        return self.coordinate[0]
    
    def get_y(self) -> float:
        """Get Y coordinate."""
        return self.coordinate[1]
    
    def get_z(self) -> float:
        """Get Z coordinate."""
        return self.coordinate[2]
    
    def is_known(self) -> bool:
        """Check if joint center coordinate is known."""
        return self.coordinate != (0.0, 0.0, 0.0) or self.source_id is not None


@dataclass(frozen=True)
class JointCenterSet:
    """Collection of joint centers.
    
    Attributes:
        set_id: Unique identifier for the joint center set
        name: Name of the joint center set
        version: Version of the joint center set
        joint_centers: Dictionary of joint centers by ID
        created_at: Creation timestamp
    """
    
    set_id: str
    name: str
    version: str
    joint_centers: Dict[str, JointCenter]
    created_at: date = field(default_factory=date.today)
    
    def get_joint_center(self, joint_center_id: str) -> Optional[JointCenter]:
        """Get joint center by ID."""
        return self.joint_centers.get(joint_center_id)
    
    def get_joint_center_by_canonical_name(self, canonical_name: str) -> Optional[JointCenter]:
        """Get joint center by canonical name."""
        for joint_center in self.joint_centers.values():
            if joint_center.canonical_name == canonical_name:
                return joint_center
        return None
    
    def get_bilateral_pair(self, joint_name: str) -> tuple[Optional[JointCenter], Optional[JointCenter]]:
        """Get left and right versions of a bilateral joint."""
        left = self.get_joint_center_by_canonical_name(f"{joint_name}_L")
        right = self.get_joint_center_by_canonical_name(f"{joint_name}_R")
        return left, right
    
    def get_joint_centers_by_type(self, joint_type: JointType) -> list[JointCenter]:
        """Get all joint centers of a specific type."""
        return [jc for jc in self.joint_centers.values() if jc.joint_type == joint_type]
    
    def get_anatomical_centers(self) -> list[JointCenter]:
        """Get all anatomical joint centers."""
        return [jc for jc in self.joint_centers.values() if jc.is_anatomical_center()]
    
    def get_bone_endpoints(self) -> list[JointCenter]:
        """Get all bone endpoints."""
        return [jc for jc in self.joint_centers.values() if jc.is_bone_endpoint()]
    
    def get_known_joint_centers(self) -> list[JointCenter]:
        """Get all joint centers with known coordinates."""
        return [jc for jc in self.joint_centers.values() if jc.is_known()]


class JointCenterSetBuilder:
    """Builder for creating joint center sets."""
    
    def __init__(self, set_id: str, name: str, version: str):
        self.set_id = set_id
        self.name = name
        self.version = version
        self.joint_centers: Dict[str, JointCenter] = {}
    
    def add_joint_center(self, joint_center: JointCenter) -> "JointCenterSetBuilder":
        """Add a joint center to the set."""
        self.joint_centers[joint_center.id] = joint_center
        return self
    
    def build(self) -> JointCenterSet:
        """Build the joint center set."""
        return JointCenterSet(
            set_id=self.set_id,
            name=self.name,
            version=self.version,
            joint_centers=dict(self.joint_centers)
        )


def create_unknown_joint_center(canonical_name: str, joint_type: JointType,
                                 center_type: JointCenterType = JointCenterType.ANATOMICAL_CENTER,
                                 bilateral: bool = False,
                                 side: Optional[LateralSide] = None) -> JointCenter:
    """Create a placeholder unknown joint center."""
    return JointCenter(
        id=f"UNKNOWN_{canonical_name}",
        name=f"Unknown {canonical_name}",
        canonical_name=canonical_name,
        joint_type=joint_type,
        center_type=center_type,
        coordinate=(0.0, 0.0, 0.0),
        bilateral=bilateral,
        side=side,
        confidence=Confidence.UNKNOWN,
        metadata={"notes": "Joint center coordinate not yet determined"}
    )


def create_measured_joint_center(canonical_name: str, joint_type: JointType,
                                  coordinate: Tuple[float, float, float],
                                  source_id: str,
                                  center_type: JointCenterType = JointCenterType.ANATOMICAL_CENTER,
                                  bilateral: bool = False,
                                  side: Optional[LateralSide] = None,
                                  parent_bone: Optional[str] = None,
                                  child_bone: Optional[str] = None) -> JointCenter:
    """Create a measured joint center from reference data."""
    return JointCenter(
        id=f"MEASURED_{canonical_name}",
        name=f"Measured {canonical_name}",
        canonical_name=canonical_name,
        joint_type=joint_type,
        center_type=center_type,
        coordinate=coordinate,
        bilateral=bilateral,
        side=side,
        parent_bone=parent_bone,
        child_bone=child_bone,
        source_id=source_id,
        confidence=Confidence.HIGH,
        metadata={"notes": "Measured from reference data"}
    )


def create_bilateral_joint_center_pair(canonical_name: str, joint_type: JointType,
                                        left_coordinate: Tuple[float, float, float],
                                        right_coordinate: Tuple[float, float, float],
                                        source_id: str,
                                        center_type: JointCenterType = JointCenterType.ANATOMICAL_CENTER,
                                        parent_bone: Optional[str] = None,
                                        child_bone: Optional[str] = None) -> tuple[JointCenter, JointCenter]:
    """Create a bilateral joint center pair.
    
    Args:
        canonical_name: Base name (without _L/_R suffix)
        joint_type: Type of joint
        left_coordinate: Left side coordinate
        right_coordinate: Right side coordinate
        source_id: Reference source ID
        center_type: Type of center representation
        parent_bone: Parent bone name
        child_bone: Child bone name
        
    Returns:
        Tuple of (left_joint_center, right_joint_center)
    """
    left = JointCenter(
        id=f"{canonical_name}_L",
        name=f"Left {canonical_name}",
        canonical_name=f"{canonical_name}_L",
        joint_type=joint_type,
        center_type=center_type,
        coordinate=left_coordinate,
        bilateral=True,
        side=LateralSide.LEFT,
        parent_bone=parent_bone,
        child_bone=child_bone,
        source_id=source_id,
        confidence=Confidence.HIGH
    )
    
    right = JointCenter(
        id=f"{canonical_name}_R",
        name=f"Right {canonical_name}",
        canonical_name=f"{canonical_name}_R",
        joint_type=joint_type,
        center_type=center_type,
        coordinate=right_coordinate,
        bilateral=True,
        side=LateralSide.RIGHT,
        parent_bone=parent_bone,
        child_bone=child_bone,
        source_id=source_id,
        confidence=Confidence.HIGH
    )
    
    return left, right
