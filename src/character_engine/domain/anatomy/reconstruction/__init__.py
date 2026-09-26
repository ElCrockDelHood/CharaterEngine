"""Anatomical reconstruction infrastructure.

This module provides the foundational components for deterministic anatomical
reconstruction, including parameter normalization, proportion calculation,
and reference data management.
"""

from .parameter_normalizer import (
    ParameterNormalizer,
    NormalizedParameter,
    NormalizationMethod
)

from .proportion_calculator import (
    ProportionCalculator,
    CalculatedProportion,
    CalculationMethod
)

from .landmark_positioner import (
    LandmarkPositioner,
    LandmarkPosition,
    PositioningMethod
)

from .bone_generator import (
    BoneGenerator,
    BoneGeometry,
    BoneGenerationMethod
)

from .pipeline import (
    ReconstructionPipeline,
    PipelineResult,
    PipelineStage,
    PipelineStatus
)

from .integration import (
    ReconstructionIntegrationAdapter,
    IntegrationConfig
)

__all__ = [
    'ParameterNormalizer',
    'NormalizedParameter',
    'NormalizationMethod',
    'ProportionCalculator',
    'CalculatedProportion',
    'CalculationMethod',
    'LandmarkPositioner',
    'LandmarkPosition',
    'PositioningMethod',
    'BoneGenerator',
    'BoneGeometry',
    'BoneGenerationMethod',
    'ReconstructionPipeline',
    'PipelineResult',
    'PipelineStage',
    'PipelineStatus',
    'ReconstructionIntegrationAdapter',
    'IntegrationConfig'
]