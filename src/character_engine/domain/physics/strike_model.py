"""Blunt strike with a reduced-mass collision and a force-based fracture criterion (concept of docs A11 / A14).

What changes with respect to ``blunt.py`` / ``body_strike.py`` (which stay as they are, so no earlier result moves):

* The striker is ``(effective mass m, speed v, contact radius)``. Only the part of its kinetic energy that the *struck
  segment cannot take along* deforms tissue: ``E_diss = ½·μ·v²`` with the reduced mass ``μ = m·M/(m+M)``, ``M`` = the
  struck segment's effective mass. The rest (``½·m·v² − E_diss``) is knock-back: it is reported, and belongs to a
  concussion / knockdown model, not to the wound.
* Fracture of the rigid shell (ribs, skull, long bones) is decided by the peak force ``F = v·√(k·μ)`` against a
  force range per region, with ``k`` the stiffness of the whole region under local loading. Cadaver thorax data
  (140 g at 20 m/s: 3.4 kN, 26 mm; 40 m/s: 10.6 kN, 55 mm) give ``k ≈ 1.3–1.9e5 N/m``, and the formula then
  reproduces the 20 m/s peak force to about 20 %. The layer stack (``blunt_through``) still decides *how deep* the
  damage goes; the shell is told whether it breaks (energy 0) or holds (energy ∞).
* The skull additionally uses its only measured energy criterion (22–24 J, Delye et al., 18 cadaver heads; the version
  read is IUTAM 2005, the 2007 year is unconfirmed) on ``E_diss``.

Reduced mass and the struck segment's effective mass come from ``collision.py`` (Decision 58): one table of target
masses for the whole engine (body mass × segment fraction, ESTIMATE). This module adds only what is specific to the
force criterion: region stiffness, fracture force ranges, the skull energy criterion and the depth-from-deflection
rule.

Provenance: SOURCED means the number or range was read in a published paper (see the note beside each); ASSUMED
means a placeholder in the right order of magnitude. Nothing here is PROVEN. Every force range is a *range*: the
fracture flag uses the midpoint and a probability is reported next to it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, Mapping, Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..tissue import BodyRegion, TissueLayer
from ..trauma import WoundAssessment, assess_wound
from .blunt import BluntResult, Impactor, blunt_through, blunt_wound
from .body_strike import LayeredBody
from .collision import reduced_mass, regional_target_mass_kg, target_mass_for

__all__ = ["REGION_RESPONSE", "TARGET_MASS_KG", "NOMINAL_SPEED_M_S", "RegionResponse", "Striker", "StrikeOutcome",
           "fracture_probability", "peak_force", "reduced_mass", "strike_blunt"]


@dataclass(frozen=True)
class RegionResponse:
    stiffness_n_per_m: float                     # whole-region local stiffness
    fracture_force_n: Tuple[float, float, float]  # low, mid, high
    fracture_energy_j: Optional[Tuple[float, float]] = None   # extra energy criterion on E_diss (skull)
    note: str = ""
    provenance: ProvenanceState = ProvenanceState.ASSUMED


# Target effective mass per region: the engine-wide table of collision.py (75 kg body, relaxed segments, ESTIMATE).
TARGET_MASS_KG: Mapping[BodyRegion, float] = regional_target_mass_kg()

# Order of magnitude per region. SOURCED entries are marked; everything else is ASSUMED and exists only so the
# model runs.
REGION_RESPONSE: Mapping[BodyRegion, RegionResponse] = {
    BodyRegion.HEAD: RegionResponse(1.0e5, (3000.0, 5000.0, 8000.0), (22.0, 24.0),
                                    "energy 22-24 J: Delye et al. (18 cadaver heads; IUTAM 2005 version read, 2007 unconfirmed) SOURCED; "
                                    "force range and k ASSUMED"),
    BodyRegion.NECK: RegionResponse(5.0e4, (1500.0, 3000.0, 5000.0), None, "ASSUMED"),
    BodyRegion.THORAX: RegionResponse(1.6e5, (1200.0, 3300.0, 5900.0), None,
                                      "k from cadaver thorax 3.4 kN / 26 mm and 10.6 kN / 55 mm; rib force range 1.2-5.9 kN "
                                      "(review citing others) and 3.3 kN = 25 % rib crack (popular article): SOURCED, weak"),
    BodyRegion.ABDOMEN: RegionResponse(8.0e4, (2000.0, 4000.0, 7000.0), None, "ASSUMED (lumbar spine / pelvis ring)"),
    BodyRegion.PELVIS: RegionResponse(3.0e5, (4000.0, 6000.0, 9000.0), None, "ASSUMED"),
    BodyRegion.UPPER_ARM: RegionResponse(1.0e5, (1500.0, 3000.0, 5000.0), None, "ASSUMED"),
    BodyRegion.FOREARM: RegionResponse(1.2e5, (670.0, 2100.0, 3550.0), None,
                                       "force range 670-3550 N cited in a review: SOURCED, weak"),
    BodyRegion.HAND: RegionResponse(8.0e4, (500.0, 1500.0, 2500.0), None, "ASSUMED"),
    BodyRegion.THIGH: RegionResponse(2.5e5, (3800.0, 4500.0, 8230.0), None,
                                     "force range ASSUMED: Kennedy 2004 (45 femurs, 3-point bending) reports peak bending MOMENTS "
                                     "352 +/- 83 and 348 +/- 96 N m, 50 % risk at 395 N m (50th male); converting to "
                                     "a force needs the span, not read (thesis pending)"),
    BodyRegion.LEG: RegionResponse(2.0e5, (4110.0, 6000.0, 8450.0), None,
                                   "tibia range 4110-8450 N cited in a review: SOURCED, weak"),
    BodyRegion.FOOT: RegionResponse(1.0e5, (1500.0, 3000.0, 5000.0), None, "ASSUMED"),
}

# Nominal strike speed per move kind (m/s). Punch 6.8-8.6 m/s (Mosler 2024, velocity at max force); kicks 5.6-7.2 m/s
# at impact for roundhouse (Gavagan 2017), up to 18 m/s in the literature; throw / shoulder ASSUMED.
NOMINAL_SPEED_M_S: Mapping[str, float] = {"punch": 7.5, "kick": 9.0, "throw": 6.0}


@dataclass(frozen=True)
class Striker:
    effective_mass_kg: float
    speed_m_s: float
    contact_radius_m: float

    @property
    def kinetic_energy_j(self) -> float:
        return 0.5 * self.effective_mass_kg * self.speed_m_s ** 2

    @staticmethod
    def from_move(energy_j: float, contact_radius_m: float, kind: str) -> Striker:
        """Nominal striker of a gameplay move: the table keeps ``energy_j``; v by kind, m = 2E/v²."""
        v = NOMINAL_SPEED_M_S.get(kind, NOMINAL_SPEED_M_S["punch"])
        return Striker(2.0 * energy_j / (v * v), v, contact_radius_m)


@dataclass(frozen=True)
class StrikeOutcome:
    segment: str
    region: str
    striker_energy_j: float
    reduced_mass_kg: float
    dissipated_j: float
    knockback_j: float
    target_speed_after_m_s: float            # inelastic: m·v/(m+M)
    peak_force_n: float
    fracture_force_n: Tuple[float, float, float]
    fracture_probability: float              # linear in the force range
    fractured: bool
    energy_criterion_met: Optional[bool]
    layers: BluntResult
    assessment: WoundAssessment
    provenance: ProvenanceState = ProvenanceState.ESTIMATE


def peak_force(v: float, k: float, mu: float) -> float:
    """Linear-spring collision: ½·μ·v² = ½·k·x² and F = k·x give F = v·√(k·μ)."""
    return v * math.sqrt(k * mu)


def fracture_probability(force: float, rng: Tuple[float, float, float]) -> float:
    low, mid, high = rng
    if force <= low:
        return 0.0
    if force >= high:
        return 1.0
    return 0.5 * (force - low) / (mid - low) if force <= mid else 0.5 + 0.5 * (force - mid) / (high - mid)


def strike_blunt(body: LayeredBody, segment: str, striker: Striker,
                 response: Optional[Mapping[BodyRegion, RegionResponse]] = None,
                 t_axial: float = 0.5, target_mass_kg: Optional[Mapping[BodyRegion, float]] = None) -> StrikeOutcome:
    """Central normal blunt strike on one segment (same convention as ``LayeredBody.central_strike``).

    ``target_mass_kg`` defaults to :data:`TARGET_MASS_KG` (``collision.regional_target_mass_kg()``); pass another
    body mass or bracing through ``collision.regional_target_mass_kg(body_mass, bracing)``."""
    resp_table: Dict[BodyRegion, RegionResponse] = dict(response or REGION_RESPONSE)
    lc = body.capsules[segment]
    region = lc.placement.region
    resp = resp_table[region]
    big_m = target_mass_for(region, target_mass_kg or TARGET_MASS_KG)
    m, v = striker.effective_mass_kg, striker.speed_m_s
    mu = reduced_mass(m, big_m)
    e_diss = 0.5 * mu * v * v
    force = peak_force(v, resp.stiffness_n_per_m, mu)
    prob = fracture_probability(force, resp.fracture_force_n)
    fractured = force >= resp.fracture_force_n[1]
    energy_ok: Optional[bool] = None
    if resp.fracture_energy_j is not None:
        energy_ok = e_diss >= 0.5 * (resp.fracture_energy_j[0] + resp.fracture_energy_j[1])
        fractured = fractured and energy_ok          # skull: both criteria
    imp = Impactor(mu, v, striker.contact_radius_m)          # kinetic energy of this impactor = E_diss
    res = blunt_through(lc, imp, t_axial=t_axial, rigid_shell_energy_j=0.0 if fractured else math.inf)
    # Depth that matters for injury is the peak compression x = F/k (chest deflection is the classic criterion), not
    # the depth the plateau model could crush with the leftover energy: the region springs back. A fractured shell
    # means the bone layer is breached, so the wound must at least reach it.
    deflection = force / resp.stiffness_n_per_m
    depth = min(res.affected_depth_m, deflection)
    if fractured:
        depth = max(depth, lc.profile.depth_to_layer(TissueLayer.BONE) + 1.0e-4)
    res = replace(res, affected_depth_m=round(depth, 6))
    wound = blunt_wound(lc.placement.weight_bone, imp, res)
    return StrikeOutcome(
        segment=segment, region=region.value, striker_energy_j=round(striker.kinetic_energy_j, 3),
        reduced_mass_kg=round(mu, 4), dissipated_j=round(e_diss, 3),
        knockback_j=round(striker.kinetic_energy_j - e_diss, 3),
        target_speed_after_m_s=round(m * v / (m + big_m), 4),
        peak_force_n=round(force, 1), fracture_force_n=resp.fracture_force_n,
        fracture_probability=round(prob, 3), fractured=fractured, energy_criterion_met=energy_ok, layers=res,
        assessment=assess_wound(wound, lc.profile))
