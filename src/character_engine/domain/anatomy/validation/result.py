"""Anatomical validation result model.

This module defines the validation result types for anatomical validation,
extending the existing validation framework to support PASS, FAIL, WARNING,
UNKNOWN, and NOT_EVALUATED states.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import date


class AnatomicalValidationStatus(Enum):
    """Status of anatomical validation."""
    PASS = "pass"  # Validation passed
    FAIL = "fail"  # Validation failed
    WARNING = "warning"  # Validation passed with warnings
    UNKNOWN = "unknown"  # Cannot evaluate (missing data)
    NOT_EVALUATED = "not_evaluated"  # Not evaluated


@dataclass(frozen=True)
class AnatomicalValidationResult:
    """Result of an anatomical validation check.
    
    Attributes:
        test_id: Identifier for the validation test
        test_name: Human-readable test name
        status: Validation status
        expected_value: Expected value (with range if applicable)
        actual_value: Actual value found
        deviation: Deviation from expected
        unit: Unit of measurement
        source: Source/model being validated
        recommendation: Recommendation for fixing issues
        notes: Additional context
        validated_at: Timestamp of validation
    """
    
    test_id: str
    test_name: str
    status: AnatomicalValidationStatus
    expected_value: str
    actual_value: str
    deviation: Optional[str] = None
    unit: Optional[str] = None
    source: str = ""
    recommendation: str = ""
    notes: str = ""
    validated_at: date = field(default_factory=date.today)
    
    def passed(self) -> bool:
        """Check if validation passed."""
        return self.status == AnatomicalValidationStatus.PASS
    
    def failed(self) -> bool:
        """Check if validation failed."""
        return self.status == AnatomicalValidationStatus.FAIL
    
    def has_warning(self) -> bool:
        """Check if validation has warnings."""
        return self.status == AnatomicalValidationStatus.WARNING
    
    def is_unknown(self) -> bool:
        """Check if validation result is unknown."""
        return self.status == AnatomicalValidationStatus.UNKNOWN
    
    def is_not_evaluated(self) -> bool:
        """Check if validation was not evaluated."""
        return self.status == AnatomicalValidationStatus.NOT_EVALUATED


@dataclass(frozen=True)
class AnatomicalValidationReport:
    """Complete anatomical validation report.
    
    Attributes:
        report_id: Unique identifier for the report
        skeleton_id: Identifier of skeleton being validated
        validation_date: Date of validation
        results: Dictionary of test results by test ID
        total_tests: Total number of tests
        passed_tests: Number of passed tests
        failed_tests: Number of failed tests
        warning_tests: Number of warnings
        unknown_tests: Number of unknown results
        not_evaluated_tests: Number of not evaluated tests
        overall_status: Overall validation status
        notes: Additional context
    """
    
    report_id: str
    skeleton_id: str
    validation_date: date
    results: Dict[str, AnatomicalValidationResult]
    total_tests: int
    passed_tests: int
    failed_tests: int
    warning_tests: int
    unknown_tests: int
    not_evaluated_tests: int
    overall_status: AnatomicalValidationStatus
    notes: str = ""
    
    def get_pass_rate(self) -> float:
        """Calculate pass rate (excluding unknown/not evaluated)."""
        evaluable_tests = self.total_tests - self.unknown_tests - self.not_evaluated_tests
        if evaluable_tests == 0:
            return 0.0
        return self.passed_tests / evaluable_tests
    
    def get_result(self, test_id: str) -> Optional[AnatomicalValidationResult]:
        """Get result for a specific test."""
        return self.results.get(test_id)
    
    def get_failed_tests(self) -> List[AnatomicalValidationResult]:
        """Get all failed test results."""
        return [r for r in self.results.values() if r.failed()]
    
    def get_warning_tests(self) -> List[AnatomicalValidationResult]:
        """Get all warning test results."""
        return [r for r in self.results.values() if r.has_warning()]
    
    def get_unknown_tests(self) -> List[AnatomicalValidationResult]:
        """Get all unknown test results."""
        return [r for r in self.results.values() if r.is_unknown()]


class AnatomicalValidationReportBuilder:
    """Builder for creating anatomical validation reports."""
    
    def __init__(self, report_id: str, skeleton_id: str):
        self.report_id = report_id
        self.skeleton_id = skeleton_id
        self.validation_date = date.today()
        self.results: Dict[str, AnatomicalValidationResult] = {}
        self.notes = ""
    
    def add_result(self, result: AnatomicalValidationResult) -> "AnatomicalValidationReportBuilder":
        """Add a validation result."""
        self.results[result.test_id] = result
        return self
    
    def set_notes(self, notes: str) -> "AnatomicalValidationReportBuilder":
        """Set report notes."""
        self.notes = notes
        return self
    
    def build(self) -> AnatomicalValidationReport:
        """Build the validation report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r.passed())
        failed_tests = sum(1 for r in self.results.values() if r.failed())
        warning_tests = sum(1 for r in self.results.values() if r.has_warning())
        unknown_tests = sum(1 for r in self.results.values() if r.is_unknown())
        not_evaluated_tests = sum(1 for r in self.results.values() if r.is_not_evaluated())
        
        # Determine overall status
        if failed_tests > 0:
            overall_status = AnatomicalValidationStatus.FAIL
        elif warning_tests > 0:
            overall_status = AnatomicalValidationStatus.WARNING
        elif unknown_tests > 0:
            overall_status = AnatomicalValidationStatus.UNKNOWN
        else:
            overall_status = AnatomicalValidationStatus.PASS
        
        return AnatomicalValidationReport(
            report_id=self.report_id,
            skeleton_id=self.skeleton_id,
            validation_date=self.validation_date,
            results=dict(self.results),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            warning_tests=warning_tests,
            unknown_tests=unknown_tests,
            not_evaluated_tests=not_evaluated_tests,
            overall_status=overall_status,
            notes=self.notes
        )


def create_pass_result(test_id: str, test_name: str, 
                       expected_value: str, actual_value: str) -> AnatomicalValidationResult:
    """Create a passing validation result."""
    return AnatomicalValidationResult(
        test_id=test_id,
        test_name=test_name,
        status=AnatomicalValidationStatus.PASS,
        expected_value=expected_value,
        actual_value=actual_value
    )


def create_fail_result(test_id: str, test_name: str,
                       expected_value: str, actual_value: str,
                       deviation: str,
                       source: str = "",
                       recommendation: str = "") -> AnatomicalValidationResult:
    """Create a failing validation result."""
    return AnatomicalValidationResult(
        test_id=test_id,
        test_name=test_name,
        status=AnatomicalValidationStatus.FAIL,
        expected_value=expected_value,
        actual_value=actual_value,
        deviation=deviation,
        source=source,
        recommendation=recommendation
    )


def create_warning_result(test_id: str, test_name: str,
                          expected_value: str, actual_value: str,
                          deviation: str,
                          notes: str = "") -> AnatomicalValidationResult:
    """Create a warning validation result."""
    return AnatomicalValidationResult(
        test_id=test_id,
        test_name=test_name,
        status=AnatomicalValidationStatus.WARNING,
        expected_value=expected_value,
        actual_value=actual_value,
        deviation=deviation,
        notes=notes
    )


def create_unknown_result(test_id: str, test_name: str,
                          reason: str = "") -> AnatomicalValidationResult:
    """Create an unknown validation result."""
    return AnatomicalValidationResult(
        test_id=test_id,
        test_name=test_name,
        status=AnatomicalValidationStatus.UNKNOWN,
        expected_value="UNKNOWN",
        actual_value="UNKNOWN",
        notes=f"Cannot evaluate: {reason}"
    )
