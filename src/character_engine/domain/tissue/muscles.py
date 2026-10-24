"""Catalogue of major skeletal muscles as bone-to-bone attachments.

Which bones a muscle originates from / inserts on is textbook gross anatomy
(``attachment_provenance = PROVEN``, any anatomy atlas). *Where* along the bone
the attachment sits is expressed as a fraction of head→tail and is an
``ESTIMATE`` used only to place proxy geometry; it is not a measured landmark.

Coverage: the muscles that define silhouette and wound relevance (limbs, trunk,
neck). Deep/small muscles are intentionally omitted until sourced data exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..anatomy.reference.source import ProvenanceState


@dataclass(frozen=True)
class MuscleSpec:
    name: str                      # canonical, uppercase, _L/_R for bilateral
    origin_bone: str
    origin_t: float                # 0 = bone head, 1 = bone tail (ESTIMATE)
    insertion_bone: str
    insertion_t: float
    radius_m: float                # proxy mid-belly radius (ESTIMATE)
    tendon_fraction: float = 0.15  # fraction of length that is tendon at each end (ESTIMATE)
    attachment_provenance: ProvenanceState = ProvenanceState.PROVEN
    geometry_provenance: ProvenanceState = ProvenanceState.ESTIMATE
    group: str = ""

    @property
    def is_bilateral(self) -> bool:
        return self.name.endswith(("_L", "_R"))


def _bilateral(name: str, ob: str, ot: float, ib: str, it: float, r: float, group: str, tendon: float = 0.15) -> List[MuscleSpec]:
    out = []
    for side in ("L", "R"):
        def s(b: str, side: str = side) -> str:
            return b if b in _AXIAL else f"{b}_{side}"
        out.append(MuscleSpec(f"{name}_{side}", s(ob), ot, s(ib), it, r, tendon, group=group))
    return out


_AXIAL = {"STERNUM", "SACRUM", "COCCYX", "OCCIPITAL", "MANDIBLE", "HYOID",
          *{f"CERVICAL_{i}" for i in range(1, 8)}, *{f"THORACIC_{i}" for i in range(1, 13)}, *{f"LUMBAR_{i}" for i in range(1, 6)}}

_CATALOGUE: List[MuscleSpec] = []
# --- shoulder / arm ---
_CATALOGUE += _bilateral("DELTOID", "CLAVICLE", 0.6, "HUMERUS", 0.45, 0.035, "shoulder")
_CATALOGUE += _bilateral("PECTORALIS_MAJOR", "STERNUM", 0.3, "HUMERUS", 0.2, 0.030, "chest", 0.10)
_CATALOGUE += _bilateral("LATISSIMUS_DORSI", "SACRUM", 0.1, "HUMERUS", 0.15, 0.025, "back", 0.10)
_CATALOGUE += _bilateral("TRAPEZIUS", "OCCIPITAL", 0.5, "CLAVICLE", 0.7, 0.020, "back", 0.10)
_CATALOGUE += _bilateral("BICEPS_BRACHII", "SCAPULA", 0.1, "RADIUS", 0.15, 0.022, "arm", 0.20)
_CATALOGUE += _bilateral("TRICEPS_BRACHII", "SCAPULA", 0.2, "ULNA", 0.02, 0.024, "arm", 0.20)
_CATALOGUE += _bilateral("BRACHIALIS", "HUMERUS", 0.5, "ULNA", 0.1, 0.016, "arm")
_CATALOGUE += _bilateral("BRACHIORADIALIS", "HUMERUS", 0.8, "RADIUS", 0.95, 0.012, "forearm", 0.30)
_CATALOGUE += _bilateral("FLEXOR_GROUP", "HUMERUS", 0.97, "METACARPAL_3", 0.2, 0.020, "forearm", 0.30)
_CATALOGUE += _bilateral("EXTENSOR_GROUP", "HUMERUS", 0.97, "METACARPAL_3", 0.1, 0.018, "forearm", 0.30)
# --- trunk ---
_CATALOGUE += _bilateral("RECTUS_ABDOMINIS", "STERNUM", 1.0, "COXAL", 0.9, 0.018, "abdomen", 0.05)
_CATALOGUE += _bilateral("EXTERNAL_OBLIQUE", "RIB_08", 0.5, "COXAL", 0.3, 0.012, "abdomen", 0.10)
_CATALOGUE += _bilateral("ERECTOR_SPINAE", "SACRUM", 0.2, "THORACIC_1", 0.5, 0.020, "back", 0.05)
_CATALOGUE += _bilateral("STERNOCLEIDOMASTOID", "STERNUM", 0.0, "TEMPORAL", 0.5, 0.010, "neck", 0.15)
# --- hip / thigh ---
_CATALOGUE += _bilateral("GLUTEUS_MAXIMUS", "COXAL", 0.2, "FEMUR", 0.25, 0.045, "hip", 0.10)
_CATALOGUE += _bilateral("GLUTEUS_MEDIUS", "COXAL", 0.1, "FEMUR", 0.05, 0.030, "hip", 0.10)
_CATALOGUE += _bilateral("ILIOPSOAS", "LUMBAR_3", 0.5, "FEMUR", 0.1, 0.020, "hip", 0.15)
_CATALOGUE += _bilateral("QUADRICEPS", "COXAL", 0.7, "PATELLA", 0.0, 0.045, "thigh", 0.12)
_CATALOGUE += _bilateral("HAMSTRINGS", "COXAL", 1.0, "TIBIA", 0.1, 0.030, "thigh", 0.18)
_CATALOGUE += _bilateral("ADDUCTOR_GROUP", "COXAL", 0.95, "FEMUR", 0.6, 0.032, "thigh", 0.10)
_CATALOGUE += _bilateral("SARTORIUS", "COXAL", 0.6, "TIBIA", 0.15, 0.010, "thigh", 0.15)
# --- leg / foot ---
_CATALOGUE += _bilateral("GASTROCNEMIUS", "FEMUR", 0.95, "CALCANEUS", 0.5, 0.032, "leg", 0.35)
_CATALOGUE += _bilateral("SOLEUS", "TIBIA", 0.15, "CALCANEUS", 0.5, 0.026, "leg", 0.30)
_CATALOGUE += _bilateral("TIBIALIS_ANTERIOR", "TIBIA", 0.1, "CUNEIFORM_MEDIAL", 0.5, 0.016, "leg", 0.30)
_CATALOGUE += _bilateral("PERONEUS_GROUP", "FIBULA", 0.2, "METATARSAL_5", 0.0, 0.012, "leg", 0.35)

MUSCLES: Dict[str, MuscleSpec] = {m.name: m for m in _CATALOGUE}


def muscles_attached_to(bone: str) -> Tuple[MuscleSpec, ...]:
    return tuple(m for m in _CATALOGUE if bone in (m.origin_bone, m.insertion_bone))
