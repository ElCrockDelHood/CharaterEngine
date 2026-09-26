"""Reconstruction eligibility validation for anatomical reconstruction.

This module provides validation gates to ensure that only reference-backed
data can enter canonical anatomical reconstruction, preventing placeholder
data from becoming anatomical truth.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import date

from .source import (
    ReferenceValue,
    ReferenceDataset,
    ProvenanceState,
    Confidence
)


class ReconstructionEligibility(Enum):
    """Eligibility status for anatomical reconstruction."""
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    CONDITIONAL = "conditional"
    REQUIRES_AUTHORIZATION = "requires_authorization"


class RejectionReason(Enum):
    """Reason for reconstruction rejection."""
    PLACEHOLDER_DATA = "placeholder_data"
    ASSUMED_DATA = "assumed_data"
    UNKNOWN_DATA = "unknown_data"
    LOW_CONFIDENCE = "low_confidence"
    MISSING_PROVENANCE = "missing_provenance"
    INVALID_DERIVATION = "invalid_derivation"
    CONTAMINATED_CHAIN = "contaminated_chain"
    MISSING_METADATA = "missing_metadata"


@dataclass
class EligibilityCheck:
    """Result of reconstruction eligibility check.
    
    Attributes:
        parameter: Parameter name
        value: Parameter value
        provenance_state: Provenance state
        eligibility: Eligibility status
        rejection_reason: Reason for rejection if not eligible
        confidence: Confidence level
        notes: Additional context
    """
    
    parameter: str
    value: Optional[float]
    provenance_state: ProvenanceState
    eligibility: ReconstructionEligibility
    rejection_reason: Optional[RejectionReason] = None
    confidence: Confidence = Confidence.UNKNOWN
    notes: str = ""
    
    def is_eligible(self) -> bool:
        """Check if parameter is eligible for reconstruction."""
        return self.eligibility == ReconstructionEligibility.ELIGIBLE
    
    def is_rejected(self) -> bool:
        """Check if parameter is rejected for reconstruction."""
        return self.eligibility == ReconstructionEligibility.NOT_ELIGIBLE


@dataclass
class ReconstructionGateResult:
    """Result of reconstruction gate validation.
    
    Attributes:
        gate_name: Name of the validation gate
        passed: Whether gate passed
        total_parameters: Total parameters checked
        eligible_parameters: Parameters that passed
        rejected_parameters: Parameters that failed
        conditional_parameters: Parameters with conditions
        rejection_reasons: Dictionary of rejection reasons by parameter
        errors: List of errors encountered
        warnings: List of warnings
        validated_at: Validation timestamp
    """
    
    gate_name: str
    passed: bool
    total_parameters: int
    eligible_parameters: int
    rejected_parameters: int
    conditional_parameters: int
    rejection_reasons: Dict[str, RejectionReason]
    errors: List[str]
    warnings: List[str]
    validated_at: date = field(default_factory=date.today)
    
    def get_completion_percentage(self) -> float:
        """Calculate completion percentage (eligible / total)."""
        if self.total_parameters == 0:
            return 0.0
        return (self.eligible_parameters / self.total_parameters) * 100.0
    
    def get_rejection_summary(self) -> Dict[str, int]:
        """Get summary of rejection reasons."""
        summary = {}
        for reason in self.rejection_reasons.values():
            summary[reason.value] = summary.get(reason.value, 0) + 1
        return summary


class ReconstructionEligibilityValidator:
    """Validates reconstruction eligibility based on provenance and data quality."""
    
    def __init__(self, strict_mode: bool = True):
        """Initialize eligibility validator.
        
        Args:
            strict_mode: If True, rejects all non-PROVEN data for canonical reconstruction
        """
        self.strict_mode = strict_mode
        self.rejection_policy = self._define_rejection_policy()
    
    def _define_rejection_policy(self) -> Dict[ProvenanceState, ReconstructionEligibility]:
        """Define the rejection policy for reconstruction eligibility.
        
        Args:
            None
            
        Returns:
            Dictionary mapping provenance states to eligibility
        """
        if self.strict_mode:
            # Strict mode: Only PROVEN data is eligible
            return {
                ProvenanceState.PROVEN: ReconstructionEligibility.ELIGIBLE,
                ProvenanceState.DERIVED: ReconstructionEligibility.CONDITIONAL,
                ProvenanceState.ESTIMATE: ReconstructionEligibility.NOT_ELIGIBLE,
                ProvenanceState.ASSUMED: ReconstructionEligibility.NOT_ELIGIBLE,
                ProvenanceState.PLACEHOLDER: ReconstructionEligibility.NOT_ELIGIBLE,
                ProvenanceState.UNKNOWN: ReconstructionEligibility.NOT_ELIGIBLE,
                ProvenanceState.USER_INPUT: ReconstructionEligibility.CONDITIONAL
            }
        else:
            # Lenient mode: PROVEN and DERIVED are eligible
            return {
                ProvenanceState.PROVEN: ReconstructionEligibility.ELIGIBLE,
                ProvenanceState.DERIVED: ReconstructionEligibility.ELIGIBLE,
                ProvenanceState.ESTIMATE: ReconstructionEligibility.REQUIRES_AUTHORIZATION,
                ProvenanceState.ASSUMED: ReconstructionEligibility.NOT_ELIGIBLE,
                ProvenanceState.PLACEHOLDER: ReconstructionEligibility.NOT_ELIGIBLE,
                ProvenanceState.UNKNOWN: ReconstructionEligibility.NOT_ELIGIBLE,
                ProvenanceState.USER_INPUT: ReconstructionEligibility.CONDITIONAL
            }
    
    def validate_parameter(self, parameter: str, value: ReferenceValue) -> EligibilityCheck:
        """Validate single parameter for reconstruction eligibility.
        
        Args:
            parameter: Parameter name
            value: Reference value to validate
            
        Returns:
            Eligibility check result
        """
        # Check provenance state eligibility
        eligibility = self.rejection_policy.get(value.provenance_state, 
                                                      ReconstructionEligibility.NOT_ELIGIBLE)
        
        rejection_reason = None
        notes = ""
        
        # Determine rejection reason if not eligible
        if eligibility == ReconstructionEligibility.NOT_ELIGIBLE:
            if value.provenance_state == ProvenanceState.PLACEHOLDER:
                rejection_reason = RejectionReason.PLACEHOLDER_DATA
                notes = "Placeholder data cannot enter canonical reconstruction"
            elif value.provenance_state == ProvenanceState.ASSUMED:
                rejection_reason = RejectionReason.ASSUMED_DATA
                notes = "Assumed data cannot enter canonical reconstruction"
            elif value.provenance_state == ProvenanceState.UNKNOWN:
                rejection_reason = RejectionReason.UNKNOWN_DATA
                notes = "Unknown data cannot enter canonical reconstruction"
            elif value.provenance_state == ProvenanceState.ESTIMATE:
                rejection_reason = RejectionReason.LOW_CONFIDENCE
                notes = "Estimate data requires explicit authorization"
        
        # Check confidence level for PROVEN data
        if eligibility == ReconstructionEligibility.ELIGIBLE and value.confidence == Confidence.LOW:
            if self.strict_mode:
                eligibility = ReconstructionEligibility.CONDITIONAL
                rejection_reason = RejectionReason.LOW_CONFIDENCE
                notes = "PROVEN data with LOW confidence requires review"
        
        return EligibilityCheck(
            parameter=parameter,
            value=value.value,
            provenance_state=value.provenance_state,
            eligibility=eligibility,
            rejection_reason=rejection_reason,
            confidence=value.confidence,
            notes=notes
        )
    
    def validate_derivation_chain(self, 
                                 parameter: str,
                                 value: ReferenceValue,
                                 derivation_chain: List[ReferenceValue]) -> EligibilityCheck:
        """Validate derivation chain for derived values.
        
        Args:
            parameter: Parameter name
            value: Reference value to validate
            derivation_chain: Chain of values used in derivation
            
        Returns:
            Eligibility check result with derivation validation
        """
        # Start with basic validation
        check = self.validate_parameter(parameter, value)
        
        # Additional validation for derived values
        if value.provenance_state == ProvenanceState.DERIVED:
            # Check that all parent inputs are eligible
            for parent_value in derivation_chain:
                parent_check = self.validate_parameter(parent_value.parameter, parent_value)
                if not parent_check.is_eligible():
                    check.eligibility = ReconstructionEligibility.NOT_ELIGIBLE
                    check.rejection_reason = RejectionReason.CONTAMINATED_CHAIN
                    check.notes = f"Derived from ineligible parameter: {parent_value.parameter}"
                    break
        
        return check
    
    def validate_dataset(self, dataset) -> ReconstructionGateResult:
        """Validate entire dataset for reconstruction eligibility.
        
        Args:
            dataset: Reference dataset to validate
            
        Returns:
            Reconstruction gate result
        """
        checks = []
        rejection_reasons = {}
        errors = []
        warnings = []
        
        for value_id, value in dataset.values.items():
            check = self.validate_parameter(value.parameter, value)
            checks.append(check)
            
            if check.is_rejected():
                rejection_reasons[value.parameter] = check.rejection_reason
                errors.append(f"{value.parameter}: {check.notes}")
            elif check.eligibility == ReconstructionEligibility.CONDITIONAL:
                warnings.append(f"{value.parameter}: {check.notes}")
        
        eligible_count = sum(1 for check in checks if check.is_eligible())
        rejected_count = sum(1 for check in checks if check.is_rejected())
        conditional_count = sum(1 for check in checks if check.eligibility == ReconstructionEligibility.CONDITIONAL)
        
        passed = rejected_count == 0
        
        return ReconstructionGateResult(
            gate_name="reconstruction_eligibility",
            passed=passed,
            total_parameters=len(checks),
            eligible_parameters=eligible_count,
            rejected_parameters=rejected_count,
            conditional_parameters=conditional_count,
            rejection_reasons=rejection_reasons,
            errors=errors,
            warnings=warnings
        )
    
    def validate_provenance_gate(self, provenance_state: ProvenanceState) -> bool:
        """Quick check if provenance state can pass reconstruction gate.
        
        Args:
            provenance_state: Provenance state to check
            
        Returns:
            True if state can pass, False otherwise
        """
        eligibility = self.rejection_policy.get(provenance_state, 
                                                      ReconstructionEligibility.NOT_ELIGIBLE)
        # In strict mode, only ELIGIBLE states pass (not CONDITIONAL)
        if self.strict_mode:
            return eligibility == ReconstructionEligibility.ELIGIBLE
        else:
            return eligibility in [ReconstructionEligibility.ELIGIBLE, ReconstructionEligibility.CONDITIONAL]