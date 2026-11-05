"""Blade cut through a layered capsule: kinetic energy spent on cut area, shell by shell.

Model (ESTIMATE): a straight edge, perpendicular to the capsule axis and longer than the limb is wide, advances
along a radial direction. At a penetration ``d`` (from the outermost shell), the edge is at distance
``h = R_out - d`` from the axis and crosses every shell whose outer radius exceeds ``h``; the cut length inside
the disc of radius ``r`` is ``2 * sqrt(r^2 - h^2)``. Advancing by ``dd`` costs ``sum(G_c * length_in_shell) * dd``
(``G_c`` = material cut energy per area, J/m²). The blade stops when the spent energy reaches its kinetic energy.

What is NOT modelled: blade deflection, sliding (draw) cuts, rate effects, compression before cutting, shell
deformation. If the blade stops inside a shell that cannot be cut (armour), the remaining energy is reported as the
upper bound of what the limb receives as a blunt impact.

Where ``Blade`` comes from (A34, opt-in, ESTIMATE): :func:`blade_impact` turns a rigid weapon (mass, balance, rotational
inertia), a swing (grip speed + angular speed) and an impact point into the effective mass and normal speed at that
point. The physics is DERIVED, textbook rigid-body impulse: ``1 / m_eff = 1 / M + r² / I_cg``. Nothing in the default
tables uses it; ``Blade(0.6, 10.0, ...)`` stays the placeholder until the owner adopts this.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..materials.catalog import MaterialKind, material
from ..materials.layered_capsule import LayeredCapsule, Shell
from ..tissue import BodyRegion
from .collision import DEFAULT_BODY_MASS_KG, SEGMENT_MASS_FRACTION


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


# --- Weapon dynamics (A34): effective mass, rotational inertia and impact point -------------------------------------
# Positions are metres along the weapon axis from the centre of the grip (x = 0), positive towards the tip. The weapon
# is a straight rigid body and the impulse is normal to the axis, in the plane of the swing. A curved blade is read by
# its axial position, ASSUMED; blade vibration and the rotation during the few milliseconds of contact are ignored.

GRIP_TO_GUARD_M = 0.07                   # ASSUMED hand centre to guard
HILT_CG_M = 0.03                         # ASSUMED hilt (guard, grip, pommel) lumped between the guard and the hand
TIP_DENSITY_RATIO = 0.45                 # ASSUMED blade mass per length at the tip / at the guard (no measurement)

# Six Pattern 1796 light cavalry sabres weighed and balanced by M. Easton (A34 §3): (mass kg, balance m "from hilt",
# blade m). Informal, method not stated; No. 6 is an 1850-60 revival and No. 5 is non-regulation, both kept.
P1796_MEASURED = ((0.975, 0.175, 0.825), (0.950, 0.190, 0.830), (0.950, 0.145, 0.810),
                  (0.830, 0.160, 0.815), (0.860, 0.165, 0.780), (0.925, 0.170, 0.825))


@dataclass(frozen=True)
class BladeBody:
    """A weapon as a rigid body. No inertia has been measured: from a balance it is an ESTIMATE, never PROVEN."""

    mass_kg: float
    cg_m: float
    inertia_cg_kg_m2: float
    tip_m: float
    provenance: ProvenanceState = ProvenanceState.ESTIMATE

    def __post_init__(self) -> None:
        if self.mass_kg <= 0.0 or self.inertia_cg_kg_m2 <= 0.0 or self.tip_m <= 0.0:
            raise ValueError("mass, inertia and tip position must be positive")

    def inertia_about_kg_m2(self, x_m: float) -> float:
        """Parallel axis: ``I = I_cg + M d²``."""
        return self.inertia_cg_kg_m2 + self.mass_kg * (x_m - self.cg_m) ** 2

    def center_of_percussion_m(self, pivot_m: float = 0.0) -> float:
        """Impact point that gives no jolt at ``pivot_m``: ``pivot + I_pivot / (M a)``, ``a`` = pivot to CG."""
        arm = self.cg_m - pivot_m
        if arm <= 0.0:
            raise ValueError("the pivot must be on the hilt side of the centre of gravity")
        return pivot_m + self.inertia_about_kg_m2(pivot_m) / (self.mass_kg * arm)

    def pivot_velocity_change_per_impulse(self, impact_m: float, pivot_m: float = 0.0) -> float:
        """Speed change at ``pivot_m`` per unit impulse at ``impact_m`` (m/s per N·s) of the free body: the jolt in the
        hand. Positive = pushed back with the impulse, negative = levered forward, zero at the centre of percussion."""
        return 1.0 / self.mass_kg + (impact_m - self.cg_m) * (pivot_m - self.cg_m) / self.inertia_cg_kg_m2


def blade_body_from_balance(mass_kg: float, balance_from_guard_m: float, blade_length_m: float,
                            tip_density_ratio: float = TIP_DENSITY_RATIO, grip_to_guard_m: float = GRIP_TO_GUARD_M,
                            hilt_cg_m: float = HILT_CG_M) -> BladeBody:
    """Weapon from what collectors publish. The blade's mass per length falls linearly from the guard to the tip; the
    hilt is a point mass, so its own small inertia is left out. The split hilt / blade is the one that lands the centre
    of gravity on the balance. The inertia depends on ``tip_density_ratio``, which nobody published: ESTIMATE."""
    if not 0.0 < tip_density_ratio <= 1.0:
        raise ValueError("tip_density_ratio must be in (0, 1]")
    r = tip_density_ratio
    s_mean = blade_length_m * (1.0 + 2.0 * r) / (3.0 * (1.0 + r))       # centroid of the blade from the guard
    s2_mean = blade_length_m ** 2 * (1.0 + 3.0 * r) / (6.0 * (1.0 + r))
    blade_cg = grip_to_guard_m + s_mean
    cg = grip_to_guard_m + balance_from_guard_m
    blade_mass = mass_kg * (cg - hilt_cg_m) / (blade_cg - hilt_cg_m)
    if not 0.0 < blade_mass <= mass_kg:
        raise ValueError("no hilt / blade split reaches this balance with this blade")
    hilt_mass = mass_kg - blade_mass
    inertia = (blade_mass * (s2_mean - s_mean ** 2) + blade_mass * (blade_cg - cg) ** 2
               + hilt_mass * (hilt_cg_m - cg) ** 2)
    return BladeBody(mass_kg, cg, inertia, grip_to_guard_m + blade_length_m)


def _median(values: Tuple[float, ...]) -> float:
    s = sorted(values)
    return 0.5 * (s[(len(s) - 1) // 2] + s[len(s) // 2])


def p1796_sabre_body(tip_density_ratio: float = TIP_DENSITY_RATIO) -> BladeBody:
    """Median of the six measured sabres. "From hilt" is read as from the guard, ASSUMED: the source does not say."""
    mass, balance, blade = (_median(tuple(row[i] for row in P1796_MEASURED)) for i in range(3))
    return blade_body_from_balance(mass, balance, blade, tip_density_ratio)


def coupled_arm_mass_kg(body_mass_kg: float = DEFAULT_BODY_MASS_KG, include_forearm: bool = False) -> float:
    """Arm mass that may travel rigidly with the grip during contact (de Leva fractions, A14). Lumping it at the grip
    is ASSUMED. It only bounds the answer: ``effective_mass_at`` runs from 0 (free blade) to infinity (pinned grip)."""
    fraction = SEGMENT_MASS_FRACTION[BodyRegion.HAND]
    if include_forearm:
        fraction += SEGMENT_MASS_FRACTION[BodyRegion.FOREARM]
    return body_mass_kg * fraction


def effective_mass_at(body: BladeBody, impact_m: float, coupled_mass_kg: float = 0.0, coupled_at_m: float = 0.0
                      ) -> float:
    """Normal effective mass at the impact point: ``1 / m_eff = 1 / M + r² / I_cg`` of the weapon plus
    ``coupled_mass_kg`` rigidly attached at ``coupled_at_m``. At infinity the grip is a pin: ``m_eff = I_pin / d²``."""
    if coupled_mass_kg < 0.0:
        raise ValueError("coupled mass must not be negative")
    if math.isinf(coupled_mass_kg):
        d = impact_m - coupled_at_m
        if d == 0.0:
            return math.inf
        return body.inertia_about_kg_m2(coupled_at_m) / (d * d)
    total = body.mass_kg + coupled_mass_kg
    cg = (body.mass_kg * body.cg_m + coupled_mass_kg * coupled_at_m) / total
    inertia = (body.inertia_cg_kg_m2 + body.mass_kg * (body.cg_m - cg) ** 2
               + coupled_mass_kg * (coupled_at_m - cg) ** 2)
    return 1.0 / (1.0 / total + (impact_m - cg) ** 2 / inertia)


@dataclass(frozen=True)
class BladeSwing:
    """Planar swing at the moment of contact: grip speed along the cut plus rotation of the weapon about the grip."""

    grip_speed_m_s: float
    angular_speed_rad_s: float

    def speed_at(self, x_m: float) -> float:
        return self.grip_speed_m_s + self.angular_speed_rad_s * x_m


def swing_from_tip_speed(body: BladeBody, tip_speed_m_s: float, grip_fraction: float = 0.0) -> BladeSwing:
    """Swing for a given tip speed; ``grip_fraction`` = grip speed / tip speed (0 = pure rotation about the grip)."""
    if not 0.0 <= grip_fraction < 1.0:
        raise ValueError("grip_fraction must be in [0, 1)")
    return BladeSwing(tip_speed_m_s * grip_fraction, tip_speed_m_s * (1.0 - grip_fraction) / body.tip_m)


@dataclass(frozen=True)
class BladeImpact:
    impact_m: float
    speed_m_s: float                     # weapon speed at the impact point
    effective_mass_kg: float
    contact_energy_j: float              # ½ m_eff v²: what contact can take out of the swing, before the target split
    swing_energy_j: float                # kinetic energy of the weapon alone (translation + rotation about its CG)
    center_of_percussion_m: float        # with the grip as pivot
    grip_velocity_change_per_impulse: float
    blade: Blade                         # feeds cut_through / LayeredBody.strike unchanged
    provenance: ProvenanceState = ProvenanceState.ESTIMATE


def blade_impact(body: BladeBody, swing: BladeSwing, impact_m: float, edge_width_m: float,
                 coupled_mass_kg: float = 0.0, coupled_at_m: float = 0.0) -> BladeImpact:
    """Effective mass, speed and energy at ``impact_m``. The result's ``blade`` carries ESTIMATE provenance on both."""
    if not 0.0 < impact_m <= body.tip_m:
        raise ValueError("the impact point must lie on the weapon, beyond the grip")
    mass = effective_mass_at(body, impact_m, coupled_mass_kg, coupled_at_m)
    speed = swing.speed_at(impact_m)
    blade = Blade(mass, speed, edge_width_m, mass_provenance=ProvenanceState.ESTIMATE)
    cg_speed = swing.speed_at(body.cg_m)
    swing_energy = 0.5 * body.mass_kg * cg_speed ** 2 + 0.5 * body.inertia_cg_kg_m2 * swing.angular_speed_rad_s ** 2
    return BladeImpact(impact_m=impact_m, speed_m_s=speed, effective_mass_kg=mass,
                       contact_energy_j=blade.kinetic_energy_j, swing_energy_j=swing_energy,
                       center_of_percussion_m=body.center_of_percussion_m(),
                       grip_velocity_change_per_impulse=body.pivot_velocity_change_per_impulse(impact_m),
                       blade=blade)
