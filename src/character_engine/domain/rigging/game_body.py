"""Block body for the CE-GAME-v1 game rig: one capsule per game bone (Souls arena visuals, owner request).

A Workbench-level stand-in for a character mesh so the duel reads as two bodies instead of a skeleton display.
Like the canonical block dummy (:mod:`.block_dummy`) it is a proxy, not anatomy:

* each capsule runs along a game bone (head → tail of the game rig points, any pose / stature),
* its radius is the block dummy's per-region **envelope radius** (ESTIMATE, 1.80 m adult, scaled with stature);
  finger bones use half the hand radius and the clavicle the upper-arm radius (ASSUMED choices),
* every vertex of a capsule is weighted 100 % to its game bone (one influence),
* feet / balls are lifted to stay above the ground (as in the block dummy).

The mesh is built and skinned in Blender (``scripts/bake_game_body.py``) and exported as a glTF that Godot only
consumes (Blender-first rule).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..tissue import BodyRegion
from .block_dummy import ENVELOPE_RADIUS_M, REFERENCE_STATURE_M, BlockPlacement

Vec = Tuple[float, float, float]
E, A = ProvenanceState.ESTIMATE, ProvenanceState.ASSUMED


@dataclass(frozen=True)
class BodySegment:
    bone: str                         # game bone the capsule follows and is weighted to
    region: BodyRegion
    radius_scale: float = 1.0         # x envelope radius of the region
    on_ground: bool = False
    provenance: ProvenanceState = E


def _side(s: str) -> List[BodySegment]:
    out = [
        BodySegment(f"clavicle_{s}", BodyRegion.UPPER_ARM, provenance=A),
        BodySegment(f"upperarm_{s}", BodyRegion.UPPER_ARM),
        BodySegment(f"lowerarm_{s}", BodyRegion.FOREARM),
        BodySegment(f"hand_{s}", BodyRegion.HAND),
        BodySegment(f"ring_metacarpal_{s}", BodyRegion.HAND),
        BodySegment(f"pinky_metacarpal_{s}", BodyRegion.HAND),
        BodySegment(f"thigh_{s}", BodyRegion.THIGH),
        BodySegment(f"calf_{s}", BodyRegion.LEG),
        BodySegment(f"foot_{s}", BodyRegion.FOOT, on_ground=True),
        BodySegment(f"ball_{s}", BodyRegion.FOOT, on_ground=True),
    ]
    for finger in ("thumb", "index", "middle", "ring", "pinky"):
        out += [BodySegment(f"{finger}_0{i}_{s}", BodyRegion.HAND, 0.5, provenance=A) for i in (1, 2, 3)]
    return out


GAME_BODY_SEGMENTS: Tuple[BodySegment, ...] = (
    BodySegment("head", BodyRegion.HEAD),
    BodySegment("neck_01", BodyRegion.NECK),
    BodySegment("spine_03", BodyRegion.THORAX),
    BodySegment("spine_02", BodyRegion.ABDOMEN),
    BodySegment("spine_01", BodyRegion.ABDOMEN),
    BodySegment("pelvis", BodyRegion.PELVIS),
    *_side("l"),
    *_side("r"),
)


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def game_body_placements(points: Mapping[str, Tuple[Vec, Vec]], stature_m: float = REFERENCE_STATURE_M,
                         segments: Tuple[BodySegment, ...] = GAME_BODY_SEGMENTS) -> List[BlockPlacement]:
    """Capsules (hemisphere centres + radius) for game-rig ``points`` at ``stature_m``; weight bone = game bone."""
    if stature_m <= 0:
        raise ValueError("stature must be positive")
    k = stature_m / REFERENCE_STATURE_M
    out: List[BlockPlacement] = []
    for seg in segments:
        p0, p1 = points[seg.bone]
        r = round(ENVELOPE_RADIUS_M[seg.region] * seg.radius_scale * k, 5)
        d = _sub(p1, p0)
        length = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
        if length <= 2 * r:
            mid = tuple((p0[i] + p1[i]) / 2 for i in range(3))
            a = b = mid
            r = max(r, length / 2)
        else:
            u = tuple(c / length for c in d)
            a = tuple(p0[i] + u[i] * r for i in range(3))
            b = tuple(p1[i] - u[i] * r for i in range(3))
        if seg.on_ground:
            lift = r - min(a[2], b[2])
            if lift > 0:
                a, b = (a[0], a[1], a[2] + lift), (b[0], b[1], b[2] + lift)
        out.append(BlockPlacement(seg.bone, seg.region, seg.bone, a, b, r, seg.provenance))  # type: ignore[arg-type]
    return out


def body_spec(points: Mapping[str, Tuple[Vec, Vec]], stature_m: Optional[float] = None) -> Dict[str, object]:
    """Engine-neutral description of the body (its SHA-256 is stamped into the Blender export)."""
    caps = game_body_placements(points, stature_m or REFERENCE_STATURE_M)
    return {"segments": [{"bone": c.weight_bone, "region": c.region.value, "a": [round(v, 6) for v in c.a],
                          "b": [round(v, 6) for v in c.b], "radius_m": c.radius_m, "provenance": c.provenance.value}
                         for c in caps]}
