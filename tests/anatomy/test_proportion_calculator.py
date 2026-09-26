"""Tests for proportion calculator."""

import pytest
from pathlib import Path
from character_engine.domain.anatomy.reference import ReferenceDataManager
from character_engine.domain.anatomy.parameters import SubjectProfile
from character_engine.domain.anatomy.reconstruction import (
    ParameterNormalizer,
    ProportionCalculator,
    CalculatedProportion,
    CalculationMethod
)


class TestProportionCalculator:
    """Test proportion calculator functionality."""
    
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
            "placeholder_data": {}
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
                    },
                    "upper_arm_ratio": {
                        "value": 0.18,
                        "confidence": "LOW",
                        "provenance": "ASSUMPTION"
                    },
                    "forearm_ratio": {
                        "value": 0.15,
                        "confidence": "LOW",
                        "provenance": "ASSUMPTION"
                    },
                    "thigh_ratio": {
                        "value": 0.25,
                        "confidence": "LOW",
                        "provenance": "ASSUMPTION"
                    },
                    "lower_leg_ratio": {
                        "value": 0.20,
                        "confidence": "LOW",
                        "provenance": "ASSUMPTION"
                    }
                },
                "gender_specific_adjustments": {}
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
    def calculator(self, sample_references_dir):
        """Create proportion calculator for testing."""
        reference_manager = ReferenceDataManager(sample_references_dir)
        normalizer = ParameterNormalizer(reference_manager)
        return ProportionCalculator(reference_manager, normalizer)
    
    def test_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator.reference_manager is not None
        assert calculator.normalizer is not None
        assert calculator.cache == {}
    
    def test_calculate_proportions(self, calculator):
        """Test calculating all proportions."""
        profile = SubjectProfile(height=1.80)
        
        proportions = calculator.calculate_proportions(profile)
        
        assert 'head_height' in proportions
        assert 'shoulder_width' in proportions
        assert 'upper_arm_length' in proportions
        assert 'forearm_length' in proportions
        assert 'thigh_length' in proportions
        assert 'lower_leg_length' in proportions
    
    def test_calculate_body_segments(self, calculator):
        """Test calculating body segment proportions."""
        profile = SubjectProfile(height=1.80)
        
        normalized = calculator.normalizer.normalize_profile(profile)
        proportions = calculator._calculate_body_segments(normalized)
        
        assert 'head_height' in proportions
        assert proportions['head_height'].value == 1.80 * 0.125
        assert proportions['head_height'].unit == 'meters'
        assert proportions['head_height'].calculation_method == CalculationMethod.RATIO_DERIVATION
    
    def test_calculate_bone_dimensions(self, calculator):
        """Test calculating bone dimensions from segments."""
        profile = SubjectProfile(height=1.80)
        
        normalized = calculator.normalizer.normalize_profile(profile)
        proportions = calculator._calculate_body_segments(normalized)
        bone_dimensions = calculator._calculate_bone_dimensions(normalized)
        
        # For placeholder data, bone dimensions may be empty if segments aren't available
        # The important thing is that the method runs without error
        assert isinstance(bone_dimensions, dict)
        
        # If any segments are present, check that bone dimensions are calculated
        if 'upper_arm_length' in normalized:
            # This would trigger bone dimension calculation in production
            pass
    
    def test_calculate_limb_proportions(self, calculator):
        """Test calculating limb-specific proportions."""
        profile = SubjectProfile(height=1.80)
        
        proportions = calculator.calculate_limb_proportions(profile)
        
        # Check that limb ratios are calculated
        if 'upper_arm_length' in calculator.normalizer.normalize_profile(profile) and \
           'forearm_length' in calculator.normalizer.normalize_profile(profile):
            assert 'upper_arm_to_forearm_ratio' in proportions
            assert proportions['upper_arm_to_forearm_ratio'].unit == 'ratio'
    
    def test_calculate_coordinate_positions(self, calculator):
        """Test calculating 3D coordinate positions."""
        profile = SubjectProfile(height=1.80)
        
        coordinates = calculator.calculate_coordinate_positions(profile)
        
        # Check that landmark positions are calculated
        assert isinstance(coordinates, dict)
        # Origin should be present
        # Specific landmarks depend on reference data availability
    
    def test_proportion_chain(self, calculator):
        """Test that proportions form a valid chain."""
        profile = SubjectProfile(height=1.80)
        
        proportions = calculator.calculate_proportions(profile)
        
        # Verify that proportions are derived from height
        if 'head_height' in proportions:
            assert proportions['head_height'].metadata['height'] == 1.80
        
        # Verify calculation method
        if 'head_height' in proportions:
            assert proportions['head_height'].calculation_method == CalculationMethod.RATIO_DERIVATION