"""Reference data infrastructure for anatomical reconstruction."""

from .reference_manager import (
    ReferenceSourceEntry,
    ReferenceData,
    ReferenceRegistry,
    ReferenceDataManager
)

from .source import (
    ReferenceSource,
    ReferenceValue,
    ReferenceDataset,
    ReferenceDatasetBuilder,
    SourceType,
    Confidence,
    ProvenanceState,
    UNKNOWN_SOURCE,
    create_unknown_value,
    create_assumed_value,
    create_placeholder_value,
    create_proven_value
)

from .eligibility import (
    ReconstructionEligibility,
    RejectionReason,
    EligibilityCheck,
    ReconstructionGateResult,
    ReconstructionEligibilityValidator
)

__all__ = [
    'ReferenceSourceEntry',
    'ReferenceData',
    'ReferenceRegistry',
    'ReferenceDataManager',
    'ReferenceSource',
    'ReferenceValue',
    'ReferenceDataset',
    'ReferenceDatasetBuilder',
    'SourceType',
    'Confidence',
    'ProvenanceState',
    'UNKNOWN_SOURCE',
    'create_unknown_value',
    'create_assumed_value',
    'create_placeholder_value',
    'create_proven_value',
    'ReconstructionEligibility',
    'RejectionReason',
    'EligibilityCheck',
    'ReconstructionGateResult',
    'ReconstructionEligibilityValidator'
]