"""Trauma / wound model: penetration through tissue layers → severity and lethality (pure Python)."""

from .wound import (
    LETHALITY_BY_REGION,
    REFERENCE_BLUNT_ENERGY_J,
    Severity,
    Wound,
    WoundAssessment,
    WoundType,
    assess_wound,
    blunt_impact_to_wound,
)

__all__ = [
    "LETHALITY_BY_REGION",
    "REFERENCE_BLUNT_ENERGY_J",
    "Severity",
    "Wound",
    "WoundAssessment",
    "WoundType",
    "assess_wound",
    "blunt_impact_to_wound",
]
