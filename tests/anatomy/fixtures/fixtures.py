"""Test fixtures for anatomical validation.

This module provides test fixtures including:
- A0.2 baseline fixture (demonstrates known failures)
- Synthetic valid fixture (verifies validation machinery)
"""

from character_engine.domain.anatomy.landmarks import (
    LandmarkRegion,
    LandmarkSet,
    LandmarkSetBuilder,
    create_bilateral_landmark_pair,
    create_measured_landmark,
)
from character_engine.domain.anatomy.parameters import (
    ParameterSet,
    ParameterSetBuilder,
    create_direct_reference_parameter,
)
from character_engine.domain.anatomy.validation import create_anatomical_validator


def create_a02_baseline_parameter_set() -> ParameterSet:
    """Create parameter set based on A0.2 baseline (demonstrates known failures).

    This fixture uses the known problematic values from the A0.2 forensic audit:
    - Total height: 3.08m (should be 1.7-1.9m)
    - Straight spine (no curvature)
    - Uniform hand dimensions
    - Excessive gaps at joints
    """
    builder = ParameterSetBuilder("A02_BASELINE", "A0.2 Baseline Parameters", "1.0.0")

    # Add known problematic height
    builder.add_parameter(create_direct_reference_parameter(
        "total_height",
        3.08,  # Known failure: 3.08m vs expected 1.7-1.9m
        "meters",
        "A02_BASELINE"
    ))

    # Add other parameters with reasonable values for testing
    builder.add_parameter(create_direct_reference_parameter(
        "shoulder_width",
        0.79,  # Approximate based on 3.08m height
        "meters",
        "A02_BASELINE"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "head_height",
        0.45,  # Known failure: oversized
        "meters",
        "A02_BASELINE"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "torso_height",
        1.20,  # Known failure: incorrect proportion
        "meters",
        "A02_BASELINE"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "upper_arm_length",
        0.51,  # Based on proportion
        "meters",
        "A02_BASELINE"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "forearm_length",
        0.44,  # Based on proportion
        "meters",
        "A02_BASELINE"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "thigh_length",
        0.77,  # Based on proportion
        "meters",
        "A02_BASELINE"
    ))

    return builder.build()


def create_synthetic_valid_parameter_set() -> ParameterSet:
    """Create synthetic valid parameter set for validation machinery testing.

    This fixture uses mathematically controlled values that should pass validation:
    - Total height: 1.75m (within normal range)
    - Proper proportions
    - Bilateral consistency
    """
    builder = ParameterSetBuilder("SYNTHETIC_VALID", "Synthetic Valid Parameters", "1.0.0")

    # Add valid height
    builder.add_parameter(create_direct_reference_parameter(
        "total_height",
        1.75,  # Valid: within 1.7-1.9m range
        "meters",
        "SYNTHETIC"
    ))

    # Add proper proportions
    builder.add_parameter(create_direct_reference_parameter(
        "shoulder_width",
        0.44,  # 1/4 of height
        "meters",
        "SYNTHETIC"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "head_height",
        0.22,  # 1/8 of height
        "meters",
        "SYNTHETIC"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "torso_height",
        0.58,  # 1/3 of height
        "meters",
        "SYNTHETIC"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "upper_arm_length",
        0.29,  # 1/6 of height
        "meters",
        "SYNTHETIC"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "forearm_length",
        0.25,  # ~1/7 of height
        "meters",
        "SYNTHETIC"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "thigh_length",
        0.44,  # 1/4 of height
        "meters",
        "SYNTHETIC"
    ))

    # Add bilateral pairs with consistent values
    builder.add_parameter(create_direct_reference_parameter(
        "femur_L",
        0.44,
        "meters",
        "SYNTHETIC"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "femur_R",
        0.44,  # Same as left for bilateral consistency
        "meters",
        "SYNTHETIC"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "humerus_L",
        0.29,
        "meters",
        "SYNTHETIC"
    ))

    builder.add_parameter(create_direct_reference_parameter(
        "humerus_R",
        0.29,  # Same as left for bilateral consistency
        "meters",
        "SYNTHETIC"
    ))

    return builder.build()


def create_minimal_landmark_set() -> LandmarkSet:
    """Create minimal landmark set for testing.

    This fixture provides a basic set of landmarks for validation testing.
    """
    builder = LandmarkSetBuilder("MINIMAL", "Minimal Landmark Set", "1.0.0")

    # Add some midline landmarks
    builder.add_landmark(create_measured_landmark(
        "head_top",
        LandmarkRegion.SKULL,
        (0.0, 0.0, 1.75),
        "SYNTHETIC"
    ))

    builder.add_landmark(create_measured_landmark(
        "neck_base",
        LandmarkRegion.SPINE,
        (0.0, 0.0, 1.53),
        "SYNTHETIC"
    ))

    # Add bilateral landmarks
    left_shoulder, right_shoulder = create_bilateral_landmark_pair(
        "shoulder",
        LandmarkRegion.SHOULDER,
        (-0.22, 0.0, 1.53),
        (0.22, 0.0, 1.53),
        "SYNTHETIC"
    )

    builder.add_landmark(left_shoulder)
    builder.add_landmark(right_shoulder)

    return builder.build()


def run_a02_baseline_validation() -> dict:
    """Run validation against A0.2 baseline to verify tests detect known failures.

    Returns:
        Dictionary with validation results summary
    """
    parameter_set = create_a02_baseline_parameter_set()
    landmark_set = create_minimal_landmark_set()

    validator = create_anatomical_validator()
    report = validator.validate_all(
        parameter_set=parameter_set,
        landmark_set=landmark_set,
        joint_center_set=None,  # Not implemented yet
        spine_model=None,  # Not implemented yet
        hand_models=None,  # Not implemented yet
        foot_models=None  # Not implemented yet
    )

    return {
        "total_tests": report.total_tests,
        "passed_tests": report.passed_tests,
        "failed_tests": report.failed_tests,
        "unknown_tests": report.unknown_tests,
        "overall_status": report.overall_status.value,
        "detected_failures": [r.test_id for r in report.get_failed_tests()]
    }


def run_synthetic_valid_validation() -> dict:
    """Run validation against synthetic valid fixture.

    Returns:
        Dictionary with validation results summary
    """
    parameter_set = create_synthetic_valid_parameter_set()
    landmark_set = create_minimal_landmark_set()

    validator = create_anatomical_validator()
    report = validator.validate_all(
        parameter_set=parameter_set,
        landmark_set=landmark_set,
        joint_center_set=None,
        spine_model=None,
        hand_models=None,
        foot_models=None
    )

    return {
        "total_tests": report.total_tests,
        "passed_tests": report.passed_tests,
        "failed_tests": report.failed_tests,
        "unknown_tests": report.unknown_tests,
        "overall_status": report.overall_status.value,
        "pass_rate": report.get_pass_rate()
    }
