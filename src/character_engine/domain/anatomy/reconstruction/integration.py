"""Integration adapter for anatomical reconstruction pipeline.

This module provides integration points between the new anatomical reconstruction
pipeline and the existing character engine pipeline.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..coordinate_system import CoordinateSystem
from ..osteology.builder import SkeletonBuilder
from ..osteology.skeleton import Skeleton
from ..osteology.validator import SkeletonValidator
from ..parameters import SubjectProfile
from .pipeline import PipelineResult, ReconstructionPipeline


@dataclass
class IntegrationConfig:
    """Configuration for reconstruction integration.

    Attributes:
        references_dir: Directory containing reference data
        coordinate_system: Anatomical coordinate system
        enable_reconstruction: Whether to enable anatomical reconstruction
        enhance_existing_data: Whether to enhance existing skeleton data with reconstruction
        validation_mode: Validation mode (strict, lenient, disabled)
    """

    references_dir: Path
    coordinate_system: CoordinateSystem
    enable_reconstruction: bool = True
    enhance_existing_data: bool = True
    validation_mode: str = "strict"


class ReconstructionIntegrationAdapter:
    """Adapter for integrating anatomical reconstruction with existing pipeline."""

    def __init__(self, config: IntegrationConfig):
        """Initialize reconstruction integration adapter.

        Args:
            config: Integration configuration
        """
        self.config = config

        # Initialize reconstruction pipeline if enabled
        if config.enable_reconstruction:
            self.reconstruction_pipeline = ReconstructionPipeline(
                config.references_dir,
                config.coordinate_system
            )
        else:
            self.reconstruction_pipeline = None

        # Initialize existing pipeline components
        self.skeleton_builder = SkeletonBuilder()
        self.skeleton_validator = SkeletonValidator()

    def integrate_with_existing_pipeline(self,
                                       subject_profile: SubjectProfile,
                                       existing_skeleton_data: Optional[Dict[str, Any]] = None) -> Tuple[PipelineResult, Optional[Skeleton]]:
        """Integrate reconstruction with existing pipeline.

        Args:
            subject_profile: Subject profile for reconstruction
            existing_skeleton_data: Optional existing skeleton data to enhance

        Returns:
            Tuple of (reconstruction result, enhanced skeleton)
        """
        # Run reconstruction pipeline if enabled
        if self.reconstruction_pipeline:
            reconstruction_result = self.reconstruction_pipeline.reconstruct(subject_profile)
        else:
            reconstruction_result = None

        # Integrate with existing skeleton data if provided
        enhanced_skeleton = None
        if existing_skeleton_data and self.config.enhance_existing_data:
            enhanced_skeleton = self._enhance_skeleton_data(
                existing_skeleton_data,
                reconstruction_result
            )

        return reconstruction_result, enhanced_skeleton

    def _enhance_skeleton_data(self,
                               existing_data: Dict[str, Any],
                               reconstruction_result: Optional[PipelineResult]) -> Skeleton:
        """Enhance existing skeleton data with reconstruction results.

        Args:
            existing_data: Existing skeleton data
            reconstruction_result: Reconstruction pipeline results

        Returns:
            Enhanced skeleton
        """
        # Start with existing data
        enhanced_spec = existing_data.copy()

        # Enhance with reconstruction data if available
        if reconstruction_result and reconstruction_result.is_successful():
            # Add landmark positions to bone data
            if reconstruction_result.landmark_positions:
                enhanced_spec = self._add_landmark_data(
                    enhanced_spec,
                    reconstruction_result.landmark_positions
                )

            # Add bone geometry enhancements
            if reconstruction_result.bone_geometries:
                enhanced_spec = self._add_bone_geometry_data(
                    enhanced_spec,
                    reconstruction_result.bone_geometries
                )

            # Add proportion metadata
            if reconstruction_result.calculated_proportions:
                enhanced_spec = self._add_proportion_metadata(
                    enhanced_spec,
                    reconstruction_result.calculated_proportions
                )

        # Build enhanced skeleton
        skeleton = self.skeleton_builder.build(enhanced_spec)

        # Validate enhanced skeleton
        if self.config.validation_mode != "disabled":
            validation_result = self.skeleton_validator.validate(skeleton)
            if not validation_result.is_valid and self.config.validation_mode == "strict":
                raise ValueError(f"Enhanced skeleton validation failed: {validation_result.errors}")

        return skeleton

    def _add_landmark_data(self,
                          skeleton_spec: Dict[str, Any],
                          landmarks: Dict[str, Any]) -> Dict[str, Any]:
        """Add landmark data to skeleton specification.

        Args:
            skeleton_spec: Skeleton specification
            landmarks: Landmark positions

        Returns:
            Enhanced skeleton specification
        """
        # Add landmarks to metadata
        if "metadata" not in skeleton_spec:
            skeleton_spec["metadata"] = {}

        skeleton_spec["metadata"]["landmarks"] = {
            name: {
                "position": landmark.position,
                "confidence": landmark.confidence,
                "provenance": landmark.provenance
            }
            for name, landmark in landmarks.items()
        }

        return skeleton_spec

    def _add_bone_geometry_data(self,
                                skeleton_spec: Dict[str, Any],
                                bones: Dict[str, Any]) -> Dict[str, Any]:
        """Add bone geometry data to skeleton specification.

        Args:
            skeleton_spec: Skeleton specification
            bones: Bone geometries

        Returns:
            Enhanced skeleton specification
        """
        # Enhance bone data with geometry information
        if "bones" not in skeleton_spec:
            skeleton_spec["bones"] = []

        # Create mapping of existing bones by canonical name
        bone_map = {bone["canonical_name"]: bone for bone in skeleton_spec["bones"]}

        # Add geometry data to existing bones
        for bone_name, bone_geometry in bones.items():
            if bone_name in bone_map:
                # Enhance existing bone
                bone_map[bone_name]["geometry"] = {
                    "length": bone_geometry.length,
                    "diameter": bone_geometry.diameter,
                    "start_position": bone_geometry.start_position,
                    "end_position": bone_geometry.end_position,
                    "orientation": bone_geometry.orientation,
                    "confidence": bone_geometry.confidence
                }
            else:
                # Add new bone from reconstruction
                skeleton_spec["bones"].append({
                    "canonical_name": bone_geometry.canonical_name,
                    "name": bone_geometry.name,
                    "geometry": {
                        "length": bone_geometry.length,
                        "diameter": bone_geometry.diameter,
                        "start_position": bone_geometry.start_position,
                        "end_position": bone_geometry.end_position,
                        "orientation": bone_geometry.orientation,
                        "confidence": bone_geometry.confidence
                    },
                    "parent": None,  # Reconstruction bones may not have hierarchy
                    "head": bone_geometry.start_position,
                    "tail": bone_geometry.end_position
                })

        return skeleton_spec

    def _add_proportion_metadata(self,
                                 skeleton_spec: Dict[str, Any],
                                 proportions: Dict[str, Any]) -> Dict[str, Any]:
        """Add proportion metadata to skeleton specification.

        Args:
            skeleton_spec: Skeleton specification
            proportions: Calculated proportions

        Returns:
            Enhanced skeleton specification
        """
        # Add proportions to metadata
        if "metadata" not in skeleton_spec:
            skeleton_spec["metadata"] = {}

        skeleton_spec["metadata"]["proportions"] = {
            name: {
                "value": proportion.value,
                "unit": proportion.unit,
                "confidence": proportion.confidence,
                "calculation_method": proportion.calculation_method.value
            }
            for name, proportion in proportions.items()
        }

        return skeleton_spec

    def generate_subject_profile_from_existing(self,
                                              existing_data: Dict[str, Any]) -> SubjectProfile:
        """Generate subject profile from existing skeleton data.

        Args:
            existing_data: Existing skeleton data

        Returns:
            Subject profile for reconstruction
        """
        # Extract height from existing data if available
        height = None
        if "metadata" in existing_data and "height" in existing_data["metadata"]:
            height = existing_data["metadata"]["height"]

        # Extract other subject information if available
        weight = existing_data.get("metadata", {}).get("weight")
        age = existing_data.get("metadata", {}).get("age")
        gender = existing_data.get("metadata", {}).get("gender")
        ethnicity = existing_data.get("metadata", {}).get("ethnicity")

        return SubjectProfile(
            height=height,
            weight=weight,
            age=age,
            gender=gender,
            ethnicity=ethnicity
        )

    def validate_integration(self, reconstruction_result: PipelineResult) -> Dict[str, Any]:
        """Validate integration results.

        Args:
            reconstruction_result: Reconstruction pipeline result

        Returns:
            Validation report
        """
        validation_report = {
            "reconstruction_successful": reconstruction_result.is_successful() if reconstruction_result else False,
            "has_errors": reconstruction_result.has_errors() if reconstruction_result else False,
            "has_warnings": reconstruction_result.has_warnings() if reconstruction_result else False,
            "completion_percentage": reconstruction_result.get_completion_percentage() if reconstruction_result else 0.0,
            "landmark_count": len(reconstruction_result.landmark_positions) if reconstruction_result else 0,
            "bone_count": len(reconstruction_result.bone_geometries) if reconstruction_result else 0,
            "proportion_count": len(reconstruction_result.calculated_proportions) if reconstruction_result else 0
        }

        return validation_report
