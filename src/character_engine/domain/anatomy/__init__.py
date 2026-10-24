"""Anatomical reconstruction domain package.

This package contains the foundational modules for deterministic anatomical
reconstruction in the Character Engine.
"""

from .coordinate_system import (
    CANONICAL_COORDINATE_SYSTEM,
    CANONICAL_TOLERANCE,
    UNIT_CONVERTER,
    AngularUnit,
    Axis,
    CoordinateSystem,
    Handedness,
    LateralSide,
    LinearUnit,
    Tolerance,
    UnitConverter,
)
from .feet import (
    FootBone,
    FootBoneType,
    FootModel,
    FootModelBuilder,
    ToeRay,
    create_measured_foot_bone,
    create_unknown_foot_bone,
)
from .hands import (
    FingerRay,
    HandBone,
    HandBoneType,
    HandModel,
    HandModelBuilder,
    create_measured_hand_bone,
    create_unknown_hand_bone,
)
from .joints import (
    JointCenter,
    JointCenterSet,
    JointCenterSetBuilder,
    JointCenterType,
    JointType,
    create_bilateral_joint_center_pair,
    create_measured_joint_center,
    create_unknown_joint_center,
)
from .landmarks import (
    CoordinateSpace,
    Landmark,
    LandmarkRegion,
    LandmarkSet,
    LandmarkSetBuilder,
    create_bilateral_landmark_pair,
    create_measured_landmark,
    create_midline_landmark,
    create_unknown_landmark,
)
from .parameters import (
    AnatomicalParameter,
    DerivationMetadata,
    ParameterConstraint,
    ParameterSet,
    ParameterSetBuilder,
    ParameterStatus,
    ParameterType,
    create_assumed_parameter,
    create_derived_parameter,
    create_direct_reference_parameter,
    create_unknown_parameter,
)
from .proportions import (
    DerivedDimension,
    ProportionCalculator,
    ProportionFormula,
    ProportionSystem,
    calculate_ratio_value,
    calculate_simple_proportion,
    create_proportion_calculator,
)

# NOTE: the reconstruction package has its own ProportionCalculator (operates on
# normalized parameters). It is exported under an explicit alias so it does not
# shadow `proportions.ProportionCalculator` (classical proportion systems).
from .reconstruction import (
    BoneGenerationMethod,
    BoneGenerator,
    BoneGeometry,
    CalculatedProportion,
    CalculationMethod,
    IntegrationConfig,
    LandmarkPosition,
    LandmarkPositioner,
    NormalizationMethod,
    NormalizedParameter,
    ParameterNormalizer,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    PositioningMethod,
    ReconstructionIntegrationAdapter,
    ReconstructionPipeline,
)
from .reconstruction import ProportionCalculator as ReconstructionProportionCalculator
from .reference import (
    UNKNOWN_SOURCE,
    Confidence,
    ReferenceData,
    ReferenceDataManager,
    ReferenceDataset,
    ReferenceDatasetBuilder,
    ReferenceRegistry,
    ReferenceSource,
    ReferenceSourceEntry,
    ReferenceValue,
    SourceType,
    create_assumed_value,
    create_unknown_value,
)
from .reference import ReferenceData as RefData
from .spine import (
    CurvatureParameter,
    CurvatureType,
    SpineModel,
    SpineModelBuilder,
    SpineRegion,
    VertebralParameter,
    create_measured_curvature,
    create_measured_vertebra,
    create_unknown_curvature,
    create_unknown_vertebra,
)
from .validation import (
    AnatomicalValidationReport,
    AnatomicalValidationReportBuilder,
    AnatomicalValidationResult,
    AnatomicalValidationStatus,
    AnatomicalValidator,
    create_anatomical_validator,
    create_fail_result,
    create_pass_result,
    create_unknown_result,
    create_warning_result,
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
    "ReconstructionProportionCalculator",
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

    # Reference (full name in addition to the RefData alias above)
    "ReferenceData",
]
