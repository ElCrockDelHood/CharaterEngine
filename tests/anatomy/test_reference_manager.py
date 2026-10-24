"""Tests for reference data infrastructure."""

import json

import pytest

from character_engine.domain.anatomy.reference import (
    ReferenceDataManager,
    ReferenceRegistry,
)


class TestReferenceRegistry:
    """Test reference registry functionality."""

    @pytest.fixture
    def sample_registry(self, tmp_path):
        """Create a sample source registry for testing."""
        registry_data = {
            "source_registry": {
                "version": "1.0.0",
                "status": "PLACEHOLDER"
            },
            "sources": {
                "anthropometric_data": {
                    "nhanes": {
                        "id": "nhanes",
                        "name": "National Health and Nutrition Examination Survey",
                        "type": "ANTHROPOMETRIC_DATABASE",
                        "coverage": "US population",
                        "status": "NOT_ACQUIRED",
                        "required_for": ["height_data"],
                        "notes": "Primary source"
                    }
                }
            },
            "placeholder_data": {
                "anthropometric_averages": {
                    "status": "PLACEHOLDER",
                    "values": {
                        "height": {
                            "value": 1.75,
                            "unit": "meters",
                            "confidence": "LOW",
                            "provenance": "ASSUMPTION"
                        }
                    }
                }
            }
        }

        registry_file = tmp_path / "source_registry.json"
        with open(registry_file, 'w') as f:
            json.dump(registry_data, f)

        return registry_file

    def test_load_registry(self, sample_registry):
        """Test loading source registry from JSON."""
        registry = ReferenceRegistry(sample_registry)

        assert len(registry.sources) == 1
        assert "nhanes" in registry.sources

        source = registry.get_source("nhanes")
        assert source is not None
        assert source.name == "National Health and Nutrition Examination Survey"
        assert source.status == "NOT_ACQUIRED"

    def test_get_placeholder_data(self, sample_registry):
        """Test getting placeholder reference data."""
        registry = ReferenceRegistry(sample_registry)

        data = registry.get_placeholder_data("anthropometric_averages", "height")

        assert data.value == 1.75
        assert data.unit == "meters"
        assert data.confidence == "LOW"
        assert data.provenance == "ASSUMPTION"

    def test_get_placeholder_data_invalid_category(self, sample_registry):
        """Test getting placeholder data with invalid category."""
        registry = ReferenceRegistry(sample_registry)

        with pytest.raises(ValueError, match="Category 'invalid' not found"):
            registry.get_placeholder_data("invalid", "height")

    def test_get_placeholder_data_invalid_key(self, sample_registry):
        """Test getting placeholder data with invalid key."""
        registry = ReferenceRegistry(sample_registry)

        with pytest.raises(ValueError, match="Key 'invalid' not found"):
            registry.get_placeholder_data("anthropometric_averages", "invalid")

    def test_get_all_sources(self, sample_registry):
        """Test getting all registered sources."""
        registry = ReferenceRegistry(sample_registry)

        sources = registry.get_all_sources()

        assert len(sources) == 1
        assert "nhanes" in sources

    def test_get_placeholder_categories(self, sample_registry):
        """Test getting all placeholder categories."""
        registry = ReferenceRegistry(sample_registry)

        categories = registry.get_placeholder_categories()

        assert len(categories) == 1
        assert "anthropometric_averages" in categories


class TestReferenceDataManager:
    """Test reference data manager functionality."""

    @pytest.fixture
    def sample_references_dir(self, tmp_path):
        """Create sample reference data files for testing."""
        references_dir = tmp_path / "references"
        references_dir.mkdir()

        # Create source registry
        registry_data = {
            "source_registry": {
                "version": "1.0.0",
                "status": "PLACEHOLDER"
            },
            "sources": {},
            "placeholder_data": {
                "anthropometric_averages": {
                    "status": "PLACEHOLDER",
                    "values": {
                        "height": {
                            "value": 1.75,
                            "unit": "meters",
                            "confidence": "LOW",
                            "provenance": "ASSUMPTION"
                        }
                    }
                }
            }
        }

        with open(references_dir / "source_registry.json", 'w') as f:
            json.dump(registry_data, f)

        # Create anthropometry data
        anthropometry_data = {
            "anthropometric_data": {
                "version": "1.0.0",
                "status": "PLACEHOLDER",
                "global_parameters": {
                    "height": {
                        "value": 1.75,
                        "unit": "meters",
                        "confidence": "LOW",
                        "provenance": "ASSUMPTION"
                    }
                },
                "body_proportions": {
                    "head_height_ratio": {
                        "value": 0.125,
                        "confidence": "LOW",
                        "provenance": "ASSUMPTION"
                    }
                }
            }
        }

        with open(references_dir / "anthropometry.json", 'w') as f:
            json.dump(anthropometry_data, f)

        # Create biomechanics data
        biomechanics_data = {
            "biomechanical_data": {
                "version": "1.0.0",
                "status": "PLACEHOLDER",
                "joint_centers": {
                    "shoulder": {
                        "glenohumeral": {
                            "value": 0.020,
                            "unit": "meters",
                            "confidence": "LOW",
                            "provenance": "ASSUMPTION"
                        }
                    }
                }
            }
        }

        with open(references_dir / "biomechanics.json", 'w') as f:
            json.dump(biomechanics_data, f)

        return references_dir

    def test_initialization(self, sample_references_dir):
        """Test reference data manager initialization."""
        manager = ReferenceDataManager(sample_references_dir)

        assert manager.registry is not None
        assert manager.anthropometry_data is not None
        assert manager.biomechanics_data is not None

    def test_get_anthropometric_parameter(self, sample_references_dir):
        """Test getting anthropometric parameter."""
        manager = ReferenceDataManager(sample_references_dir)

        data = manager.get_anthropometric_parameter('height')

        assert data.value == 1.75
        assert data.unit == "meters"
        assert data.confidence == "LOW"
        assert data.provenance == "ASSUMPTION"

    def test_get_anthropometric_parameter_invalid(self, sample_references_dir):
        """Test getting invalid anthropometric parameter."""
        manager = ReferenceDataManager(sample_references_dir)

        with pytest.raises(ValueError, match="Parameter 'invalid' not found"):
            manager.get_anthropometric_parameter('invalid')

    def test_get_joint_center_offset(self, sample_references_dir):
        """Test getting joint center offset."""
        manager = ReferenceDataManager(sample_references_dir)

        data = manager.get_joint_center_offset('shoulder')

        assert data.value == 0.020
        assert data.unit == "meters"
        assert data.confidence == "LOW"
        assert data.provenance == "ASSUMPTION"

    def test_get_joint_center_offset_invalid(self, sample_references_dir):
        """Test getting invalid joint center offset."""
        manager = ReferenceDataManager(sample_references_dir)

        with pytest.raises(ValueError, match="Joint 'invalid' not found"):
            manager.get_joint_center_offset('invalid')

    def test_get_gender_adjustment_missing(self, sample_references_dir):
        """Test getting gender adjustment when not present."""
        manager = ReferenceDataManager(sample_references_dir)

        with pytest.raises(ValueError, match="Gender 'male' not found"):
            manager.get_gender_adjustment('male', 'shoulder_to_hip_ratio')

    def test_get_data_quality_report(self, sample_references_dir):
        """Test getting data quality report."""
        manager = ReferenceDataManager(sample_references_dir)

        report = manager.get_data_quality_report()

        assert 'anthropometric_accuracy' in report
        assert 'biomechanical_accuracy' in report
        assert report['overall_status'] == 'PLACEHOLDER_DATA'
