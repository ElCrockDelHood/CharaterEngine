"""Proportion calculator for anatomical reconstruction.

This module calculates anatomical proportions from normalized parameters,
converting height-based ratios to absolute measurements and applying
proportion relationships.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from ..reference import ReferenceDataManager, ReferenceData
from ..parameters import SubjectProfile
from .parameter_normalizer import NormalizedParameter, ParameterNormalizer


class CalculationMethod(Enum):
    """Methods for proportion calculation."""
    RATIO_DERIVATION = "ratio_derivation"
    REFERENCE_BASED = "reference_based"
    INTERPOLATION = "interpolation"
    FORMULA_BASED = "formula_based"


@dataclass
class CalculatedProportion:
    """Calculated anatomical proportion with provenance."""
    
    name: str
    value: float
    unit: str
    confidence: str
    provenance: str
    calculation_method: CalculationMethod
    input_parameters: Dict[str, float]
    formula: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProportionCalculator:
    """Calculates anatomical proportions from normalized parameters."""
    
    def __init__(self, reference_manager: ReferenceDataManager,
                 normalizer: ParameterNormalizer):
        """Initialize proportion calculator.
        
        Args:
            reference_manager: Reference data manager
            normalizer: Parameter normalizer
        """
        self.reference_manager = reference_manager
        self.normalizer = normalizer
        self.cache: Dict[str, CalculatedProportion] = {}
    
    def calculate_proportions(self, profile: SubjectProfile) -> Dict[str, CalculatedProportion]:
        """Calculate all anatomical proportions for a subject profile.
        
        Args:
            profile: Subject profile
            
        Returns:
            Dictionary of calculated proportions by name
        """
        proportions = {}
        
        # Normalize parameters first
        normalized = self.normalizer.normalize_profile(profile)
        
        # Calculate body segment proportions
        proportions.update(self._calculate_body_segments(normalized))
        
        # Calculate joint positions
        proportions.update(self._calculate_joint_positions(normalized))
        
        # Calculate bone dimensions
        proportions.update(self._calculate_bone_dimensions(normalized))
        
        return proportions
    
    def _calculate_body_segments(self, normalized: Dict[str, NormalizedParameter]) -> Dict[str, CalculatedProportion]:
        """Calculate body segment proportions.
        
        Args:
            normalized: Normalized parameters
            
        Returns:
            Dictionary of body segment proportions
        """
        proportions = {}
        
        # Get height
        height = self._get_parameter_value(normalized, 'height')
        
        # Calculate body segments from proportions
        segments = {
            'head_height': ('head_height_ratio', 'head'),
            'neck_height': ('neck_height_ratio', 'neck'),
            'upper_body_height': ('upper_body_ratio', 'upper_body'),
            'lower_body_height': ('lower_body_ratio', 'lower_body'),
            'shoulder_width': ('shoulder_width_ratio', 'shoulder_width'),
            'hip_width': ('hip_width_ratio', 'hip_width'),
            'upper_arm_length': ('upper_arm_ratio', 'upper_arm'),
            'forearm_length': ('forearm_ratio', 'forearm'),
            'hand_length': ('hand_ratio', 'hand'),
            'thigh_length': ('thigh_ratio', 'thigh'),
            'lower_leg_length': ('lower_leg_ratio', 'lower_leg'),
            'foot_length': ('foot_ratio', 'foot')
        }
        
        for segment_name, (ratio_name, segment_key) in segments.items():
            if ratio_name in normalized:
                ratio_param = normalized[ratio_name]
                value = ratio_param.value
                
                proportions[segment_name] = CalculatedProportion(
                    name=segment_name,
                    value=value,
                    unit='meters',
                    confidence=ratio_param.confidence,
                    provenance=ratio_param.provenance,
                    calculation_method=CalculationMethod.RATIO_DERIVATION,
                    input_parameters={'height': height, 'ratio': ratio_param.value},
                    formula=f"{segment_name} = height * {ratio_name}",
                    metadata={
                        'height': height,
                        'ratio': ratio_param.value,
                        'source': 'body_segment_calculation'
                    }
                )
        
        return proportions
    
    def _calculate_joint_positions(self, normalized: Dict[str, NormalizedParameter]) -> Dict[str, CalculatedProportion]:
        """Calculate joint position proportions.
        
        Args:
            normalized: Normalized parameters
            
        Returns:
            Dictionary of joint position proportions
        """
        proportions = {}
        
        # Get height
        height = self._get_parameter_value(normalized, 'height')
        
        # Calculate joint heights from ratios
        joint_heights = {
            'shoulder_joint_height': ('shoulder_joint_height_ratio', 'shoulder'),
            'elbow_joint_height': ('elbow_joint_height_ratio', 'elbow'),
            'wrist_joint_height': ('wrist_joint_height_ratio', 'wrist'),
            'hip_joint_height': ('hip_joint_height_ratio', 'hip'),
            'knee_joint_height': ('knee_joint_height_ratio', 'knee'),
            'ankle_joint_height': ('ankle_joint_height_ratio', 'ankle')
        }
        
        for joint_name, (ratio_name, joint_key) in joint_heights.items():
            if ratio_name in normalized:
                ratio_param = normalized[ratio_name]
                value = ratio_param.value
                
                proportions[joint_name] = CalculatedProportion(
                    name=joint_name,
                    value=value,
                    unit='meters',
                    confidence=ratio_param.confidence,
                    provenance=ratio_param.provenance,
                    calculation_method=CalculationMethod.RATIO_DERIVATION,
                    input_parameters={'height': height, 'ratio': ratio_param.value},
                    formula=f"{joint_name} = height * {ratio_name}",
                    metadata={
                        'height': height,
                        'ratio': ratio_param.value,
                        'source': 'joint_position_calculation'
                    }
                )
        
        return proportions
    
    def _calculate_bone_dimensions(self, normalized: Dict[str, NormalizedParameter]) -> Dict[str, CalculatedProportion]:
        """Calculate bone dimensions from segment proportions.
        
        Args:
            normalized: Normalized parameters
            
        Returns:
            Dictionary of bone dimension proportions
        """
        proportions = {}
        
        # Calculate individual bone dimensions from segment lengths
        # This is simplified - in production would use more detailed reference data
        
        # Upper limb bones
        if 'upper_arm_length' in normalized:
            humerus_length = normalized['upper_arm_length'].value * 0.95  # Humerus is ~95% of upper arm
            proportions['humerus_length'] = CalculatedProportion(
                name='humerus_length',
                value=humerus_length,
                unit='meters',
                confidence='LOW',
                provenance='DERIVED',
                calculation_method=CalculationMethod.FORMULA_BASED,
                input_parameters={'upper_arm_length': normalized['upper_arm_length'].value},
                formula='humerus_length = upper_arm_length * 0.95',
                metadata={'source': 'bone_dimension_derivation'}
            )
        
        if 'forearm_length' in normalized:
            radius_length = normalized['forearm_length'].value * 0.52  # Radius is ~52% of forearm
            ulna_length = normalized['forearm_length'].value * 0.48  # Ulna is ~48% of forearm
            
            proportions['radius_length'] = CalculatedProportion(
                name='radius_length',
                value=radius_length,
                unit='meters',
                confidence='LOW',
                provenance='DERIVED',
                calculation_method=CalculationMethod.FORMULA_BASED,
                input_parameters={'forearm_length': normalized['forearm_length'].value},
                formula='radius_length = forearm_length * 0.52',
                metadata={'source': 'bone_dimension_derivation'}
            )
            
            proportions['ulna_length'] = CalculatedProportion(
                name='ulna_length',
                value=ulna_length,
                unit='meters',
                confidence='LOW',
                provenance='DERIVED',
                calculation_method=CalculationMethod.FORMULA_BASED,
                input_parameters={'forearm_length': normalized['forearm_length'].value},
                formula='ulna_length = forearm_length * 0.48',
                metadata={'source': 'bone_dimension_derivation'}
            )
        
        # Lower limb bones
        if 'thigh_length' in normalized:
            femur_length = normalized['thigh_length'].value * 0.98  # Femur is ~98% of thigh
            proportions['femur_length'] = CalculatedProportion(
                name='femur_length',
                value=femur_length,
                unit='meters',
                confidence='LOW',
                provenance='DERIVED',
                calculation_method=CalculationMethod.FORMULA_BASED,
                input_parameters={'thigh_length': normalized['thigh_length'].value},
                formula='femur_length = thigh_length * 0.98',
                metadata={'source': 'bone_dimension_derivation'}
            )
        
        if 'lower_leg_length' in normalized:
            tibia_length = normalized['lower_leg_length'].value * 0.94  # Tibia is ~94% of lower leg
            fibula_length = normalized['lower_leg_length'].value * 0.91  # Fibula is ~91% of lower leg
            
            proportions['tibia_length'] = CalculatedProportion(
                name='tibia_length',
                value=tibia_length,
                unit='meters',
                confidence='LOW',
                provenance='DERIVED',
                calculation_method=CalculationMethod.FORMULA_BASED,
                input_parameters={'lower_leg_length': normalized['lower_leg_length'].value},
                formula='tibia_length = lower_leg_length * 0.94',
                metadata={'source': 'bone_dimension_derivation'}
            )
            
            proportions['fibula_length'] = CalculatedProportion(
                name='fibula_length',
                value=fibula_length,
                unit='meters',
                confidence='LOW',
                provenance='DERIVED',
                calculation_method=CalculationMethod.FORMULA_BASED,
                input_parameters={'lower_leg_length': normalized['lower_leg_length'].value},
                formula='fibula_length = lower_leg_length * 0.91',
                metadata={'source': 'bone_dimension_derivation'}
            )
        
        return proportions
    
    def calculate_limb_proportions(self, profile: SubjectProfile) -> Dict[str, CalculatedProportion]:
        """Calculate limb-specific proportions.
        
        Args:
            profile: Subject profile
            
        Returns:
            Dictionary of limb proportions
        """
        proportions = {}
        normalized = self.normalizer.normalize_profile(profile)
        
        # Upper arm to forearm ratio
        if 'upper_arm_length' in normalized and 'forearm_length' in normalized:
            upper_arm = normalized['upper_arm_length'].value
            forearm = normalized['forearm_length'].value
            ratio = upper_arm / forearm if forearm > 0 else 0.0
            
            proportions['upper_arm_to_forearm_ratio'] = CalculatedProportion(
                name='upper_arm_to_forearm_ratio',
                value=ratio,
                unit='ratio',
                confidence='LOW',
                provenance='DERIVED',
                calculation_method=CalculationMethod.FORMULA_BASED,
                input_parameters={'upper_arm_length': upper_arm, 'forearm_length': forearm},
                formula='upper_arm_to_forearm_ratio = upper_arm_length / forearm_length',
                metadata={'source': 'limb_proportion_calculation'}
            )
        
        # Thigh to lower leg ratio
        if 'thigh_length' in normalized and 'lower_leg_length' in normalized:
            thigh = normalized['thigh_length'].value
            lower_leg = normalized['lower_leg_length'].value
            ratio = thigh / lower_leg if lower_leg > 0 else 0.0
            
            proportions['thigh_to_lower_leg_ratio'] = CalculatedProportion(
                name='thigh_to_lower_leg_ratio',
                value=ratio,
                unit='ratio',
                confidence='LOW',
                provenance='DERIVED',
                calculation_method=CalculationMethod.FORMULA_BASED,
                input_parameters={'thigh_length': thigh, 'lower_leg_length': lower_leg},
                formula='thigh_to_lower_leg_ratio = thigh_length / lower_leg_length',
                metadata={'source': 'limb_proportion_calculation'}
            )
        
        return proportions
    
    def calculate_coordinate_positions(self, profile: SubjectProfile) -> Dict[str, Tuple[float, float, float]]:
        """Calculate 3D coordinate positions for landmarks.
        
        Args:
            profile: Subject profile
            
        Returns:
            Dictionary of landmark coordinates by name
        """
        coordinates = {}
        proportions = self.calculate_proportions(profile)
        
        # Calculate landmark positions based on proportions
        # This is simplified - would use more sophisticated methods in production
        
        # Origin at foot midline (0, 0, 0)
        origin = (0.0, 0.0, 0.0)
        
        # Calculate key landmark positions
        if 'ankle_joint_height' in proportions:
            ankle_z = proportions['ankle_joint_height'].value
            coordinates['ankle_center'] = (0.0, 0.0, ankle_z)
        
        if 'knee_joint_height' in proportions:
            knee_z = proportions['knee_joint_height'].value
            coordinates['knee_center'] = (0.0, 0.0, knee_z)
        
        if 'hip_joint_height' in proportions:
            hip_z = proportions['hip_joint_height'].value
            coordinates['hip_center'] = (0.0, 0.0, hip_z)
        
        if 'shoulder_joint_height' in proportions:
            shoulder_z = proportions['shoulder_joint_height'].value
            coordinates['shoulder_center'] = (0.0, 0.0, shoulder_z)
        
        if 'head_height' in proportions:
            head_z = proportions['head_height'].value
            coordinates['head_top'] = (0.0, 0.0, head_z)
        
        return coordinates
    
    def _get_parameter_value(self, normalized: Dict[str, NormalizedParameter], 
                           name: str) -> float:
        """Get value from normalized parameters.
        
        Args:
            normalized: Normalized parameters
            name: Parameter name
            
        Returns:
            Parameter value
        """
        if name in normalized:
            return normalized[name].value
        return 0.0