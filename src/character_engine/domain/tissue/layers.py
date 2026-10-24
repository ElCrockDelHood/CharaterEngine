"""Tissue layers and body regions.

Layer *order* (outside → inside) is anatomical fact. Layer *thicknesses* are
region-level ESTIMATES with ranges and must not be read as measurements; replace
with sourced ultrasound/MRI tables when acquired (tracked in source_registry).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Mapping, Tuple

from ..anatomy.reference.source import ProvenanceState


class TissueLayer(Enum):
    """Outside → inside."""

    SKIN = "skin"          # epidermis + dermis
    FAT = "fat"            # subcutaneous adipose / superficial fascia
    MUSCLE = "muscle"
    TENDON = "tendon"      # + ligament / deep fascia at attachments
    BONE = "bone"
    VISCERA = "viscera"    # cavity content (thorax / abdomen / cranium)

    @property
    def depth_order(self) -> int:
        return list(TissueLayer).index(self)


class BodyRegion(Enum):
    HEAD = "head"
    NECK = "neck"
    THORAX = "thorax"
    ABDOMEN = "abdomen"
    PELVIS = "pelvis"
    UPPER_ARM = "upper_arm"
    FOREARM = "forearm"
    HAND = "hand"
    THIGH = "thigh"
    LEG = "leg"
    FOOT = "foot"


BODY_REGIONS = tuple(BodyRegion)


@dataclass(frozen=True)
class TissueProfile:
    """Nominal thickness (m) of each layer for a region, outside → inside."""

    region: BodyRegion
    thickness_m: Mapping[TissueLayer, float]
    thickness_range_m: Mapping[TissueLayer, Tuple[float, float]]
    has_cavity: bool
    provenance: ProvenanceState = ProvenanceState.ESTIMATE
    notes: str = ""

    def layers(self) -> Tuple[TissueLayer, ...]:
        order = [TissueLayer.SKIN, TissueLayer.FAT, TissueLayer.MUSCLE, TissueLayer.TENDON, TissueLayer.BONE]
        if self.has_cavity:
            order.append(TissueLayer.VISCERA)
        return tuple(layer for layer in order if layer in self.thickness_m)

    def depth_to_layer(self, layer: TissueLayer) -> float:
        """Cumulative depth (m) from the skin surface to the *outer* face of ``layer``."""
        d = 0.0
        for current in self.layers():
            if current == layer:
                return d
            d += self.thickness_m[current]
        raise KeyError(f"{layer} not present in {self.region}")

    def layer_at_depth(self, depth_m: float) -> TissueLayer:
        d = 0.0
        layers = self.layers()
        for current in layers:
            d += self.thickness_m[current]
            if depth_m < d:
                return current
        return layers[-1]

    def total_depth_m(self) -> float:
        return sum(self.thickness_m[layer] for layer in self.layers())


def _profile(region: BodyRegion, skin, fat, muscle, tendon, bone, cavity=None, notes="") -> TissueProfile:
    th: Dict[TissueLayer, float] = {}
    rng: Dict[TissueLayer, Tuple[float, float]] = {}
    for layer, (lo, hi) in ((TissueLayer.SKIN, skin), (TissueLayer.FAT, fat), (TissueLayer.MUSCLE, muscle),
                            (TissueLayer.TENDON, tendon), (TissueLayer.BONE, bone)):
        th[layer] = round((lo + hi) / 2, 4)
        rng[layer] = (lo, hi)
    if cavity is not None:
        th[TissueLayer.VISCERA] = round((cavity[0] + cavity[1]) / 2, 4)
        rng[TissueLayer.VISCERA] = cavity
    return TissueProfile(region=region, thickness_m=th, thickness_range_m=rng,
                         has_cavity=cavity is not None, notes=notes)


# All ranges in metres. ESTIMATE: order-of-magnitude values for proxy geometry and
# wound-depth classification only. Skin (epidermis+dermis) 1-4 mm is textbook range;
# the rest are coarse regional estimates pending sourced tables.
_PROFILES: Dict[BodyRegion, TissueProfile] = {
    BodyRegion.HEAD: _profile(BodyRegion.HEAD, (0.001, 0.003), (0.002, 0.006), (0.002, 0.008), (0.001, 0.002), (0.005, 0.008),
                              cavity=(0.10, 0.14), notes="Scalp over calvarium; cavity = cranial contents"),
    BodyRegion.NECK: _profile(BodyRegion.NECK, (0.001, 0.003), (0.003, 0.012), (0.010, 0.030), (0.002, 0.004), (0.010, 0.020),
                              notes="Great vessels and airway lie in the muscle layer"),
    BodyRegion.THORAX: _profile(BodyRegion.THORAX, (0.0015, 0.004), (0.005, 0.030), (0.010, 0.040), (0.002, 0.005), (0.006, 0.012),
                                cavity=(0.15, 0.25), notes="Bone = rib; cavity = lungs/heart"),
    BodyRegion.ABDOMEN: _profile(BodyRegion.ABDOMEN, (0.0015, 0.004), (0.010, 0.050), (0.010, 0.030), (0.002, 0.005), (0.0, 0.0),
                                 cavity=(0.15, 0.25), notes="No bone plate anteriorly; cavity = viscera"),
    BodyRegion.PELVIS: _profile(BodyRegion.PELVIS, (0.0015, 0.004), (0.010, 0.050), (0.020, 0.060), (0.003, 0.006), (0.010, 0.020),
                                cavity=(0.08, 0.12)),
    BodyRegion.UPPER_ARM: _profile(BodyRegion.UPPER_ARM, (0.001, 0.003), (0.004, 0.020), (0.020, 0.045), (0.002, 0.005), (0.018, 0.026)),
    BodyRegion.FOREARM: _profile(BodyRegion.FOREARM, (0.001, 0.003), (0.003, 0.012), (0.015, 0.035), (0.002, 0.005), (0.012, 0.018)),
    BodyRegion.HAND: _profile(BodyRegion.HAND, (0.001, 0.004), (0.002, 0.008), (0.004, 0.012), (0.001, 0.003), (0.006, 0.012)),
    BodyRegion.THIGH: _profile(BodyRegion.THIGH, (0.001, 0.003), (0.006, 0.030), (0.040, 0.080), (0.003, 0.006), (0.024, 0.032)),
    BodyRegion.LEG: _profile(BodyRegion.LEG, (0.001, 0.003), (0.004, 0.020), (0.020, 0.050), (0.003, 0.006), (0.020, 0.028)),
    BodyRegion.FOOT: _profile(BodyRegion.FOOT, (0.001, 0.005), (0.003, 0.015), (0.004, 0.015), (0.002, 0.004), (0.008, 0.015)),
}


def tissue_profile(region: BodyRegion) -> TissueProfile:
    return _PROFILES[region]


def region_of_bone(canonical_name: str) -> BodyRegion:
    """Map a canonical bone name to its body region (deterministic, name-based)."""
    n = canonical_name.upper()
    if n in REGION_OF_BONE:
        return REGION_OF_BONE[n]
    for prefix, region in _PREFIX_REGION:
        if n.startswith(prefix):
            return region
    raise KeyError(f"no region for bone {canonical_name}")


_PREFIX_REGION = (
    ("CERVICAL", BodyRegion.NECK), ("HYOID", BodyRegion.NECK),
    ("THORACIC", BodyRegion.THORAX), ("RIB_", BodyRegion.THORAX), ("STERNUM", BodyRegion.THORAX),
    ("CLAVICLE", BodyRegion.THORAX), ("SCAPULA", BodyRegion.THORAX),
    ("LUMBAR", BodyRegion.ABDOMEN),
    ("SACRUM", BodyRegion.PELVIS), ("COCCYX", BodyRegion.PELVIS), ("COXAL", BodyRegion.PELVIS),
    ("HUMERUS", BodyRegion.UPPER_ARM),
    ("RADIUS", BodyRegion.FOREARM), ("ULNA", BodyRegion.FOREARM),
    ("SCAPHOID", BodyRegion.HAND), ("LUNATE", BodyRegion.HAND), ("TRIQUETRUM", BodyRegion.HAND), ("PISIFORM", BodyRegion.HAND),
    ("TRAPEZIUM", BodyRegion.HAND), ("TRAPEZOID", BodyRegion.HAND), ("CAPITATE", BodyRegion.HAND), ("HAMATE", BodyRegion.HAND),
    ("METACARPAL", BodyRegion.HAND), ("PHALANX_", BodyRegion.HAND),
    ("FEMUR", BodyRegion.THIGH), ("PATELLA", BodyRegion.THIGH),
    ("TIBIA", BodyRegion.LEG), ("FIBULA", BodyRegion.LEG),
    ("TALUS", BodyRegion.FOOT), ("CALCANEUS", BodyRegion.FOOT), ("NAVICULAR", BodyRegion.FOOT), ("CUBOID", BodyRegion.FOOT),
    ("CUNEIFORM", BodyRegion.FOOT), ("METATARSAL", BodyRegion.FOOT), ("TOE_", BodyRegion.FOOT), ("PHALANX_FOOT", BodyRegion.FOOT),
)

REGION_OF_BONE: Dict[str, BodyRegion] = {
    name: BodyRegion.HEAD for name in (
        "CRANIUM", "FRONTAL", "PARIETAL_L", "PARIETAL_R", "TEMPORAL_L", "TEMPORAL_R", "OCCIPITAL", "SPHENOID", "ETHMOID",
        "MANDIBLE", "MAXILLA_L", "MAXILLA_R", "ZYGOMATIC_L", "ZYGOMATIC_R", "NASAL_L", "NASAL_R", "LACRIMAL_L", "LACRIMAL_R",
        "PALATINE_L", "PALATINE_R", "VOMER", "INFERIOR_NASAL_CONCHA_L", "INFERIOR_NASAL_CONCHA_R",
        "MALLEUS_L", "MALLEUS_R", "INCUS_L", "INCUS_R", "STAPES_L", "STAPES_R",
    )
}
REGION_OF_BONE["ROOT_SKELETON"] = BodyRegion.PELVIS
