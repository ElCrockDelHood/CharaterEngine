"""Material catalogue: one entry per tissue layer, garment and armour, with a mechanical and an optical face.

* **Mechanical** values drive the pure-Python XPBD solver and the cut-energy model (``domain/physics``).
* **Optical** values use OpenPBR Surface parameter names (``base_color``, ``specular_roughness``,
  ``subsurface_*``, ``fuzz_*``, ``coat_*``) so any renderer adapter (Blender Principled BSDF, Godot
  StandardMaterial3D) maps them at the boundary.

Honesty rules (AGENTS.md invariant 1): every number is a :class:`Quantity` with a provenance state and a range.
Nothing here is PROVEN. Tissue mechanics are order-of-magnitude ESTIMATES pending a sourced biomechanics pass;
XPBD compliances and the armour "blade defeat" constant are ASSUMED tuning values, not material properties;
optical values are ASSUMED look-development choices.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Mapping, Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..tissue import TissueLayer

RGB = Tuple[float, float, float]

E = ProvenanceState.ESTIMATE
A = ProvenanceState.ASSUMED


@dataclass(frozen=True)
class Quantity:
    value: float
    low: float
    high: float
    unit: str
    provenance: ProvenanceState
    note: str = ""

    def __post_init__(self):
        if not self.low <= self.value <= self.high:
            raise ValueError(f"{self.value} {self.unit} outside its range [{self.low}, {self.high}]")


def _q(value, low, high, unit, provenance=E, note=""):
    return Quantity(float(value), float(low), float(high), unit, provenance, note)


class MaterialKind(Enum):
    SKIN = "skin"
    FAT = "fat"
    MUSCLE = "muscle"
    TENDON = "tendon"
    BONE = "bone"
    CLOTH_WOOL = "cloth_wool"
    ARMOR_STEEL = "armor_steel"
    AIR = "air"                      # gap between garment layers (no resistance, not rendered)


TISSUE_MATERIAL: Mapping[TissueLayer, MaterialKind] = {
    TissueLayer.SKIN: MaterialKind.SKIN,
    TissueLayer.FAT: MaterialKind.FAT,
    TissueLayer.MUSCLE: MaterialKind.MUSCLE,
    TissueLayer.TENDON: MaterialKind.TENDON,
    TissueLayer.BONE: MaterialKind.BONE,
}


@dataclass(frozen=True)
class MechanicalParams:
    density: Quantity                         # kg/m^3 (volumetric) — cloth also carries areal_density
    youngs_modulus: Quantity                  # Pa
    poisson_ratio: Quantity
    friction: Quantity                        # Coulomb coefficient against skin/cloth (dimensionless)
    cut_energy: Quantity                      # J/m^2: energy to advance a blade cut by unit area
    areal_density: Optional[Quantity] = None  # kg/m^2 (cloth / plate)
    stretch_compliance: Optional[Quantity] = None   # m/N, XPBD distance constraint (cloth)
    bend_compliance: Optional[Quantity] = None      # m/N, XPBD second-neighbour constraint (cloth)
    damping: Optional[Quantity] = None              # 1/s velocity damping (cloth)


@dataclass(frozen=True)
class OpticalParams:
    """OpenPBR Surface parameters (subset). Radii in metres. All ASSUMED look-dev values."""

    base_color: RGB
    base_metalness: float = 0.0
    specular_roughness: float = 0.5
    specular_ior: float = 1.5
    subsurface_weight: float = 0.0
    subsurface_color: RGB = (1.0, 1.0, 1.0)
    subsurface_radius: float = 0.0
    subsurface_radius_scale: RGB = (1.0, 0.5, 0.25)
    fuzz_weight: float = 0.0
    fuzz_color: RGB = (1.0, 1.0, 1.0)
    fuzz_roughness: float = 0.5
    coat_weight: float = 0.0
    coat_roughness: float = 0.0
    provenance: ProvenanceState = A


@dataclass(frozen=True)
class Material:
    kind: MaterialKind
    mechanical: MechanicalParams
    optical: Optional[OpticalParams]
    notes: str = ""

    @property
    def name(self) -> str:
        return self.kind.value


_SOFT_NOTE = "order of magnitude from general soft-tissue biomechanics; not yet registered in source_registry"
_CUT_NOTE = ("blade cutting energy per unit area, order of magnitude from cutting / fracture-toughness "
             "literature; very wide spread with rate and blade sharpness; to be sourced")

MATERIALS: Dict[MaterialKind, Material] = {
    MaterialKind.SKIN: Material(MaterialKind.SKIN, MechanicalParams(
        density=_q(1100, 1050, 1150, "kg/m^3", note=_SOFT_NOTE),
        youngs_modulus=_q(1.0e6, 1.0e5, 1.0e8, "Pa", note=_SOFT_NOTE + "; strongly non-linear, anisotropic"),
        poisson_ratio=_q(0.48, 0.40, 0.49, "", note=_SOFT_NOTE),
        friction=_q(0.5, 0.3, 0.9, "", note="skin against fabric; humidity dependent"),
        cut_energy=_q(5.0e3, 1.0e3, 2.0e4, "J/m^2", note=_CUT_NOTE)),
        OpticalParams(base_color=(0.80, 0.58, 0.47), specular_roughness=0.45, specular_ior=1.4,
                      subsurface_weight=1.0, subsurface_color=(0.85, 0.45, 0.35), subsurface_radius=0.004,
                      subsurface_radius_scale=(1.0, 0.45, 0.25))),
    MaterialKind.FAT: Material(MaterialKind.FAT, MechanicalParams(
        density=_q(920, 900, 950, "kg/m^3", note=_SOFT_NOTE),
        youngs_modulus=_q(3.0e3, 1.0e3, 1.0e4, "Pa", note=_SOFT_NOTE),
        poisson_ratio=_q(0.49, 0.45, 0.499, "", note=_SOFT_NOTE + "; near incompressible"),
        friction=_q(0.3, 0.1, 0.5, ""),
        cut_energy=_q(5.0e2, 1.0e2, 2.0e3, "J/m^2", note=_CUT_NOTE)),
        OpticalParams(base_color=(0.95, 0.82, 0.50), specular_roughness=0.35, specular_ior=1.45,
                      subsurface_weight=1.0, subsurface_color=(0.95, 0.80, 0.45), subsurface_radius=0.005,
                      subsurface_radius_scale=(1.0, 0.8, 0.5), coat_weight=0.3, coat_roughness=0.2)),
    MaterialKind.MUSCLE: Material(MaterialKind.MUSCLE, MechanicalParams(
        density=_q(1060, 1040, 1090, "kg/m^3", note=_SOFT_NOTE),
        youngs_modulus=_q(5.0e4, 1.0e4, 5.0e5, "Pa", note=_SOFT_NOTE + "; passive, along fibre"),
        poisson_ratio=_q(0.49, 0.45, 0.499, "", note=_SOFT_NOTE),
        friction=_q(0.3, 0.1, 0.5, ""),
        cut_energy=_q(2.0e3, 5.0e2, 5.0e3, "J/m^2", note=_CUT_NOTE)),
        OpticalParams(base_color=(0.50, 0.07, 0.06), specular_roughness=0.35, specular_ior=1.4,
                      subsurface_weight=0.6, subsurface_color=(0.60, 0.10, 0.08), subsurface_radius=0.002,
                      coat_weight=0.4, coat_roughness=0.15)),
    MaterialKind.TENDON: Material(MaterialKind.TENDON, MechanicalParams(
        density=_q(1120, 1100, 1160, "kg/m^3", note=_SOFT_NOTE),
        youngs_modulus=_q(1.2e9, 0.5e9, 2.0e9, "Pa", note=_SOFT_NOTE + "; along fibre"),
        poisson_ratio=_q(0.45, 0.3, 0.49, "", note=_SOFT_NOTE),
        friction=_q(0.2, 0.05, 0.4, ""),
        cut_energy=_q(1.5e4, 5.0e3, 3.0e4, "J/m^2", note=_CUT_NOTE)),
        OpticalParams(base_color=(0.90, 0.88, 0.80), specular_roughness=0.3, specular_ior=1.45,
                      subsurface_weight=0.3, subsurface_radius=0.001, coat_weight=0.5, coat_roughness=0.1)),
    MaterialKind.BONE: Material(MaterialKind.BONE, MechanicalParams(
        density=_q(1900, 1800, 2000, "kg/m^3", note="cortical bone; " + _SOFT_NOTE),
        youngs_modulus=_q(1.8e10, 1.5e10, 2.2e10, "Pa", note="cortical bone, longitudinal; " + _SOFT_NOTE),
        poisson_ratio=_q(0.3, 0.2, 0.4, ""),
        friction=_q(0.3, 0.1, 0.5, ""),
        cut_energy=_q(3.0e5, 2.0e4, 1.0e6, "J/m^2", A,
                      "effective CHOPPING energy, tuning value: fracture toughness alone (order 1e3-2e4 J/m^2) "
                      "would let a 30 J reference cut sever a forearm; chopping also crushes and wedges. Needs a "
                      "sourced sharp-force bone trauma study before any claim")),
        OpticalParams(base_color=(0.90, 0.86, 0.74), specular_roughness=0.6, specular_ior=1.5,
                      subsurface_weight=0.2, subsurface_radius=0.001)),
    MaterialKind.CLOTH_WOOL: Material(MaterialKind.CLOTH_WOOL, MechanicalParams(
        density=_q(1300, 1250, 1350, "kg/m^3", note="wool fibre density"),
        youngs_modulus=_q(1.0e6, 1.0e5, 1.0e7, "Pa", note="effective in-plane modulus of woven wool; ESTIMATE"),
        poisson_ratio=_q(0.3, 0.1, 0.5, ""),
        friction=_q(0.4, 0.2, 0.7, "", note="wool on skin"),
        cut_energy=_q(3.0e3, 1.0e3, 1.0e4, "J/m^2", note=_CUT_NOTE),
        areal_density=_q(0.35, 0.25, 0.50, "kg/m^2", note="heavy uniform broadcloth"),
        stretch_compliance=_q(1.0e-6, 1.0e-8, 1.0e-4, "m/N", A, "XPBD tuning: nearly inextensible"),
        bend_compliance=_q(5.0e-3, 1.0e-4, 1.0e-1, "m/N", A, "XPBD tuning: soft drape"),
        damping=_q(0.5, 0.0, 5.0, "1/s", A, "XPBD tuning")),
        OpticalParams(base_color=(0.04, 0.06, 0.20), specular_roughness=0.85, specular_ior=1.5,
                      fuzz_weight=1.0, fuzz_color=(0.25, 0.30, 0.55), fuzz_roughness=0.5),
        notes="Dark blue uniform wool (granadero coat sleeve)."),
    MaterialKind.ARMOR_STEEL: Material(MaterialKind.ARMOR_STEEL, MechanicalParams(
        density=_q(7850, 7750, 8050, "kg/m^3", note="carbon steel, engineering handbook value; not yet registered"),
        youngs_modulus=_q(2.0e11, 1.9e11, 2.1e11, "Pa", note="carbon steel, engineering handbook value"),
        poisson_ratio=_q(0.29, 0.27, 0.30, ""),
        friction=_q(0.3, 0.15, 0.6, "", note="steel on steel / cloth"),
        cut_energy=_q(1.0e8, 1.0e7, 1.0e9, "J/m^2", A,
                      "blade-defeat tuning constant so a 1.5 mm steel shell is not cut by a hand-held sabre; "
                      "NOT a material property (plate defeat is plastic deformation, not fracture)")),
        OpticalParams(base_color=(0.62, 0.62, 0.64), base_metalness=1.0, specular_roughness=0.3),
        notes="Plate bracer."),
    MaterialKind.AIR: Material(MaterialKind.AIR, MechanicalParams(
        density=_q(1.2, 1.1, 1.3, "kg/m^3"), youngs_modulus=_q(0, 0, 0, "Pa"),
        poisson_ratio=_q(0, 0, 0, ""), friction=_q(0, 0, 0, ""), cut_energy=_q(0, 0, 0, "J/m^2")), None),
}


def material(kind: MaterialKind) -> Material:
    return MATERIALS[kind]


def material_table() -> list:
    """JSON-ready dump (value, range, unit, provenance) for reports and runtimes."""
    out = []
    for kind, m in MATERIALS.items():
        mech = {}
        for field_name in m.mechanical.__dataclass_fields__:
            q = getattr(m.mechanical, field_name)
            if q is not None:
                mech[field_name] = {"value": q.value, "range": [q.low, q.high], "unit": q.unit,
                                    "provenance": q.provenance.value, "note": q.note}
        opt = None
        if m.optical is not None:
            opt = {k: getattr(m.optical, k) for k in m.optical.__dataclass_fields__ if k != "provenance"}
            opt["provenance"] = m.optical.provenance.value
        out.append({"kind": kind.value, "mechanical": mech, "optical_openpbr": opt, "notes": m.notes})
    return out
