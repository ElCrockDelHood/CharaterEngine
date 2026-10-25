"""Wound assessment from a penetration path through the regional tissue profile.

Deterministic and engine-agnostic: engines supply *where* (canonical bone hit,
depth reached, wound type, width); this module answers *what was breached* and
*how bad it is*. Severity follows the Abbreviated Injury Scale (AIS) ladder
1 minor … 6 maximal; region weights and depth thresholds are ESTIMATE, tuned for
simulation plausibility, not clinical prediction. Replace with sourced trauma
registry data when available (see source_registry).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..tissue.layers import BodyRegion, TissueLayer, TissueProfile, region_of_bone, tissue_profile


class WoundType(Enum):
    ABRASION = "abrasion"        # skin only
    LACERATION = "laceration"    # tearing, irregular
    INCISION = "incision"        # clean cut (blade)
    STAB = "stab"                # deep, narrow
    GUNSHOT = "gunshot"          # projectile, cavitation
    BLUNT = "blunt"              # contusion / fracture, skin may be intact
    BURN = "burn"
    AMPUTATION = "amputation"


class Severity(Enum):
    """AIS-like ladder."""

    MINOR = 1
    MODERATE = 2
    SERIOUS = 3
    SEVERE = 4
    CRITICAL = 5
    MAXIMAL = 6


# Baseline lethality weight per region (0..1) — ESTIMATE.
LETHALITY_BY_REGION: Mapping[BodyRegion, float] = {
    BodyRegion.HEAD: 0.90,
    BodyRegion.NECK: 0.85,
    BodyRegion.THORAX: 0.80,
    BodyRegion.ABDOMEN: 0.65,
    BodyRegion.PELVIS: 0.55,
    BodyRegion.THIGH: 0.35,   # femoral vessels
    BodyRegion.UPPER_ARM: 0.25,
    BodyRegion.LEG: 0.15,
    BodyRegion.FOREARM: 0.15,
    BodyRegion.HAND: 0.05,
    BodyRegion.FOOT: 0.05,
}

# Maximum AIS-like severity reachable by a non-amputating wound in each region — ESTIMATE
# (AIS codes extremity injuries at most 3-4; proximal limbs may reach 5 via major vessels).
_REGION_SEVERITY_CAP: Mapping[BodyRegion, int] = {
    BodyRegion.HEAD: 6, BodyRegion.NECK: 6, BodyRegion.THORAX: 6, BodyRegion.ABDOMEN: 5, BodyRegion.PELVIS: 5,
    BodyRegion.THIGH: 5, BodyRegion.UPPER_ARM: 4, BodyRegion.LEG: 4, BodyRegion.FOREARM: 3,
    BodyRegion.HAND: 3, BodyRegion.FOOT: 3,
}

# Layer breached → base severity contribution — ESTIMATE.
_LAYER_SEVERITY = {
    TissueLayer.SKIN: 1,
    TissueLayer.FAT: 1,
    TissueLayer.MUSCLE: 2,
    TissueLayer.TENDON: 3,
    TissueLayer.BONE: 3,
    TissueLayer.VISCERA: 5,
}

_TYPE_MULTIPLIER = {
    WoundType.ABRASION: 0.5,
    WoundType.LACERATION: 1.0,
    WoundType.INCISION: 1.0,
    WoundType.STAB: 1.2,
    WoundType.GUNSHOT: 1.5,
    WoundType.BLUNT: 0.8,
    WoundType.BURN: 1.0,
    WoundType.AMPUTATION: 2.0,
}


@dataclass(frozen=True)
class Wound:
    bone_hit: str                 # canonical bone nearest the entry point
    wound_type: WoundType
    depth_m: float                # penetration depth from skin surface
    width_m: float = 0.01
    energy_j: Optional[float] = None
    entry_point: Optional[Tuple[float, float, float]] = None  # canonical frame
    direction: Optional[Tuple[float, float, float]] = None
    provenance: ProvenanceState = ProvenanceState.USER_INPUT

    def __post_init__(self):
        if self.depth_m < 0 or self.width_m < 0:
            raise ValueError("depth/width must be non-negative")


@dataclass(frozen=True)
class WoundAssessment:
    wound: Wound
    region: BodyRegion
    layers_breached: Tuple[TissueLayer, ...]
    deepest_layer: TissueLayer
    severity: Severity
    lethality: float                       # 0..1 probability-like score
    bleeding_rate: float                   # arbitrary units/s for simulation
    fracture: bool
    incapacitating: bool
    notes: str = ""
    provenance: ProvenanceState = ProvenanceState.ESTIMATE
    tags: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_lethal(self) -> bool:
        return self.lethality >= 0.5 or self.severity in (Severity.CRITICAL, Severity.MAXIMAL)


def _layers_breached(profile: TissueProfile, depth_m: float) -> Tuple[TissueLayer, ...]:
    out = []
    depth_before = 0.0
    for layer in profile.layers():
        if out and depth_m <= depth_before:
            break
        out.append(layer)
        depth_before += profile.thickness_m[layer]
    return tuple(out)


def assess_wound(wound: Wound, profile: Optional[TissueProfile] = None) -> WoundAssessment:
    region = region_of_bone(wound.bone_hit)
    profile = profile or tissue_profile(region)

    if wound.wound_type == WoundType.AMPUTATION:
        layers = profile.layers()
    elif wound.wound_type == WoundType.BLUNT:
        # Blunt trauma: skin often intact; depth expresses the energy-affected depth.
        layers = tuple(layer for layer in _layers_breached(profile, wound.depth_m) if layer is not TissueLayer.SKIN) or (TissueLayer.SKIN,)
    else:
        layers = _layers_breached(profile, wound.depth_m)

    deepest = layers[-1]
    base = max(_LAYER_SEVERITY[layer] for layer in layers)
    score = base * _TYPE_MULTIPLIER[wound.wound_type]
    # Width/cavitation increases severity for wide wounds.
    if wound.width_m > 0.03 and wound.wound_type is not WoundType.BLUNT:
        score += 1
    if wound.wound_type == WoundType.GUNSHOT and (wound.energy_j or 0) > 500:
        score += 1
    sev_value = int(min(6, max(1, round(score))))
    if region in (BodyRegion.HEAD, BodyRegion.THORAX) and deepest == TissueLayer.VISCERA:
        sev_value = max(sev_value, 5)
    if wound.wound_type is not WoundType.AMPUTATION:
        sev_value = min(sev_value, _REGION_SEVERITY_CAP[region])
    severity = Severity(sev_value)

    depth_ratio = min(1.0, wound.depth_m / max(profile.total_depth_m(), 1e-6))
    lethality = LETHALITY_BY_REGION[region] * depth_ratio * min(1.0, severity.value / 5.0)
    if wound.wound_type == WoundType.AMPUTATION:
        lethality = max(lethality, 0.4 if region in (BodyRegion.THIGH, BodyRegion.UPPER_ARM) else 0.15)
    lethality = round(min(1.0, lethality), 3)

    vascular = TissueLayer.MUSCLE in layers or TissueLayer.VISCERA in layers
    bleeding = round((0.2 if TissueLayer.SKIN in layers else 0.0)
                     + (1.0 if vascular else 0.0) * (1.0 + wound.width_m * 20.0)
                     * (2.5 if region in (BodyRegion.NECK, BodyRegion.THIGH, BodyRegion.THORAX, BodyRegion.ABDOMEN) else 1.0), 3)
    if wound.wound_type == WoundType.BURN:
        bleeding = 0.0

    fracture = TissueLayer.BONE in layers and wound.wound_type in (
        WoundType.BLUNT, WoundType.GUNSHOT, WoundType.AMPUTATION) or (
        TissueLayer.BONE in layers and wound.wound_type in (WoundType.INCISION, WoundType.LACERATION) and wound.width_m > 0.03)
    incapacitating = severity.value >= 3 or fracture or region in (BodyRegion.HEAD, BodyRegion.NECK) and severity.value >= 2

    tags = []
    if fracture:
        tags.append("fracture")
    if vascular:
        tags.append("haemorrhage")
    if deepest == TissueLayer.VISCERA:
        tags.append("cavity_penetration")
    if lethality >= 0.5:
        tags.append("lethal_risk")

    return WoundAssessment(
        wound=wound, region=region, layers_breached=layers, deepest_layer=deepest, severity=severity,
        lethality=lethality, bleeding_rate=bleeding, fracture=fracture, incapacitating=incapacitating,
        notes=f"{wound.wound_type.value} at {wound.bone_hit} ({region.value}), depth {wound.depth_m*1000:.0f} mm",
        tags=tuple(tags),
    )


#: Strike energy (J) at which the affected depth reaches the regional bone surface — ESTIMATE
#: gameplay constant (order of magnitude of a trained straight punch, ~150–400 J in boxing studies).
REFERENCE_BLUNT_ENERGY_J = 400.0


def blunt_impact_to_wound(bone_hit: str, impulse: Optional[float] = None, contact_radius_m: float = 0.04,
                          energy_j: Optional[float] = None) -> Wound:
    """Map a gameplay impact (e.g. a punch) to a blunt wound.

    Give either ``impulse`` (dimensionless 0..1+, 1.0 = reaches bone) or ``energy_j``
    (converted with :data:`REFERENCE_BLUNT_ENERGY_J`). Depth is capped at the regional
    total depth so very strong hits can fracture and reach the cavity. ESTIMATE mapping.
    """
    if impulse is None:
        if energy_j is None:
            raise ValueError("provide impulse or energy_j")
        impulse = energy_j / REFERENCE_BLUNT_ENERGY_J
    region = region_of_bone(bone_hit)
    profile = tissue_profile(region)
    depth = min(profile.total_depth_m(), max(0.0, impulse) * profile.depth_to_layer(TissueLayer.BONE))
    return Wound(bone_hit=bone_hit, wound_type=WoundType.BLUNT, depth_m=round(depth, 4),
                 width_m=contact_radius_m * 2, energy_j=energy_j)


def blade_contact_to_wound(bone_hit: str, penetration_m: float, blade_width_m: float,
                           entry_point: Optional[Tuple[float, float, float]] = None,
                           direction: Optional[Tuple[float, float, float]] = None) -> Wound:
    """Map a geometric blade contact (e.g. a sabre entering a collision proxy) to an INCISION.

    ``penetration_m`` is how far the blade entered the body envelope proxy, used as the wound depth from the
    skin surface; ``blade_width_m`` is the blade width. Both come from proxies (envelope radii ESTIMATE,
    placeholder blade), so the wound is ESTIMATE. No energy is set: the incision assessment depends on depth
    and width only, and no cited cutting-energy model exists in the repository.
    """
    if penetration_m <= 0:
        raise ValueError("no penetration: a blade contact needs penetration_m > 0")
    return Wound(bone_hit=bone_hit, wound_type=WoundType.INCISION, depth_m=round(penetration_m, 4),
                 width_m=round(blade_width_m, 4), energy_j=None, entry_point=entry_point, direction=direction,
                 provenance=ProvenanceState.ESTIMATE)
