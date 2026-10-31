"""Per-move striker records: effective mass, speed and head lever arm as (low, nominal, high) ranges (A17).

Additive and opt-in: ``strike_model.Striker.from_move`` (table energy kept, speed by kind) is unchanged, and nothing
here is written back into the gameplay table. Each record says where its numbers come from, field by field:

* ``SOURCED``: read in a published paper (the page was read; the full text is not in the repository).
* ``ESTIMATE``: derived from sourced numbers or from the engine's own estimates (A14).
* ``ASSUMED``: a placeholder in the right order of magnitude, no source.

Sources used (A14, A15, A16): Walilko, Viano & Bir 2005, straight punch 2.9 ± 2.0 kg at 9.14 ± 2.06 m/s; Mosler 2024,
boxers' velocity at maximum force, jab 6.8 m/s, cross 8.6 m/s; Natale 2026 (preprint, not peer reviewed), kinematic
punch effective mass 3.5–10 kg; roundhouse foot speed at impact 5.6–7.2 m/s (Gavagan & Sayers 2017); kick speeds up to
18 m/s (Corcoran 2024); whole-leg coupling ≈ 15 kg (ESTIMATE) from the ``collision.py`` segment fractions (de Leva
1996, SOURCED).

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
Range = Tuple[float, float, float]                 # low, nominal, high

_LEG = SEGMENT_MASS_FRACTION[BodyRegion.LEG] + SEGMENT_MASS_FRACTION[BodyRegion.FOOT]
SHANK_FOOT_KG = round(_LEG * DEFAULT_BODY_MASS_KG, 2)            # ≈ 4.3 kg, ESTIMATE
WHOLE_LEG_KG = 15.0                                              # ESTIMATE (A14: thigh + shank + foot ≈ 14.9 kg)
KICK_HIGH_KG = round(0.44 * DEFAULT_BODY_MASS_KG, 1)             # ASSUMED: 44 % of body mass, one ITF case (A14)
COM_DROP_SPEED = round(math.sqrt(2 * 9.81 * 0.55 * 1.80), 2)     # DERIVED: fall from CoM height 0.55 × 1.80 m

PUNCH_MASS: Range = (0.9, 2.9, 4.9)                # Walilko 2005, mean ± SD
STRAIGHT_LEVER: Range = (0.03, 0.04, 0.06)         # ASSUMED
HOOK_LEVER: Range = (0.04, 0.08, 0.10)             # ASSUMED: no published lever arm for hooks (A17)


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
    _record("front_kick", (SHANK_FOOT_KG, WHOLE_LEG_KG, KICK_HIGH_KG), (5.6, 6.4, 18.0), 0.06, STRAIGHT_LEVER,
            {"mass": "ESTIMATE", "speed": "ESTIMATE", "speed_high": "SOURCED", "lever_arm": "ASSUMED"},
            "mass: whole leg (A14), low shank + foot, high 44 % body (one case); speed: roundhouse 5.6-7.2 m/s "
            "applied to a front kick, high 18 m/s (Corcoran 2024)", 150.0),
    _record("crescent_kick", (SHANK_FOOT_KG, WHOLE_LEG_KG, KICK_HIGH_KG), (5.6, 6.4, 18.0), 0.06, HOOK_LEVER,
            {"mass": "ESTIMATE", "speed": "SOURCED", "speed_high": "SOURCED", "lever_arm": "ASSUMED"},
            "as front kick; circular path, hook-type lever arm", 220.0),
    _record("sweep", (SHANK_FOOT_KG, WHOLE_LEG_KG, KICK_HIGH_KG), (5.6, 6.4, 18.0), 0.06, STRAIGHT_LEVER,
            {"mass": "ESTIMATE", "speed": "ESTIMATE", "lever_arm": "ASSUMED"},
            "kick values; a sweep removes support rather than striking (A16)", 140.0),
    _record("shoulder_throw", (40.0, DEFAULT_BODY_MASS_KG, 100.0), (3.0, COM_DROP_SPEED, 5.5), 0.10, STRAIGHT_LEVER,
            {"mass": "ESTIMATE", "speed": "ESTIMATE", "lever_arm": "ASSUMED"},
            "a throw is the defender's body landing: whole body mass, speed of a fall from centre-of-mass height "
            "(DERIVED); range ASSUMED", 260.0),
)}


def move_striker(move: str) -> MoveStriker:
    if move not in MOVE_STRIKERS:
        raise KeyError(f"no striker record for move {move!r}")
    return MOVE_STRIKERS[move]
