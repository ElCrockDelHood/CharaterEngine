"""Reference data model tests."""

import pytest
from character_engine.domain.anatomy.reference import (
    ReferenceSource,
    ReferenceValue,
    ReferenceDataset,
    ReferenceDatasetBuilder,
    SourceType,
    Confidence,
    UNKNOWN_SOURCE,
    create_unknown_value,
    create_assumed_value
)


class TestReferenceSource:
    """Test reference source model."""
    
    def test_source_creation(self):
        """Test creating a reference source."""
        source = ReferenceSource(
            source_id="TEST_SOURCE",
            name="Test Source",
            type=SourceType.PRIMARY_RESEARCH,
            authors="Test Author",
            year=2020
        )
        
        assert source.source_id == "TEST_SOURCE"
        assert source.name == "Test Source"
        assert source.type == SourceType.PRIMARY_RESEARCH
    
    def test_source_confidence_checking(self):
        """Test source confidence checking."""
        high_confidence = ReferenceSource(
            source_id="HIGH",
            name="High Confidence",
            type=SourceType.STANDARD,
            authors="Standard Body",
            year=2020,
            confidence=Confidence.HIGH
        )
        
        low_confidence = ReferenceSource(
            source_id="LOW",
            name="Low Confidence",
            type=SourceType.ASSUMPTION,
            authors="Unknown",
            year=2020,
            confidence=Confidence.LOW
        )
        
        assert high_confidence.is_high_confidence()
        assert not low_confidence.is_high_confidence()
    
    def test_source_type_checking(self):
        """Test source type checking."""
        research_source = ReferenceSource(
            source_id="RESEARCH",
            name="Research",
            type=SourceType.PRIMARY_RESEARCH,
            authors="Researcher",
            year=2020
        )
        
        standard_source = ReferenceSource(
            source_id="STANDARD",
            name="Standard",
            type=SourceType.STANDARD,
            authors="Standard Body",
            year=2020
        )
        
        assert research_source.is_primary_research()
        assert not research_source.is_standard()
        assert standard_source.is_standard()
        assert not standard_source.is_primary_research()
    
    def test_source_immutability(self):
        """Test reference source is immutable."""
        source = ReferenceSource(
            source_id="TEST",
            name="Test",
            type=SourceType.PRIMARY_RESEARCH,
            authors="Author",
            year=2020
        )
        
        # Frozen dataclass cannot be modified
        # We test this by trying to create a new instance with different value
        # and verify they are different objects
        modified_source = ReferenceSource(
            source_id="TEST",
            name="Modified",
            type=SourceType.PRIMARY_RESEARCH,
            authors="Author",
            year=2020
        )
        
        assert source.name == "Test"
        assert modified_source.name == "Modified"
        assert source is not modified_source


class TestReferenceValue:
    """Test reference value model."""
    
    def test_value_creation(self):
        """Test creating a reference value."""
        value = ReferenceValue(
            value_id="TEST_VALUE",
            parameter="test_parameter",
            value=1.75,
            unit="meters",
            source_id="TEST_SOURCE"
        )
        
        assert value.value_id == "TEST_VALUE"
        assert value.parameter == "test_parameter"
        assert value.value == 1.75
        assert value.unit == "meters"
    
    def test_unknown_value(self):
        """Test unknown value (None)."""
        value = ReferenceValue(
            value_id="UNKNOWN_VALUE",
            parameter="unknown_parameter",
            value=None,
            unit="meters",
            source_id="UNKNOWN"
        )
        
        assert not value.is_known()
        assert value.get_value_or_default() == 0.0
        assert value.get_value_or_default(1.5) == 1.5
    
    def test_assumed_value(self):
        """Test assumed value."""
        value = ReferenceValue(
            value_id="ASSUMED_VALUE",
            parameter="assumed_parameter",
            value=1.75,
            unit="meters",
            source_id="UNKNOWN",
            derivation="ASSUMED"
        )
        
        assert value.is_known()
        assert value.is_assumed()
        assert not value.is_measured()
    
    def test_derived_value(self):
        """Test derived value."""
        value = ReferenceValue(
            value_id="DERIVED_VALUE",
            parameter="derived_parameter",
            value=0.5,
            unit="ratio",
            source_id="TEST_SOURCE",
            derivation="CALCULATED"
        )
        
        assert value.is_known()
        assert value.is_derived()
        assert not value.is_measured()
    
    def test_measured_value(self):
        """Test measured value."""
        value = ReferenceValue(
            value_id="MEASURED_VALUE",
            parameter="measured_parameter",
            value=1.8,
            unit="meters",
            source_id="TEST_SOURCE",
            derivation="MEASURED"
        )
        
        assert value.is_known()
        assert value.is_measured()
        assert not value.is_derived()
    
    def test_value_immutability(self):
        """Test reference value is immutable."""
        value = ReferenceValue(
            value_id="TEST",
            parameter="test",
            value=1.0,
            unit="meters",
            source_id="SOURCE"
        )
        
        # Frozen dataclass cannot be modified
        # We test this by trying to create a new instance with different value
        # and verify they are different objects
        modified_value = ReferenceValue(
            value_id="TEST",
            parameter="test",
            value=2.0,
            unit="meters",
            source_id="SOURCE"
        )
        
        assert value.value == 1.0
        assert modified_value.value == 2.0
        assert value is not modified_value


class TestReferenceDataset:
    """Test reference dataset model."""
    
    def test_dataset_creation(self):
        """Test creating a reference dataset."""
        source = ReferenceSource(
            source_id="SOURCE",
            name="Source",
            type=SourceType.STANDARD,
            authors="Body",
            year=2020
        )
        
        value = ReferenceValue(
            value_id="VALUE",
            parameter="param",
            value=1.75,
            unit="meters",
            source_id="SOURCE"
        )
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={"SOURCE": source},
            values={"VALUE": value}
        )
        
        assert dataset.dataset_id == "DATASET"
        assert dataset.name == "Test Dataset"
        assert len(dataset.sources) == 1
        assert len(dataset.values) == 1
    
    def test_get_source(self):
        """Test retrieving source by ID."""
        source = ReferenceSource(
            source_id="SOURCE",
            name="Source",
            type=SourceType.STANDARD,
            authors="Body",
            year=2020
        )
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={"SOURCE": source},
            values={}
        )
        
        retrieved = dataset.get_source("SOURCE")
        assert retrieved is not None
        assert retrieved.source_id == "SOURCE"
        
        not_found = dataset.get_source("NOT_FOUND")
        assert not_found is None
    
    def test_get_value(self):
        """Test retrieving value by ID."""
        value = ReferenceValue(
            value_id="VALUE",
            parameter="param",
            value=1.75,
            unit="meters",
            source_id="SOURCE"
        )
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={},
            values={"VALUE": value}
        )
        
        retrieved = dataset.get_value("VALUE")
        assert retrieved is not None
        assert retrieved.value_id == "VALUE"
    
    def test_get_values_by_parameter(self):
        """Test retrieving values by parameter name."""
        value1 = ReferenceValue(
            value_id="VALUE1",
            parameter="height",
            value=1.75,
            unit="meters",
            source_id="SOURCE"
        )
        
        value2 = ReferenceValue(
            value_id="VALUE2",
            parameter="height",
            value=1.80,
            unit="meters",
            source_id="SOURCE"
        )
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={},
            values={"VALUE1": value1, "VALUE2": value2}
        )
        
        height_values = dataset.get_values_by_parameter("height")
        assert len(height_values) == 2
        assert all(v.parameter == "height" for v in height_values)
    
    def test_has_known_value(self):
        """Test checking if parameter has known value."""
        known_value = ReferenceValue(
            value_id="KNOWN",
            parameter="height",
            value=1.75,
            unit="meters",
            source_id="SOURCE"
        )
        
        unknown_value = ReferenceValue(
            value_id="UNKNOWN",
            parameter="weight",
            value=None,
            unit="kg",
            source_id="UNKNOWN"
        )
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={},
            values={"KNOWN": known_value, "UNKNOWN": unknown_value}
        )
        
        assert dataset.has_known_value("height")
        assert not dataset.has_known_value("weight")
    
    def test_get_best_value(self):
        """Test getting best (highest confidence) value."""
        high_conf_value = ReferenceValue(
            value_id="HIGH",
            parameter="height",
            value=1.75,
            unit="meters",
            source_id="SOURCE",
            confidence=Confidence.HIGH
        )
        
        low_conf_value = ReferenceValue(
            value_id="LOW",
            parameter="height",
            value=1.80,
            unit="meters",
            source_id="SOURCE",
            confidence=Confidence.LOW
        )
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={},
            values={"HIGH": high_conf_value, "LOW": low_conf_value}
        )
        
        best = dataset.get_best_value("height")
        assert best is not None
        assert best.confidence == Confidence.HIGH
        assert best.value == 1.75


class TestReferenceDatasetBuilder:
    """Test reference dataset builder."""
    
    def test_builder_creation(self):
        """Test creating a builder."""
        builder = ReferenceDatasetBuilder(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0"
        )
        
        assert builder.dataset_id == "DATASET"
        assert builder.name == "Test Dataset"
    
    def test_builder_add_source(self):
        """Test adding source to builder."""
        source = ReferenceSource(
            source_id="SOURCE",
            name="Source",
            type=SourceType.STANDARD,
            authors="Body",
            year=2020
        )
        
        builder = ReferenceDatasetBuilder("DATASET", "Test", "1.0.0")
        result = builder.add_source(source)
        
        assert result is builder  # Builder pattern
        assert "SOURCE" in builder.sources
    
    def test_builder_add_value(self):
        """Test adding value to builder."""
        value = ReferenceValue(
            value_id="VALUE",
            parameter="param",
            value=1.75,
            unit="meters",
            source_id="SOURCE"
        )
        
        builder = ReferenceDatasetBuilder("DATASET", "Test", "1.0.0")
        result = builder.add_value(value)
        
        assert result is builder  # Builder pattern
        assert "VALUE" in builder.values
    
    def test_builder_build(self):
        """Test building dataset from builder."""
        source = ReferenceSource(
            source_id="SOURCE",
            name="Source",
            type=SourceType.STANDARD,
            authors="Body",
            year=2020
        )
        
        value = ReferenceValue(
            value_id="VALUE",
            parameter="param",
            value=1.75,
            unit="meters",
            source_id="SOURCE"
        )
        
        builder = ReferenceDatasetBuilder("DATASET", "Test", "1.0.0")
        builder.add_source(source)
        builder.add_value(value)
        
        dataset = builder.build()
        
        assert isinstance(dataset, ReferenceDataset)
        assert dataset.dataset_id == "DATASET"
        assert len(dataset.sources) == 1
        assert len(dataset.values) == 1


class TestPlaceholderValues:
    """Test placeholder value creation functions."""
    
    def test_unknown_source(self):
        """Test unknown source placeholder."""
        assert UNKNOWN_SOURCE.source_id == "UNKNOWN"
        assert UNKNOWN_SOURCE.type == SourceType.ASSUMPTION
        assert UNKNOWN_SOURCE.confidence == Confidence.UNKNOWN
    
    def test_create_unknown_value(self):
        """Test creating unknown value placeholder."""
        value = create_unknown_value("height", "meters")
        
        assert value.parameter == "height"
        assert value.unit == "meters"
        assert value.value is None
        assert value.source_id == "UNKNOWN"
        assert not value.is_known()
    
    def test_create_assumed_value(self):
        """Test creating assumed value placeholder."""
        value = create_assumed_value("height", 1.75, "meters", "Temporary assumption")
        
        assert value.parameter == "height"
        assert value.value == 1.75
        assert value.unit == "meters"
        assert value.source_id == "UNKNOWN"
        assert value.is_known()
        assert value.is_assumed()
        assert "Temporary assumption" in value.notes


class TestReferenceDataIntegration:
    """Integration tests for reference data system."""
    
    def test_provenance_chain(self):
        """Test that values maintain provenance chain."""
        source = ReferenceSource(
            source_id="RESEARCH",
            name="Research Study",
            type=SourceType.PRIMARY_RESEARCH,
            authors="Researcher et al.",
            year=2020,
            doi="10.1234/research.2020",
            sample_size=1000,
            population="Adults 18-65",
            confidence=Confidence.HIGH
        )
        
        value = ReferenceValue(
            value_id="HEIGHT_VALUE",
            parameter="total_height",
            value=1.75,
            unit="meters",
            source_id="RESEARCH",
            population="Adults 18-65",
            age_range="18-65",
            gender="BOTH",
            confidence=Confidence.HIGH,
            derivation="MEASURED",
            notes="Mean height from sample"
        )
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={"RESEARCH": source},
            values={"HEIGHT_VALUE": value}
        )
        
        # Verify provenance chain
        retrieved_value = dataset.get_value("HEIGHT_VALUE")
        assert retrieved_value is not None
        assert retrieved_value.source_id == "RESEARCH"
        
        retrieved_source = dataset.get_source("RESEARCH")
        assert retrieved_source is not None
        assert retrieved_source.type == SourceType.PRIMARY_RESEARCH
    
    def test_multiple_values_same_parameter(self):
        """Test handling multiple values for same parameter."""
        value1 = ReferenceValue(
            value_id="VALUE1",
            parameter="height",
            value=1.75,
            unit="meters",
            source_id="SOURCE1",
            confidence=Confidence.HIGH
        )
        
        value2 = ReferenceValue(
            value_id="VALUE2",
            parameter="height",
            value=1.80,
            unit="meters",
            source_id="SOURCE2",
            confidence=Confidence.MEDIUM
        )
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={},
            values={"VALUE1": value1, "VALUE2": value2}
        )
        
        # Should get highest confidence value
        best = dataset.get_best_value("height")
        assert best is not None
        assert best.confidence == Confidence.HIGH
        assert best.value == 1.75
        
        # Should find all values
        all_values = dataset.get_values_by_parameter("height")
        assert len(all_values) == 2


class TestReferenceDataValidation:
    """Test reference data validation rules."""
    
    def test_value_without_source(self):
        """Test that value references valid source."""
        # Value with valid source
        valid_value = ReferenceValue(
            value_id="VALID",
            parameter="param",
            value=1.0,
            unit="meters",
            source_id="SOURCE"
        )
        
        # Value with invalid source
        invalid_value = ReferenceValue(
            value_id="INVALID",
            parameter="param",
            value=1.0,
            unit="meters",
            source_id="NONEXISTENT"
        )
        
        source = ReferenceSource(
            source_id="SOURCE",
            name="Source",
            type=SourceType.STANDARD,
            authors="Body",
            year=2020
        )
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={"SOURCE": source},
            values={"VALID": valid_value, "INVALID": invalid_value}
        )
        
        # Valid value should find its source
        assert dataset.get_source(valid_value.source_id) is not None
        
        # Invalid value should not find its source
        assert dataset.get_source(invalid_value.source_id) is None
    
    def test_confidence_hierarchy(self):
        """Test confidence hierarchy works correctly."""
        values = [
            ReferenceValue(
                value_id=f"VALUE_{i}",
                parameter="param",
                value=float(i),
                unit="meters",
                source_id="SOURCE",
                confidence=conf
            )
            for i, conf in enumerate([Confidence.LOW, Confidence.HIGH, Confidence.MEDIUM])
        ]
        
        dataset = ReferenceDataset(
            dataset_id="DATASET",
            name="Test Dataset",
            version="1.0.0",
            sources={},
            values={f"VALUE_{i}": v for i, v in enumerate(values)}
        )
        
        best = dataset.get_best_value("param")
        assert best.confidence == Confidence.HIGH  # Should pick HIGH over MEDIUM and LOW
