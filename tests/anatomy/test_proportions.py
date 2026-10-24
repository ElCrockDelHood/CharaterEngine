"""Proportion calculator tests."""

import pytest

from character_engine.domain.anatomy.parameters import Confidence as ParamConfidence
from character_engine.domain.anatomy.parameters import (
    ParameterSetBuilder,
    create_direct_reference_parameter,
)
from character_engine.domain.anatomy.proportions import (
    DerivedDimension,
    ProportionCalculator,
    ProportionFormula,
    ProportionSystem,
    calculate_ratio_value,
    calculate_simple_proportion,
    create_proportion_calculator,
)


class TestProportionFormula:
    """Test proportion formula model."""

    def test_formula_creation(self):
        """Test creating a proportion formula."""
        formula = ProportionFormula(
            name="head_height",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.125",
            description="Head height calculation"
        )

        assert formula.name == "head_height"
        assert formula.system == ProportionSystem.MODERN_ANTHROPOMETRIC
        assert formula.formula == "total_height * 0.125"

    def test_formula_with_source(self):
        """Test formula with source reference."""
        formula = ProportionFormula(
            name="head_height",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.125",
            source_id="SOURCE_001",
            description="Head height calculation"
        )

        assert formula.source_id == "SOURCE_001"


class TestDerivedDimension:
    """Test derived dimension model."""

    def test_derived_dimension_creation(self):
        """Test creating a derived dimension."""
        dimension = DerivedDimension(
            dimension_name="head_height",
            value=0.21875,
            unit="meters",
            parent_parameters=("total_height",),
            formula="total_height * 0.125"
        )

        assert dimension.dimension_name == "head_height"
        assert dimension.value == 0.21875
        assert dimension.unit == "meters"
        assert len(dimension.parent_parameters) == 1

    def test_derived_dimension_confidence(self):
        """Test derived dimension confidence."""
        high_conf = DerivedDimension(
            dimension_name="test",
            value=1.0,
            unit="meters",
            parent_parameters=("base",),
            formula="base * 1.0",
            confidence=ParamConfidence.HIGH
        )

        low_conf = DerivedDimension(
            dimension_name="test",
            value=1.0,
            unit="meters",
            parent_parameters=("base",),
            formula="base * 1.0",
            confidence=ParamConfidence.LOW
        )

        assert high_conf.confidence == ParamConfidence.HIGH
        assert low_conf.confidence == ParamConfidence.LOW


class TestProportionCalculator:
    """Test proportion calculator."""

    def test_calculator_creation(self):
        """Test creating a proportion calculator."""
        calculator = ProportionCalculator()

        assert calculator.proportion_system == ProportionSystem.MODERN_ANTHROPOMETRIC
        assert len(calculator.formulas) > 0

    def test_calculator_with_specific_system(self):
        """Test creating calculator with specific proportion system."""
        vitruvian_calc = ProportionCalculator(ProportionSystem.VITRUVIAN)
        leonardo_calc = ProportionCalculator(ProportionSystem.LEONARDO)

        assert vitruvian_calc.proportion_system == ProportionSystem.VITRUVIAN
        assert leonardo_calc.proportion_system == ProportionSystem.LEONARDO

    def test_get_available_dimensions(self):
        """Test getting available dimension calculations."""
        calculator = ProportionCalculator()

        dimensions = calculator.get_available_dimensions()

        assert isinstance(dimensions, list)
        assert len(dimensions) > 0
        assert "head_height" in dimensions
        assert "shoulder_width" in dimensions

    def test_get_formula(self):
        """Test getting formula for dimension."""
        calculator = ProportionCalculator()

        formula = calculator.get_formula("head_height")

        assert formula is not None
        assert formula.name == "head_height"
        assert formula.system == ProportionSystem.MODERN_ANTHROPOMETRIC

    def test_get_nonexistent_formula(self):
        """Test getting formula for nonexistent dimension."""
        calculator = ProportionCalculator()

        formula = calculator.get_formula("nonexistent_dimension")

        assert formula is None

    def test_calculate_dimension(self):
        """Test calculating a single dimension."""
        calculator = ProportionCalculator()

        # Create parameter set with total height
        total_height_param = create_direct_reference_parameter(
            "total_height",
            1.75,
            "meters",
            "SOURCE_001"
        )

        parameter_set = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        parameter_set.add_parameter(total_height_param)
        param_set = parameter_set.build()

        # Calculate head height
        head_height = calculator.calculate_dimension("head_height", param_set)

        assert head_height is not None
        assert head_height.dimension_name == "head_height"
        assert head_height.value == pytest.approx(1.75 * 0.125)  # 1/8 of height
        assert head_height.unit == "meters"

    def test_calculate_dimension_missing_parameter(self):
        """Test calculating dimension when required parameter is missing."""
        calculator = ProportionCalculator()

        # Create empty parameter set
        parameter_set = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        param_set = parameter_set.build()

        # Try to calculate head height
        head_height = calculator.calculate_dimension("head_height", param_set)

        assert head_height is None

    def test_calculate_dimension_unknown_parameter(self):
        """Test calculating dimension when parameter is unknown."""
        calculator = ProportionCalculator()

        # Create parameter set with unknown total height
        from character_engine.domain.anatomy.parameters import create_unknown_parameter
        total_height_param = create_unknown_parameter("total_height", "meters")

        parameter_set = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        parameter_set.add_parameter(total_height_param)
        param_set = parameter_set.build()

        # Try to calculate head height
        head_height = calculator.calculate_dimension("head_height", param_set)

        assert head_height is None

    def test_calculate_all_dimensions(self):
        """Test calculating all possible dimensions."""
        calculator = ProportionCalculator()

        # Create parameter set with total height
        total_height_param = create_direct_reference_parameter(
            "total_height",
            1.75,
            "meters",
            "SOURCE_001"
        )

        parameter_set = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        parameter_set.add_parameter(total_height_param)
        param_set = parameter_set.build()

        # Calculate all dimensions
        dimensions = calculator.calculate_all_dimensions(param_set)

        assert isinstance(dimensions, dict)
        assert len(dimensions) > 0
        assert "head_height" in dimensions
        assert "shoulder_width" in dimensions

    def test_proportion_accuracy(self):
        """Test proportion calculation accuracy."""
        calculator = ProportionCalculator()

        total_height_param = create_direct_reference_parameter(
            "total_height",
            1.75,
            "meters",
            "SOURCE_001"
        )

        parameter_set = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        parameter_set.add_parameter(total_height_param)
        param_set = parameter_set.build()

        # Calculate various proportions
        head_height = calculator.calculate_dimension("head_height", param_set)
        shoulder_width = calculator.calculate_dimension("shoulder_width", param_set)
        torso_height = calculator.calculate_dimension("torso_height", param_set)

        # Verify proportions
        assert head_height.value == pytest.approx(1.75 * 0.125)  # 1/8
        assert shoulder_width.value == pytest.approx(1.75 * 0.25)  # 1/4
        assert torso_height.value == pytest.approx(1.75 * 0.333)  # 1/3

    def test_different_heights(self):
        """Test proportions with different total heights."""
        calculator = ProportionCalculator()

        for height in [1.60, 1.75, 1.90]:
            total_height_param = create_direct_reference_parameter(
                "total_height",
                height,
                "meters",
                "SOURCE_001"
            )

            parameter_set = ParameterSetBuilder("SET", "Test Set", "1.0.0")
            parameter_set.add_parameter(total_height_param)
            param_set = parameter_set.build()

            head_height = calculator.calculate_dimension("head_height", param_set)

            # Proportion should be consistent
            assert head_height.value == pytest.approx(height * 0.125)


class TestProportionFactoryFunctions:
    """Test proportion factory functions."""

    def test_create_proportion_calculator(self):
        """Test creating proportion calculator factory function."""
        calculator = create_proportion_calculator()

        assert isinstance(calculator, ProportionCalculator)
        assert calculator.proportion_system == ProportionSystem.MODERN_ANTHROPOMETRIC

    def test_create_proportion_calculator_with_system(self):
        """Test creating calculator with specific system."""
        calculator = create_proportion_calculator(ProportionSystem.VITRUVIAN)

        assert isinstance(calculator, ProportionCalculator)
        assert calculator.proportion_system == ProportionSystem.VITRUVIAN

    def test_calculate_simple_proportion(self):
        """Test simple proportion calculation."""
        result = calculate_simple_proportion(1.75, 0.125)

        assert result == pytest.approx(0.21875)

    def test_calculate_ratio_value(self):
        """Test ratio value calculation."""
        result = calculate_ratio_value(1.75, "1:8")

        assert result == pytest.approx(0.21875)

    def test_calculate_ratio_value_invalid_format(self):
        """Test ratio calculation with invalid format."""
        with pytest.raises(ValueError):
            calculate_ratio_value(1.75, "invalid")

    def test_calculate_ratio_value_different_ratios(self):
        """Test different ratio formats."""
        # 1:4
        result_1_4 = calculate_ratio_value(1.75, "1:4")
        assert result_1_4 == pytest.approx(0.4375)

        # 1:3
        result_1_3 = calculate_ratio_value(1.75, "1:3")
        assert result_1_3 == pytest.approx(0.58333, rel=1e-3)


class TestProportionSystemDifferences:
    """Test differences between proportion systems."""

    def test_modern_vs_vitruvian_formulas(self):
        """Test modern vs Vitruvian formulas."""
        modern_calc = ProportionCalculator(ProportionSystem.MODERN_ANTHROPOMETRIC)
        vitruvian_calc = ProportionCalculator(ProportionSystem.VITRUVIAN)

        # Both should have head_height formula
        modern_formula = modern_calc.get_formula("head_height")
        vitruvian_formula = vitruvian_calc.get_formula("head_height")

        assert modern_formula is not None
        assert vitruvian_formula is not None
        assert modern_formula.system == ProportionSystem.MODERN_ANTHROPOMETRIC
        assert vitruvian_formula.system == ProportionSystem.VITRUVIAN

    def test_leonardo_specific_formulas(self):
        """Test Leonardo-specific formulas."""
        leonardo_calc = ProportionCalculator(ProportionSystem.LEONARDO)

        # Leonardo should have arm_span formula
        arm_span_formula = leonardo_calc.get_formula("arm_span")

        assert arm_span_formula is not None
        assert arm_span_formula.formula == "total_height"
        assert "arm span equals total height" in arm_span_formula.description.lower()


class TestProportionIntegration:
    """Integration tests for proportion system."""

    def test_derivation_tracking(self):
        """Test that derived dimensions track their derivation."""
        calculator = ProportionCalculator()

        total_height_param = create_direct_reference_parameter(
            "total_height",
            1.75,
            "meters",
            "SOURCE_001"
        )

        parameter_set = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        parameter_set.add_parameter(total_height_param)
        param_set = parameter_set.build()

        head_height = calculator.calculate_dimension("head_height", param_set)

        # Verify derivation tracking
        assert head_height.parent_parameters == ("total_height",)
        assert "total_height" in head_height.formula
        assert head_height.formula_version == "1.0.0"

    def test_formula_version_tracking(self):
        """Test that formula versions are tracked."""
        calculator = ProportionCalculator()

        formula = calculator.get_formula("head_height")

        # Formula should have version information
        assert formula is not None
        # Version tracking is handled at the derived dimension level

    def test_confidence_propagation(self):
        """Test that confidence is appropriately set for derived values."""
        calculator = ProportionCalculator()

        total_height_param = create_direct_reference_parameter(
            "total_height",
            1.75,
            "meters",
            "SOURCE_001"
        )

        parameter_set = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        parameter_set.add_parameter(total_height_param)
        param_set = parameter_set.build()

        head_height = calculator.calculate_dimension("head_height", param_set)

        # Derived values should have MEDIUM confidence (not as high as direct measurements)
        assert head_height.confidence == ParamConfidence.MEDIUM

    def test_multiple_calculations_consistency(self):
        """Test that multiple calculations are consistent."""
        calculator = ProportionCalculator()

        total_height_param = create_direct_reference_parameter(
            "total_height",
            1.75,
            "meters",
            "SOURCE_001"
        )

        parameter_set = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        parameter_set.add_parameter(total_height_param)
        param_set = parameter_set.build()

        # Calculate head height twice
        head_height_1 = calculator.calculate_dimension("head_height", param_set)
        head_height_2 = calculator.calculate_dimension("head_height", param_set)

        # Results should be identical (deterministic)
        assert head_height_1.value == head_height_2.value
        assert head_height_1.formula == head_height_2.formula
