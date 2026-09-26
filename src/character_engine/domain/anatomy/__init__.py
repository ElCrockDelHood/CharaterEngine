"""Anatomical reconstruction domain package.

This package contains the foundational modules for deterministic anatomical
reconstruction in the Character Engine.
"""

from .coordinate_system import (
    CoordinateSystem,
    Handedness,
    Axis,
    LinearUnit,
    AngularUnit,
    LateralSide,
    Tolerance,
    UnitConverter,
    CANONICAL_COORDINATE_SYSTEM,
    CANONICAL_TOLERANCE,
    UNIT_CONVERTER
)

from .reference import (
    ReferenceSource,
    ReferenceValue,
    ReferenceDataset,
    ReferenceDatasetBuilder,
    SourceType,
    Confidence,
    UNKNOWN_SOURCE,
    create_unknown_value,
    create_assumed_value,
    ReferenceSourceEntry,
    ReferenceData as RefData,
    ReferenceRegistry,
    ReferenceDataManager
)

from .parameters import (
    ParameterStatus,
    ParameterType,
    ParameterConstraint,
    DerivationMetadata,
    AnatomicalParameter,
    ParameterSet,
    ParameterSetBuilder,
    create_unknown_parameter,
    create_assumed_parameter,
    create_derived_parameter,
    create_direct_reference_parameter
)

from .landmarks import (
    LandmarkRegion,
    CoordinateSpace,
    Landmark,
    LandmarkSet,
    LandmarkSetBuilder,
    create_unknown_landmark,
    create_measured_landmark,
    create_midline_landmark,
    create_bilateral_landmark_pair
)

from .proportions import (
    ProportionSystem,
    ProportionFormula,
    DerivedDimension,
    ProportionCalculator,
    create_proportion_calculator,
    calculate_simple_proportion,
    calculate_ratio_value
)

from .joints import (
    JointType,
    JointCenterType,
    JointCenter,
    JointCenterSet,
    JointCenterSetBuilder,
    create_unknown_joint_center,
    create_measured_joint_center,
    create_bilateral_joint_center_pair
)

from .spine import (
    SpineRegion,
    CurvatureType,
    VertebralParameter,
    CurvatureParameter,
    SpineModel,
    SpineModelBuilder,
    create_unknown_vertebra,
    create_measured_vertebra,
    create_unknown_curvature,
    create_measured_curvature
)

from .hands import (
    HandBoneType,
    FingerRay,
    HandBone,
    HandModel,
    HandModelBuilder,
    create_unknown_hand_bone,
    create_measured_hand_bone
)

from .feet import (
    FootBoneType,
    ToeRay,
    FootBone,
    FootModel,
    FootModelBuilder,
    create_unknown_foot_bone,
    create_measured_foot_bone
)

from .validation import (
    AnatomicalValidationStatus,
    AnatomicalValidationResult,
    AnatomicalValidationReport,
    AnatomicalValidationReportBuilder,
    create_pass_result,
    create_fail_result,
    create_warning_result,
    create_unknown_result,
    AnatomicalValidator,
    create_anatomical_validator
)

from .reconstruction import (
    ParameterNormalizer,
    NormalizedParameter,
    NormalizationMethod,
    ProportionCalculator,
    CalculatedProportion,
    CalculationMethod,
    LandmarkPositioner,
    LandmarkPosition,
    PositioningMethod,
    BoneGenerator,
    BoneGeometry,
    BoneGenerationMethod,
    ReconstructionPipeline,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    ReconstructionIntegrationAdapter,
    IntegrationConfig
)

from .reference import (
    ReferenceSourceEntry,
    ReferenceData,
    ReferenceRegistry,
    ReferenceDataManager
)

__all__ = [
    # Coordinate System
    "CoordinateSystem",
    "Handedness",
    "Axis",
    "LinearUnit",
    "AngularUnit",
    "LateralSide",
    "Tolerance",
    "UnitConverter",
    "CANONICAL_COORDINATE_SYSTEM",
    "CANONICAL_TOLERANCE",
    "UNIT_CONVERTER",
    
    # Reference Data
    "ReferenceSource",
    "ReferenceValue",
    "ReferenceDataset",
    "ReferenceDatasetBuilder",
    "SourceType",
    "Confidence",
    "UNKNOWN_SOURCE",
    "create_unknown_value",
    "create_assumed_value",
    "ReferenceSourceEntry",
    "RefData",
    "ReferenceRegistry",
    "ReferenceDataManager",
    
    # Parameters
    "ParameterStatus",
    "ParameterType",
    "ParameterConstraint",
    "DerivationMetadata",
    "AnatomicalParameter",
    "ParameterSet",
    "ParameterSetBuilder",
    "create_unknown_parameter",
    "create_assumed_parameter",
    "create_derived_parameter",
    "create_direct_reference_parameter",
    
    # Landmarks
    "LandmarkRegion",
    "CoordinateSpace",
    "Landmark",
    "LandmarkSet",
    "LandmarkSetBuilder",
    "create_unknown_landmark",
    "create_measured_landmark",
    "create_midline_landmark",
    "create_bilateral_landmark_pair",
    
    # Proportions
    "ProportionSystem",
    "ProportionFormula",
    "DerivedDimension",
    "ProportionCalculator",
    "create_proportion_calculator",
    "calculate_simple_proportion",
    "calculate_ratio_value",
    
    # Joint Centers
    "JointType",
    "JointCenterType",
    "JointCenter",
    "JointCenterSet",
    "JointCenterSetBuilder",
    "create_unknown_joint_center",
    "create_measured_joint_center",
    "create_bilateral_joint_center_pair",
    
    # Spine
    "SpineRegion",
    "CurvatureType",
    "VertebralParameter",
    "CurvatureParameter",
    "SpineModel",
    "SpineModelBuilder",
    "create_unknown_vertebra",
    "create_measured_vertebra",
    "create_unknown_curvature",
    "create_measured_curvature",
    
    # Hands
    "HandBoneType",
    "FingerRay",
    "HandBone",
    "HandModel",
    "HandModelBuilder",
    "create_unknown_hand_bone",
    "create_measured_hand_bone",
    
    # Feet
    "FootBoneType",
    "ToeRay",
    "FootBone",
    "FootModel",
    "FootModelBuilder",
    "create_unknown_foot_bone",
    "create_measured_foot_bone",
    
    # Validation
    "AnatomicalValidationStatus",
    "AnatomicalValidationResult",
    "AnatomicalValidationReport",
    "AnatomicalValidationReportBuilder",
    "create_pass_result",
    "create_fail_result",
    "create_warning_result",
    "create_unknown_result",
    "AnatomicalValidator",
    "create_anatomical_validator",
    
    # Reconstruction
    "ParameterNormalizer",
    "NormalizedParameter",
    "NormalizationMethod",
    "ProportionCalculator",
    "CalculatedProportion",
    "CalculationMethod",
    "LandmarkPositioner",
    "LandmarkPosition",
    "PositioningMethod",
    "BoneGenerator",
    "BoneGeometry",
    "BoneGenerationMethod",
    "ReconstructionPipeline",
    "PipelineResult",
    "PipelineStage",
    "PipelineStatus",
    "ReconstructionIntegrationAdapter",
    "IntegrationConfig",
    
    # Reference
    "ReferenceSourceEntry",
    "ReferenceData",
    "ReferenceRegistry",
    "ReferenceDataManager"
]
