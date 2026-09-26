"""Landmark positioner for anatomical reconstruction.

This module calculates 3D positions for anatomical landmarks based on
body proportions and coordinate system definitions.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import math

from ..coordinate_system import CoordinateSystem, LateralSide
from ..reference import ReferenceDataManager
from .parameter_normalizer import ParameterNormalizer, NormalizedParameter
from .proportion_calculator import ProportionCalculator, CalculatedProportion


class PositioningMethod(Enum):
    """Methods for landmark positioning."""
    RATIO_DERIVATION = "ratio_derivation"  # Derived from body ratios
    FORMULA_BASED = "formula_based"  # Calculated using formulas
    OFFSET_BASED = "offset_based"  # Positioned as offsets from reference points
    INTERPOLATION = "interpolation"  # Interpolated between reference points


@dataclass
class LandmarkPosition:
    """3D position of an anatomical landmark.
    
    Attributes:
        name: Landmark name
        canonical_name: Canonical landmark name
        position: 3D coordinates (x, y, z) in the anatomical coordinate system
        unit: Unit of measurement (typically meters)
        confidence: Confidence in position accuracy
        provenance: Source of position data
        positioning_method: Method used to calculate position
        bilateral: Whether landmark is bilateral (left/right)
        side: Lateral side if bilateral
        reference_landmarks: Reference landmarks used in calculation
        metadata: Additional metadata
    """
    
    name: str
    canonical_name: str
    position: Tuple[float, float, float]  # (x, y, z)
    unit: str = "meters"
    confidence: str = "LOW"
    provenance: str = "DERIVED"
    positioning_method: PositioningMethod = PositioningMethod.RATIO_DERIVATION
    bilateral: bool = False
    side: Optional[LateralSide] = None
    reference_landmarks: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.reference_landmarks is None:
            self.reference_landmarks = {}
        if self.metadata is None:
            self.metadata = {}
    
    def get_x(self) -> float:
        """Get X coordinate (lateral axis)."""
        return self.position[0]
    
    def get_y(self) -> float:
        """Get Y coordinate (vertical axis)."""
        return self.position[1]
    
    def get_z(self) -> float:
        """Get Z coordinate (anterior-posterior axis)."""
        return self.position[2]
    
    def distance_to(self, other: 'LandmarkPosition') -> float:
        """Calculate Euclidean distance to another landmark."""
        dx = self.get_x() - other.get_x()
        dy = self.get_y() - other.get_y()
        dz = self.get_z() - other.get_z()
        return math.sqrt(dx*dx + dy*dy + dz*dz)


class LandmarkPositioner:
    """Positions anatomical landmarks in 3D space."""
    
    def __init__(self, 
                 reference_manager: ReferenceDataManager,
                 normalizer: ParameterNormalizer,
                 calculator: ProportionCalculator,
                 coordinate_system: CoordinateSystem):
        """Initialize landmark positioner.
        
        Args:
            reference_manager: Reference data manager
            normalizer: Parameter normalizer
            calculator: Proportion calculator
            coordinate_system: Anatomical coordinate system
        """
        self.reference_manager = reference_manager
        self.normalizer = normalizer
        self.calculator = calculator
        self.coordinate_system = coordinate_system
        self.cache: Dict[str, LandmarkPosition] = {}
    
    def position_landmarks(self, profile) -> Dict[str, LandmarkPosition]:
        """Position all anatomical landmarks for a subject.
        
        Args:
            profile: Subject profile
            
        Returns:
            Dictionary of landmark positions by canonical name
        """
        # Get normalized parameters and proportions
        normalized = self.normalizer.normalize_profile(profile)
        proportions = self.calculator.calculate_proportions(profile)
        
        landmarks = {}
        
        # Position core landmarks first
        landmarks.update(self._position_core_landmarks(normalized, proportions))
        
        # Position joint centers
        landmarks.update(self._position_joint_centers(normalized, proportions))
        
        # Position body segment endpoints
        landmarks.update(self._position_segment_endpoints(normalized, proportions, landmarks))
        
        # Position bilateral landmarks
        landmarks.update(self._position_bilateral_landmarks(normalized, proportions, landmarks))
        
        return landmarks
    
    def _position_core_landmarks(self, 
                                 normalized: Dict[str, NormalizedParameter],
                                 proportions: Dict[str, CalculatedProportion]) -> Dict[str, LandmarkPosition]:
        """Position core anatomical landmarks.
        
        Args:
            normalized: Normalized parameters
            proportions: Calculated proportions
            
        Returns:
            Dictionary of core landmark positions
        """
        landmarks = {}
        
        # Get height value
        height = normalized.get('height')
        if height is None:
            return landmarks
        
        h = height.value
        
        # Position origin (mid-foot ground level)
        origin = LandmarkPosition(
            name="origin",
            canonical_name="origin",
            position=(0.0, 0.0, 0.0),
            unit="meters",
            confidence="HIGH",
            provenance="REFERENCE",
            positioning_method=PositioningMethod.FORMULA_BASED,
            metadata={"description": "Anatomical origin, mid-foot ground level"}
        )
        landmarks["origin"] = origin
        
        # Position head top (vertex)
        if 'head_height' in proportions:
            head_height = proportions['head_height'].value
            head_top = LandmarkPosition(
                name="head_top",
                canonical_name="vertex",
                position=(0.0, h, 0.0),
                unit="meters",
                confidence="LOW",
                provenance="DERIVED",
                positioning_method=PositioningMethod.RATIO_DERIVATION,
                reference_landmarks={"origin": (0.0, 0.0, 0.0)},
                metadata={"height_ratio": head_height / h}
            )
            landmarks["vertex"] = head_top
        
        # Position center of mass (approximately at belly button height)
        com_height = h * 0.55  # Center of mass is ~55% of height
        center_of_mass = LandmarkPosition(
            name="center_of_mass",
            canonical_name="center_of_mass",
            position=(0.0, com_height, 0.0),
            unit="meters",
            confidence="LOW",
            provenance="DERIVED",
            positioning_method=PositioningMethod.RATIO_DERIVATION,
            metadata={"height_ratio": 0.55}
        )
        landmarks["center_of_mass"] = center_of_mass
        
        return landmarks
    
    def _position_joint_centers(self,
                               normalized: Dict[str, NormalizedParameter],
                               proportions: Dict[str, CalculatedProportion]) -> Dict[str, LandmarkPosition]:
        """Position joint centers in 3D space.
        
        Args:
            normalized: Normalized parameters
            proportions: Calculated proportions
            
        Returns:
            Dictionary of joint center positions
        """
        landmarks = {}
        
        # Get height value
        height = normalized.get('height')
        if height is None:
            return landmarks
        
        h = height.value
        
        # Position hip joint center (approximately 50% of height)
        hip_center = LandmarkPosition(
            name="hip_center",
            canonical_name="hip_joint_center",
            position=(0.0, h * 0.50, 0.0),
            unit="meters",
            confidence="LOW",
            provenance="DERIVED",
            positioning_method=PositioningMethod.RATIO_DERIVATION,
            metadata={"height_ratio": 0.50}
        )
        landmarks["hip_joint_center"] = hip_center
        
        # Position shoulder joint center (approximately 82% of height)
        shoulder_center = LandmarkPosition(
            name="shoulder_center",
            canonical_name="shoulder_joint_center",
            position=(0.0, h * 0.82, 0.0),
            unit="meters",
            confidence="LOW",
            provenance="DERIVED",
            positioning_method=PositioningMethod.RATIO_DERIVATION,
            metadata={"height_ratio": 0.82}
        )
        landmarks["shoulder_joint_center"] = shoulder_center
        
        # Position knee joint center (approximately 30% of height)
        knee_center = LandmarkPosition(
            name="knee_center",
            canonical_name="knee_joint_center",
            position=(0.0, h * 0.30, 0.0),
            unit="meters",
            confidence="LOW",
            provenance="DERIVED",
            positioning_method=PositioningMethod.RATIO_DERIVATION,
            metadata={"height_ratio": 0.30}
        )
        landmarks["knee_joint_center"] = knee_center
        
        return landmarks
    
    def _position_segment_endpoints(self,
                                   normalized: Dict[str, NormalizedParameter],
                                   proportions: Dict[str, CalculatedProportion],
                                   existing_landmarks: Dict[str, LandmarkPosition]) -> Dict[str, LandmarkPosition]:
        """Position body segment endpoints.
        
        Args:
            normalized: Normalized parameters
            proportions: Calculated proportions
            existing_landmarks: Already positioned landmarks
            
        Returns:
            Dictionary of segment endpoint positions
        """
        landmarks = {}
        
        # This is a simplified implementation
        # In production, would use more detailed anatomical knowledge
        
        return landmarks
    
    def _position_bilateral_landmarks(self,
                                      normalized: Dict[str, NormalizedParameter],
                                      proportions: Dict[str, CalculatedProportion],
                                      existing_landmarks: Dict[str, LandmarkPosition]) -> Dict[str, LandmarkPosition]:
        """Position bilateral landmarks (left and right).
        
        Args:
            normalized: Normalized parameters
            proportions: Calculated proportions
            existing_landmarks: Already positioned landmarks
            
        Returns:
            Dictionary of bilateral landmark positions
        """
        landmarks = {}
        
        # Get shoulder width if available
        if 'shoulder_width' in proportions:
            shoulder_width = proportions['shoulder_width'].value
            half_width = shoulder_width / 2.0
            
            # Position left and right shoulder joints
            if 'shoulder_joint_center' in existing_landmarks:
                base_y = existing_landmarks['shoulder_joint_center'].get_y()
                
                left_shoulder = LandmarkPosition(
                    name="left_shoulder",
                    canonical_name="left_shoulder_joint",
                    position=(-half_width, base_y, 0.0),
                    unit="meters",
                    confidence="LOW",
                    provenance="DERIVED",
                    positioning_method=PositioningMethod.OFFSET_BASED,
                    bilateral=True,
                    side=LateralSide.LEFT,
                    reference_landmarks={"shoulder_joint_center": existing_landmarks['shoulder_joint_center'].position},
                    metadata={"offset": half_width}
                )
                landmarks["left_shoulder_joint"] = left_shoulder
                
                right_shoulder = LandmarkPosition(
                    name="right_shoulder",
                    canonical_name="right_shoulder_joint",
                    position=(half_width, base_y, 0.0),
                    unit="meters",
                    confidence="LOW",
                    provenance="DERIVED",
                    positioning_method=PositioningMethod.OFFSET_BASED,
                    bilateral=True,
                    side=LateralSide.RIGHT,
                    reference_landmarks={"shoulder_joint_center": existing_landmarks['shoulder_joint_center'].position},
                    metadata={"offset": half_width}
                )
                landmarks["right_shoulder_joint"] = right_shoulder
        
        return landmarks
    
    def get_landmark(self, canonical_name: str, profile) -> Optional[LandmarkPosition]:
        """Get a specific landmark position.
        
        Args:
            canonical_name: Canonical landmark name
            profile: Subject profile
            
        Returns:
            Landmark position if found, None otherwise
        """
        # Check cache first
        cache_key = f"{canonical_name}_{profile.height}_{profile.gender}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Calculate all landmarks
        landmarks = self.position_landmarks(profile)
        
        # Get specific landmark
        landmark = landmarks.get(canonical_name)
        
        # Cache result
        if landmark:
            self.cache[cache_key] = landmark
        
        return landmark
    
    def calculate_landmark_chain(self, start_landmark: str, end_landmark: str, 
                                profile) -> Tuple[float, list]:
        """Calculate the distance and path between two landmarks.
        
        Args:
            start_landmark: Starting landmark canonical name
            end_landmark: Ending landmark canonical name
            profile: Subject profile
            
        Returns:
            Tuple of (distance, list of intermediate landmarks)
        """
        landmarks = self.position_landmarks(profile)
        
        if start_landmark not in landmarks or end_landmark not in landmarks:
            return 0.0, []
        
        start = landmarks[start_landmark]
        end = landmarks[end_landmark]
        
        distance = start.distance_to(end)
        
        return distance, [start_landmark, end_landmark]