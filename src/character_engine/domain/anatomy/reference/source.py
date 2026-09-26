"""Reference source model for anatomical reconstruction.

This module defines the data structures for representing reference sources
that provide anatomical data for reconstruction.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import date
from uuid import UUID, uuid4


class SourceType(Enum):
    """Types of reference sources."""
    PRIMARY_RESEARCH = "primary_research"
    STANDARD = "standard"
    DATABASE = "database"
    TEXTBOOK = "textbook"
    SECONDARY_REFERENCE = "secondary_reference"
    ASSUMPTION = "assumption"
    DERIVED = "derived"


class Confidence(Enum):
    """Confidence level for reference data."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ProvenanceState(Enum):
    """Provenance state for anatomical values.
    
    Critical: These states determine reconstruction eligibility.
    """
    PROVEN = "proven"  # Reference-backed with citation
    DERIVED = "derived"  # Calculated from PROVEN inputs
    ESTIMATE = "estimate"  # Approximate value with known uncertainty
    ASSUMED = "assumed"  # Assumed value without reference backing
    PLACEHOLDER = "placeholder"  # Temporary placeholder for testing
    UNKNOWN = "unknown"  # Value not yet determined
    USER_INPUT = "user_input"  # Provided by user (may be any provenance)


@dataclass(frozen=True)
class ReferenceSource:
    """Reference source for anatomical data.
    
    Attributes:
        source_id: Unique identifier for the source
        name: Name/title of the source
        type: Type of source (research, standard, database, etc.)
        authors: Authors or institution responsible
        year: Publication year
        doi: Digital Object Identifier where available
        url: URL where available
        sample_size: Sample size for studies
        population: Population description
        confidence: Subjective confidence assessment
        notes: Additional context or limitations
    """
    
    source_id: str
    name: str
    type: SourceType
    authors: str
    year: int
    doi: Optional[str] = None
    url: Optional[str] = None
    sample_size: Optional[int] = None
    population: Optional[str] = None
    confidence: Confidence = Confidence.UNKNOWN
    notes: str = ""
    
    def is_high_confidence(self) -> bool:
        """Check if source has high confidence."""
        return self.confidence == Confidence.HIGH
    
    def is_primary_research(self) -> bool:
        """Check if source is primary research."""
        return self.type == SourceType.PRIMARY_RESEARCH
    
    def is_standard(self) -> bool:
        """Check if source is an established standard."""
        return self.type == SourceType.STANDARD
    
    def has_bibliographic_info(self) -> bool:
        """Check if source has complete bibliographic information."""
        return bool(self.authors and self.year)
    
    def has_doi(self) -> bool:
        """Check if source has DOI."""
        return bool(self.doi)
    
    def has_url(self) -> bool:
        """Check if source has URL."""
        return bool(self.url)


@dataclass(frozen=True)
class ReferenceValue:
    """Individual reference value for anatomical parameter.
    
    Attributes:
        value_id: Unique identifier for the value
        parameter: Parameter name this value provides
        value: Numerical value (None if unknown)
        unit: Unit of measurement
        source_id: Reference to source ID
        provenance_state: Provenance state of this value
        population: Target population
        age_range: Applicable age range (e.g., "18-65")
        gender: Applicable gender
        confidence: Value confidence level
        derivation: How value was obtained
        uncertainty: Measurement uncertainty when available
        sample_size: Sample size from source
        notes: Additional context
    """
    
    value_id: str
    parameter: str
    value: Optional[float]
    unit: str
    source_id: str
    provenance_state: ProvenanceState = ProvenanceState.UNKNOWN
    population: Optional[str] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None
    confidence: Confidence = Confidence.UNKNOWN
    derivation: str = "UNKNOWN"
    uncertainty: Optional[float] = None
    sample_size: Optional[int] = None
    notes: str = ""
    
    def is_known(self) -> bool:
        """Check if value is known (not None)."""
        return self.value is not None
    
    def is_proven(self) -> bool:
        """Check if value is PROVEN (reference-backed)."""
        return self.provenance_state == ProvenanceState.PROVEN
    
    def is_derived(self) -> bool:
        """Check if value is DERIVED from other data."""
        return self.provenance_state == ProvenanceState.DERIVED
    
    def is_assumed(self) -> bool:
        """Check if value is ASSUMED (not from reference)."""
        return self.provenance_state == ProvenanceState.ASSUMED
    
    def is_placeholder(self) -> bool:
        """Check if value is PLACEHOLDER (for testing only)."""
        return self.provenance_state == ProvenanceState.PLACEHOLDER
    
    def is_unknown(self) -> bool:
        """Check if value is UNKNOWN."""
        return self.provenance_state == ProvenanceState.UNKNOWN
    
    def is_estimate(self) -> bool:
        """Check if value is ESTIMATE (approximate)."""
        return self.provenance_state == ProvenanceState.ESTIMATE
    
    def is_reconstruction_eligible(self) -> bool:
        """Check if value is eligible for canonical reconstruction."""
        return self.provenance_state in [ProvenanceState.PROVEN, ProvenanceState.DERIVED]
    
    def get_value_or_default(self, default: float = 0.0) -> float:
        """Get value or default if unknown."""
        return self.value if self.value is not None else default


@dataclass(frozen=True)
class ReferenceDataset:
    """Collection of reference values for anatomical reconstruction.
    
    Attributes:
        dataset_id: Unique identifier for the dataset
        name: Name of the dataset
        version: Version of the dataset
        sources: Dictionary of reference sources
        values: Dictionary of reference values
        created_at: Creation timestamp
    """
    
    dataset_id: str
    name: str
    version: str
    sources: dict[str, ReferenceSource]
    values: dict[str, ReferenceValue]
    created_at: date = field(default_factory=date.today)
    
    def get_source(self, source_id: str) -> Optional[ReferenceSource]:
        """Get source by ID."""
        return self.sources.get(source_id)
    
    def get_value(self, value_id: str) -> Optional[ReferenceValue]:
        """Get value by ID."""
        return self.values.get(value_id)
    
    def get_values_by_parameter(self, parameter: str) -> List[ReferenceValue]:
        """Get all values for a specific parameter."""
        return [v for v in self.values.values() if v.parameter == parameter]
    
    def get_values_by_source(self, source_id: str) -> List[ReferenceValue]:
        """Get all values from a specific source."""
        return [v for v in self.values.values() if v.source_id == source_id]
    
    def has_known_value(self, parameter: str) -> bool:
        """Check if parameter has at least one known value."""
        values = self.get_values_by_parameter(parameter)
        return any(v.is_known() for v in values)
    
    def get_best_value(self, parameter: str) -> Optional[ReferenceValue]:
        """Get the best (highest confidence) value for a parameter."""
        values = self.get_values_by_parameter(parameter)
        known_values = [v for v in values if v.is_known()]
        
        if not known_values:
            return None
        
        # Sort by confidence (HIGH > MEDIUM > LOW > UNKNOWN)
        confidence_order = {
            Confidence.HIGH: 0,
            Confidence.MEDIUM: 1,
            Confidence.LOW: 2,
            Confidence.UNKNOWN: 3
        }
        
        known_values.sort(key=lambda v: confidence_order.get(v.confidence, 99))
        return known_values[0]
    
    def add_source(self, source: ReferenceSource) -> None:
        """Add a source to the dataset (returns new dataset)."""
        # Note: Since dataset is frozen, this would create a new instance
        # This is a placeholder for the API
        raise NotImplementedError("Use dataset builder to create new datasets")
    
    def add_value(self, value: ReferenceValue) -> None:
        """Add a value to the dataset (returns new dataset)."""
        # Note: Since dataset is frozen, this would create a new instance
        # This is a placeholder for the API
        raise NotImplementedError("Use dataset builder to create new datasets")


class ReferenceDatasetBuilder:
    """Builder for creating reference datasets."""
    
    def __init__(self, dataset_id: str, name: str, version: str):
        self.dataset_id = dataset_id
        self.name = name
        self.version = version
        self.sources: dict[str, ReferenceSource] = {}
        self.values: dict[str, ReferenceValue] = {}
    
    def add_source(self, source: ReferenceSource) -> "ReferenceDatasetBuilder":
        """Add a reference source."""
        self.sources[source.source_id] = source
        return self
    
    def add_value(self, value: ReferenceValue) -> "ReferenceDatasetBuilder":
        """Add a reference value."""
        self.values[value.value_id] = value
        return self
    
    def build(self) -> ReferenceDataset:
        """Build the reference dataset."""
        return ReferenceDataset(
            dataset_id=self.dataset_id,
            name=self.name,
            version=self.version,
            sources=dict(self.sources),
            values=dict(self.values)
        )


# Placeholder sources for unknown data
UNKNOWN_SOURCE = ReferenceSource(
    source_id="UNKNOWN",
    name="Unknown Source",
    type=SourceType.ASSUMPTION,
    authors="Unknown",
    year=2026,
    confidence=Confidence.UNKNOWN,
    notes="Placeholder for data not yet acquired"
)

# Placeholder values for unknown parameters
def create_unknown_value(parameter: str, unit: str) -> ReferenceValue:
    """Create a placeholder unknown value."""
    return ReferenceValue(
        value_id=f"UNKNOWN_{parameter}",
        parameter=parameter,
        value=None,
        unit=unit,
        source_id="UNKNOWN",
        provenance_state=ProvenanceState.UNKNOWN,
        derivation="UNKNOWN",
        confidence=Confidence.UNKNOWN,
        notes="Reference data not yet acquired"
    )


def create_assumed_value(parameter: str, value: float, unit: str, 
                         notes: str = "") -> ReferenceValue:
    """Create a placeholder assumed value."""
    return ReferenceValue(
        value_id=f"ASSUMED_{parameter}",
        parameter=parameter,
        value=value,
        unit=unit,
        source_id="UNKNOWN",
        provenance_state=ProvenanceState.ASSUMED,
        confidence=Confidence.LOW,
        notes=f"Assumed value: {notes}"
    )


def create_placeholder_value(parameter: str, value: float, unit: str,
                           notes: str = "") -> ReferenceValue:
    """Create an explicit placeholder value for testing."""
    return ReferenceValue(
        value_id=f"PLACEHOLDER_{parameter}",
        parameter=parameter,
        value=value,
        unit=unit,
        source_id="UNKNOWN",
        provenance_state=ProvenanceState.PLACEHOLDER,
        confidence=Confidence.LOW,
        notes=f"Placeholder value for testing: {notes}"
    )


def create_proven_value(parameter: str, value: float, unit: str,
                       source_id: str, derivation: str = "MEASURED",
                       population: Optional[str] = None,
                       age_range: Optional[str] = None,
                       gender: Optional[str] = None,
                       uncertainty: Optional[float] = None,
                       sample_size: Optional[int] = None,
                       notes: str = "") -> ReferenceValue:
    """Create a proven reference-backed value."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return ReferenceValue(
        value_id=f"PROVEN_{parameter}_{unique_id}",
        parameter=parameter,
        value=value,
        unit=unit,
        source_id=source_id,
        provenance_state=ProvenanceState.PROVEN,
        confidence=Confidence.HIGH,
        derivation=derivation,
        population=population,
        age_range=age_range,
        gender=gender,
        uncertainty=uncertainty,
        sample_size=sample_size,
        notes=notes
    )
