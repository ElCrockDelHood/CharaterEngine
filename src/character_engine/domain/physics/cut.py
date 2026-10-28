"""Blade cut through a layered capsule: kinetic energy spent on cut area, shell by shell.

Model (ESTIMATE): a straight edge, perpendicular to the capsule axis and longer than the limb is wide, advances
along a radial direction. At a penetration ``d`` (from the outermost shell), the edge is at distance
``h = R_out - d`` from the axis and crosses every shell whose outer radius exceeds ``h``; the cut length inside
the disc of radius ``r`` is ``2 * sqrt(r^2 - h^2)``. Advancing by ``dd`` costs ``sum(G_c * length_in_shell) * dd``
(``G_c`` = material cut energy per area, J/m²). The blade stops when the spent energy reaches its kinetic energy.

What is NOT modelled: blade deflection, sliding (draw) cuts, rate effects, compression before cutting, shell
deformation. If the blade stops inside a shell that cannot be cut (armour), the remaining energy is reported as the
upper bound of what the limb receives as a blunt impact.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..materials.catalog import MaterialKind, material
from ..materials.layered_capsule import LayeredCapsule, Shell


@dataclass(frozen=True)
class Blade:
    """Hand-held blade strike. Mass and speed carry their own provenance."""

    effective_mass_kg: float
    speed_m_s: float
    edge_width_m: float              # blade thickness at the edge region → wound width
    mass_provenance: ProvenanceState = ProvenanceState.PLACEHOLDER
    speed_provenance: ProvenanceState = ProvenanceState.ESTIMATE

    @property
    def kinetic_energy_j(self) -> float:
        return 0.5 * self.effective_mass_kg * self.speed_m_s ** 2


@dataclass(frozen=True)
class CutResult:
    penetration_m: float             # from the outermost shell surface
    skin_depth_m: float              # depth below the skin surface (0 if the skin was not reached)
    stopped_in: str                  # shell name where the blade stopped ("through" if it went through)
    stopped_material: Optional[MaterialKind]
    energy_in_j: float
    energy_spent_j: float
    residual_energy_j: float         # energy left when the blade stopped in an uncuttable shell
    shells_cut: Tuple[str, ...]
    transected: bool
    provenance: ProvenanceState = ProvenanceState.ESTIMATE


def _length_inside(r: float, h: float) -> float:
    return 2.0 * math.sqrt(r * r - h * h) if r > abs(h) else 0.0


def _shell_at(lc: LayeredCapsule, h: float, t_axial: float) -> Optional[Shell]:
    for s in lc.shells:
        if s.r_inner <= abs(h) < s.r_outer and (s.z_range is None or s.z_range[0] <= t_axial <= s.z_range[1]):
            return s
    return None


def cut_through(lc: LayeredCapsule, blade: Blade, t_axial: float = 0.5, step_m: float = 1.0e-4,
                uncuttable_energy_per_area: float = 1.0e7) -> CutResult:
    """March the edge inward from the outermost shell present at axial position ``t_axial`` (0 = a, 1 = b)."""
    shells = [s for s in lc.shells if s.z_range is None or s.z_range[0] <= t_axial <= s.z_range[1]]
    r_out = shells[-1].r_outer
    energy = blade.kinetic_energy_j
    spent = 0.0
    cut = []
    d = 0.0
    stopped: Optional[Shell] = None
    while d < 2.0 * r_out:
        h = r_out - (d + step_m / 2.0)
        cost_per_m = 0.0
        for s in shells:
            gc = material(s.material).mechanical.cut_energy.value
            if gc == 0.0:
                continue
            seg = _length_inside(s.r_outer, h) - _length_inside(s.r_inner, h)
            if seg > 0.0:
                cost_per_m += gc * seg
                if s.name not in cut:
                    cut.append(s.name)
        cost = cost_per_m * step_m
        if spent + cost > energy:
            frac = (energy - spent) / cost if cost > 0 else 0.0
            d += step_m * frac
            spent = energy
            stopped = _shell_at(lc, r_out - d, t_axial)
            break
        spent += cost
        d += step_m
    transected = stopped is None and d >= 2.0 * r_out - 1e-12
    residual = 0.0
    if stopped is not None and material(stopped.material).mechanical.cut_energy.value >= uncuttable_energy_per_area:
        residual = energy                       # nothing cut below the armour: all of it reaches the limb (bound)
    skin_depth = max(0.0, lc.skin_radius - (r_out - d)) if not transected else 2.0 * lc.skin_radius
    shells_cut = tuple(n for n in cut if not (residual > 0.0 and n == stopped.name))
    return CutResult(penetration_m=round(d, 6), skin_depth_m=round(skin_depth, 6),
                     stopped_in=stopped.name if stopped else "through",
                     stopped_material=stopped.material if stopped else None,
                     energy_in_j=round(energy, 6), energy_spent_j=round(spent, 6),
                     residual_energy_j=round(residual, 6), shells_cut=shells_cut, transected=transected)
