"""How far two bodies (or one body and itself) go into each other, on the block-body capsules (A36).

The bodies are the game block body (:mod:`..rigging.game_body`): one capsule per game bone, the radius of the block
dummy's envelope (ESTIMATE). Fingers and the two small metacarpal capsules are left out: hands are not posed finger by
finger yet, and a fist in a gi would otherwise read as fingers through cloth.

* :func:`penetrations` between two bodies: every capsule pair whose surfaces overlap, deepest first.
* :func:`self_penetrations` inside one body: limbs against the trunk and against the other limbs. Pairs that meet at a
  joint by construction (a bone and its parent, grandparent or siblings) are skipped, because the capsules of a chain
  overlap at every joint on purpose.

Touching is allowed; going in is not. ``contact_tolerance_m`` lets a gripping hand press into the other body by the
thickness of a gi (ASSUMED 1 cm); nothing else gets a tolerance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ..rigging.game_body import game_body_placements
from ..rigging.game_rig import GAME_BONES
from .weapon_clearance import segment_closest

Vec = Tuple[float, float, float]
Points = Mapping[str, Tuple[Vec, Vec]]

GI_THICKNESS_M = 0.01                     # ASSUMED: how far a gripping hand may press into the other body's capsule
_SKIP = ("thumb", "index", "middle", "ring_0", "pinky_0", "ring_metacarpal", "pinky_metacarpal")


@dataclass(frozen=True)
class Capsule:
    bone: str
    a: Vec
    b: Vec
    radius_m: float


@dataclass(frozen=True)
class Penetration:
    bone_a: str
    bone_b: str
    depth_m: float                        # how far the surfaces overlap (> 0)
    point_a: Vec                          # closest axis points
    point_b: Vec

    @property
    def normal(self) -> Vec:
        """Unit direction from body a's axis point to body b's: pushing b along it separates the pair."""
        d = tuple(self.point_b[i] - self.point_a[i] for i in range(3))
        n = math.sqrt(sum(c * c for c in d))
        return (0.0, 0.0, 1.0) if n < 1e-9 else tuple(c / n for c in d)


def body_capsules(points: Points) -> List[Capsule]:
    """Block-body capsules of a posed body in world points (no fingers, no small metacarpals)."""
    return [Capsule(c.weight_bone, c.a, c.b, c.radius_m) for c in game_body_placements(points)
            if not c.weight_bone.startswith(_SKIP)]


def _bound(c: Capsule) -> Tuple[Vec, float]:
    mid = tuple((c.a[i] + c.b[i]) / 2 for i in range(3))
    return mid, math.dist(c.a, c.b) / 2 + c.radius_m


def _pair(c1: Capsule, c2: Capsule, tolerance: float) -> Optional[Penetration]:
    (m1, r1), (m2, r2) = _bound(c1), _bound(c2)
    if math.dist(m1, m2) >= r1 + r2 - tolerance:             # bounding spheres apart: the capsules cannot overlap
        return None
    d, s, t = segment_closest(c1.a, c1.b, c2.a, c2.b)
    depth = c1.radius_m + c2.radius_m - d - tolerance
    if depth <= 0.0:
        return None
    pa = tuple(c1.a[i] + (c1.b[i] - c1.a[i]) * s for i in range(3))
    pb = tuple(c2.a[i] + (c2.b[i] - c2.a[i]) * t for i in range(3))
    return Penetration(c1.bone, c2.bone, depth, pa, pb)


def penetrations(a: Points, b: Points, tolerant_bones_a: Iterable[str] = (), tolerant_bones_b: Iterable[str] = (),
                 tolerance_m: float = GI_THICKNESS_M) -> List[Penetration]:
    """Every overlapping capsule pair between body ``a`` and body ``b``, deepest first.

    A pair where either capsule is in ``tolerant_bones_*`` (gripping hands) only counts beyond ``tolerance_m``."""
    ta, tb = set(tolerant_bones_a), set(tolerant_bones_b)
    ca, cb = body_capsules(a), body_capsules(b)
    out = []
    for c1 in ca:
        for c2 in cb:
            hit = _pair(c1, c2, tolerance_m if (c1.bone in ta or c2.bone in tb) else 0.0)
            if hit is not None:
                out.append(hit)
    return sorted(out, key=lambda p: -p.depth_m)


def _near_in_chain() -> Dict[str, set]:
    parent = {g.name: g.parent for g in GAME_BONES}
    near: Dict[str, set] = {n: set() for n in parent}
    for n in parent:
        up = [n]
        p = parent[n]
        for _ in range(3):                   # parent, grandparent, great-grandparent
            if p is None:
                break
            up.append(p)
            p = parent[p]
        for u in up:
            near[n].add(u)
            near[u].add(n)
        for m, pm in parent.items():         # siblings share the parent's joint
            if pm is not None and pm == parent[n]:
                near[n].add(m)
    return near


_NEAR = _near_in_chain()


def self_penetrations(points: Points, skip: Sequence[Tuple[str, str]] = ()) -> List[Penetration]:
    """Overlaps inside one body, leaving out pairs that meet at a joint by construction, deepest first."""
    caps = body_capsules(points)
    skip_set = {frozenset(s) for s in skip}
    out = []
    for i, c1 in enumerate(caps):
        for c2 in caps[i + 1:]:
            if c2.bone in _NEAR.get(c1.bone, ()) or frozenset((c1.bone, c2.bone)) in skip_set:
                continue
            hit = _pair(c1, c2, 0.0)
            if hit is not None:
                out.append(hit)
    return sorted(out, key=lambda p: -p.depth_m)


def deepest(found: Sequence[Penetration]) -> float:
    return found[0].depth_m if found else 0.0
