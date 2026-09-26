"""Spine model for anatomical reconstruction.

This module defines the parameterized spine model with natural curvatures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Tuple, List
from datetime import date

from ..reference import Confidence


class SpineRegion(Enum):
    """Regions of the spine."""
    CERVICAL = "cervical"  # C1-C7
    THORACIC = "thoracic"  # T1-T12
    LUMBAR = "lumbar"  # L1-L5
    SACRUM = "sacrum"  # Sacrum
    COCCYX = "coccyx"  # Coccyx


class CurvatureType(Enum):
    """Types of spinal curvatures."""
    LORDOSIS = "lordosis"  # Inward curvature (cervical, lumbar)
    KYPHOSIS = "kyphosis"  # Outward curvature (thoracic)
    SCOLIOSIS = "scoliosis"  # Lateral curvature (pathological)
    STRAIGHT = "straight"  # No curvature (abnormal)


@dataclass(frozen=True)
class VertebralParameter:
    """Parameter for a single vertebra.
    
    Attributes:
        vertebra_id: Unique identifier (e.g., "C1", "T5", "L3")
        region: Spine region
        position: 3D coordinate (x, y, z) in meters
        height: Height of the vertebra in meters
        width: Width of the vertebra in meters
        depth: Depth of the vertebra in meters
        index: Index within region (0-based)
        source_id: Reference source ID
        confidence: Confidence in values
        notes: Additional context
    """
    
    vertebra_id: str
    region: SpineRegion
    position: Tuple[float, float, float]
    height: float
    width: float
    depth: float
    index: int
    source_id: Optional[str] = None
    confidence: Confidence = Confidence.UNKNOWN
    notes: str = ""
    
    def is_known(self) -> bool:
        """Check if vertebra parameters are known."""
        return self.position != (0.0, 0.0, 0.0) or self.source_id is not None


@dataclass(frozen=True)
class CurvatureParameter:
    """Parameter for spinal curvature.
    
    Attributes:
        region: Spine region
        curvature_type: Type of curvature
        angle: Curvature angle in degrees
        radius: Radius of curvature in meters
        start_point: Starting coordinate of curvature
        end_point: Ending coordinate of curvature
        source_id: Reference source ID
        confidence: Confidence in values
        notes: Additional context
    """
    
    region: SpineRegion
    curvature_type: CurvatureType
    angle: float
    radius: float
    start_point: Tuple[float, float, float]
    end_point: Tuple[float, float, float]
    source_id: Optional[str] = None
    confidence: Confidence = Confidence.UNKNOWN
    notes: str = ""
    
    def is_known(self) -> bool:
        """Check if curvature parameters are known."""
        return self.angle != 0.0 or self.source_id is not None


@dataclass(frozen=True)
class SpineModel:
    """Parameterized spine model.
    
    Attributes:
        model_id: Unique identifier for the spine model
        version: Version of the spine model
        vertebrae: Dictionary of vertebrae by ID
        curvatures: Dictionary of curvatures by region
        total_height: Total height of spine in meters
        intervertebral_spacing: Average spacing between vertebrae
        sacral_orientation: Sacral angle in degrees
        source_id: Reference source ID
        created_at: Creation timestamp
    """
    
    model_id: str
    version: str
    vertebrae: Dict[str, VertebralParameter]
    curvatures: Dict[SpineRegion, CurvatureParameter]
    total_height: float
    intervertebral_spacing: float
    sacral_orientation: float
    source_id: Optional[str] = None
    created_at: date = field(default_factory=date.today)
    
    def get_vertebra(self, vertebra_id: str) -> Optional[VertebralParameter]:
        """Get vertebra by ID."""
        return self.vertebrae.get(vertebra_id)
    
    def get_vertebrae_by_region(self, region: SpineRegion) -> List[VertebralParameter]:
        """Get all vertebrae in a specific region."""
        return [v for v in self.vertebrae.values() if v.region == region]
    
    def get_curvature(self, region: SpineRegion) -> Optional[CurvatureParameter]:
        """Get curvature for a region."""
        return self.curvatures.get(region)
    
    def has_natural_curvatures(self) -> bool:
        """Check if spine has natural curvatures (not straight)."""
        # Natural spine should have lordosis in cervical and lumbar regions
        # and kyphosis in thoracic region
        cervical = self.get_curvature(SpineRegion.CERVICAL)
        thoracic = self.get_curvature(SpineRegion.THORACIC)
        lumbar = self.get_curvature(SpineRegion.LUMBAR)
        
        has_cervical_lordosis = cervical and cervical.curvature_type == CurvatureType.LORDOSIS
        has_thoracic_kyphosis = thoracic and thoracic.curvature_type == CurvatureType.KYPHOSIS
        has_lumbar_lordosis = lumbar and lumbar.curvature_type == CurvatureType.LORDOSIS
        
        return has_cervical_lordosis and has_thoracic_kyphosis and has_lumbar_lordosis
    
    def is_straight(self) -> bool:
        """Check if spine is straight (abnormal)."""
        for curvature in self.curvatures.values():
            if curvature.curvature_type != CurvatureType.STRAIGHT:
                return False
        return True


class SpineModelBuilder:
    """Builder for creating spine models."""
    
    def __init__(self, model_id: str, version: str):
        self.model_id = model_id
        self.version = version
        self.vertebrae: Dict[str, VertebralParameter] = {}
        self.curvatures: Dict[SpineRegion, CurvatureParameter] = {}
        self.total_height = 0.0
        self.intervertebral_spacing = 0.0
        self.sacral_orientation = 0.0
        self.source_id: Optional[str] = None
    
    def add_vertebra(self, vertebra: VertebralParameter) -> "SpineModelBuilder":
        """Add a vertebra to the model."""
        self.vertebrae[vertebra.vertebra_id] = vertebra
        return self
    
    def add_curvature(self, curvature: CurvatureParameter) -> "SpineModelBuilder":
        """Add a curvature to the model."""
        self.curvatures[curvature.region] = curvature
        return self
    
    def set_total_height(self, height: float) -> "SpineModelBuilder":
        """Set total spine height."""
        self.total_height = height
        return self
    
    def set_intervertebral_spacing(self, spacing: float) -> "SpineModelBuilder":
        """Set intervertebral spacing."""
        self.intervertebral_spacing = spacing
        return self
    
    def set_sacral_orientation(self, angle: float) -> "SpineModelBuilder":
        """Set sacral orientation angle."""
        self.sacral_orientation = angle
        return self
    
    def set_source_id(self, source_id: str) -> "SpineModelBuilder":
        """Set reference source ID."""
        self.source_id = source_id
        return self
    
    def build(self) -> SpineModel:
        """Build the spine model."""
        return SpineModel(
            model_id=self.model_id,
            version=self.version,
            vertebrae=dict(self.vertebrae),
            curvatures=dict(self.curvatures),
            total_height=self.total_height,
            intervertebral_spacing=self.intervertebral_spacing,
            sacral_orientation=self.sacral_orientation,
            source_id=self.source_id
        )


def create_unknown_vertebra(vertebra_id: str, region: SpineRegion, index: int) -> VertebralParameter:
    """Create a placeholder unknown vertebra."""
    return VertebralParameter(
        vertebra_id=vertebra_id,
        region=region,
        position=(0.0, 0.0, 0.0),
        height=0.0,
        width=0.0,
        depth=0.0,
        index=index,
        confidence=Confidence.UNKNOWN,
        notes="Vertebra parameters not yet determined"
    )


def create_measured_vertebra(vertebra_id: str, region: SpineRegion, index: int,
                             position: Tuple[float, float, float],
                             height: float, width: float, depth: float,
                             source_id: str) -> VertebralParameter:
    """Create a measured vertebra from reference data."""
    return VertebralParameter(
        vertebra_id=vertebra_id,
        region=region,
        position=position,
        height=height,
        width=width,
        depth=depth,
        index=index,
        source_id=source_id,
        confidence=Confidence.HIGH,
        notes="Measured from reference data"
    )


def create_unknown_curvature(region: SpineRegion) -> CurvatureParameter:
    """Create a placeholder unknown curvature."""
    return CurvatureParameter(
        region=region,
        curvature_type=CurvatureType.STRAIGHT,
        angle=0.0,
        radius=0.0,
        start_point=(0.0, 0.0, 0.0),
        end_point=(0.0, 0.0, 0.0),
        confidence=Confidence.UNKNOWN,
        notes="Curvature parameters not yet determined"
    )


def create_measured_curvature(region: SpineRegion, curvature_type: CurvatureType,
                              angle: float, radius: float,
                              start_point: Tuple[float, float, float],
                              end_point: Tuple[float, float, float],
                              source_id: str) -> CurvatureParameter:
    """Create a measured curvature from reference data."""
    return CurvatureParameter(
        region=region,
        curvature_type=curvature_type,
        angle=angle,
        radius=radius,
        start_point=start_point,
        end_point=end_point,
        source_id=source_id,
        confidence=Confidence.HIGH,
        notes="Measured from reference data"
    )
