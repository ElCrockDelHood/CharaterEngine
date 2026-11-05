"""Per-move striker records: effective mass, speed and head lever arm as (low, nominal, high) ranges (A17).

Additive and opt-in: ``strike_model.Striker.from_move`` (table energy kept, speed by kind) is unchanged, and nothing
here is written back into the gameplay table. Each record says where its numbers come from, field by field:

* ``SOURCED``: read in a published paper (the page was read; the full text is not in the repository).
* ``ESTIMATE``: derived from sourced numbers or from the engine's own estimates (A14).
* ``ASSUMED``: a placeholder in the right order of magnitude, no source.

Sources used (A14, A15, A16): Walilko, Viano & Bir 2005, straight punch 2.9 ± 2.0 kg at 9.14 ± 2.06 m/s; Mosler 2024,
boxers' velocity at maximum force, jab 6.8 m/s, cross 8.6 m/s; Natale 2026 (preprint, not peer reviewed), kinematic
punch effective mass 3.5–10 kg.

Kicks and the throw (A17, "Kick effective mass" and "Fall model"): Vagner et al. 2023 (Sports 11:141, Tables 1-2), hip,
knee and foot speeds; Gavagan & Sayers 2017 (PLoS ONE 12:e0182645, Tables 1-2 and Results), roundhouse impulse and foot
speed at impact; Góra et al. 2024 (Appl Sci 14:2339), force over foot acceleration; Murayama et al. 2020 (Neurol Med
Chir 60:101) and Nakanishi et al. 2021 (Healthcare 9:214), thrown dummy; Lockhart et al. 2022 (IJERPH 19:4259, review).

"Effective mass" names three different quantities in that literature, and only one fits ``½ m v²``. Peak force over
foot acceleration (Góra: 20 % of the body for a turning kick, 73 % for a side kick) and impulse over a long contact
(front kick: the stance leg keeps pushing) are not the energy of the moving limb, so they only bound the high end. The
nominal mass here is the one that reproduces the limb's own energy or momentum at the foot's speed.

``energy_flag`` is set when the nominal ``½ m v²`` is more than ``ENERGY_TOLERANCE`` away from the move's table
``energy_j``: the numbers are not bent to match, the mismatch is reported.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional, Tuple

from ..tissue import BodyRegion
from .collision import DEFAULT_BODY_MASS_KG, SEGMENT_MASS_FRACTION

ENERGY_TOLERANCE = 0.25
GRAVITY_M_S2 = 9.81
Range = Tuple[float, float, float]                 # low, nominal, high

_LEG = SEGMENT_MASS_FRACTION[BodyRegion.LEG] + SEGMENT_MASS_FRACTION[BodyRegion.FOOT]
SHANK_FOOT_KG = round(_LEG * DEFAULT_BODY_MASS_KG, 2)            # ≈ 4.3 kg, ESTIMATE
KICK_HIGH_KG = round(0.44 * DEFAULT_BODY_MASS_KG, 1)             # ASSUMED: 44 % of body mass, one ITF case (A14)

PUNCH_MASS: Range = (0.9, 2.9, 4.9)                # Walilko 2005, mean ± SD
STRAIGHT_LEVER: Range = (0.03, 0.04, 0.06)         # ASSUMED
HOOK_LEVER: Range = (0.04, 0.08, 0.10)             # ASSUMED: no published lever arm for hooks (A17)

# Vagner 2023, pooled means (m/s): (hip, knee, foot). Table 1 front kick, to a target; Table 2 roundhouse, elite, middle
# distance and height. The review calls them maximum velocities, not velocities at impact.
FRONT_KICK_SPEEDS: Mapping[str, Tuple[float, float, float]] = {"novice": (2.1, 5.3, 7.7), "sub_elite": (2.4, 5.32, 8.56),
                                                               "elite": (2.39, 5.88, 9.61)}
ROUNDHOUSE_ELITE_SPEEDS: Tuple[float, float, float] = (2.36, 6.73, 14.34)

# Gavagan & Sayers 2017, n = 8 per group: (impulse N·s, foot speed at impact m/s, body mass kg).
ROUNDHOUSE_IMPACT: Mapping[str, Tuple[float, float, float]] = {"muay_thai": (38.1, 7.22, 65.6), "karate": (30.9, 5.57, 84.5),
                                                               "taekwondo": (38.8, 6.36, 95.8)}
TURNING_KICK_FORCE_MASS_FRACTION = 0.2012          # Góra 2024: median peak force / foot acceleration, 4 men


def leg_chain_energy_j(hip: float, knee: float, foot: float, body_mass_kg: float = DEFAULT_BODY_MASS_KG) -> float:
    """Translational energy of the kicking leg from its joint speeds (ESTIMATE).

    Thigh and shank move at the mean of their end joints (segment centre of mass taken at mid-length, ASSUMED); the
    foot moves at the foot speed. Rotation about each segment's own centre is left out: under 3 % for a front kick."""
    thigh = SEGMENT_MASS_FRACTION[BodyRegion.THIGH] * body_mass_kg * ((hip + knee) / 2) ** 2
    shank = SEGMENT_MASS_FRACTION[BodyRegion.LEG] * body_mass_kg * ((knee + foot) / 2) ** 2
    return 0.5 * (thigh + shank + SEGMENT_MASS_FRACTION[BodyRegion.FOOT] * body_mass_kg * foot ** 2)


def foot_referred_mass_kg(hip: float, knee: float, foot: float, body_mass_kg: float = DEFAULT_BODY_MASS_KG) -> float:
    """The mass that, at the foot's speed, carries the whole leg's energy: 2E / v_foot²."""
    return 2.0 * leg_chain_energy_j(hip, knee, foot, body_mass_kg) / foot ** 2


def momentum_mass_fraction() -> float:
    """Roundhouse impulse over foot speed at impact, as a fraction of body mass; mean of the three Gavagan groups."""
    groups = ROUNDHOUSE_IMPACT.values()
    return sum(j / (v * body) for j, v, body in groups) / len(groups)


_FRONT_KICK_MASS = round(foot_referred_mass_kg(*FRONT_KICK_SPEEDS["sub_elite"]), 2)            # ≈ 5.3 kg
_ROUNDHOUSE_LOW_KG = round(foot_referred_mass_kg(*ROUNDHOUSE_ELITE_SPEEDS), 2)                 # ≈ 3.9 kg
_ROUNDHOUSE_KG = round(momentum_mass_fraction() * DEFAULT_BODY_MASS_KG, 2)                     # ≈ 5.2 kg
_ROUNDHOUSE_HIGH_KG = round(TURNING_KICK_FORCE_MASS_FRACTION * DEFAULT_BODY_MASS_KG, 2)        # ≈ 15.1 kg
_IMPACT_SPEEDS = sorted(v for _, v, _ in ROUNDHOUSE_IMPACT.values())
_ROUNDHOUSE_SPEED: Range = (_IMPACT_SPEEDS[0], round(sum(_IMPACT_SPEEDS) / 3, 2), ROUNDHOUSE_ELITE_SPEEDS[2])
_ROUNDHOUSE_MASS: Range = (_ROUNDHOUSE_LOW_KG, _ROUNDHOUSE_KG, _ROUNDHOUSE_HIGH_KG)


@dataclass(frozen=True)
class FallLanding:
    """A body dropped onto its back: the energy of the fall and the part the trunk delivers to the ground (ESTIMATE).

    Every segment is taken to land at the speed of the centre of mass, with no rotation and no help from the thrower.
    Contact time and peak ground force are not modelled: no landing force of a thrown person was read (A17)."""
    body_mass_kg: float = DEFAULT_BODY_MASS_KG
    release_com_height_m: Range = (0.75, 0.55 * 1.80, 1.40)   # ASSUMED: lowered / standing CoM (0.55 × 1.80 m) / lifted
    rest_com_height_m: float = 0.12                           # ASSUMED: lying on the back, half the depth of the chest

    def impact_speed_m_s(self, release_com_height_m: float) -> float:
        return math.sqrt(2.0 * GRAVITY_M_S2 * max(0.0, release_com_height_m - self.rest_com_height_m))

    @property
    def trunk_mass_kg(self) -> float:
        fractions = (SEGMENT_MASS_FRACTION[r] for r in (BodyRegion.THORAX, BodyRegion.ABDOMEN, BodyRegion.PELVIS))
        return sum(fractions) * self.body_mass_kg

    def total_energy_j(self, release_com_height_m: float) -> float:
        return 0.5 * self.body_mass_kg * self.impact_speed_m_s(release_com_height_m) ** 2

    def trunk_energy_j(self, release_com_height_m: float) -> float:
        return 0.5 * self.trunk_mass_kg * self.impact_speed_m_s(release_com_height_m) ** 2

    def limbs_and_head_energy_j(self, release_com_height_m: float) -> float:
        return self.total_energy_j(release_com_height_m) - self.trunk_energy_j(release_com_height_m)


SHOULDER_THROW_FALL = FallLanding()
_THROW_LOW, _THROW_NOMINAL, _THROW_HIGH = SHOULDER_THROW_FALL.release_com_height_m
_THROW_MASS: Range = (round(FallLanding(60.0).trunk_mass_kg, 2), round(SHOULDER_THROW_FALL.trunk_mass_kg, 2),
                      round(FallLanding(100.0).trunk_mass_kg, 2))             # 60 and 100 kg bodies, ASSUMED
_THROW_SPEED: Range = (round(SHOULDER_THROW_FALL.impact_speed_m_s(_THROW_LOW), 2),
                       round(SHOULDER_THROW_FALL.impact_speed_m_s(_THROW_NOMINAL), 2),
                       round(SHOULDER_THROW_FALL.impact_speed_m_s(_THROW_HIGH), 2))


@dataclass(frozen=True)
class ThrowHeadMeasurement:
    """Measured head loads of a person or dummy thrown by seoi-nage (SOURCED). ``None``: not reported."""
    subject: str
    ukemi: bool
    surface: str
    linear_g: Optional[Range]
    angular_rad_s2: Range
    source: str


SEOI_NAGE_HEAD: Tuple[ThrowHeadMeasurement, ...] = (
    ThrowHeadMeasurement("dummy, 75 kg, 175 cm", False, "tatami over 60 mm sponge on concrete", (9.1, 20.3, 30.8),
                         (641.3, 1890.1, 3195.4), "Murayama 2020, range and mean of 5 throws by one expert"),
    ThrowHeadMeasurement("novice judoka, 72.4 kg mean", True, "not read", None, (276.2, 276.2, 276.2),
                         "Ishikawa 2018 as printed in Lockhart 2022, Table 2; primary paper not read"),
)
SEOI_NAGE_NECK = {"upper_compression_n": 4223.2, "nij_median": 0.68, "beam_criterion_median": 0.90}   # Nakanishi 2021


@dataclass(frozen=True)
class MoveStriker:
    move: str
    mass_kg: Range
    speed_m_s: Range
    contact_radius_m: float
    lever_arm_m: Range
    provenance: Mapping[str, str]                  # field → SOURCED | ESTIMATE | ASSUMED
    note: str
    table_energy_j: float
    energy_flag: Optional[str] = field(default=None)

    @property
    def nominal_energy_j(self) -> float:
        return 0.5 * self.mass_kg[1] * self.speed_m_s[1] ** 2

    @property
    def energy_ratio(self) -> float:
        return self.nominal_energy_j / self.table_energy_j

    def range_energy_j(self) -> Tuple[float, float]:
        return 0.5 * self.mass_kg[0] * self.speed_m_s[0] ** 2, 0.5 * self.mass_kg[2] * self.speed_m_s[2] ** 2


def _record(move: str, mass: Range, speed: Range, radius: float, lever: Range, prov: Dict[str, str], note: str,
            table_energy_j: float) -> MoveStriker:
    r = MoveStriker(move, mass, speed, radius, lever, prov, note, table_energy_j)
    flag = None
    if abs(r.energy_ratio - 1.0) > ENERGY_TOLERANCE:
        lo, hi = r.range_energy_j()
        flag = (f"nominal {r.nominal_energy_j:.0f} J vs table {table_energy_j:.0f} J ({(r.energy_ratio - 1) * 100:+.0f} %); "
                f"range {lo:.0f}-{hi:.0f} J")
    return MoveStriker(move, mass, speed, radius, lever, prov, note, table_energy_j, flag)


def _sd(v: float, sd: float = 2.06) -> Range:
    return (round(v - sd, 2), v, round(v + sd, 2))


# Contact radius and table energy are the move's own values in gameplay_shenmue.json (copied, not changed).
MOVE_STRIKERS: Mapping[str, MoveStriker] = {r.move: r for r in (
    _record("jab", PUNCH_MASS, _sd(6.8), 0.045, STRAIGHT_LEVER,
            {"mass": "SOURCED", "speed": "SOURCED", "speed_range": "ESTIMATE", "lever_arm": "ASSUMED"},
            "mass Walilko 2005; speed Mosler 2024 (jab at max force), range ± Walilko SD", 60.0),
    _record("straight", PUNCH_MASS, _sd(8.6), 0.045, STRAIGHT_LEVER,
            {"mass": "SOURCED", "speed": "SOURCED", "speed_range": "ESTIMATE", "lever_arm": "ASSUMED"},
            "mass Walilko 2005; speed Mosler 2024 (cross at max force), range ± Walilko SD", 90.0),
    _record("hook", PUNCH_MASS, _sd(9.14), 0.05, HOOK_LEVER,
            {"mass": "ESTIMATE", "speed": "ESTIMATE", "lever_arm": "ASSUMED"},
            "straight-punch values of Walilko 2005 applied to a hook (no hook data read)", 130.0),
    _record("elbow_assault", (3.5, 5.0, 10.0), (6.8, 8.0, 9.14), 0.05, HOOK_LEVER,
            {"mass": "ESTIMATE", "speed": "ASSUMED", "lever_arm": "ASSUMED"},
            "mass range Natale 2026 kinematic punch mass (preprint), nominal ASSUMED; speed between jab and "
            "Walilko mean, ASSUMED", 170.0),
    _record("front_kick", (SHANK_FOOT_KG, _FRONT_KICK_MASS, KICK_HIGH_KG), (7.7, 8.56, 9.61), 0.06, STRAIGHT_LEVER,
            {"mass": "ESTIMATE", "mass_high": "ASSUMED", "speed": "SOURCED", "lever_arm": "ASSUMED"},
            "mass: leg energy from hip, knee and foot speeds (Vagner 2023, sub-elite) referred to the foot, low shank + "
            "foot, high 44 % body (one case; includes the push during contact); speed: novice / sub-elite / elite, "
            "maximum not at impact", 150.0),
    _record("crescent_kick", _ROUNDHOUSE_MASS, _ROUNDHOUSE_SPEED, 0.06, HOOK_LEVER,
            {"mass": "ESTIMATE", "speed": "ESTIMATE", "lever_arm": "ASSUMED"},
            "no crescent data read, roundhouse applied: mass impulse / speed at impact (Gavagan 2017), low leg energy "
            "of Vagner 2023 elite, high peak force / acceleration (Góra 2024); speed at impact, high Vagner elite", 220.0),
    _record("sweep", _ROUNDHOUSE_MASS, _ROUNDHOUSE_SPEED, 0.06, STRAIGHT_LEVER,
            {"mass": "ESTIMATE", "speed": "ESTIMATE", "lever_arm": "ASSUMED"},
            "no sweep data read, roundhouse values as for crescent_kick; a sweep removes support rather than striking "
            "(A16)", 140.0),
    _record("shoulder_throw", _THROW_MASS, _THROW_SPEED, 0.10, STRAIGHT_LEVER,
            {"mass": "ESTIMATE", "speed": "ESTIMATE", "release_height": "ASSUMED", "lever_arm": "ASSUMED"},
            "a throw is the defender's body landing (FallLanding): trunk mass at the speed of the fall; the head is not "
            "struck by this mass, see SEOI_NAGE_HEAD for measured head loads", 260.0),
)}


def move_striker(move: str) -> MoveStriker:
    if move not in MOVE_STRIKERS:
        raise KeyError(f"no striker record for move {move!r}")
    return MOVE_STRIKERS[move]
