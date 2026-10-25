"""Block dummy: one solid capsule per body segment, rigidly bound to one canonical bone (owner request P1).

A test mannequin for collisions and coarse "muscle" volume, built over the canonical skeleton:

* each segment runs between the averaged joint points of a few canonical bones (head/tail),
* its radius is the per-region **envelope radius** already used for the skin graph (ESTIMATE,
  defined for a 1.80 m adult and scaled linearly with stature) — not an anatomical measurement,
* every vertex of a block is weighted 100 % to ``weight_bone``; the same capsule doubles as the
  collision shape.

Pure Python: the Blender addon turns the placements into meshes, weights and collision objects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..tissue import BodyRegion

Vec = Tuple[float, float, float]
Joint = Tuple[str, str]                     # (canonical bone, "head" | "tail")

REFERENCE_STATURE_M = 1.80

# Envelope radius per body region for a 1.80 m adult (ESTIMATE, proxy only; also used by the
# addon's skin envelope so both stay consistent).
ENVELOPE_RADIUS_M: Mapping[BodyRegion, float] = {
    BodyRegion.HEAD: 0.085, BodyRegion.NECK: 0.06, BodyRegion.THORAX: 0.13, BodyRegion.ABDOMEN: 0.13,
    BodyRegion.PELVIS: 0.14, BodyRegion.UPPER_ARM: 0.05, BodyRegion.FOREARM: 0.04, BodyRegion.HAND: 0.018,
    BodyRegion.THIGH: 0.08, BodyRegion.LEG: 0.055, BodyRegion.FOOT: 0.03,
}


@dataclass(frozen=True)
class BlockSegment:
    name: str
    region: BodyRegion
    start: Tuple[Joint, ...]                # averaged joint points
    end: Tuple[Joint, ...]
    weight_bone: str


@dataclass(frozen=True)
class BlockPlacement:
    name: str
    region: BodyRegion
    weight_bone: str
    a: Vec                                  # capsule axis end points (hemisphere centres)
    b: Vec
    radius_m: float
    provenance: ProvenanceState = ProvenanceState.ESTIMATE

    @property
    def extent_m(self) -> float:
        return _norm(_sub(self.b, self.a)) + 2 * self.radius_m


def _side(side: str) -> Tuple[BlockSegment, ...]:
    s = side
    return (
        BlockSegment(f"upper_arm.{s}", BodyRegion.UPPER_ARM, ((f"HUMERUS_{s}", "head"),), ((f"HUMERUS_{s}", "tail"),),
                     f"HUMERUS_{s}"),
        BlockSegment(f"forearm.{s}", BodyRegion.FOREARM, ((f"RADIUS_{s}", "head"), (f"ULNA_{s}", "head")),
                     ((f"RADIUS_{s}", "tail"), (f"ULNA_{s}", "tail")), f"RADIUS_{s}"),
        BlockSegment(f"hand.{s}", BodyRegion.HAND, ((f"CAPITATE_{s}", "head"),), ((f"PHALANX_DISTAL_3_{s}", "tail"),),
                     f"METACARPAL_3_{s}"),
        BlockSegment(f"thigh.{s}", BodyRegion.THIGH, ((f"FEMUR_{s}", "head"),), ((f"FEMUR_{s}", "tail"),), f"FEMUR_{s}"),
        BlockSegment(f"leg.{s}", BodyRegion.LEG, ((f"TIBIA_{s}", "head"),), ((f"TIBIA_{s}", "tail"),), f"TIBIA_{s}"),
        BlockSegment(f"foot.{s}", BodyRegion.FOOT, ((f"CALCANEUS_{s}", "head"),), ((f"METATARSAL_3_{s}", "tail"),),
                     f"TALUS_{s}"),
    )


BLOCK_SEGMENTS: Tuple[BlockSegment, ...] = (
    BlockSegment("head", BodyRegion.HEAD, (("CERVICAL_1", "head"),), (("FRONTAL", "tail"),), "OCCIPITAL"),
    BlockSegment("neck", BodyRegion.NECK, (("CERVICAL_7", "tail"),), (("CERVICAL_1", "head"),), "CERVICAL_4"),
    BlockSegment("thorax", BodyRegion.THORAX, (("THORACIC_12", "tail"),), (("THORACIC_1", "head"),), "THORACIC_6"),
    BlockSegment("abdomen", BodyRegion.ABDOMEN, (("LUMBAR_5", "tail"),), (("LUMBAR_1", "head"),), "LUMBAR_3"),
    BlockSegment("pelvis", BodyRegion.PELVIS, (("FEMUR_L", "head"), ("FEMUR_R", "head")), (("SACRUM", "head"),),
                 "SACRUM"),
    *_side("L"),
    *_side("R"),
)


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _norm(v: Vec) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _avg(points: Sequence[Vec]) -> Vec:
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n, sum(p[2] for p in points) / n)


def required_bones(segments: Sequence[BlockSegment] = BLOCK_SEGMENTS) -> List[str]:
    names = set()
    for seg in segments:
        names.update(b for b, _ in seg.start + seg.end)
        names.add(seg.weight_bone)
    return sorted(names)


def block_placements(points: Mapping[str, Tuple[Vec, Vec]], stature_m: float = REFERENCE_STATURE_M,
                     segments: Sequence[BlockSegment] = BLOCK_SEGMENTS) -> List[BlockPlacement]:
    """Capsules for ``points`` (canonical bone -> (head, tail), any pose) at ``stature_m``.

    The capsule spans exactly from the start joint to the end joint: hemisphere centres are inset by
    the radius; when a segment is shorter than its diameter it becomes a sphere at the midpoint.
    """
    missing = [b for b in required_bones(segments) if b not in points]
    if missing:
        raise KeyError(f"block dummy needs canonical bones missing from the skeleton: {missing}")
    if stature_m <= 0:
        raise ValueError("stature must be positive")
    k = stature_m / REFERENCE_STATURE_M
    out: List[BlockPlacement] = []
    for seg in segments:
        p0 = _avg([points[b][0 if end == "head" else 1] for b, end in seg.start])
        p1 = _avg([points[b][0 if end == "head" else 1] for b, end in seg.end])
        r = round(ENVELOPE_RADIUS_M[seg.region] * k, 5)
        d = _sub(p1, p0)
        length = _norm(d)
        if length <= 2 * r:
            mid = _avg([p0, p1])
            a = b = mid
            r = max(r, length / 2)
        else:
            u = (d[0] / length, d[1] / length, d[2] / length)
            a = (p0[0] + u[0] * r, p0[1] + u[1] * r, p0[2] + u[2] * r)
            b = (p1[0] - u[0] * r, p1[1] - u[1] * r, p1[2] - u[2] * r)
        out.append(BlockPlacement(seg.name, seg.region, seg.weight_bone, a, b, r))
    return out


def placements_by_name(placements: Sequence[BlockPlacement]) -> Dict[str, BlockPlacement]:
    return {p.name: p for p in placements}
