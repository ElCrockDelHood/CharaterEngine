"""Hand-held weapons for the gameplay layer: reach, impact energy and wound type (pure Python).

A :class:`Weapon` is carried in a canonical hand bone (the grip bone, same parent as
``SOCKET-hand_grip.R``) and modifies the hand strikes of :class:`~.combat.ShenmueCombat`:

* reach — ``reach_m`` is *added* to the move reach (the stature-scaled arm reach); a held
  object does not scale with the wielder,
* energy — the move energy is multiplied by ``energy_multiplier``,
* wound — BLUNT weapons route the strike through :func:`~..trauma.blunt_impact_to_wound` with
  the weapon contact radius; BLADE weapons route it through :func:`~..trauma.blade_contact_to_wound`
  (INCISION). No cited cutting-energy model exists in the repository, so a blade cut uses a fixed
  ``cut_depth_m`` (PLACEHOLDER) instead of an energy-derived depth.

A weapon applies only to hand strikes (striking bone in the hand: METACARPAL/PHALANX) on the grip
side, or with either hand when the weapon is two-handed (rule ASSUMED). Kicks, throws and elbows
stay unarmed. ``unarmed`` applies to nothing, so a fighter without a weapon resolves exactly as
before weapons existed.

Every numeric value carries a provenance state in ``provenance``; none is PROVEN. ``mass_kg`` is
descriptive data for runtimes (placeholders, future physics); the combat formula does not use it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Mapping

from ..anatomy.reference.source import ProvenanceState
from ..trauma import Wound, WoundType, blade_contact_to_wound, blunt_impact_to_wound

E, A, P = ProvenanceState.ESTIMATE, ProvenanceState.ASSUMED, ProvenanceState.PLACEHOLDER

#: Numeric fields of :class:`Weapon`; each one needs an entry in ``Weapon.provenance``.
NUMERIC_FIELDS = ("reach_m", "mass_kg", "energy_multiplier", "contact_radius_m", "cut_depth_m",
                  "length_m", "width_m", "grip_fraction")

_HAND_BONE_PREFIXES = ("METACARPAL_", "PHALANX_")


class WeaponCategory(Enum):
    UNARMED = "unarmed"
    BLUNT = "blunt"
    BLADE = "blade"


#: Wound type each category produces through the trauma domain.
WOUND_TYPE_BY_CATEGORY: Mapping[WeaponCategory, WoundType] = {
    WeaponCategory.UNARMED: WoundType.BLUNT,
    WeaponCategory.BLUNT: WoundType.BLUNT,
    WeaponCategory.BLADE: WoundType.INCISION,
}


@dataclass(frozen=True)
class Weapon:
    weapon_id: str
    name: str
    category: WeaponCategory
    reach_m: float                 # added to the move reach when the weapon applies
    mass_kg: float                 # descriptive; not used by the combat formula
    energy_multiplier: float       # move energy x this when the weapon applies
    contact_radius_m: float        # BLUNT: contact radius at the striking surface
    cut_depth_m: float             # BLADE: nominal incision depth (no cutting-energy model)
    length_m: float                # overall length (placeholder geometry)
    width_m: float                 # BLADE: blade width; BLUNT: shaft diameter (placeholder geometry)
    grip_fraction: float           # where the hand holds, 0 = butt / pommel, 1 = tip
    grip_bone: str = "METACARPAL_3_R"
    grip_socket: str = "SOCKET-hand_grip.R"
    two_handed: bool = False
    provenance: Mapping[str, ProvenanceState] = field(default_factory=dict, hash=False)
    notes: str = ""

    @property
    def wound_type(self) -> WoundType:
        return WOUND_TYPE_BY_CATEGORY[self.category]

    @property
    def grip_side(self) -> str:
        return self.grip_bone.rsplit("_", 1)[-1]

    def applies_to(self, move_kind: str, striking_bone: str) -> bool:
        """True when a move of ``move_kind`` ("punch"/"kick"/"throw") struck with ``striking_bone`` uses it."""
        if self.category is WeaponCategory.UNARMED or move_kind != "punch":
            return False
        if not striking_bone.startswith(_HAND_BONE_PREFIXES):
            return False
        return self.two_handed or striking_bone.rsplit("_", 1)[-1] == self.grip_side

    def strike_wound(self, bone_hit: str, energy_j: float) -> Wound:
        """Wound of a strike that uses this weapon; ``energy_j`` is the already multiplied energy."""
        if self.category is WeaponCategory.BLADE:
            return blade_contact_to_wound(bone_hit, penetration_m=self.cut_depth_m, blade_width_m=self.width_m)
        if self.category is WeaponCategory.BLUNT:
            return blunt_impact_to_wound(bone_hit, contact_radius_m=self.contact_radius_m, energy_j=energy_j)
        raise ValueError("unarmed strikes use the move's own blunt impact")


UNARMED = Weapon(
    "unarmed", "Unarmed", WeaponCategory.UNARMED, reach_m=0.0, mass_kg=0.0, energy_multiplier=1.0,
    contact_radius_m=0.0, cut_depth_m=0.0, length_m=0.0, width_m=0.0, grip_fraction=0.0,
    provenance={k: A for k in NUMERIC_FIELDS},
    notes="Identity values by definition (ASSUMED): strikes keep the move's reach, energy and contact radius.")

WEAPONS: Dict[str, Weapon] = {w.weapon_id: w for w in (
    UNARMED,
    Weapon(
        "staff", "Staff (bo)", WeaponCategory.BLUNT, reach_m=0.60, mass_kg=0.9, energy_multiplier=1.3,
        contact_radius_m=0.014, cut_depth_m=0.0, length_m=1.82, width_m=0.028, grip_fraction=0.5,
        two_handed=True,
        provenance={"reach_m": P, "mass_kg": E, "energy_multiplier": P, "contact_radius_m": E, "cut_depth_m": A,
                    "length_m": E, "width_m": E, "grip_fraction": A},
        notes="Length ~6 shaku and ~28 mm shaft are typical bo dimensions (ESTIMATE, no cited source in the "
              "repository); mass ESTIMATE; reach bonus and energy multiplier are gameplay PLACEHOLDERs. "
              "Held at mid-length (ASSUMED); cut_depth_m unused for blunt weapons."),
    Weapon(
        "short_blade", "Short blade (tanto-like)", WeaponCategory.BLADE, reach_m=0.20, mass_kg=0.25,
        energy_multiplier=1.0, contact_radius_m=0.0, cut_depth_m=0.012, length_m=0.35, width_m=0.028,
        grip_fraction=0.15,
        provenance={"reach_m": P, "mass_kg": E, "energy_multiplier": P, "contact_radius_m": A, "cut_depth_m": P,
                    "length_m": E, "width_m": E, "grip_fraction": A},
        notes="Overall length, blade width and mass ESTIMATE for a tanto-sized knife (no cited source in the "
              "repository); reach bonus, energy multiplier and the fixed cut depth are gameplay PLACEHOLDERs "
              "(no cited cutting-energy model). contact_radius_m unused for blades."),
)}


def weapon(weapon_id: str) -> Weapon:
    try:
        return WEAPONS[weapon_id]
    except KeyError:
        raise KeyError(f"unknown weapon {weapon_id!r}; known: {', '.join(sorted(WEAPONS))}") from None
