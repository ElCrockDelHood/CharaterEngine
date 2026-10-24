"""Anatomical validation tests."""

import pytest
from tests.anatomy.fixtures import (
    create_a02_baseline_parameter_set,
    create_minimal_landmark_set,
    create_synthetic_valid_parameter_set,
    run_a02_baseline_validation,
    run_synthetic_valid_validation,
)

from character_engine.domain.anatomy.landmarks import (
    LandmarkSet,
)
from character_engine.domain.anatomy.parameters import (
    ParameterSet,
    ParameterSetBuilder,
    create_direct_reference_parameter,
)
from character_engine.domain.anatomy.validation import (
    AnatomicalValidationReport,
    AnatomicalValidationReportBuilder,
    AnatomicalValidationStatus,
    AnatomicalValidator,
    create_anatomical_validator,
    create_fail_result,
    create_pass_result,
    create_unknown_result,
    create_warning_result,
)


class TestAnatomicalValidationResult:
    """Test anatomical validation result model."""

    def test_pass_result(self):
        """Test creating a pass result."""
        result = create_pass_result("TEST", "Test", "expected", "actual")

        assert result.test_id == "TEST"
        assert result.status == AnatomicalValidationStatus.PASS
        assert result.passed()
        assert not result.failed()

    def test_fail_result(self):
        """Test creating a fail result."""
        result = create_fail_result("TEST", "Test", "expected", "actual", "deviation")

        assert result.test_id == "TEST"
        assert result.status == AnatomicalValidationStatus.FAIL
        assert result.failed()
        assert not result.passed()
        assert result.deviation == "deviation"

    def test_warning_result(self):
        """Test creating a warning result."""
        result = create_warning_result("TEST", "Test", "expected", "actual", "deviation")

        assert result.test_id == "TEST"
        assert result.status == AnatomicalValidationStatus.WARNING
        assert result.has_warning()
        assert not result.failed()

    def test_unknown_result(self):
        """Test creating an unknown result."""
        result = create_unknown_result("TEST", "Test", "reason")

        assert result.test_id == "TEST"
        assert result.status == AnatomicalValidationStatus.UNKNOWN
        assert result.is_unknown()
        assert not result.failed()


class TestAnatomicalValidationReport:
    """Test anatomical validation report model."""

    def test_report_creation(self):
        """Test creating a validation report."""
        builder = AnatomicalValidationReportBuilder("REPORT", "SKELETON")

        builder.add_result(create_pass_result("T1", "Test 1", "exp", "act"))
        builder.add_result(create_fail_result("T2", "Test 2", "exp", "act", "dev"))

        report = builder.build()

        assert report.report_id == "REPORT"
        assert report.skeleton_id == "SKELETON"
        assert report.total_tests == 2
        assert report.passed_tests == 1
        assert report.failed_tests == 1
        assert report.overall_status == AnatomicalValidationStatus.FAIL

    def test_pass_rate_calculation(self):
        """Test pass rate calculation."""
        builder = AnatomicalValidationReportBuilder("REPORT", "SKELETON")

        builder.add_result(create_pass_result("T1", "Test 1", "exp", "act"))
        builder.add_result(create_pass_result("T2", "Test 2", "exp", "act"))
        builder.add_result(create_fail_result("T3", "Test 3", "exp", "act", "dev"))
        builder.add_result(create_unknown_result("T4", "Test 4", "reason"))

        report = builder.build()

        # Pass rate should be 2/3 (excluding unknown)
        assert report.get_pass_rate() == pytest.approx(0.667, rel=0.01)

    def test_get_failed_tests(self):
        """Test retrieving failed tests."""
        builder = AnatomicalValidationReportBuilder("REPORT", "SKELETON")

        builder.add_result(create_pass_result("T1", "Test 1", "exp", "act"))
        builder.add_result(create_fail_result("T2", "Test 2", "exp", "act", "dev"))
        builder.add_result(create_fail_result("T3", "Test 3", "exp", "act", "dev"))

        report = builder.build()

        failed = report.get_failed_tests()
        assert len(failed) == 2
        assert all(r.failed() for r in failed)

    def test_overall_status_determination(self):
        """Test overall status determination."""
        # All pass
        builder1 = AnatomicalValidationReportBuilder("REPORT", "SKELETON")
        builder1.add_result(create_pass_result("T1", "Test 1", "exp", "act"))
        report1 = builder1.build()
        assert report1.overall_status == AnatomicalValidationStatus.PASS

        # Has failures
        builder2 = AnatomicalValidationReportBuilder("REPORT", "SKELETON")
        builder2.add_result(create_pass_result("T1", "Test 1", "exp", "act"))
        builder2.add_result(create_fail_result("T2", "Test 2", "exp", "act", "dev"))
        report2 = builder2.build()
        assert report2.overall_status == AnatomicalValidationStatus.FAIL

        # Has warnings
        builder3 = AnatomicalValidationReportBuilder("REPORT", "SKELETON")
        builder3.add_result(create_warning_result("T1", "Test 1", "exp", "act", "dev"))
        report3 = builder3.build()
        assert report3.overall_status == AnatomicalValidationStatus.WARNING

        # Has unknown
        builder4 = AnatomicalValidationReportBuilder("REPORT", "SKELETON")
        builder4.add_result(create_unknown_result("T1", "Test 1", "reason"))
        report4 = builder4.build()
        assert report4.overall_status == AnatomicalValidationStatus.UNKNOWN


class TestAnatomicalValidator:
    """Test anatomical validator."""

    def test_validator_creation(self):
        """Test creating an anatomical validator."""
        validator = create_anatomical_validator()

        assert isinstance(validator, AnatomicalValidator)

    def test_validate_bs_01_height_valid(self):
        """Test BS-01 with valid height."""
        builder = ParameterSetBuilder("TEST", "Test", "1.0.0")
        builder.add_parameter(create_direct_reference_parameter("total_height", 1.75, "meters", "SOURCE"))
        param_set = builder.build()

        validator = create_anatomical_validator()
        result = validator.validate_bs_01_height(param_set)

        assert result.passed()
        assert result.test_id == "BS-01"

    def test_validate_bs_01_height_invalid(self):
        """Test BS-01 with invalid height (A0.2 baseline)."""
        param_set = create_a02_baseline_parameter_set()

        validator = create_anatomical_validator()
        result = validator.validate_bs_01_height(param_set)

        assert result.failed()
        assert result.test_id == "BS-01"
        assert "3.08" in result.actual_value  # Known failure value

    def test_validate_bs_01_height_unknown(self):
        """Test BS-01 with unknown height."""
        builder = ParameterSetBuilder("TEST", "Test", "1.0.0")
        param_set = builder.build()

        validator = create_anatomical_validator()
        result = validator.validate_bs_01_height(param_set)

        assert result.is_unknown()

    def test_validate_la_01_landmark_completeness(self):
        """Test LA-01 landmark completeness."""
        landmark_set = create_minimal_landmark_set()

        validator = create_anatomical_validator()
        result = validator.validate_la_01_landmark_completeness(landmark_set)

        # Minimal set has < 20 landmarks, so should fail
        assert result.failed()

    def test_validate_la_02_bilateral_symmetry(self):
        """Test LA-02 bilateral symmetry."""
        landmark_set = create_minimal_landmark_set()

        validator = create_anatomical_validator()
        result = validator.validate_la_02_bilateral_symmetry(landmark_set)

        # Should pass for our symmetric landmarks
        assert result.passed()

    def test_validate_ap_01_total_height_valid(self):
        """Test AP-01 with valid height."""
        param_set = create_synthetic_valid_parameter_set()

        validator = create_anatomical_validator()
        result = validator.validate_ap_01_total_height(param_set)

        assert result.passed()

    def test_validate_ap_01_total_height_invalid(self):
        """Test AP-01 with invalid height."""
        param_set = create_a02_baseline_parameter_set()

        validator = create_anatomical_validator()
        result = validator.validate_ap_01_total_height(param_set)

        assert result.failed()

    def test_validate_all(self):
        """Test complete validation run."""
        param_set = create_synthetic_valid_parameter_set()
        landmark_set = create_minimal_landmark_set()

        validator = create_anatomical_validator()
        report = validator.validate_all(
            parameter_set=param_set,
            landmark_set=landmark_set
        )

        assert isinstance(report, AnatomicalValidationReport)
        assert report.total_tests > 0
        assert report.skeleton_id == "RECONSTRUCTED_SKELETON"


class TestFixtures:
    """Test fixture functionality."""

    def test_a02_baseline_parameter_set(self):
        """Test A0.2 baseline parameter set creation."""
        param_set = create_a02_baseline_parameter_set()

        assert isinstance(param_set, ParameterSet)
        assert param_set.name == "A0.2 Baseline Parameters"

        # Verify known failure value
        height_param = param_set.get_parameter_by_canonical_name("total_height")
        assert height_param is not None
        assert height_param.value == 3.08  # Known failure

    def test_synthetic_valid_parameter_set(self):
        """Test synthetic valid parameter set creation."""
        param_set = create_synthetic_valid_parameter_set()

        assert isinstance(param_set, ParameterSet)
        assert param_set.name == "Synthetic Valid Parameters"

        # Verify valid value
        height_param = param_set.get_parameter_by_canonical_name("total_height")
        assert height_param is not None
        assert 1.7 <= height_param.value <= 1.9  # Valid range

    def test_minimal_landmark_set(self):
        """Test minimal landmark set creation."""
        landmark_set = create_minimal_landmark_set()

        assert isinstance(landmark_set, LandmarkSet)
        assert len(landmark_set.landmarks) > 0

    def test_a02_baseline_validation(self):
        """Test A0.2 baseline validation detects known failures."""
        results = run_a02_baseline_validation()

        assert results["total_tests"] > 0
        assert results["failed_tests"] > 0  # Should detect failures
        assert "BS-01" in results["detected_failures"]  # Height should fail
        assert results["overall_status"] == "fail"

    def test_synthetic_valid_validation(self):
        """Test synthetic valid validation passes appropriate tests."""
        results = run_synthetic_valid_validation()

        assert results["total_tests"] > 0
        assert results["pass_rate"] > 0.5  # Should pass most tests
        # Overall status might be unknown due to missing joint center data


class TestValidationIntegration:
    """Integration tests for validation system."""

    def test_validation_detects_a02_failures(self):
        """Test that validation correctly detects A0.2 known failures."""
        param_set = create_a02_baseline_parameter_set()
        landmark_set = create_minimal_landmark_set()

        validator = create_anatomical_validator()
        report = validator.validate_all(
            parameter_set=param_set,
            landmark_set=landmark_set
        )

        # Should detect the 3.08m height failure
        height_result = report.get_result("BS-01")
        assert height_result is not None
        assert height_result.failed()
        assert "3.08" in height_result.actual_value

    def test_validation_passes_synthetic_valid(self):
        """Test that validation passes synthetic valid fixture."""
        param_set = create_synthetic_valid_parameter_set()
        landmark_set = create_minimal_landmark_set()

        validator = create_anatomical_validator()
        report = validator.validate_all(
            parameter_set=param_set,
            landmark_set=landmark_set
        )

        # Height should pass
        height_result = report.get_result("BS-01")
        assert height_result is not None
        assert height_result.passed()

    def test_validation_result_actionable(self):
        """Test that validation results provide actionable information."""
        param_set = create_a02_baseline_parameter_set()

        validator = create_anatomical_validator()
        result = validator.validate_bs_01_height(param_set)

        # Failed result should have actionable info
        if result.failed():
            assert result.deviation is not None
            assert result.recommendation != ""
            assert result.source != ""

    def test_validation_unknown_handling(self):
        """Test that validation handles missing data appropriately."""
        # Parameter set without landmarks
        param_set = create_synthetic_valid_parameter_set()

        validator = create_anatomical_validator()
        report = validator.validate_all(
            parameter_set=param_set,
            landmark_set=None  # No landmarks
        )

        # Joint center tests should be unknown
        jc_result = report.get_result("JC-01")
        assert jc_result is not None
        assert jc_result.is_unknown()

    def test_bilateral_consistency_validation(self):
        """Test bilateral consistency validation."""
        builder = ParameterSetBuilder("TEST", "Test", "1.0.0")

        # Add inconsistent bilateral pair
        builder.add_parameter(create_direct_reference_parameter("femur_L", 0.44, "meters", "SOURCE"))
        builder.add_parameter(create_direct_reference_parameter("femur_R", 0.50, "meters", "SOURCE"))  # Different value

        param_set = builder.build()

        validator = create_anatomical_validator()
        result = validator.validate_ap_05_bilateral_consistency(param_set)

        # Should detect inconsistency
        assert result.failed()
        assert "consistency" in result.recommendation.lower()
