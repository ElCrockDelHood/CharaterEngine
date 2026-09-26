"""Bone generator for anatomical reconstruction.

This module generates bone geometries based on anatomical parameters,
landmark positions, and reference data.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum
import math

from ..coordinate_system import CoordinateSystem, LateralSide
from ..reference import ReferenceDataManager
from .parameter_normalizer import ParameterNormalizer, NormalizedParameter
from .proportion_calculator import ProportionCalculator, CalculatedProportion
from .landmark_positioner import LandmarkPositioner, LandmarkPosition


class BoneGenerationMethod(Enum):
    """Methods for bone generation."""
    PARAMETER_BASED = "parameter_based"  # Based on anatomical parameters
    LANDMARK_BASED = "landmark_based"  # Based on landmark positions
    REFERENCE_BASED = "reference_based"  # Based on reference templates
    PROPORTIONAL = "proportional"  # Proportional scaling of reference bones


@dataclass
class BoneGeometry:
    """Geometric representation of a bone.
    
    Attributes:
        name: Bone name
        canonical_name: Canonical bone name
        bone_type: Type of bone (long, short, flat, irregular)
        length: Bone length
        diameter: Bone diameter
        start_position: 3D start position (proximal end)
        end_position: 3D end position (distal end)
        orientation: Bone orientation vector
        unit: Unit of measurement (typically meters)
        confidence: Confidence in geometry accuracy
        provenance: Source of geometry data
        generation_method: Method used to generate geometry
        bilateral: Whether bone is bilateral (left/right)
        side: Lateral side if bilateral
        metadata: Additional metadata
    """
    
    name: str
    canonical_name: str
    bone_type: str
    length: float
    diameter: float
    start_position: tuple
    end_position: tuple
    orientation: tuple
    unit: str = "meters"
    confidence: str = "LOW"
    provenance: str = "DERIVED"
    generation_method: BoneGenerationMethod = BoneGenerationMethod.PARAMETER_BASED
    bilateral: bool = False
    side: Optional[LateralSide] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_midpoint(self) -> tuple:
        """Calculate the midpoint of the bone."""
        x = (self.start_position[0] + self.end_position[0]) / 2
        y = (self.start_position[1] + self.end_position[1]) / 2
        z = (self.start_position[2] + self.end_position[2]) / 2
        return (x, y, z)
    
    def get_volume(self) -> float:
        """Calculate approximate bone volume (simplified cylinder model)."""
        radius = self.diameter / 2.0
        return math.pi * radius * radius * self.length
    
    def get_surface_area(self) -> float:
        """Calculate approximate bone surface area (simplified cylinder model)."""
        radius = self.diameter / 2.0
        lateral_area = 2 * math.pi * radius * self.length
        end_area = 2 * math.pi * radius * radius
        return lateral_area + end_area


class BoneGenerator:
    """Generates bone geometries for anatomical reconstruction."""
    
    def __init__(self,
                 reference_manager: ReferenceDataManager,
                 normalizer: ParameterNormalizer,
                 calculator: ProportionCalculator,
                 positioner: LandmarkPositioner,
                 coordinate_system: CoordinateSystem):
        """Initialize bone generator.
        
        Args:
            reference_manager: Reference data manager
            normalizer: Parameter normalizer
            calculator: Proportion calculator
            positioner: Landmark positioner
            coordinate_system: Anatomical coordinate system
        """
        self.reference_manager = reference_manager
        self.normalizer = normalizer
        self.calculator = calculator
        self.positioner = positioner
        self.coordinate_system = coordinate_system
        self.cache: Dict[str, BoneGeometry] = {}
    
    def generate_skeleton(self, profile) -> Dict[str, BoneGeometry]:
        """Generate complete skeleton for a subject.
        
        Args:
            profile: Subject profile
            
        Returns:
            Dictionary of bone geometries by canonical name
        """
        # Get normalized parameters and proportions
        normalized = self.normalizer.normalize_profile(profile)
        proportions = self.calculator.calculate_proportions(profile)
        
        # Get landmark positions
        landmarks = self.positioner.position_landmarks(profile)
        
        bones = {}
        
        # Generate axial skeleton bones
        bones.update(self._generate_axial_skeleton(normalized, proportions, landmarks))
        
        # Generate appendicular skeleton bones
        bones.update(self._generate_appendicular_skeleton(normalized, proportions, landmarks))
        
        return bones
    
    def _generate_axial_skeleton(self,
                                 normalized: Dict[str, NormalizedParameter],
                                 proportions: Dict[str, CalculatedProportion],
                                 landmarks: Dict[str, LandmarkPosition]) -> Dict[str, BoneGeometry]:
        """Generate axial skeleton bones (spine, skull, ribs).
        
        Args:
            normalized: Normalized parameters
            proportions: Calculated proportions
            landmarks: Landmark positions
            
        Returns:
            Dictionary of axial bone geometries
        """
        bones = {}
        
        # Get height value
        height = normalized.get('height')
        if height is None:
            return bones
        
        h = height.value
        
        # Generate simplified spine (as a single bone for now)
        # In production, would generate individual vertebrae and intervertebral discs
        
        spine_length = h * 0.40  # Spine is ~40% of total height
        spine_diameter = h * 0.08  # Spine diameter (simplified)
        
        spine_start = (0.0, h * 0.10, 0.0)  # Sacrum area
        spine_end = (0.0, h * 0.50, 0.0)   # Cervical spine area
        
        spine = BoneGeometry(
            name="spine",
            canonical_name="spine",
            bone_type="irregular",
            length=spine_length,
            diameter=spine_diameter,
            start_position=spine_start,
            end_position=spine_end,
            orientation=(0.0, 1.0, 0.0),  # Vertical orientation
            unit="meters",
            confidence="LOW",
            provenance="DERIVED",
            generation_method=BoneGenerationMethod.PROPORTIONAL,
            metadata={"simplified": True, "height_ratio": 0.40}
        )
        bones["spine"] = spine
        
        # Generate simplified skull
        if 'head_height' in proportions:
            head_height = proportions['head_height'].value
            skull_diameter = head_height * 0.75  # Skull diameter (simplified)
            
            skull_start = (0.0, h * 0.50, 0.0)  # Base of skull
            skull_end = (0.0, h, 0.0)           # Top of skull
            
            skull = BoneGeometry(
                name="skull",
                canonical_name="skull",
                bone_type="irregular",
                length=head_height,
                diameter=skull_diameter,
                start_position=skull_start,
                end_position=skull_end,
                orientation=(0.0, 1.0, 0.0),
                unit="meters",
                confidence="LOW",
                provenance="DERIVED",
                generation_method=BoneGenerationMethod.PROPORTIONAL,
                metadata={"simplified": True}
            )
            bones["skull"] = skull
        
        return bones
    
    def _generate_appendicular_skeleton(self,
                                        normalized: Dict[str, NormalizedParameter],
                                        proportions: Dict[str, CalculatedProportion],
                                        landmarks: Dict[str, LandmarkPosition]) -> Dict[str, BoneGeometry]:
        """Generate appendicular skeleton bones (limbs).
        
        Args:
            normalized: Normalized parameters
            proportions: Calculated proportions
            landmarks: Landmark positions
            
        Returns:
            Dictionary of appendicular bone geometries
        """
        bones = {}
        
        # Get height value
        height = normalized.get('height')
        if height is None:
            return bones
        
        h = height.value
        
        # Generate simplified femur (thigh bone)
        femur_length = h * 0.25  # Femur is ~25% of height
        femur_diameter = femur_length * 0.15  # Diameter proportional to length
        
        if 'hip_joint_center' in landmarks and 'knee_joint_center' in landmarks:
            hip = landmarks['hip_joint_center']
            knee = landmarks['knee_joint_center']
            
            femur = BoneGeometry(
                name="femur",
                canonical_name="femur",
                bone_type="long",
                length=femur_length,
                diameter=femur_diameter,
                start_position=hip.position,
                end_position=knee.position,
                orientation=(0.0, -1.0, 0.0),  # Points downward
                unit="meters",
                confidence="LOW",
                provenance="DERIVED",
                generation_method=BoneGenerationMethod.LANDMARK_BASED,
                bilateral=True,
                side=None,  # Central for now
                metadata={"height_ratio": 0.25}
            )
            bones["femur"] = femur
        
        # Generate simplified humerus (upper arm bone)
        humerus_length = h * 0.18  # Humerus is ~18% of height
        humerus_diameter = humerus_length * 0.12
        
        if 'shoulder_joint_center' in landmarks:
            shoulder = landmarks['shoulder_joint_center']
            # Elbow would be at approximately 70% of shoulder height
            elbow_height = shoulder.get_y() - humerus_length
            elbow_position = (shoulder.get_x(), elbow_height, shoulder.get_z())
            
            humerus = BoneGeometry(
                name="humerus",
                canonical_name="humerus",
                bone_type="long",
                length=humerus_length,
                diameter=humerus_diameter,
                start_position=shoulder.position,
                end_position=elbow_position,
                orientation=(0.0, -1.0, 0.0),
                unit="meters",
                confidence="LOW",
                provenance="DERIVED",
                generation_method=BoneGenerationMethod.LANDMARK_BASED,
                bilateral=True,
                side=None,  # Central for now
                metadata={"height_ratio": 0.18}
            )
            bones["humerus"] = humerus
        
        return bones
    
    def generate_bone(self, canonical_name: str, profile) -> Optional[BoneGeometry]:
        """Generate a specific bone geometry.
        
        Args:
            canonical_name: Canonical bone name
            profile: Subject profile
            
        Returns:
            Bone geometry if found, None otherwise
        """
        # Check cache first
        cache_key = f"{canonical_name}_{profile.height}_{profile.gender}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Generate all bones
        bones = self.generate_skeleton(profile)
        
        # Get specific bone
        bone = bones.get(canonical_name)
        
        # Cache result
        if bone:
            self.cache[cache_key] = bone
        
        return bone
    
    def calculate_bone_proportions(self, profile) -> Dict[str, float]:
        """Calculate bone proportions relative to total height.
        
        Args:
            profile: Subject profile
            
        Returns:
            Dictionary of bone proportions (bone_length / total_height)
        """
        bones = self.generate_skeleton(profile)
        proportions = {}
        
        height = profile.height if profile.height else 1.75  # Default height
        
        for bone_name, bone in bones.items():
            proportion = bone.length / height
            proportions[bone_name] = proportion
        
        return proportions