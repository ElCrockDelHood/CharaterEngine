"""Parameter normalizer for anatomical reconstruction.

This module normalizes raw anatomical parameters to standard reference values,
applying gender-specific, age-specific, and height-based adjustments.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

from ..reference import ReferenceDataManager, ReferenceData, Confidence
from ..parameters import SubjectProfile, AnatomicalParameter, ParameterType


class NormalizationMethod(Enum):
    """Methods for parameter normalization."""
    HEIGHT_BASED = "height_based"
    GENDER_ADJUSTED = "gender_adjusted"
    AGE_ADJUSTED = "age_adjusted"
    POPULATION_ADJUSTED = "population_adjusted"
    DIRECT = "direct"


@dataclass
class NormalizedParameter:
    """Normalized anatomical parameter with provenance."""
    
    name: str
    value: float
    unit: str
    confidence: str
    provenance: str
    normalization_method: NormalizationMethod
    original_value: Optional[float] = None
    adjustment_factor: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ParameterNormalizer:
    """Normalizes anatomical parameters based on reference data."""
    
    def __init__(self, reference_manager: ReferenceDataManager):
        """Initialize parameter normalizer.
        
        Args:
            reference_manager: Reference data manager
        """
        self.reference_manager = reference_manager
        self.cache: Dict[str, NormalizedParameter] = {}
    
    def normalize_profile(self, profile: SubjectProfile) -> Dict[str, NormalizedParameter]:
        """Normalize all parameters in a subject profile.
        
        Args:
            profile: Subject profile with raw parameters
            
        Returns:
            Dictionary of normalized parameters by name
        """
        normalized = {}
        
        # Normalize global parameters
        normalized.update(self._normalize_global_parameters(profile))
        
        # Normalize body proportions
        normalized.update(self._normalize_body_proportions(profile))
        
        # Normalize joint positions
        normalized.update(self._normalize_joint_positions(profile))
        
        return normalized
    
    def _normalize_global_parameters(self, profile: SubjectProfile) -> Dict[str, NormalizedParameter]:
        """Normalize global subject parameters.
        
        Args:
            profile: Subject profile
            
        Returns:
            Dictionary of normalized global parameters
        """
        normalized = {}
        
        # Height - keep as-is if provided, otherwise use reference
        if profile.height is not None:
            height = profile.height
            method = NormalizationMethod.DIRECT
            provenance = "USER_INPUT"
        else:
            try:
                height_ref = self.reference_manager.get_anthropometric_parameter('height')
                height = height_ref.value
                method = NormalizationMethod.HEIGHT_BASED
                provenance = height_ref.provenance
            except ValueError:
                # Fallback to default
                height = 1.75
                method = NormalizationMethod.DIRECT
                provenance = "DEFAULT"
        
        normalized['height'] = NormalizedParameter(
            name='height',
            value=height,
            unit='meters',
            confidence='MEDIUM',
            provenance=provenance,
            normalization_method=method,
            metadata={'source': 'global_normalization'}
        )
        
        # Normalize weight if provided
        if profile.weight is not None:
            normalized['weight'] = NormalizedParameter(
                name='weight',
                value=profile.weight,
                unit='kg',
                confidence='MEDIUM',
                provenance='USER_INPUT',
                normalization_method=NormalizationMethod.DIRECT,
                metadata={'source': 'global_normalization'}
            )
        
        # Apply gender adjustments if gender is specified
        if profile.gender is not None:
            normalized.update(self._apply_gender_adjustments(profile.gender, normalized))
        
        # Apply age adjustments if age is specified
        if profile.age is not None:
            normalized.update(self._apply_age_adjustments(profile.age, normalized))
        
        return normalized
    
    def _normalize_body_proportions(self, profile: SubjectProfile) -> Dict[str, NormalizedParameter]:
        """Normalize body proportion parameters.
        
        Args:
            profile: Subject profile
            
        Returns:
            Dictionary of normalized proportion parameters
        """
        normalized = {}
        height = self._get_height_value(profile)
        
        # Standard proportions to normalize
        proportions = [
            'head_height_ratio',
            'shoulder_width_ratio',
            'hip_width_ratio',
            'upper_arm_ratio',
            'forearm_ratio',
            'hand_ratio',
            'thigh_ratio',
            'lower_leg_ratio',
            'foot_ratio'
        ]
        
        for prop_name in proportions:
            try:
                ref_data = self.reference_manager.get_anthropometric_parameter(prop_name)
                ratio = ref_data.value
                
                # Calculate absolute value from height
                absolute_value = height * ratio
                
                normalized[prop_name] = NormalizedParameter(
                    name=prop_name,
                    value=absolute_value,
                    unit='meters',
                    confidence=ref_data.confidence,
                    provenance=ref_data.provenance,
                    normalization_method=NormalizationMethod.HEIGHT_BASED,
                    adjustment_factor=ratio,
                    metadata={
                        'ratio': ratio,
                        'height': height,
                        'source': 'proportion_normalization'
                    }
                )
            except ValueError:
                # Skip if parameter not found
                continue
        
        return normalized
    
    def _normalize_joint_positions(self, profile: SubjectProfile) -> Dict[str, NormalizedParameter]:
        """Normalize joint position parameters.
        
        Args:
            profile: Subject profile
            
        Returns:
            Dictionary of normalized joint position parameters
        """
        normalized = {}
        height = self._get_height_value(profile)
        
        # Joint height ratios
        joint_ratios = [
            'shoulder_joint_height_ratio',
            'elbow_joint_height_ratio',
            'wrist_joint_height_ratio',
            'hip_joint_height_ratio',
            'knee_joint_height_ratio',
            'ankle_joint_height_ratio'
        ]
        
        for ratio_name in joint_ratios:
            try:
                ref_data = self.reference_manager.get_anthropometric_parameter(ratio_name)
                ratio = ref_data.value
                
                # Calculate absolute height from ratio
                absolute_height = height * ratio
                
                normalized[ratio_name] = NormalizedParameter(
                    name=ratio_name,
                    value=absolute_height,
                    unit='meters',
                    confidence=ref_data.confidence,
                    provenance=ref_data.provenance,
                    normalization_method=NormalizationMethod.HEIGHT_BASED,
                    adjustment_factor=ratio,
                    metadata={
                        'ratio': ratio,
                        'height': height,
                        'source': 'joint_position_normalization'
                    }
                )
            except ValueError:
                # Skip if parameter not found
                continue
        
        return normalized
    
    def _apply_gender_adjustments(self, gender: str, 
                                   normalized: Dict[str, NormalizedParameter]) -> Dict[str, NormalizedParameter]:
        """Apply gender-specific adjustments to normalized parameters.
        
        Args:
            gender: Gender (e.g., 'male', 'female')
            normalized: Already normalized parameters
            
        Returns:
            Dictionary of gender-adjusted parameters
        """
        adjusted = {}
        
        # Gender-specific adjustments to apply
        gender_adjustments = [
            'shoulder_to_hip_ratio',
            'head_to_body_ratio'
        ]
        
        for adj_name in gender_adjustments:
            try:
                ref_data = self.reference_manager.get_gender_adjustment(gender, adj_name)
                adjustment_factor = ref_data.value
                
                # Apply adjustment to relevant parameters
                if adj_name == 'shoulder_to_hip_ratio':
                    # Adjust shoulder width relative to hip width
                    if 'shoulder_width_ratio' in normalized:
                        shoulder = normalized['shoulder_width_ratio']
                        adjusted_shoulder = shoulder.value * adjustment_factor
                        adjusted['shoulder_width_ratio'] = NormalizedParameter(
                            name='shoulder_width_ratio',
                            value=adjusted_shoulder,
                            unit='meters',
                            confidence='LOW',
                            provenance='GENDER_ADJUSTED',
                            normalization_method=NormalizationMethod.GENDER_ADJUSTED,
                            original_value=shoulder.value,
                            adjustment_factor=adjustment_factor,
                            metadata={
                                'gender': gender,
                                'original': shoulder.metadata,
                                'source': 'gender_adjustment'
                            }
                        )
                
                elif adj_name == 'head_to_body_ratio':
                    # Adjust head height
                    if 'head_height_ratio' in normalized:
                        head = normalized['head_height_ratio']
                        adjusted_head = head.value * adjustment_factor
                        adjusted['head_height_ratio'] = NormalizedParameter(
                            name='head_height_ratio',
                            value=adjusted_head,
                            unit='meters',
                            confidence='LOW',
                            provenance='GENDER_ADJUSTED',
                            normalization_method=NormalizationMethod.GENDER_ADJUSTED,
                            original_value=head.value,
                            adjustment_factor=adjustment_factor,
                            metadata={
                                'gender': gender,
                                'original': head.metadata,
                                'source': 'gender_adjustment'
                            }
                        )
            except ValueError:
                # Skip if adjustment not found
                continue
        
        return adjusted
    
    def _apply_age_adjustments(self, age: int,
                              normalized: Dict[str, NormalizedParameter]) -> Dict[str, NormalizedParameter]:
        """Apply age-related adjustments to normalized parameters.
        
        Args:
            age: Subject age in years
            normalized: Already normalized parameters
            
        Returns:
            Dictionary of age-adjusted parameters
        """
        adjusted = {}
        
        # Simple age-based adjustments (placeholder logic)
        # In production, this would use age-specific reference data
        
        if age > 60:
            # Elderly: slight height reduction, increased kyphosis
            if 'height' in normalized:
                height = normalized['height']
                # Assume 1% height reduction per decade after 60
                reduction_factor = 1.0 - (0.01 * (age - 60) / 10)
                adjusted_height = height.value * max(0.95, reduction_factor)
                adjusted['height'] = NormalizedParameter(
                    name='height',
                    value=adjusted_height,
                    unit='meters',
                    confidence='LOW',
                    provenance='AGE_ADJUSTED',
                    normalization_method=NormalizationMethod.AGE_ADJUSTED,
                    original_value=height.value,
                    adjustment_factor=reduction_factor,
                    metadata={
                        'age': age,
                        'original': height.metadata,
                        'source': 'age_adjustment'
                    }
                )
        
        return adjusted
    
    def _get_height_value(self, profile: SubjectProfile) -> float:
        """Get height value from profile or reference.
        
        Args:
            profile: Subject profile
            
        Returns:
            Height in meters
        """
        if profile.height is not None:
            return profile.height
        
        try:
            height_ref = self.reference_manager.get_anthropometric_parameter('height')
            return height_ref.value
        except ValueError:
            return 1.75  # Default fallback
    
    def normalize_parameter(self, parameter: AnatomicalParameter,
                          profile: SubjectProfile) -> NormalizedParameter:
        """Normalize a single anatomical parameter.
        
        Args:
            parameter: Anatomical parameter to normalize
            profile: Subject profile for context
            
        Returns:
            Normalized parameter
        """
        # Check cache first
        cache_key = f"{parameter.name}_{profile.gender}_{profile.age}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Normalize based on parameter type
        if parameter.parameter_type == ParameterType.RATIO:
            # Ratio parameters use height-based normalization
            height = self._get_height_value(profile)
            value = height * parameter.value
            method = NormalizationMethod.HEIGHT_BASED
            # Convert unit from ratio to meters
            unit = 'meters'
        else:
            # Absolute parameters use direct normalization
            value = parameter.value
            method = NormalizationMethod.DIRECT
            unit = parameter.unit
        
        # Extract provenance from metadata or use default
        provenance = parameter.metadata.get('provenance', 'UNKNOWN')
        
        # Convert confidence string to enum if needed
        if isinstance(parameter.confidence, str):
            confidence = Confidence(parameter.confidence.upper())
        else:
            confidence = parameter.confidence
        
        normalized = NormalizedParameter(
            name=parameter.name,
            value=value,
            unit=unit,
            confidence=confidence,
            provenance=provenance,
            normalization_method=method,
            original_value=parameter.value,
            metadata={'parameter': parameter.metadata}
        )
        
        # Cache result
        self.cache[cache_key] = normalized
        
        return normalized