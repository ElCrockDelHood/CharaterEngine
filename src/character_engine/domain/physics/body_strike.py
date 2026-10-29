"""Whole-body layered strike: one layered capsule per block-dummy segment, one ray, one wound.

This is the single contact interface the fight mockup needs: give it a weapon (a ``Blade`` or a blunt ``Impactor``),
a ray (origin, direction) and the posed canonical bones, and it answers *which segment was hit, where, how deep the
layers took it and which* ``Wound`` *comes out* — the same ``Wound`` the trauma module already consumes through the
unchanged ``assess_wound``.

Simplifications (ESTIMATE, tuning-level, all reported in the result):

* The ray hits the skin envelope of the nearest capsule (capsule = block-dummy segment). The layer models of
  ``cut.py`` / ``blunt.py`` are one-dimensional through the thickness, so only the *normal* component of the impact
  counts: the energy is scaled by ``cos(incidence)²`` (velocity component along the inward surface normal, squared).
  Glancing blows lose most of their energy; the tangential part is dropped, not converted into a slash.
* Garments are optional outer layers per segment (``garments``); nothing is dressed by default.
* No cloth simulation here (that lives in the XPBD samples); garment layers act as material layers only.
* Capsules do not overlap-resolve: where two block segments overlap (shoulder, hip) the first surface the ray meets wins.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

from ..materials.layered_capsule import LayeredCapsule, OuterLayer, layered_capsule
from ..rigging.block_dummy import BlockPlacement, block_placements
from ..tissue import BodyRegion
from ..trauma import WoundAssessment, assess_wound, blade_contact_to_wound, blunt_impact_to_wound
from .blunt import BluntResult, Impactor, blunt_through, blunt_wound
from .cut import Blade, CutResult, cut_through

Vec = Tuple[float, float, float]
Weapon = Union[Blade, Impactor]

MARCH_STEP_M = 0.002
RESIDUAL_BLUNT_CONTACT_RADIUS_M = 0.02      # same value the forearm sample uses for energy left under armour


@dataclass(frozen=True)
class StrikeResult:
    segment: str
    bone_hit: str
    point: Vec
    t_axial: float
    incidence_cos: float
    energy_in_j: float                       # weapon kinetic energy before the incidence scaling
    energy_normal_j: float                   # the part that goes through the layers
    stopped_in: str
    depth_below_skin_m: float
    model: str                               # "cut" or "blunt"
    detail: Union[CutResult, BluntResult]
    assessment: Optional[WoundAssessment]


class LayeredBody:
    """Layered capsules for every block segment of one posed skeleton."""

    def __init__(self, points: Mapping[str, Tuple[Vec, Vec]], stature_m: float = 1.80,
                 garments: Optional[Mapping[str, Sequence[OuterLayer]]] = None,
                 rigid_shell_energy_j: Optional[Mapping[BodyRegion, float]] = None) -> None:
        """``rigid_shell_energy_j``: optional per-region fracture energy of the rigid shell (rib cage, skull, long
        bone) for blunt hits; default None = the single catalog value (sample 2 behaviour)."""
        garments = garments or {}
        self.rigid_shell_energy_j = dict(rigid_shell_energy_j or {})
        self.placements: Dict[str, BlockPlacement] = {p.name: p for p in block_placements(points, stature_m)}
        self.capsules: Dict[str, LayeredCapsule] = {
            name: layered_capsule(p, tuple(garments.get(name, ()))) for name, p in self.placements.items()}

    def nearest_hit(self, origin: Vec, direction: Vec, max_distance_m: float = 3.0
                    ) -> Optional[Tuple[str, Vec, float, Vec]]:
        """First skin-envelope contact along the ray: (segment, point, t_axial, outward normal)."""
        d = _unit(direction)
        n_steps = int(max_distance_m / MARCH_STEP_M)
        for i in range(n_steps + 1):
            s = i * MARCH_STEP_M
            p = _add(origin, _mul(d, s))
            for name, lc in self.capsules.items():
                if lc.signed_distance(p) <= 0.0:
                    lo, hi = max(0.0, s - MARCH_STEP_M), s
                    for _ in range(24):
                        mid = 0.5 * (lo + hi)
                        if lc.signed_distance(_add(origin, _mul(d, mid))) <= 0.0:
                            hi = mid
                        else:
                            lo = mid
                    q = _add(origin, _mul(d, hi))
                    dist, t = lc.axial(q)
                    a, b = lc.placement.a, lc.placement.b
                    ab = _sub(b, a)
                    foot = _add(a, _mul(ab, t))
                    radial = _sub(q, foot)
                    norm = _norm(radial)
                    normal = _mul(radial, 1.0 / norm) if norm > 1e-9 else _mul(d, -1.0)
                    return name, q, t, normal
        return None

    def strike(self, weapon: Weapon, origin: Vec, direction: Vec) -> Optional[StrikeResult]:
        hit = self.nearest_hit(origin, direction)
        if hit is None:
            return None
        name, point, t, normal = hit
        lc = self.capsules[name]
        d = _unit(direction)
        cos = max(0.0, -_dot(d, normal))
        energy = weapon.kinetic_energy_j
        scale = cos * cos
        bone = lc.placement.weight_bone
        if isinstance(weapon, Blade):
            eff = Blade(weapon.effective_mass_kg, weapon.speed_m_s * cos, weapon.edge_width_m)
            cut = cut_through(lc, eff, t_axial=t)
            if cut.skin_depth_m > 0.0:
                wound = blade_contact_to_wound(bone, cut.skin_depth_m, weapon.edge_width_m,
                                               entry_point=tuple(round(c, 6) for c in point), direction=d)
            elif cut.residual_energy_j > 0.0:
                wound = blunt_impact_to_wound(bone, energy_j=cut.residual_energy_j,
                                              contact_radius_m=RESIDUAL_BLUNT_CONTACT_RADIUS_M)
            else:
                wound = None
            return StrikeResult(name, bone, tuple(round(c, 6) for c in point), round(t, 4), round(cos, 4),
                                round(energy, 4), round(energy * scale, 4), cut.stopped_in, cut.skin_depth_m, "cut",
                                cut, assess_wound(wound, lc.profile) if wound else None)
        eff_i = Impactor(weapon.effective_mass_kg, weapon.speed_m_s * cos, weapon.contact_radius_m)
        res = blunt_through(lc, eff_i, t_axial=t,
                            rigid_shell_energy_j=self.rigid_shell_energy_j.get(lc.placement.region))
        wound = blunt_wound(bone, eff_i, res)
        return StrikeResult(name, bone, tuple(round(c, 6) for c in point), round(t, 4), round(cos, 4),
                            round(energy, 4), round(energy * scale, 4), res.stopped_in, res.affected_depth_m, "blunt",
                            res, assess_wound(wound, lc.profile))

    def central_strike(self, segment: str, weapon: Weapon, from_dir: Vec = (0.0, -1.0, 0.0),
                       t_axial: float = 0.5) -> Optional[StrikeResult]:
        """Strike a segment at the axial position ``t_axial`` along ``-from_dir`` (default: from the front)."""
        p = self.placements[segment]
        centre = _add(p.a, _mul(_sub(p.b, p.a), t_axial))
        far = self.capsules[segment].outer_radius + 0.5
        u = _unit(from_dir)
        return self.strike(weapon, _add(centre, _mul(u, far)), _mul(u, -1.0))


def sweep(body: LayeredBody, weapon: Weapon) -> List[Dict[str, object]]:
    """One central frontal strike per segment (the 'what does this weapon do where' table)."""
    rows = []
    for name in body.capsules:
        r = body.central_strike(name, weapon)
        if r is None:
            rows.append({"segment": name, "hit": False, "hit_segment": None})
            continue
        a = r.assessment
        rows.append({"segment": name, "hit": r.segment == name, "hit_segment": r.segment, "model": r.model,
                     "stopped_in": r.stopped_in, "depth_mm": round(r.depth_below_skin_m * 1000, 1),
                     "severity": a.severity.name if a else None,
                     "deepest": a.deepest_layer.value if a else None, "fracture": a.fracture if a else None})
    return rows


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a: Vec, k: float) -> Vec:
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a: Vec) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: Vec) -> Vec:
    n = _norm(a)
    return (a[0] / n, a[1] / n, a[2] / n)


# Per-region fracture energy of the rigid shell under a blunt blow (J). ASSUMED: orders of magnitude recalled from the
# blunt-trauma biomechanics literature, NOT verified against sources in this repository; ranges are wide on purpose.
# Used only when passed to ``LayeredBody``; the catalog default (25 J, sample 2) stays the default.
FIGHT_RIGID_SHELL_ENERGY_J: Dict[BodyRegion, float] = {
    BodyRegion.HEAD: 80.0, BodyRegion.NECK: 40.0, BodyRegion.THORAX: 150.0, BodyRegion.ABDOMEN: 150.0,
    BodyRegion.PELVIS: 300.0, BodyRegion.UPPER_ARM: 120.0, BodyRegion.FOREARM: 80.0, BodyRegion.HAND: 20.0,
    BodyRegion.THIGH: 300.0, BodyRegion.LEG: 200.0, BodyRegion.FOOT: 30.0,
}
