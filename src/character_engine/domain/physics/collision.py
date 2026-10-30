"""Striker / target effective masses and the energy split of a blunt or cutting contact (A14).

Physics (DERIVED, textbook): a striker of effective mass ``m_s`` at speed ``v`` hits a free target segment of
effective mass ``m_t``. In a perfectly inelastic contact both end at the common speed ``V = m_s v / (m_s + m_t)``
and the energy available to deform tissue is ``½ μ v²`` with the reduced mass ``μ = m_s m_t / (m_s + m_t)``. The
rest, ``½ (m_s + m_t) V²``, stays as motion of striker + segment: knockback and head / segment acceleration, the
input of a knockdown or concussion model, not of tissue damage. ``m_t → ∞`` (immovable target) gives back the old
``½ m_s v²``.

Target effective mass per region (ESTIMATE): body mass × segment mass fraction. The fractions are recalled from the
de Leva (1996) adjustment of Zatsiorsky–Seluyanov segment parameters (male) and are NOT yet verified against the
paper in this repository. A struck segment drags its neighbours along (bracing, a stiff neck), so the real coupled
mass is at least the segment mass; ``bracing`` multiplies it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Mapping, Optional

from ..anatomy.reference.source import ProvenanceState
from ..tissue import BodyRegion

DEFAULT_BODY_MASS_KG = 75.0              # ASSUMED adult male, only used when no body mass is given

# Fraction of body mass per region (head and neck share the head+neck segment; thorax / abdomen / pelvis are the
# upper / middle / lower trunk). ESTIMATE: de Leva 1996 values, recalled, pending verification (A14 §5).
SEGMENT_MASS_FRACTION: Dict[BodyRegion, float] = {
    BodyRegion.HEAD: 0.0694, BodyRegion.NECK: 0.0694,
    BodyRegion.THORAX: 0.1596, BodyRegion.ABDOMEN: 0.1633, BodyRegion.PELVIS: 0.1117,
    BodyRegion.UPPER_ARM: 0.0271, BodyRegion.FOREARM: 0.0162, BodyRegion.HAND: 0.0061,
    BodyRegion.THIGH: 0.1416, BodyRegion.LEG: 0.0433, BodyRegion.FOOT: 0.0137,
}
SEGMENT_MASS_PROVENANCE = ProvenanceState.ESTIMATE


def regional_target_mass_kg(body_mass_kg: float = DEFAULT_BODY_MASS_KG, bracing: float = 1.0
                            ) -> Dict[BodyRegion, float]:
    """Target effective mass per region: ``body_mass × fraction × bracing`` (``bracing`` ≥ 1, 1 = relaxed)."""
    if body_mass_kg <= 0.0 or bracing < 1.0:
        raise ValueError("body mass must be positive and bracing >= 1")
    return {r: round(body_mass_kg * f * bracing, 4) for r, f in SEGMENT_MASS_FRACTION.items()}


def reduced_mass(m_striker: float, m_target: Optional[float]) -> float:
    """``μ = m_s m_t / (m_s + m_t)``; ``m_target`` None or infinite = immovable target (μ = m_s)."""
    if m_target is None or math.isinf(m_target):
        return m_striker
    if m_striker <= 0.0 or m_target <= 0.0:
        raise ValueError("effective masses must be positive")
    return m_striker * m_target / (m_striker + m_target)


@dataclass(frozen=True)
class CollisionSplit:
    striker_mass_kg: float
    target_mass_kg: float
    reduced_mass_kg: float
    speed_m_s: float                     # normal component of the striker speed at contact
    kinetic_j: float                     # ½ m_s v²
    deformation_j: float                 # ½ μ v²: what the layer models may spend
    momentum_j: float                    # ½ (m_s + m_t) V²: knockback, not tissue damage
    target_speed_m_s: float              # V, common speed after a perfectly inelastic contact
    provenance: ProvenanceState = ProvenanceState.ESTIMATE

    @property
    def deformation_speed_m_s(self) -> float:
        """Speed that gives ``deformation_j`` with the striker's own mass (feeds the unchanged layer models)."""
        return math.sqrt(2.0 * self.deformation_j / self.striker_mass_kg) if self.deformation_j > 0.0 else 0.0


def split(m_striker: float, speed_m_s: float, m_target: float) -> CollisionSplit:
    mu = reduced_mass(m_striker, m_target)
    ke = 0.5 * m_striker * speed_m_s ** 2
    deform = 0.5 * mu * speed_m_s ** 2
    v_common = m_striker * speed_m_s / (m_striker + m_target)
    return CollisionSplit(striker_mass_kg=m_striker, target_mass_kg=m_target, reduced_mass_kg=round(mu, 6),
                          speed_m_s=round(speed_m_s, 6), kinetic_j=round(ke, 6), deformation_j=round(deform, 6),
                          momentum_j=round(ke - deform, 6), target_speed_m_s=round(v_common, 6))


def target_mass_for(region: BodyRegion, table: Mapping[BodyRegion, float]) -> float:
    if region not in table:
        raise KeyError(f"no target effective mass for region {region.value}")
    return table[region]
