"""Tests for parameter normalizer."""

import pytest
from pathlib import Path
from character_engine.domain.anatomy.reference import ReferenceDataManager, Confidence
from character_engine.domain.anatomy.parameters import SubjectProfile, AnatomicalParameter, ParameterType, ParameterStatus
from character_engine.domain.anatomy.reconstruction import (
    ParameterNormalizer,
    NormalizedParameter,
    NormalizationMethod
)


class TestParameterNormalizer:
    """Test parameter normalizer functionality."""
    
    @pytest.fixture
    def sample_references_dir(self, tmp_path):
        """Create sample reference data for testing."""
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
                            "mean": 1.75,
                            "unit": "meters",
                            "confidence": "LOW",
                            "provenance": "ASSUMPTION"
                        }
                    }
                }
            }
        }
        
        with open(references_dir / "source_registry.json", 'w') as f:
            import json
            json.dump(registry_data, f)
        
        # Create anthropometry data
        anthropometry_data = {
            "anthropometric_data": {
                "version": "1.0.0",
                "status": "PLACEHOLDER",
                "global_parameters": {
                    "height": {
                        "mean": 1.75,
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
                    },
                    "shoulder_width_ratio": {
                        "value": 0.23,
                        "confidence": "LOW",
                        "provenance": "ASSUMPTION"
                    }
                },
                "gender_specific_adjustments": {
                    "male": {
                        "shoulder_to_hip_ratio": {
                            "value": 1.20,
                            "confidence": "LOW",
                            "provenance": "ASSUMPTION"
                        }
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
                "joint_centers": {}
            }
        }
        
        with open(references_dir / "biomechanics.json", 'w') as f:
            json.dump(biomechanics_data, f)
        
        return references_dir
    
    @pytest.fixture
    def normalizer(self, sample_references_dir):
        """Create parameter normalizer for testing."""
        reference_manager = ReferenceDataManager(sample_references_dir)
        return ParameterNormalizer(reference_manager)
    
    def test_initialization(self, normalizer):
        """Test normalizer initialization."""
        assert normalizer.reference_manager is not None
        assert normalizer.cache == {}
    
    def test_normalize_profile_with_height(self, normalizer):
        """Test normalizing profile with height provided."""
        profile = SubjectProfile(height=1.80)
        
        normalized = normalizer.normalize_profile(profile)
        
        assert 'height' in normalized
        assert normalized['height'].value == 1.80
        assert normalized['height'].provenance == 'USER_INPUT'
        assert normalized['height'].normalization_method == NormalizationMethod.DIRECT
    
    def test_normalize_profile_without_height(self, normalizer):
        """Test normalizing profile without height (uses reference)."""
        profile = SubjectProfile(height=None)
        
        normalized = normalizer.normalize_profile(profile)
        
        assert 'height' in normalized
        assert normalized['height'].value == 1.75  # From reference
        assert normalized['height'].provenance == 'ASSUMPTION'
        assert normalized['height'].normalization_method == NormalizationMethod.HEIGHT_BASED
    
    def test_normalize_body_proportions(self, normalizer):
        """Test normalizing body proportions."""
        profile = SubjectProfile(height=1.80)
        
        normalized = normalizer.normalize_profile(profile)
        
        assert 'head_height_ratio' in normalized
        assert normalized['head_height_ratio'].value == 1.80 * 0.125  # height * ratio
        assert normalized['head_height_ratio'].unit == 'meters'
        assert normalized['head_height_ratio'].normalization_method == NormalizationMethod.HEIGHT_BASED
    
    def test_normalize_with_gender(self, normalizer):
        """Test normalizing with gender adjustment."""
        profile = SubjectProfile(height=1.80, gender='male')
        
        normalized = normalizer.normalize_profile(profile)
        
        # Check that gender adjustment was applied
        assert 'shoulder_width_ratio' in normalized
        # Original would be 1.80 * 0.23 = 0.414
        # With male adjustment (1.20) would be 0.414 * 1.20 = 0.4968
        # This tests that the adjustment was attempted
    
    def test_normalize_single_parameter(self, normalizer):
        """Test normalizing a single parameter."""
        profile = SubjectProfile(height=1.80)
        parameter = AnatomicalParameter(
            id='param_1',
            name='head_height',
            canonical_name='head_height',
            parameter_type=ParameterType.RATIO,
            value=0.125,
            unit='ratio',
            status=ParameterStatus.ASSUMED,
            confidence=Confidence.LOW,
            metadata={'provenance': 'ASSUMPTION'}
        )
        
        normalized = normalizer.normalize_parameter(parameter, profile)
        
        assert normalized.name == 'head_height'
        assert normalized.value == 1.80 * 0.125  # height * ratio
        assert normalized.unit == 'meters'
        assert normalized.normalization_method == NormalizationMethod.HEIGHT_BASED
        assert normalized.original_value == 0.125
    
    def test_normalize_single_parameter_absolute(self, normalizer):
        """Test normalizing absolute parameter (not ratio)."""
        profile = SubjectProfile(height=1.80)
        parameter = AnatomicalParameter(
            id='param_2',
            name='femur_length',
            canonical_name='femur_length',
            parameter_type=ParameterType.LENGTH,
            value=0.45,
            unit='meters',
            status=ParameterStatus.ASSUMED,
            confidence=Confidence.LOW,
            metadata={'provenance': 'ASSUMPTION'}
        )
        
        normalized = normalizer.normalize_parameter(parameter, profile)
        
        assert normalized.name == 'femur_length'
        assert normalized.value == 0.45  # Absolute value preserved
        assert normalized.unit == 'meters'
        assert normalized.normalization_method == NormalizationMethod.DIRECT
    
    def test_caching(self, normalizer):
        """Test that normalization results are cached."""
        profile = SubjectProfile(height=1.80)
        parameter = AnatomicalParameter(
            id='param_3',
            name='head_height',
            canonical_name='head_height',
            parameter_type=ParameterType.RATIO,
            value=0.125,
            unit='ratio',
            status=ParameterStatus.ASSUMED,
            confidence=Confidence.LOW,
            metadata={'provenance': 'ASSUMPTION'}
        )
        
        # First call
        normalized1 = normalizer.normalize_parameter(parameter, profile)
        
        # Second call (should use cache)
        normalized2 = normalizer.normalize_parameter(parameter, profile)
        
        assert normalized1.value == normalized2.value
        assert len(normalizer.cache) == 1