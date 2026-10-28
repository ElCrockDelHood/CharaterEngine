"""Materials: per-layer mechanical (XPBD / cut energy) and optical (OpenPBR) parameters, layered capsules."""

from .catalog import (
    MATERIALS,
    TISSUE_MATERIAL,
    Material,
    MaterialKind,
    MechanicalParams,
    OpticalParams,
    Quantity,
    material,
    material_table,
)
from .layered_capsule import LayeredCapsule, OuterLayer, Shell, layered_capsule, segment_distance

__all__ = [
    "MATERIALS",
    "TISSUE_MATERIAL",
    "LayeredCapsule",
    "Material",
    "MaterialKind",
    "MechanicalParams",
    "OpticalParams",
    "OuterLayer",
    "Quantity",
    "Shell",
    "layered_capsule",
    "material",
    "material_table",
    "segment_distance",
]
