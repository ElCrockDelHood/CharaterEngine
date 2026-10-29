"""Blunt impact through a layered capsule: kinetic energy absorbed layer by layer (plateau crush model).

Model (ESTIMATE, tuning-level): an impactor with contact area ``A`` compresses each layer at its plateau stress
``σ`` up to its bottom-out strain ``ε``; fully crushing a layer of thickness ``t`` costs ``σ·A·ε·t`` joules. A
rigid shell (rib / skull) costs its ``fracture_energy`` once, all or nothing: if the energy that reaches it is
lower, the shell holds and the impact stops there (the remaining energy is reported as stored, not transmitted).
Air gaps between garment layers cost nothing and close completely.

The *affected depth* below the skin (sum of fully crushed tissue layers plus the partial fraction of the layer where
the energy ran out) is what the trauma entry point wants: it becomes ``Wound(BLUNT, depth_m=…)`` and goes through
the unchanged ``assess_wound``. The existing ``blunt_impact_to_wound`` maps energy with the single constant
``REFERENCE_BLUNT_ENERGY_J``; :func:`legacy_blunt_depth_m` reproduces that mapping so the two can be compared.

Not modelled: rate dependence, pressure waves through a shell that does not break, rib flexion, impactor
deformation, glancing blows, force-based (not energy-based) injury criteria. Steel plate needs its own model and is
rejected here on purpose.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..materials.catalog import MaterialKind, material
from ..materials.layered_capsule import LayeredCapsule
from ..tissue import TissueLayer
from ..trauma import REFERENCE_BLUNT_ENERGY_J, Wound, WoundType


@dataclass(frozen=True)
class Impactor:
    effective_mass_kg: float
    speed_m_s: float
    contact_radius_m: float                      # end-on contact patch (punch / baton tip)
    mass_provenance: ProvenanceState = ProvenanceState.PLACEHOLDER
    speed_provenance: ProvenanceState = ProvenanceState.ESTIMATE

    @property
    def kinetic_energy_j(self) -> float:
        return 0.5 * self.effective_mass_kg * self.speed_m_s ** 2

    @property
    def contact_area_m2(self) -> float:
        return math.pi * self.contact_radius_m ** 2


@dataclass(frozen=True)
class ShellAbsorption:
    shell: str
    material: str
    capacity_j: float                            # energy to fully crush / break the shell
    absorbed_j: float
    fraction: float                              # 0..1 of the capacity used
    compression_m: float


@dataclass(frozen=True)
class BluntResult:
    energy_in_j: float
    absorbed: Tuple[ShellAbsorption, ...]
    stopped_in: str                              # shell name, or "through"
    affected_depth_m: float                      # below the skin surface
    displacement_m: float                        # how far the impactor travels after first contact
    fractured: bool                              # a rigid shell broke
    stored_j: float                              # energy left when a rigid shell held (not transmitted)
    residual_j: float                            # energy left after the last shell (impact went through)
    provenance: ProvenanceState = ProvenanceState.ESTIMATE


def blunt_through(lc: LayeredCapsule, imp: Impactor, t_axial: float = 0.5) -> BluntResult:
    shells = [s for s in lc.shells if s.z_range is None or s.z_range[0] <= t_axial <= s.z_range[1]]
    energy = imp.kinetic_energy_j
    area = imp.contact_area_m2
    left = energy
    affected = disp = stored = 0.0
    fractured = False
    stopped = "through"
    rows: List[ShellAbsorption] = []
    for s in reversed(shells):                   # outside → in
        t = s.thickness
        tissue = s.tissue_layer is not None
        if s.material is MaterialKind.AIR:
            disp += t
            rows.append(ShellAbsorption(s.name, "air", 0.0, 0.0, 1.0, t))
            continue
        mech = material(s.material).mechanical
        if mech.fracture_energy is not None:     # rigid shell: all or nothing
            cap = mech.fracture_energy.value
            if left >= cap:
                left -= cap
                fractured = True
                disp += t                        # fragments are pushed in by about the wall thickness
                affected += t if tissue else 0.0
                rows.append(ShellAbsorption(s.name, s.material.value, cap, cap, 1.0, t))
                continue
            stored = left
            left = 0.0
            stopped = s.name
            rows.append(ShellAbsorption(s.name, s.material.value, cap, 0.0, 0.0, 0.0))
            break
        if mech.crush_stress is None or mech.crush_strain is None:
            raise ValueError(f"{s.material.value} has no crush parameters; blunt model does not cover it")
        eps = mech.crush_strain.value
        cap = mech.crush_stress.value * area * eps * t
        if left >= cap:
            left -= cap
            disp += eps * t
            affected += t if tissue else 0.0
            rows.append(ShellAbsorption(s.name, s.material.value, cap, cap, 1.0, eps * t))
            continue
        frac = left / cap
        disp += frac * eps * t
        affected += frac * t if tissue else 0.0
        rows.append(ShellAbsorption(s.name, s.material.value, cap, left, frac, frac * eps * t))
        left = 0.0
        stopped = s.name
        break
    return BluntResult(energy_in_j=round(energy, 6), absorbed=tuple(rows), stopped_in=stopped,
                       affected_depth_m=round(affected, 6), displacement_m=round(disp, 6), fractured=fractured,
                       stored_j=round(stored, 6), residual_j=round(left, 6))


def blunt_wound(bone_hit: str, imp: Impactor, result: BluntResult) -> Wound:
    """Wound for the trauma entry points: depth from the layer model, width from the contact patch."""
    return Wound(bone_hit=bone_hit, wound_type=WoundType.BLUNT, depth_m=round(result.affected_depth_m, 4),
                 width_m=round(2.0 * imp.contact_radius_m, 4), energy_j=result.energy_in_j,
                 provenance=ProvenanceState.ESTIMATE)


def legacy_blunt_depth_m(lc: LayeredCapsule, energy_j: float, reference_energy_j: Optional[float] = None) -> float:
    """Depth the old mapping gives: ``min(total, E / 400 J · depth_to_bone)`` on the fitted profile."""
    ref = REFERENCE_BLUNT_ENERGY_J if reference_energy_j is None else reference_energy_j
    prof = lc.profile
    return round(min(prof.total_depth_m(), max(0.0, energy_j / ref) * prof.depth_to_layer(TissueLayer.BONE)), 4)
