"""Reconstruction pipeline orchestrator for anatomical reconstruction.

This module orchestrates the complete anatomical reconstruction pipeline,
coordinating parameter normalization, proportion calculation, landmark positioning,
and bone generation.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

from ..coordinate_system import CoordinateSystem
from ..parameters import SubjectProfile
from ..reference import ReferenceDataManager
from .bone_generator import BoneGenerator, BoneGeometry
from .landmark_positioner import LandmarkPosition, LandmarkPositioner
from .parameter_normalizer import NormalizedParameter, ParameterNormalizer
from .proportion_calculator import CalculatedProportion, ProportionCalculator


class PipelineStage(Enum):
    """Stages in the reconstruction pipeline."""
    INITIALIZATION = "initialization"
    PARAMETER_NORMALIZATION = "parameter_normalization"
    PROPORTION_CALCULATION = "proportion_calculation"
    LANDMARK_POSITIONING = "landmark_positioning"
    BONE_GENERATION = "bone_generation"
    VALIDATION = "validation"
    COMPLETION = "completion"


class PipelineStatus(Enum):
    """Status of the reconstruction pipeline."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


@dataclass
class PipelineResult:
    """Result of the reconstruction pipeline.

    Attributes:
        subject_profile: Subject profile used for reconstruction
        normalized_parameters: Normalized anatomical parameters
        calculated_proportions: Calculated body proportions
        landmark_positions: Positioned anatomical landmarks
        bone_geometries: Generated bone geometries
        status: Pipeline status
        stages_completed: List of completed stages
        errors: List of errors encountered
        warnings: List of warnings
        metadata: Additional metadata
        created_at: Creation timestamp
    """

    subject_profile: SubjectProfile
    normalized_parameters: Dict[str, NormalizedParameter]
    calculated_proportions: Dict[str, CalculatedProportion]
    landmark_positions: Dict[str, LandmarkPosition]
    bone_geometries: Dict[str, BoneGeometry]
    status: PipelineStatus
    stages_completed: List[PipelineStage]
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    created_at: date = field(default_factory=date.today)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def is_successful(self) -> bool:
        """Check if pipeline completed successfully."""
        return self.status == PipelineStatus.COMPLETED

    def has_errors(self) -> bool:
        """Check if pipeline encountered errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if pipeline has warnings."""
        return len(self.warnings) > 0

    def get_completion_percentage(self) -> float:
        """Calculate completion percentage based on stages."""
        total_stages = len(PipelineStage)
        completed_stages = len(self.stages_completed)
        return (completed_stages / total_stages) * 100.0


class ReconstructionPipeline:
    """Orchestrates the complete anatomical reconstruction pipeline."""

    def __init__(self, references_dir: Path, coordinate_system: CoordinateSystem):
        """Initialize reconstruction pipeline.

        Args:
            references_dir: Directory containing reference data
            coordinate_system: Anatomical coordinate system
        """
        self.references_dir = references_dir
        self.coordinate_system = coordinate_system

        # Initialize components
        self.reference_manager = ReferenceDataManager(references_dir)
        self.normalizer = ParameterNormalizer(self.reference_manager)
        self.calculator = ProportionCalculator(self.reference_manager, self.normalizer)
        self.positioner = LandmarkPositioner(
            self.reference_manager,
            self.normalizer,
            self.calculator,
            coordinate_system
        )
        self.bone_generator = BoneGenerator(
            self.reference_manager,
            self.normalizer,
            self.calculator,
            self.positioner,
            coordinate_system
        )

        # Pipeline state
        self.current_stage = PipelineStage.NOT_STARTED
        self.status = PipelineStatus.NOT_STARTED
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stages_completed: List[PipelineStage] = []

    def reconstruct(self, subject_profile: SubjectProfile) -> PipelineResult:
        """Execute complete reconstruction pipeline.

        Args:
            subject_profile: Subject profile for reconstruction

        Returns:
            Pipeline result with all reconstruction data
        """
        # Reset pipeline state
        self._reset_pipeline()

        try:
            # Stage 1: Parameter Normalization
            self.current_stage = PipelineStage.PARAMETER_NORMALIZATION
            normalized = self._normalize_parameters(subject_profile)
            self.stages_completed.append(PipelineStage.PARAMETER_NORMALIZATION)

            # Stage 2: Proportion Calculation
            self.current_stage = PipelineStage.PROPORTION_CALCULATION
            proportions = self._calculate_proportions(subject_profile)
            self.stages_completed.append(PipelineStage.PROPORTION_CALCULATION)

            # Stage 3: Landmark Positioning
            self.current_stage = PipelineStage.LANDMARK_POSITIONING
            landmarks = self._position_landmarks(subject_profile)
            self.stages_completed.append(PipelineStage.LANDMARK_POSITIONING)

            # Stage 4: Bone Generation
            self.current_stage = PipelineStage.BONE_GENERATION
            bones = self._generate_bones(subject_profile)
            self.stages_completed.append(PipelineStage.BONE_GENERATION)

            # Stage 5: Validation
            self.current_stage = PipelineStage.VALIDATION
            self._validate_reconstruction(normalized, proportions, landmarks, bones)
            self.stages_completed.append(PipelineStage.VALIDATION)

            # Mark as completed
            self.status = PipelineStatus.COMPLETED
            self.current_stage = PipelineStage.COMPLETION
            self.stages_completed.append(PipelineStage.COMPLETION)

        except Exception as e:
            self.status = PipelineStatus.FAILED
            self.errors.append(f"Pipeline failed at stage {self.current_stage}: {str(e)}")

        # Create result
        result = PipelineResult(
            subject_profile=subject_profile,
            normalized_parameters=normalized,
            calculated_proportions=proportions,
            landmark_positions=landmarks,
            bone_geometries=bones,
            status=self.status,
            stages_completed=self.stages_completed,
            errors=self.errors,
            warnings=self.warnings,
            metadata={
                "pipeline_version": "1.0.0",
                "coordinate_system": self.coordinate_system.__class__.__name__,
                "references_dir": str(self.references_dir)
            }
        )

        return result

    def _reset_pipeline(self):
        """Reset pipeline state for new reconstruction."""
        self.current_stage = PipelineStage.INITIALIZATION
        self.status = PipelineStatus.IN_PROGRESS
        self.errors = []
        self.warnings = []
        self.stages_completed = []

    def _normalize_parameters(self, subject_profile: SubjectProfile) -> Dict[str, NormalizedParameter]:
        """Normalize anatomical parameters.

        Args:
            subject_profile: Subject profile

        Returns:
            Dictionary of normalized parameters
        """
        try:
            return self.normalizer.normalize_profile(subject_profile)
        except Exception as e:
            self.errors.append(f"Parameter normalization failed: {str(e)}")
            return {}

    def _calculate_proportions(self, subject_profile: SubjectProfile) -> Dict[str, CalculatedProportion]:
        """Calculate body proportions.

        Args:
            subject_profile: Subject profile

        Returns:
            Dictionary of calculated proportions
        """
        try:
            return self.calculator.calculate_proportions(subject_profile)
        except Exception as e:
            self.errors.append(f"Proportion calculation failed: {str(e)}")
            return {}

    def _position_landmarks(self, subject_profile: SubjectProfile) -> Dict[str, LandmarkPosition]:
        """Position anatomical landmarks.

        Args:
            subject_profile: Subject profile

        Returns:
            Dictionary of landmark positions
        """
        try:
            return self.positioner.position_landmarks(subject_profile)
        except Exception as e:
            self.errors.append(f"Landmark positioning failed: {str(e)}")
            return {}

    def _generate_bones(self, subject_profile: SubjectProfile) -> Dict[str, BoneGeometry]:
        """Generate bone geometries.

        Args:
            subject_profile: Subject profile

        Returns:
            Dictionary of bone geometries
        """
        try:
            return self.bone_generator.generate_skeleton(subject_profile)
        except Exception as e:
            self.errors.append(f"Bone generation failed: {str(e)}")
            return {}

    def _validate_reconstruction(self,
                                normalized: Dict[str, NormalizedParameter],
                                proportions: Dict[str, CalculatedProportion],
                                landmarks: Dict[str, LandmarkPosition],
                                bones: Dict[str, BoneGeometry]):
        """Validate reconstruction results.

        Args:
            normalized: Normalized parameters
            proportions: Calculated proportions
            landmarks: Landmark positions
            bones: Bone geometries
        """
        # Check for missing critical data
        if not normalized:
            self.warnings.append("No normalized parameters generated")

        if not proportions:
            self.warnings.append("No proportions calculated")

        if not landmarks:
            self.warnings.append("No landmarks positioned")

        if not bones:
            self.warnings.append("No bones generated")

        # Check for critical landmarks
        critical_landmarks = ['origin', 'vertex', 'hip_joint_center', 'shoulder_joint_center']
        for landmark in critical_landmarks:
            if landmark not in landmarks:
                self.warnings.append(f"Critical landmark missing: {landmark}")

        # Check for critical bones
        critical_bones = ['spine', 'skull']
        for bone in critical_bones:
            if bone not in bones:
                self.warnings.append(f"Critical bone missing: {bone}")

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status.

        Returns:
            Dictionary with pipeline status information
        """
        return {
            "current_stage": self.current_stage.value,
            "status": self.status.value,
            "stages_completed": [stage.value for stage in self.stages_completed],
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "completion_percentage": (len(self.stages_completed) / len(PipelineStage)) * 100.0
        }

    def get_reference_data_quality(self) -> Dict[str, Any]:
        """Get reference data quality report.

        Returns:
            Dictionary with reference data quality information
        """
        return self.reference_manager.get_data_quality_report()
