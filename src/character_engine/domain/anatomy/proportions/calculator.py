"""Proportion calculator for anatomical reconstruction.

This module implements pure mathematical functions for deriving anatomical
dimensions from canonical body parameters based on established proportion
relationships.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from datetime import date

from ..parameters import AnatomicalParameter, ParameterSet, ParameterStatus, Confidence as ParamConfidence
from ..reference import Confidence as RefConfidence


class ProportionSystem(Enum):
    """Types of proportion systems."""
    VITRUVIAN = "vitruvian"  # Classical Vitruvian proportions
    LEONARDO = "leonardo"  # Leonardo da Vinci's proportions
    MODERN_ANTHROPOMETRIC = "modern_anthropometric"  # Modern anthropometric data
    DERIVED = "derived"  # Derived from other proportions


@dataclass(frozen=True)
class ProportionFormula:
    """Definition of a proportion formula.
    
    Attributes:
        name: Name of the proportion formula
        system: Proportion system this formula belongs to
        formula: Mathematical formula as string
        source_id: Reference source ID
        description: Description of what this formula calculates
        notes: Additional context
    """
    
    name: str
    system: ProportionSystem
    formula: str
    source_id: Optional[str] = None
    description: str = ""
    notes: str = ""


@dataclass(frozen=True)
class DerivedDimension:
    """Result of a proportion calculation.
    
    Attributes:
        dimension_name: Name of the derived dimension
        value: Calculated value
        unit: Unit of measurement
        parent_parameters: Parameters used in calculation
        formula: Formula used
        formula_version: Version of formula used
        confidence: Confidence in the derived value
        notes: Additional context
    """
    
    dimension_name: str
    value: float
    unit: str
    parent_parameters: Tuple[str, ...]
    formula: str
    formula_version: str = "1.0.0"
    confidence: ParamConfidence = ParamConfidence.MEDIUM
    notes: str = ""


class ProportionCalculator:
    """Pure mathematical proportion calculator.
    
    This class provides deterministic calculations for deriving anatomical
    dimensions from canonical body parameters. All calculations are based on
    established proportion relationships and maintain full traceability.
    """
    
    def __init__(self, proportion_system: ProportionSystem = ProportionSystem.MODERN_ANTHROPOMETRIC):
        self.proportion_system = proportion_system
        self.formulas: Dict[str, ProportionFormula] = {}
        self._initialize_formulas()
    
    def _initialize_formulas(self):
        """Initialize proportion formulas based on selected system."""
        if self.proportion_system == ProportionSystem.MODERN_ANTHROPOMETRIC:
            self._initialize_modern_formulas()
        elif self.proportion_system == ProportionSystem.VITRUVIAN:
            self._initialize_vitruvian_formulas()
        elif self.proportion_system == ProportionSystem.LEONARDO:
            self._initialize_leonardo_formulas()
    
    def _initialize_modern_formulas(self):
        """Initialize modern anthropometric formulas."""
        # Head height (approximately 1/8 of total height)
        self.formulas["head_height"] = ProportionFormula(
            name="head_height",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.125",
            description="Head height as proportion of total height",
            notes="Modern anthropometric average: head ≈ 1/8 of total height"
        )
        
        # Shoulder width (approximately 1/4 of total height)
        self.formulas["shoulder_width"] = ProportionFormula(
            name="shoulder_width",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.25",
            description="Shoulder width as proportion of total height",
            notes="Modern anthropometric average: shoulder width ≈ 1/4 of total height"
        )
        
        # Pelvis width (approximately 1/5 of total height)
        self.formulas["pelvis_width"] = ProportionFormula(
            name="pelvis_width",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.20",
            description="Pelvis width as proportion of total height",
            notes="Modern anthropometric average: pelvis width ≈ 1/5 of total height"
        )
        
        # Upper arm length (approximately 1/6 of total height)
        self.formulas["upper_arm_length"] = ProportionFormula(
            name="upper_arm_length",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.167",
            description="Upper arm length as proportion of total height",
            notes="Modern anthropometric average: upper arm ≈ 1/6 of total height"
        )
        
        # Forearm length (approximately 1/7 of total height)
        self.formulas["forearm_length"] = ProportionFormula(
            name="forearm_length",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.143",
            description="Forearm length as proportion of total height",
            notes="Modern anthropometric average: forearm ≈ 1/7 of total height"
        )
        
        # Hand length (approximately 1/10 of total height)
        self.formulas["hand_length"] = ProportionFormula(
            name="hand_length",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.10",
            description="Hand length as proportion of total height",
            notes="Modern anthropometric average: hand ≈ 1/10 of total height"
        )
        
        # Thigh length (approximately 1/4 of total height)
        self.formulas["thigh_length"] = ProportionFormula(
            name="thigh_length",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.25",
            description="Thigh length as proportion of total height",
            notes="Modern anthropometric average: thigh ≈ 1/4 of total height"
        )
        
        # Lower leg length (approximately 1/4 of total height)
        self.formulas["lower_leg_length"] = ProportionFormula(
            name="lower_leg_length",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.25",
            description="Lower leg length as proportion of total height",
            notes="Modern anthropometric average: lower leg ≈ 1/4 of total height"
        )
        
        # Foot length (approximately 1/7 of total height)
        self.formulas["foot_length"] = ProportionFormula(
            name="foot_length",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.143",
            description="Foot length as proportion of total height",
            notes="Modern anthropometric average: foot ≈ 1/7 of total height"
        )
        
        # Torso height (approximately 1/3 of total height)
        self.formulas["torso_height"] = ProportionFormula(
            name="torso_height",
            system=ProportionSystem.MODERN_ANTHROPOMETRIC,
            formula="total_height * 0.333",
            description="Torso height as proportion of total height",
            notes="Modern anthropometric average: torso ≈ 1/3 of total height"
        )
    
    def _initialize_vitruvian_formulas(self):
        """Initialize Vitruvian proportion formulas."""
        # Vitruvian proportions are more idealized
        self.formulas["head_height"] = ProportionFormula(
            name="head_height",
            system=ProportionSystem.VITRUVIAN,
            formula="total_height * 0.125",
            description="Head height per Vitruvian proportions",
            notes="Vitruvian: head = 1/8 of total height"
        )
        
        self.formulas["shoulder_width"] = ProportionFormula(
            name="shoulder_width",
            system=ProportionSystem.VITRUVIAN,
            formula="total_height * 0.25",
            description="Shoulder width per Vitruvian proportions",
            notes="Vitruvian: shoulder width = 1/4 of total height"
        )
    
    def _initialize_leonardo_formulas(self):
        """Initialize Leonardo da Vinci proportion formulas."""
        # Leonardo's Vitruvian Man proportions
        self.formulas["arm_span"] = ProportionFormula(
            name="arm_span",
            system=ProportionSystem.LEONARDO,
            formula="total_height",
            description="Arm span equals total height",
            notes="Leonardo: arm span = total height"
        )
        
        self.formulas["head_height"] = ProportionFormula(
            name="head_height",
            system=ProportionSystem.LEONARDO,
            formula="total_height * 0.125",
            description="Head height per Leonardo's proportions",
            notes="Leonardo: head = 1/8 of total height"
        )
    
    def calculate_dimension(self, dimension_name: str, parameter_set: ParameterSet) -> Optional[DerivedDimension]:
        """Calculate a derived dimension from parameters.
        
        Args:
            dimension_name: Name of dimension to calculate
            parameter_set: Set of anatomical parameters
            
        Returns:
            Derived dimension if calculation successful, None otherwise
        """
        if dimension_name not in self.formulas:
            return None
        
        formula = self.formulas[dimension_name]
        
        # Parse formula and extract parameters
        # For now, implement simple linear formulas: total_height * X
        if "total_height" in formula.formula:
            total_height_param = parameter_set.get_parameter_by_canonical_name("total_height")
            
            if total_height_param is None or not total_height_param.is_known():
                return None
            
            total_height = total_height_param.value
            
            # Extract multiplier from formula
            if "* 0.125" in formula.formula:
                multiplier = 0.125
            elif "* 0.25" in formula.formula:
                multiplier = 0.25
            elif "* 0.20" in formula.formula:
                multiplier = 0.20
            elif "* 0.167" in formula.formula:
                multiplier = 0.167
            elif "* 0.143" in formula.formula:
                multiplier = 0.143
            elif "* 0.10" in formula.formula:
                multiplier = 0.10
            elif "* 0.333" in formula.formula:
                multiplier = 0.333
            else:
                return None
            
            value = total_height * multiplier
            
            return DerivedDimension(
                dimension_name=dimension_name,
                value=value,
                unit="meters",
                parent_parameters=("total_height",),
                formula=formula.formula,
                confidence=ParamConfidence.MEDIUM,
                notes=f"Calculated using {formula.system.value} proportions"
            )
        
        return None
    
    def calculate_all_dimensions(self, parameter_set: ParameterSet) -> Dict[str, DerivedDimension]:
        """Calculate all possible dimensions from parameter set.
        
        Args:
            parameter_set: Set of anatomical parameters
            
        Returns:
            Dictionary of dimension names to derived dimensions
        """
        results = {}
        
        for dimension_name in self.formulas:
            dimension = self.calculate_dimension(dimension_name, parameter_set)
            if dimension is not None:
                results[dimension_name] = dimension
        
        return results
    
    def get_formula(self, dimension_name: str) -> Optional[ProportionFormula]:
        """Get formula for a dimension.
        
        Args:
            dimension_name: Name of dimension
            
        Returns:
            Proportion formula if exists, None otherwise
        """
        return self.formulas.get(dimension_name)
    
    def get_available_dimensions(self) -> list[str]:
        """Get list of available dimension calculations."""
        return list(self.formulas.keys())


def create_proportion_calculator(system: ProportionSystem = ProportionSystem.MODERN_ANTHROPOMETRIC) -> ProportionCalculator:
    """Create a proportion calculator with specified system.
    
    Args:
        system: Proportion system to use
        
    Returns:
        Configured proportion calculator
    """
    return ProportionCalculator(system)


def calculate_simple_proportion(base_value: float, proportion: float) -> float:
    """Calculate a simple proportion.
    
    Args:
        base_value: Base value (e.g., total height)
        proportion: Proportion as fraction (e.g., 0.125 for 1/8)
        
    Returns:
        Calculated proportional value
    """
    return base_value * proportion


def calculate_ratio_value(base_value: float, ratio: str) -> float:
    """Calculate value from ratio string.
    
    Args:
        base_value: Base value
        ratio: Ratio as string (e.g., "1:8" for 1/8)
        
    Returns:
        Calculated value
    """
    parts = ratio.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid ratio format: {ratio}")
    
    numerator = float(parts[0])
    denominator = float(parts[1])
    
    return base_value * (numerator / denominator)
