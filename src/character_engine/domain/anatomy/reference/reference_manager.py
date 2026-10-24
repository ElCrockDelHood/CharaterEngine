"""Reference data infrastructure module."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ReferenceSourceEntry:
    """Reference data source definition."""

    id: str
    name: str
    type: str
    coverage: str
    status: str
    required_for: list
    notes: str


@dataclass
class ReferenceData:
    """Reference data with provenance tracking."""

    value: Any
    unit: str
    confidence: str
    provenance: str
    source_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ReferenceRegistry:
    """Registry for anatomical reference data sources."""

    def __init__(self, registry_path: Path):
        """Initialize reference registry.

        Args:
            registry_path: Path to source registry JSON file
        """
        self.registry_path = registry_path
        self.sources: Dict[str, ReferenceSourceEntry] = {}
        self.placeholder_data: Dict[str, Dict[str, Any]] = {}
        self._load_registry()

    def _load_registry(self):
        """Load source registry from JSON file."""
        if self.registry_path.exists():
            with open(self.registry_path) as f:
                data = json.load(f)

            # Load sources
            for sources in data.get('sources', {}).values():
                for source_id, source_data in sources.items():
                    self.sources[source_id] = ReferenceSourceEntry(
                        id=source_id,
                        name=source_data['name'],
                        type=source_data['type'],
                        coverage=source_data['coverage'],
                        status=source_data['status'],
                        required_for=source_data['required_for'],
                        notes=source_data['notes']
                    )

            # Load placeholder data
            self.placeholder_data = data.get('placeholder_data', {})

    def get_source(self, source_id: str) -> Optional[ReferenceSourceEntry]:
        """Get reference source by ID.

        Args:
            source_id: Source identifier

        Returns:
            ReferenceSourceEntry if found, None otherwise
        """
        return self.sources.get(source_id)

    def get_placeholder_data(self, category: str, key: str) -> ReferenceData:
        """Get placeholder reference data.

        Args:
            category: Data category (e.g., 'anthropometric_averages')
            key: Data key within category

        Returns:
            ReferenceData with placeholder information
        """
        if category not in self.placeholder_data:
            raise ValueError(f"Category '{category}' not found in placeholder data")

        category_data = self.placeholder_data[category]
        values = category_data.get('values', {})

        if key not in values:
            raise ValueError(f"Key '{key}' not found in category '{category}'")

        data = values[key]

        return ReferenceData(
            value=data.get('value'),
            unit=data.get('unit', 'meters'),
            confidence=data.get('confidence', 'LOW'),
            provenance=data.get('provenance', 'ASSUMPTION'),
            metadata={'category': category, 'key': key}
        )

    def get_all_sources(self) -> Dict[str, ReferenceSourceEntry]:
        """Get all registered reference sources.

        Returns:
            Dictionary of all sources by ID
        """
        return self.sources.copy()

    def get_placeholder_categories(self) -> list:
        """Get all placeholder data categories.

        Returns:
            List of category names
        """
        return list(self.placeholder_data.keys())


class ReferenceDataManager:
    """Manager for anatomical reference data."""

    def __init__(self, references_dir: Path):
        """Initialize reference data manager.

        Args:
            references_dir: Directory containing reference data files
        """
        self.references_dir = references_dir
        self.registry = ReferenceRegistry(references_dir / "source_registry.json")

        # Load anthropometry data and extract the inner structure
        anthropometry_json = self._load_json(references_dir / "anthropometry.json")
        self.anthropometry_data = anthropometry_json.get('anthropometric_data', {})

        # Load biomechanics data and extract the inner structure
        biomechanics_json = self._load_json(references_dir / "biomechanics.json")
        self.biomechanics_data = biomechanics_json.get('biomechanical_data', {})

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON data from file.

        Args:
            file_path: Path to JSON file

        Returns:
            Dictionary of JSON data
        """
        if file_path.exists():
            with open(file_path) as f:
                return json.load(f)
        return {}

    def get_anthropometric_parameter(self, parameter_name: str) -> ReferenceData:
        """Get anthropometric parameter with provenance.

        Args:
            parameter_name: Name of the parameter (e.g., 'height', 'shoulder_width')

        Returns:
            ReferenceData with parameter information
        """
        # Search in global parameters
        global_params = self.anthropometry_data.get('global_parameters', {})
        if parameter_name in global_params:
            data = global_params[parameter_name]
            return ReferenceData(
                value=data.get('value', data.get('assumed_value', data.get('mean'))),
                unit=data.get('unit', 'meters'),
                confidence=data.get('confidence', 'LOW'),
                provenance=data.get('provenance', 'ASSUMPTION'),
                source_id='PLACEHOLDER',
                metadata={'parameter': parameter_name}
            )

        # Search in proportions
        proportions = self.anthropometry_data.get('body_proportions', {})
        if parameter_name in proportions:
            data = proportions[parameter_name]
            return ReferenceData(
                value=data.get('value'),
                unit='ratio',
                confidence=data.get('confidence', 'LOW'),
                provenance=data.get('provenance', 'ASSUMPTION'),
                source_id='PLACEHOLDER',
                metadata={'parameter': parameter_name}
            )

        raise ValueError(f"Parameter '{parameter_name}' not found in anthropometric data")

    def get_joint_center_offset(self, joint_name: str) -> ReferenceData:
        """Get joint center offset with provenance.

        Args:
            joint_name: Name of the joint (e.g., 'shoulder', 'elbow')

        Returns:
            ReferenceData with offset information
        """
        joint_centers = self.biomechanics_data.get('joint_centers', {})
        if joint_name not in joint_centers:
            raise ValueError(f"Joint '{joint_name}' not found in biomechanical data")

        joint_data = joint_centers[joint_name]
        # Find the first joint center (there may be multiple per joint)
        for joint_center_name, center_data in joint_data.items():
            if 'offset' in joint_center_name.lower():
                data = center_data
                return ReferenceData(
                    value=data.get('value'),
                    unit=data.get('unit', 'meters'),
                    confidence=data.get('confidence', 'LOW'),
                    provenance=data.get('provenance', 'ASSUMPTION'),
                    source_id='PLACEHOLDER',
                    metadata={'joint': joint_name, 'center': joint_center_name}
                )

        # If no offset found, return the first available center
        for joint_center_name, center_data in joint_data.items():
            data = center_data
            return ReferenceData(
                value=data.get('value'),
                unit=data.get('unit', 'meters'),
                confidence=data.get('confidence', 'LOW'),
                provenance=data.get('provenance', 'ASSUMPTION'),
                source_id='PLACEHOLDER',
                metadata={'joint': joint_name, 'center': joint_center_name}
            )

    def get_gender_adjustment(self, gender: str, parameter_name: str) -> ReferenceData:
        """Get gender-specific adjustment for a parameter.

        Args:
            gender: Gender (e.g., 'male', 'female')
            parameter_name: Name of the parameter

        Returns:
            ReferenceData with adjustment information
        """
        gender_data = self.anthropometry_data.get('gender_specific_adjustments', {})
        if gender.lower() not in gender_data:
            raise ValueError(f"Gender '{gender}' not found in gender-specific adjustments")

        gender_params = gender_data[gender.lower()]
        if parameter_name not in gender_params:
            raise ValueError(f"Parameter '{parameter_name}' not found for gender '{gender}'")

        data = gender_params[parameter_name]
        return ReferenceData(
            value=data.get('value'),
            unit='ratio',
            confidence=data.get('confidence', 'LOW'),
            provenance=data.get('provenance', 'ASSUMPTION'),
            source_id='PLACEHOLDER',
            metadata={'gender': gender, 'parameter': parameter_name}
        )

    def get_data_quality_report(self) -> Dict[str, str]:
        """Get data quality report.

        Returns:
            Dictionary with quality metrics
        """
        anthropometric_quality = self.anthropometry_data.get('data_quality', {})
        biomechanical_quality = self.biomechanics_data.get('data_quality', {})

        return {
            'anthropometric_accuracy': anthropometric_quality.get('accuracy', 'UNKNOWN'),
            'anthropometric_precision': anthropometric_quality.get('precision', 'UNKNOWN'),
            'anthropometric_completeness': anthropometric_quality.get('completeness', 'UNKNOWN'),
            'biomechanical_accuracy': biomechanical_quality.get('accuracy', 'UNKNOWN'),
            'biomechanical_precision': biomechanical_quality.get('precision', 'UNKNOWN'),
            'biomechanical_completeness': biomechanical_quality.get('completeness', 'UNKNOWN'),
            'overall_status': 'PLACEHOLDER_DATA'
        }
