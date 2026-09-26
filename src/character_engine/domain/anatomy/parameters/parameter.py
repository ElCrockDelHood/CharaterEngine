"""Anatomical parameter model for deterministic reconstruction.

This module defines the data structures for representing anatomical parameters
with full provenance tracking and validation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import date

from ..reference import Confidence
from ..coordinate_system import LateralSide


class ParameterStatus(Enum):
    """Status of anatomical parameter value."""
    DIRECT_REFERENCE = "direct_reference"  # Directly from reference data
    DERIVED = "derived"  # Calculated from other parameters
    ASSUMED = "assumed"  # Assumed value (not from reference)
    UNKNOWN = "unknown"  # Value not yet determined


class ParameterType(Enum):
    """Type of anatomical parameter."""
    SCALAR = "scalar"  # Single numerical value
    VECTOR = "vector"  # 3D coordinate (x, y, z)
    ANGLE = "angle"  # Angular measurement
    RATIO = "ratio"  # Proportion/ratio
    LENGTH = "length"  # Linear measurement
    DIMENSION = "dimension"  # Multi-dimensional measurement


@dataclass(frozen=True)
class ParameterConstraint:
    """Constraint definition for parameter validation.
    
    Attributes:
        min_value: Minimum allowed value (None if no minimum)
        max_value: Maximum allowed value (None if no maximum)
        unit: Unit for constraint validation
        description: Description of constraint
    """
    
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: str = "meters"
    description: str = ""
    
    def is_valid(self, value: float) -> bool:
        """Check if value satisfies constraint."""
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        return True
    
    def get_validation_error(self, value: float) -> Optional[str]:
        """Get validation error message if value violates constraint."""
        if self.min_value is not None and value < self.min_value:
            return f"Value {value} below minimum {self.min_value}"
        if self.max_value is not None and value > self.max_value:
            return f"Value {value} above maximum {self.max_value}"
        return None


@dataclass(frozen=True)
class DerivationMetadata:
    """Metadata for derived parameters.
    
    Attributes:
        parent_parameters: List of parameter IDs used in derivation
        formula: Formula or calculation method used
        formula_version: Version of formula used
        derivation_date: Date of derivation
        notes: Additional derivation context
    """
    
    parent_parameters: tuple[str, ...] = field(default_factory=tuple)
    formula: str = ""
    formula_version: str = "1.0.0"
    derivation_date: date = field(default_factory=date.today)
    notes: str = ""


@dataclass(frozen=True)
class AnatomicalParameter:
    """Anatomical parameter with full provenance tracking.
    
    Attributes:
        id: Unique identifier for the parameter
        name: Human-readable parameter name
        canonical_name: Canonical parameter name
        parameter_type: Type of parameter (scalar, vector, angle, etc.)
        value: Numerical value (None if unknown)
        unit: Unit of measurement
        status: Status of parameter value
        confidence: Confidence in value
        source_id: Reference to source ID
        derivation: Derivation metadata if derived
        constraints: Validation constraints
        bilateral: Whether parameter is bilateral (left/right)
        side: Lateral side if bilateral
        metadata: Additional metadata
        version: Parameter version
        created_at: Creation timestamp
    """
    
    id: str
    name: str
    canonical_name: str
    parameter_type: ParameterType
    value: Optional[float]
    unit: str
    status: ParameterStatus
    confidence: Confidence = Confidence.UNKNOWN
    source_id: Optional[str] = None
    derivation: Optional[DerivationMetadata] = None
    constraints: Optional[ParameterConstraint] = None
    bilateral: bool = False
    side: Optional[LateralSide] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: date = field(default_factory=date.today)
    
    def is_known(self) -> bool:
        """Check if parameter value is known."""
        return self.value is not None
    
    def is_unknown(self) -> bool:
        """Check if parameter value is unknown."""
        return self.value is None
    
    def is_derived(self) -> bool:
        """Check if parameter is derived."""
        return self.status == ParameterStatus.DERIVED
    
    def is_assumed(self) -> bool:
        """Check if parameter is assumed."""
        return self.status == ParameterStatus.ASSUMED
    
    def is_direct_reference(self) -> bool:
        """Check if parameter is direct reference."""
        return self.status == ParameterStatus.DIRECT_REFERENCE
    
    def is_bilateral(self) -> bool:
        """Check if parameter is bilateral."""
        return self.bilateral
    
    def get_side(self) -> Optional[LateralSide]:
        """Get lateral side."""
        return self.side
    
    def satisfies_constraints(self) -> bool:
        """Check if parameter value satisfies constraints."""
        if self.constraints is None or self.value is None:
            return True
        return self.constraints.is_valid(self.value)
    
    def get_constraint_error(self) -> Optional[str]:
        """Get constraint validation error."""
        if self.constraints is None or self.value is None:
            return None
        return self.constraints.get_validation_error(self.value)
    
    def is_high_confidence(self) -> bool:
        """Check if parameter has high confidence."""
        return self.confidence == Confidence.HIGH
    
    def get_value_or_default(self, default: float = 0.0) -> float:
        """Get value or default if unknown."""
        return self.value if self.value is not None else default


@dataclass(frozen=True)
class ParameterSet:
    """Collection of anatomical parameters.
    
    Attributes:
        set_id: Unique identifier for the parameter set
        name: Name of the parameter set
        version: Version of the parameter set
        parameters: Dictionary of parameters by ID
        created_at: Creation timestamp
    """
    
    set_id: str
    name: str
    version: str
    parameters: Dict[str, AnatomicalParameter]
    created_at: date = field(default_factory=date.today)
    
    def get_parameter(self, parameter_id: str) -> Optional[AnatomicalParameter]:
        """Get parameter by ID."""
        return self.parameters.get(parameter_id)
    
    def get_parameter_by_canonical_name(self, canonical_name: str) -> Optional[AnatomicalParameter]:
        """Get parameter by canonical name."""
        for param in self.parameters.values():
            if param.canonical_name == canonical_name:
                return param
        return None
    
    def get_bilateral_pair(self, parameter_name: str) -> tuple[Optional[AnatomicalParameter], Optional[AnatomicalParameter]]:
        """Get left and right versions of a bilateral parameter."""
        left = self.get_parameter_by_canonical_name(f"{parameter_name}_L")
        right = self.get_parameter_by_canonical_name(f"{parameter_name}_R")
        return left, right
    
    def get_parameters_by_type(self, parameter_type: ParameterType) -> list[AnatomicalParameter]:
        """Get all parameters of a specific type."""
        return [p for p in self.parameters.values() if p.parameter_type == parameter_type]
    
    def get_known_parameters(self) -> list[AnatomicalParameter]:
        """Get all parameters with known values."""
        return [p for p in self.parameters.values() if p.is_known()]
    
    def get_unknown_parameters(self) -> list[AnatomicalParameter]:
        """Get all parameters with unknown values."""
        return [p for p in self.parameters.values() if p.is_unknown()]
    
    def get_derived_parameters(self) -> list[AnatomicalParameter]:
        """Get all derived parameters."""
        return [p for p in self.parameters.values() if p.is_derived()]
    
    def get_assumed_parameters(self) -> list[AnatomicalParameter]:
        """Get all assumed parameters."""
        return [p for p in self.parameters.values() if p.is_assumed()]
    
    def validate_constraints(self) -> Dict[str, bool]:
        """Validate all parameter constraints.
        
        Returns:
            Dictionary mapping parameter IDs to validation results
        """
        results = {}
        for param_id, param in self.parameters.items():
            results[param_id] = param.satisfies_constraints()
        return results
    
    def get_constraint_violations(self) -> Dict[str, str]:
        """Get constraint violations.
        
        Returns:
            Dictionary mapping parameter IDs to violation messages
        """
        violations = {}
        for param_id, param in self.parameters.items():
            error = param.get_constraint_error()
            if error:
                violations[param_id] = error
        return violations


class ParameterSetBuilder:
    """Builder for creating parameter sets."""
    
    def __init__(self, set_id: str, name: str, version: str):
        self.set_id = set_id
        self.name = name
        self.version = version
        self.parameters: Dict[str, AnatomicalParameter] = {}
    
    def add_parameter(self, parameter: AnatomicalParameter) -> "ParameterSetBuilder":
        """Add a parameter to the set."""
        self.parameters[parameter.id] = parameter
        return self
    
    def build(self) -> ParameterSet:
        """Build the parameter set."""
        return ParameterSet(
            set_id=self.set_id,
            name=self.name,
            version=self.version,
            parameters=dict(self.parameters)
        )


def create_unknown_parameter(canonical_name: str, unit: str, 
                            parameter_type: ParameterType = ParameterType.SCALAR) -> AnatomicalParameter:
    """Create a placeholder unknown parameter."""
    return AnatomicalParameter(
        id=f"UNKNOWN_{canonical_name}",
        name=f"Unknown {canonical_name}",
        canonical_name=canonical_name,
        parameter_type=parameter_type,
        value=None,
        unit=unit,
        status=ParameterStatus.UNKNOWN,
        confidence=Confidence.UNKNOWN,
        metadata={"notes": "Parameter value not yet determined"}
    )


def create_assumed_parameter(canonical_name: str, value: float, unit: str,
                             notes: str = "",
                             parameter_type: ParameterType = ParameterType.SCALAR) -> AnatomicalParameter:
    """Create a placeholder assumed parameter."""
    return AnatomicalParameter(
        id=f"ASSUMED_{canonical_name}",
        name=f"Assumed {canonical_name}",
        canonical_name=canonical_name,
        parameter_type=parameter_type,
        value=value,
        unit=unit,
        status=ParameterStatus.ASSUMED,
        confidence=Confidence.LOW,
        metadata={"notes": f"Assumed value: {notes}"}
    )


def create_derived_parameter(canonical_name: str, value: float, unit: str,
                             parent_parameters: tuple[str, ...],
                             formula: str,
                             parameter_type: ParameterType = ParameterType.SCALAR) -> AnatomicalParameter:
    """Create a derived parameter."""
    return AnatomicalParameter(
        id=f"DERIVED_{canonical_name}",
        name=f"Derived {canonical_name}",
        canonical_name=canonical_name,
        parameter_type=parameter_type,
        value=value,
        unit=unit,
        status=ParameterStatus.DERIVED,
        confidence=Confidence.MEDIUM,
        derivation=DerivationMetadata(
            parent_parameters=parent_parameters,
            formula=formula
        )
    )


def create_direct_reference_parameter(canonical_name: str, value: float, unit: str,
                                      source_id: str,
                                      parameter_type: ParameterType = ParameterType.SCALAR) -> AnatomicalParameter:
    """Create a direct reference parameter."""
    return AnatomicalParameter(
        id=f"REF_{canonical_name}",
        name=f"Reference {canonical_name}",
        canonical_name=canonical_name,
        parameter_type=parameter_type,
        value=value,
        unit=unit,
        status=ParameterStatus.DIRECT_REFERENCE,
        confidence=Confidence.HIGH,
        source_id=source_id
    )


@dataclass
class SubjectProfile:
    """Subject profile for anatomical reconstruction.
    
    Attributes:
        height: Total body height in meters
        weight: Total body weight in kg
        age: Subject age in years
        gender: Biological gender (male, female, other)
        ethnicity: Ethnic background
        notes: Additional notes
    """
    
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    ethnicity: Optional[str] = None
    notes: str = ""
