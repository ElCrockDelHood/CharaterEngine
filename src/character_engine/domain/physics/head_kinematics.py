"""Head kinematics, concussion probability and knock-back stagger of a blunt blow (A16). Additive and opt-in.

``collision.py`` splits a blow into tissue energy and motion; ``strike_model.py`` gives the peak contact force. This
module turns the motion into what a fight needs, without changing any wound result:

1. **Head linear acceleration** ``a = F_peak / M_head`` (the struck head carries the peak contact force), ``M_head``
   from the shared target-mass table of ``collision.py`` (ESTIMATE).
2. **Head rotational acceleration** ``α = F_peak · d / I_head``: ``d`` is the lever arm of the blow's line of action
   about the head's rotation centre (ASSUMED 0.04 m for a straight frontal blow, 0.08 m for a hook-type blow) and
   ``I_head`` the head's moment of inertia (ASSUMED 0.0225 kg·m², unverified, inside the 0.02–0.025 range).
3. **Concussion probability** from the rotational-acceleration risk table of Rowson et al. 2012 (Ann Biomed Eng
   40(1):1–13; 335 players, 300 977 impacts, 57 concussions): 10 / 25 / 50 / 75 / 90 % at 5260 / 5821 / 6383 / 6945 /
   7483 rad/s², linearly interpolated; 0 → 10 % linear below the first row, 90 → 99 % above the last one (the tails
   are ASSUMED). Helmeted American-football players, not bare heads or gloved punches. The paper's logistic fit is
   α = −12.531, β = 0.002 (β printed rounded: with 0.002 the 50 % point falls at 6266 rad/s², β ≈ 0.001963 reproduces
   the table), so the table stays the implementation.
4. **Stagger** from the impulse the blow gives the body, ``J = μ · v`` (perfectly inelastic contact with the struck
   segment, ``collision.py``). One recovery step at ``P_STEP``, several at 1.3 × ``P_STEP`` (ASSUMED: inspired by the
   ratio of platform *levels* in Batcir et al. 2020, a lateral moving platform, not convertible to N·s), fall at
   2 × ``P_STEP`` (ASSUMED). Older adults (≈ 80 y) step at 50.3 / 45.6 / 70.5 N forward / backward / lateral under a
   waist pull whose force–time area is 0.40 s × F (Sturnieks et al. 2013), that is ≈ 20 / 18 / 28 N·s (DERIVED from
   SOURCED values, older adults). ``P_STEP`` = 25 N·s is ASSUMED for a young fighter (≈ 1.25–1.4 × the older-adult
   value). ``bracing`` (≥ 1) raises the thresholds.

Not modelled: rotational velocity and angular impulse, the neck, gloves, cumulative blows, the direction of rotation
(sagittal / coronal / axial), sweeps (they remove the support, they do not push the centre of mass).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..tissue import BodyRegion
from .collision import reduced_mass, regional_target_mass_kg, target_mass_for

G = 9.81
LEVER_STRAIGHT_M = 0.04                  # ASSUMED: straight frontal blow, line of action near the head's centre
LEVER_HOOK_M = 0.08                      # ASSUMED: hook-type blow, off-centre line of action
HEAD_INERTIA_KG_M2 = 0.0225              # ASSUMED (0.02–0.025 kg·m², unverified)

# Rowson et al. 2012, Table: concussion probability vs peak rotational acceleration (rad/s²). SOURCED (football).
ROWSON_2012_LOGISTIC = (-12.531, 0.002)    # printed α, β (β rounded); the interpolated table is what the code uses
ROWSON_2012_ROTATIONAL: Tuple[Tuple[float, float], ...] = (
    (5260.0, 0.10), (5821.0, 0.25), (6383.0, 0.50), (6945.0, 0.75), (7483.0, 0.90))
SATURATION_RAD_S2 = 9000.0               # ASSUMED: tail above the last table row reaches 0.99 here
SATURATION_PROBABILITY = 0.99

P_STEP_N_S = 25.0                        # ASSUMED (young fighter); older adults 0.40 s × F ≈ 18–20 N·s AP, 28 lateral
MULTI_STEP_RATIO = 1.3                   # ASSUMED (Batcir 2020 ratio of platform levels, not of force or impulse)
FALL_RATIO = 2.0                         # ASSUMED
STAGGER_LEVELS = ("none", "step", "steps", "fall")
HEAD_REGIONS = (BodyRegion.HEAD, BodyRegion.NECK)


@dataclass(frozen=True)
class HeadKinematics:
    peak_force_n: float
    head_mass_kg: float
    lever_arm_m: float
    linear_g: float
    rotational_rad_s2: float
    concussion_probability: float
    provenance: ProvenanceState = ProvenanceState.ESTIMATE


@dataclass(frozen=True)
class Stagger:
    striker_momentum_n_s: float          # m·v of the striker
    impulse_n_s: float                   # μ·v given to the body through the struck segment
    segment_speed_m_s: float             # m·v / (m + M) of the struck segment
    level: str                           # none | step | steps | fall
    threshold_n_s: float                 # P_STEP × bracing
    provenance: ProvenanceState = ProvenanceState.ASSUMED


@dataclass(frozen=True)
class KnockbackResult:
    region: str
    head: Optional[HeadKinematics]       # None off head / neck
    stagger: Stagger
    knocked_down: bool                   # fall, or concussion probability >= 0.5


def concussion_probability(rotational_rad_s2: float) -> float:
    """Piecewise-linear over the Rowson 2012 table (0 at 0 rad/s², 0.99 at ``SATURATION_RAD_S2``)."""
    pts = ((0.0, 0.0),) + ROWSON_2012_ROTATIONAL + ((SATURATION_RAD_S2, SATURATION_PROBABILITY),)
    if rotational_rad_s2 <= 0.0:
        return 0.0
    if rotational_rad_s2 >= pts[-1][0]:
        return SATURATION_PROBABILITY
    for (x0, p0), (x1, p1) in zip(pts, pts[1:]):
        if rotational_rad_s2 <= x1:
            return p0 + (p1 - p0) * (rotational_rad_s2 - x0) / (x1 - x0)
    return SATURATION_PROBABILITY        # pragma: no cover


def head_kinematics(peak_force_n: float, head_mass_kg: float, lever_arm_m: float = LEVER_STRAIGHT_M,
                    inertia_kg_m2: float = HEAD_INERTIA_KG_M2) -> HeadKinematics:
    a = peak_force_n / head_mass_kg
    alpha = peak_force_n * lever_arm_m / inertia_kg_m2
    return HeadKinematics(peak_force_n=round(peak_force_n, 1), head_mass_kg=head_mass_kg, lever_arm_m=lever_arm_m,
                          linear_g=round(a / G, 2), rotational_rad_s2=round(alpha, 1),
                          concussion_probability=round(concussion_probability(alpha), 4))


def stagger(striker_mass_kg: float, speed_m_s: float, target_mass_kg: float, bracing: float = 1.0) -> Stagger:
    if bracing < 1.0:
        raise ValueError("bracing must be >= 1")
    mu = reduced_mass(striker_mass_kg, target_mass_kg)
    j = mu * speed_m_s
    thr = P_STEP_N_S * bracing
    level = 0 if j < thr else 1 if j < MULTI_STEP_RATIO * thr else 2 if j < FALL_RATIO * thr else 3
    return Stagger(striker_momentum_n_s=round(striker_mass_kg * speed_m_s, 3), impulse_n_s=round(j, 3),
                   segment_speed_m_s=round(striker_mass_kg * speed_m_s / (striker_mass_kg + target_mass_kg), 4),
                   level=STAGGER_LEVELS[level], threshold_n_s=round(thr, 3))


def knockback(region: BodyRegion, striker_mass_kg: float, speed_m_s: float, peak_force_n: float,
              lever_arm_m: float = LEVER_STRAIGHT_M, bracing: float = 1.0,
              target_mass_kg: Optional[Mapping[BodyRegion, float]] = None) -> KnockbackResult:
    """Head kinematics (head / neck only) and stagger of one normal blow with peak force ``peak_force_n``."""
    m_t = target_mass_for(region, target_mass_kg or regional_target_mass_kg())
    st = stagger(striker_mass_kg, speed_m_s, m_t, bracing)
    head = head_kinematics(peak_force_n, m_t, lever_arm_m) if region in HEAD_REGIONS else None
    down = st.level == "fall" or (head is not None and head.concussion_probability >= 0.5)
    return KnockbackResult(region=region.value, head=head, stagger=st, knocked_down=down)


def knockback_of(outcome, striker, lever_arm_m: float = LEVER_STRAIGHT_M, bracing: float = 1.0) -> KnockbackResult:
    """Knock-back of a ``strike_model.StrikeOutcome`` produced by ``striker`` (a ``strike_model.Striker``)."""
    return knockback(BodyRegion(outcome.region), striker.effective_mass_kg, striker.speed_m_s, outcome.peak_force_n,
                     lever_arm_m, bracing)
