"""Anatomical landmark model for deterministic reconstruction.

This module defines the data structures for representing anatomical landmarks
with bilateral support and coordinate-space management.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import date

from ..coordinate_system import LateralSide, CoordinateSystem, CANONICAL_COORDINATE_SYSTEM
from ..reference import Confidence


class LandmarkRegion(Enum):
    """Anatomical regions for landmarks."""
    PELVIS = "pelvis"
    SPINE = "spine"
    THORAX = "thorax"
    SHOULDER = "shoulder"
    ELBOW = "elbow"
    WRIST = "wrist"
    HAND = "hand"
    HIP = "hip"
    KNEE = "knee"
    ANKLE = "ankle"
    FOOT = "foot"
    SKULL = "skull"
    FACE = "face"
    GENERAL = "general"


class CoordinateSpace(Enum):
    """Coordinate space for landmark coordinates."""
    WORLD = "world"  # World-space coordinates
    LOCAL = "local"  # Local to reference frame
    RELATIVE = "relative"  # Relative to another landmark


@dataclass(frozen=True)
class Landmark:
    """Anatomical landmark with full coordinate and provenance information.
    
    Attributes:
        id: Unique identifier for the landmark
        name: Human-readable landmark name
        canonical_name: Canonical landmark name
        region: Anatomical region
        coordinate: 3D coordinate (x, y, z) in meters
        coordinate_space: Coordinate space definition
        bilateral: Whether landmark is bilateral (left/right)
        side: Lateral side if bilateral
        reference_point: Reference point for coordinate
        source_id: Reference to source ID
        confidence: Confidence in coordinate accuracy
        notes: Additional context
        metadata: Additional metadata
        version: Landmark version
        created_at: Creation timestamp
    """
    
    id: str
    name: str
    canonical_name: str
    region: LandmarkRegion
    coordinate: Tuple[float, float, float]
    coordinate_space: CoordinateSpace
    bilateral: bool = False
    side: Optional[LateralSide] = None
    reference_point: Optional[str] = None
    source_id: Optional[str] = None
    confidence: Confidence = Confidence.UNKNOWN
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: date = field(default_factory=date.today)
    
    def is_midline(self) -> bool:
        """Check if landmark is midline (not bilateral)."""
        return not self.bilateral
    
    def is_bilateral(self) -> bool:
        """Check if landmark is bilateral."""
        return self.bilateral
    
    def is_left(self) -> bool:
        """Check if landmark is on left side."""
        return self.side == LateralSide.LEFT
    
    def is_right(self) -> bool:
        """Check if landmark is on right side."""
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
    
    def is_world_space(self) -> bool:
        """Check if coordinate is in world-space."""
        return self.coordinate_space == CoordinateSpace.WORLD
    
    def is_known(self) -> bool:
        """Check if landmark coordinate is known (not None)."""
        return self.coordinate != (0.0, 0.0, 0.0) or self.source_id is not None
    
    def get_side(self) -> Optional[LateralSide]:
        """Get lateral side."""
        return self.side


@dataclass(frozen=True)
class LandmarkSet:
    """Collection of anatomical landmarks.
    
    Attributes:
        set_id: Unique identifier for the landmark set
        name: Name of the landmark set
        version: Version of the landmark set
        landmarks: Dictionary of landmarks by ID
        coordinate_system: Coordinate system used
        created_at: Creation timestamp
    """
    
    set_id: str
    name: str
    version: str
    landmarks: Dict[str, Landmark]
    coordinate_system: CoordinateSystem = field(default_factory=lambda: CANONICAL_COORDINATE_SYSTEM)
    created_at: date = field(default_factory=date.today)
    
    def get_landmark(self, landmark_id: str) -> Optional[Landmark]:
        """Get landmark by ID."""
        return self.landmarks.get(landmark_id)
    
    def get_landmark_by_canonical_name(self, canonical_name: str) -> Optional[Landmark]:
        """Get landmark by canonical name."""
        for landmark in self.landmarks.values():
            if landmark.canonical_name == canonical_name:
                return landmark
        return None
    
    def get_bilateral_pair(self, landmark_name: str) -> tuple[Optional[Landmark], Optional[Landmark]]:
        """Get left and right versions of a bilateral landmark."""
        left = self.get_landmark_by_canonical_name(f"{landmark_name}_L")
        right = self.get_landmark_by_canonical_name(f"{landmark_name}_R")
        return left, right
    
    def get_landmarks_by_region(self, region: LandmarkRegion) -> list[Landmark]:
        """Get all landmarks in a specific region."""
        return [l for l in self.landmarks.values() if l.region == region]
    
    def get_midline_landmarks(self) -> list[Landmark]:
        """Get all midline landmarks."""
        return [l for l in self.landmarks.values() if l.is_midline()]
    
    def get_bilateral_landmarks(self) -> list[Landmark]:
        """Get all bilateral landmarks."""
        return [l for l in self.landmarks.values() if l.is_bilateral()]
    
    def get_left_landmarks(self) -> list[Landmark]:
        """Get all left-side landmarks."""
        return [l for l in self.landmarks.values() if l.is_left()]
    
    def get_right_landmarks(self) -> list[Landmark]:
        """Get all right-side landmarks."""
        return [l for l in self.landmarks.values() if l.is_right()]
    
    def get_known_landmarks(self) -> list[Landmark]:
        """Get all landmarks with known coordinates."""
        return [l for l in self.landmarks.values() if l.is_known()]
    
    def mirror_landmark(self, landmark: Landmark) -> Landmark:
        """Mirror a landmark across X = 0 plane.
        
        Args:
            landmark: Landmark to mirror
            
        Returns:
            New landmark with mirrored coordinate
        """
        if landmark.is_midline():
            # Midline landmarks don't change
            return landmark
        
        # Mirror coordinate
        mirrored_coord = self.coordinate_system.mirror_x(landmark.coordinate)
        
        # Determine new side
        current_side = landmark.get_side()
        new_side = LateralSide.RIGHT if current_side == LateralSide.LEFT else LateralSide.LEFT
        
        # Create new landmark with mirrored coordinate
        return Landmark(
            id=f"{landmark.id}_MIRRORED",
            name=f"{landmark.name} (Mirrored)",
            canonical_name=f"{landmark.canonical_name}_MIRRORED",
            region=landmark.region,
            coordinate=mirrored_coord,
            coordinate_space=landmark.coordinate_space,
            bilateral=True,
            side=new_side,
            reference_point=landmark.reference_point,
            source_id=landmark.source_id,
            confidence=landmark.confidence,
            notes=f"Mirrored from {landmark.id}",
            metadata=landmark.metadata,
            version=landmark.version,
            created_at=landmark.created_at
        )
    
    def validate_bilateral_symmetry(self, tolerance: float = 0.002) -> Dict[str, bool]:
        """Validate bilateral landmark symmetry.
        
        Args:
            tolerance: Tolerance in meters for coordinate comparison
            
        Returns:
            Dictionary mapping landmark names to symmetry results
        """
        results = {}
        
        for landmark in self.get_bilateral_landmarks():
            canonical_base = landmark.canonical_name.replace("_L", "").replace("_R", "")
            left, right = self.get_bilateral_pair(canonical_base)
            
            if left is None or right is None:
                continue
            
            # Mirror left to right and compare
            mirrored_left = self.mirror_landmark(left)
            
            # Compare coordinates
            matches = all(
                abs(a - b) <= tolerance
                for a, b in zip(mirrored_left.coordinate, right.coordinate)
            )
            
            results[canonical_base] = matches
        
        return results


class LandmarkSetBuilder:
    """Builder for creating landmark sets."""
    
    def __init__(self, set_id: str, name: str, version: str, 
                 coordinate_system: CoordinateSystem = None):
        self.set_id = set_id
        self.name = name
        self.version = version
        self.coordinate_system = coordinate_system or CANONICAL_COORDINATE_SYSTEM
        self.landmarks: Dict[str, Landmark] = {}
    
    def add_landmark(self, landmark: Landmark) -> "LandmarkSetBuilder":
        """Add a landmark to the set."""
        self.landmarks[landmark.id] = landmark
        return self
    
    def build(self) -> LandmarkSet:
        """Build the landmark set."""
        return LandmarkSet(
            set_id=self.set_id,
            name=self.name,
            version=self.version,
            landmarks=dict(self.landmarks),
            coordinate_system=self.coordinate_system
        )


def create_unknown_landmark(canonical_name: str, region: LandmarkRegion,
                            bilateral: bool = False,
                            side: Optional[LateralSide] = None) -> Landmark:
    """Create a placeholder unknown landmark."""
    return Landmark(
        id=f"UNKNOWN_{canonical_name}",
        name=f"Unknown {canonical_name}",
        canonical_name=canonical_name,
        region=region,
        coordinate=(0.0, 0.0, 0.0),
        coordinate_space=CoordinateSpace.WORLD,
        bilateral=bilateral,
        side=side,
        confidence=Confidence.UNKNOWN,
        metadata={"notes": "Landmark coordinate not yet determined"}
    )


def create_measured_landmark(canonical_name: str, region: LandmarkRegion,
                             coordinate: Tuple[float, float, float],
                             source_id: str,
                             bilateral: bool = False,
                             side: Optional[LateralSide] = None) -> Landmark:
    """Create a measured landmark from reference data."""
    return Landmark(
        id=f"MEASURED_{canonical_name}",
        name=f"Measured {canonical_name}",
        canonical_name=canonical_name,
        region=region,
        coordinate=coordinate,
        coordinate_space=CoordinateSpace.WORLD,
        bilateral=bilateral,
        side=side,
        source_id=source_id,
        confidence=Confidence.HIGH,
        metadata={"notes": "Measured from reference data"}
    )


def create_midline_landmark(canonical_name: str, region: LandmarkRegion,
                             coordinate: Tuple[float, float, float],
                             source_id: str) -> Landmark:
    """Create a midline landmark."""
    return Landmark(
        id=f"MIDLINE_{canonical_name}",
        name=f"Midline {canonical_name}",
        canonical_name=canonical_name,
        region=region,
        coordinate=coordinate,
        coordinate_space=CoordinateSpace.WORLD,
        bilateral=False,
        side=LateralSide.MIDLINE,
        source_id=source_id,
        confidence=Confidence.HIGH,
        metadata={"notes": "Midline landmark"}
    )


def create_bilateral_landmark_pair(canonical_name: str, region: LandmarkRegion,
                                   left_coordinate: Tuple[float, float, float],
                                   right_coordinate: Tuple[float, float, float],
                                   source_id: str) -> tuple[Landmark, Landmark]:
    """Create a bilateral landmark pair.
    
    Args:
        canonical_name: Base name (without _L/_R suffix)
        region: Anatomical region
        left_coordinate: Left side coordinate
        right_coordinate: Right side coordinate
        source_id: Reference source ID
        
    Returns:
        Tuple of (left_landmark, right_landmark)
    """
    left = Landmark(
        id=f"{canonical_name}_L",
        name=f"Left {canonical_name}",
        canonical_name=f"{canonical_name}_L",
        region=region,
        coordinate=left_coordinate,
        coordinate_space=CoordinateSpace.WORLD,
        bilateral=True,
        side=LateralSide.LEFT,
        source_id=source_id,
        confidence=Confidence.HIGH
    )
    
    right = Landmark(
        id=f"{canonical_name}_R",
        name=f"Right {canonical_name}",
        canonical_name=f"{canonical_name}_R",
        region=region,
        coordinate=right_coordinate,
        coordinate_space=CoordinateSpace.WORLD,
        bilateral=True,
        side=LateralSide.RIGHT,
        source_id=source_id,
        confidence=Confidence.HIGH
    )
    
    return left, right
