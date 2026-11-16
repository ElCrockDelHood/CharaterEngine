"""Judo / jujutsu throw model: kumikata (grip) -> kuzushi (unbalancing) -> throw -> fall -> ukemi (A36).

Additive and opt-in: no existing move, table or hash changes. A throw is resolved from mechanics, not from a button:

* **Kumikata**: a grip is a hand of tori on a point of uke, anchored to a game bone.
* **Kuzushi**: uke's centre of mass against the base of support of the feet on the ground. A horizontal impulse ``J`` gives
  the centre of mass the speed ``v = J / m``; an inverted pendulum of height ``h`` then travels ``v / sqrt(g / h)`` before
  it can be stopped without a step (plain mechanics of the linear inverted pendulum, no fitted number). The **margin** is
  the distance left to the edge of the support in that direction; ``margin <= 0`` means balance is broken. A reaped or
  swept foot is taken out of the support, which is why leg techniques need far less pull.
* **Fall**: :class:`~.move_strikers.FallLanding` (A17) from the throw's release height.
* **Ukemi**: decides whether the head reaches the mat. Head loads are the measured ones where a paper was read (A17),
  ``None`` where nothing was read.

Provenance: segment mass fractions SOURCED (de Leva 1996, through ``collision.py``); head loads SOURCED; everything else
(segment centres at mid-length, contact height, release heights, ukemi rule, tori's pull) ASSUMED and named below.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..tissue import BodyRegion
from .collision import DEFAULT_BODY_MASS_KG, SEGMENT_MASS_FRACTION
from .move_strikers import GRAVITY_M_S2, FallLanding

SCHEMA = "ce-throw/1"
Vec = Tuple[float, float, float]
Points = Mapping[str, Tuple[Vec, Vec]]

CONTACT_HEIGHT_M = 0.09           # ASSUMED: a foot point (ankle, ball, toe tip) below this height is on the ground
HEEL_BEHIND_ANKLE_M = 0.05        # ASSUMED: the game rig has no heel bone; the heel is this far behind the ankle
UKEMI_THRESHOLD = 0.5             # ASSUMED: skill x (1 - fatigue) at or above this gives a correct breakfall
TORI_PULL_N_S: Tuple[float, float, float] = (20.0, 40.0, 60.0)   # ASSUMED: no kuzushi impulse was read

#: Game bones whose mid-point carries each segment mass (centre at mid-length: ASSUMED).
SEGMENT_BONES: Tuple[Tuple[BodyRegion, Tuple[str, ...]], ...] = (
    (BodyRegion.HEAD, ("head",)), (BodyRegion.THORAX, ("spine_03",)), (BodyRegion.ABDOMEN, ("spine_02",)),
    (BodyRegion.PELVIS, ("pelvis",)), (BodyRegion.UPPER_ARM, ("upperarm_l", "upperarm_r")),
    (BodyRegion.FOREARM, ("lowerarm_l", "lowerarm_r")), (BodyRegion.HAND, ("hand_l", "hand_r")),
    (BodyRegion.THIGH, ("thigh_l", "thigh_r")), (BodyRegion.LEG, ("calf_l", "calf_r")),
    (BodyRegion.FOOT, ("foot_l", "foot_r")),
)

#: The eight directions of happo no kuzushi in uke's own frame: (forward, left).
KUZUSHI_DIRECTIONS: Mapping[str, Tuple[float, float]] = {
    "forward": (1.0, 0.0), "back": (-1.0, 0.0), "left": (0.0, 1.0), "right": (0.0, -1.0),
    "forward_left": (1.0, 1.0), "forward_right": (1.0, -1.0), "back_left": (-1.0, 1.0), "back_right": (-1.0, -1.0),
}

#: Grip points on uke and the game bone that carries each (side letter appended where the point is paired).
GRIP_POINTS: Mapping[str, str] = {"sleeve": "lowerarm", "lapel": "spine_03", "collar": "neck_01", "belt": "pelvis",
                                  "wrist": "hand", "neck": "neck_01", "waist": "spine_01", "armpit": "upperarm"}


@dataclass(frozen=True)
class Grip:
    hand: str                      # tori's hand: "l" | "r"
    point: str                     # key of GRIP_POINTS
    side: str = ""                 # uke's side for paired points: "l" | "r"

    @property
    def bone(self) -> str:
        base = GRIP_POINTS[self.point]
        return f"{base}_{self.side}" if self.side else base


@dataclass(frozen=True)
class HeadLoad:
    """Measured head load on landing (SOURCED). ``None``: not read."""
    angular_rad_s2: float
    linear_g: Optional[float]
    source: str


@dataclass(frozen=True)
class Throw:
    throw_id: str
    name: str
    family: str                                 # te-waza | koshi-waza | ashi-waza
    kuzushi: str                                # key of KUZUSHI_DIRECTIONS
    grips: Tuple[Grip, ...]
    removed_foot: str                           # uke's foot taken off the ground at kake: "l" | "r" | ""
    fall: str                                   # back | forward_rotation | side
    ukemi: str                                  # ushiro | mae_mawari | yoko
    first_contact: Tuple[str, ...]              # segments that meet the mat first, without ukemi
    release_com_height_m: Tuple[float, float, float]     # ASSUMED, as in A17
    head_no_ukemi: Optional[HeadLoad]
    head_ukemi: Optional[HeadLoad]
    existing_move: str = ""                     # gameplay move this throw refines, if any


_RIGHT_GRIP = (Grip("r", "lapel"), Grip("l", "sleeve", "r"))
_STANDING, _LOW, _LIFTED = 0.55 * 1.80, 0.75, 1.40      # release heights of the centre of mass, ASSUMED (A17)
_LOCKHART = "as printed in Lockhart 2022 (review); primary paper not read"

THROWS: Mapping[str, Throw] = {t.throw_id: t for t in (
    Throw("seoi_nage", "Seoi-nage", "te-waza", "forward", (Grip("l", "sleeve", "r"), Grip("r", "armpit", "r")), "",
          "forward_rotation", "mae_mawari", ("head", "thorax", "pelvis"), (_STANDING, 1.20, _LIFTED),
          HeadLoad(1890.1, 20.3, "Murayama 2020, dummy 75 kg, 5 throws"),
          HeadLoad(276.2, None, "Ishikawa 2018, novices, " + _LOCKHART), "shoulder_throw"),
    Throw("o_goshi", "O-goshi", "koshi-waza", "forward", (Grip("l", "sleeve", "r"), Grip("r", "waist")), "",
          "forward_rotation", "mae_mawari", ("thorax", "pelvis"), (_LOW, _STANDING, 1.20), None, None),
    Throw("o_soto_gari", "O-soto-gari", "ashi-waza", "back_right", _RIGHT_GRIP, "r", "back", "ushiro",
          ("pelvis", "thorax", "head"), (_LOW, _STANDING, 1.10),
          HeadLoad(4572.6, 46.5, "Murayama 2020, Table 1, citing the authors' earlier dummy study"),
          HeadLoad(679.4, 10.3, "Murayama 2020 human study, " + _LOCKHART)),
    Throw("o_uchi_gari", "O-uchi-gari", "ashi-waza", "back_left", _RIGHT_GRIP, "l", "back", "ushiro",
          ("pelvis", "thorax", "head"), (_LOW, _STANDING, 1.10),
          HeadLoad(2176.0, 87.9, "Murayama 2020, Table 1, citing the authors' earlier dummy study"),
          HeadLoad(401.6, None, "Ishikawa 2018, novices, " + _LOCKHART)),
    Throw("de_ashi_barai", "De-ashi-barai", "ashi-waza", "right", _RIGHT_GRIP, "r", "side", "yoko",
          ("pelvis", "upper_arm", "thorax"), (0.60, _LOW, _STANDING), None, None, "sweep"),
)}


def _mid(points: Points, bone: str) -> Vec:
    h, t = points[bone]
    return ((h[0] + t[0]) / 2, (h[1] + t[1]) / 2, (h[2] + t[2]) / 2)


def centre_of_mass(points: Points) -> Vec:
    """Whole-body centre of mass from the game bones (de Leva fractions, segment centres at mid-length: ESTIMATE)."""
    total, acc = 0.0, [0.0, 0.0, 0.0]
    for region, bones in SEGMENT_BONES:
        for b in bones:
            w, m = SEGMENT_MASS_FRACTION[region], _mid(points, b)
            total += w
            for i in range(3):
                acc[i] += w * m[i]
    return (acc[0] / total, acc[1] / total, acc[2] / total)


def support_points(points: Points, removed: Sequence[str] = ()) -> List[Tuple[float, float]]:
    """Ground contact points (heel, ankle, ball and toe tip of each foot, those that are down), as XY. ``removed``: sides taken off the ground."""
    out: List[Tuple[float, float]] = []
    for s in ("l", "r"):
        if s in removed:
            continue
        ankle, ball = points[f"foot_{s}"]
        for p in (ankle, ball, points[f"ball_{s}"][1]):
            if p[2] <= CONTACT_HEIGHT_M:
                out.append((p[0], p[1]))
        dx, dy = ankle[0] - ball[0], ankle[1] - ball[1]
        n = math.hypot(dx, dy)
        if ankle[2] <= CONTACT_HEIGHT_M and n > 1e-6:
            out.append((ankle[0] + dx / n * HEEL_BEHIND_ANKLE_M, ankle[1] + dy / n * HEEL_BEHIND_ANKLE_M))
    return out


@dataclass(frozen=True)
class Kuzushi:
    direction: str
    world_xy: Tuple[float, float]
    margin_m: float                  # distance left inside the support along the direction; <= 0: balance broken
    impulse_to_break_n_s: float      # horizontal impulse that takes the margin to zero (0 if already broken)
    supported: bool                  # False: no foot on the ground

    @property
    def broken(self) -> bool:
        return self.margin_m <= 0.0


def world_direction(points: Points, direction: str) -> Tuple[float, float]:
    """A kuzushi direction of uke's own frame as a world XY unit vector (left from the hips, forward square to it)."""
    hl, hr = points["thigh_l"][0], points["thigh_r"][0]
    lx, ly = hl[0] - hr[0], hl[1] - hr[1]
    n = math.hypot(lx, ly)
    if n < 1e-6:                                      # hips stacked (lying on the side): no heading, use the world frame
        lx, ly, n = 1.0, 0.0, 1.0
    lx, ly = lx / n, ly / n
    fx, fy = ly, -lx                                  # forward = left rotated -90 deg about Z (rest: left +X, fwd -Y)
    f, left = KUZUSHI_DIRECTIONS[direction]
    x, y = f * fx + left * lx, f * fy + left * ly
    n = math.hypot(x, y)
    return (x / n, y / n)


def kuzushi(points: Points, direction: str, impulse_n_s: float = 0.0, body_mass_kg: float = DEFAULT_BODY_MASS_KG,
            removed: Sequence[str] = ()) -> Kuzushi:
    """Balance of ``points`` (uke, world frame) against a pull or push of ``impulse_n_s`` along ``direction``."""
    d = world_direction(points, direction)
    com = centre_of_mass(points)
    sup = support_points(points, removed)
    omega = math.sqrt(GRAVITY_M_S2 / max(com[2], 1e-6))
    if not sup:
        return Kuzushi(direction, d, -math.inf, 0.0, False)
    edge = max(p[0] * d[0] + p[1] * d[1] for p in sup)
    static = edge - (com[0] * d[0] + com[1] * d[1])
    margin = static - (impulse_n_s / body_mass_kg) / omega
    need = max(0.0, static) * omega * body_mass_kg
    return Kuzushi(direction, d, margin, need, True)


@dataclass(frozen=True)
class Ukemi:
    attempted: bool
    correct: bool
    kind: str
    quality: float


def resolve_ukemi(throw: Throw, skill: float, fatigue: float = 0.0, attempted: bool = True) -> Ukemi:
    """ASSUMED rule: quality = skill x (1 - fatigue), both in 0..1; correct at or above ``UKEMI_THRESHOLD``."""
    q = max(0.0, min(1.0, skill)) * (1.0 - max(0.0, min(1.0, fatigue))) if attempted else 0.0
    return Ukemi(attempted, attempted and q >= UKEMI_THRESHOLD, throw.ukemi, q)


@dataclass(frozen=True)
class ThrowEvent:
    throw: Throw
    kuzushi_before: Kuzushi          # both feet counted
    kuzushi_at_kake: Kuzushi         # the reaped / swept foot removed
    thrown: bool
    ukemi: Optional[Ukemi]
    release_com_height_m: float
    impact_speed_m_s: float
    fall_energy_j: float
    trunk_energy_j: float
    head_hits_ground: Optional[bool]
    head: Optional[HeadLoad]

    def to_dict(self) -> Dict[str, object]:
        def kz(k: Kuzushi) -> Dict[str, object]:
            return {"direction": k.direction, "world_xy": [round(c, 6) for c in k.world_xy],
                    "margin_m": None if math.isinf(k.margin_m) else round(k.margin_m, 4),
                    "impulse_to_break_n_s": round(k.impulse_to_break_n_s, 2), "supported": k.supported,
                    "broken": k.broken}
        t = self.throw
        head = None if self.head is None else {"angular_rad_s2": self.head.angular_rad_s2,
                                                "linear_g": self.head.linear_g, "source": self.head.source}
        return {
            "schema": SCHEMA, "throw": t.throw_id, "name": t.name, "family": t.family,
            "grips": [{"hand": g.hand, "point": g.point, "bone": g.bone} for g in t.grips],
            "kuzushi": {"before": kz(self.kuzushi_before), "at_kake": kz(self.kuzushi_at_kake)},
            "thrown": self.thrown,
            "fall": None if not self.thrown else {
                "type": t.fall, "release_com_height_m": round(self.release_com_height_m, 3),
                "impact_speed_m_s": round(self.impact_speed_m_s, 3), "energy_j": round(self.fall_energy_j, 1),
                "trunk_energy_j": round(self.trunk_energy_j, 1), "first_contact": list(t.first_contact)},
            "ukemi": None if self.ukemi is None else {"attempted": self.ukemi.attempted, "correct": self.ukemi.correct,
                                                      "type": self.ukemi.kind, "quality": round(self.ukemi.quality, 3)},
            "head": {"hits_ground": self.head_hits_ground, "measured": head},
            "provenance": {"kuzushi": "ESTIMATE", "release_com_height_m": "ASSUMED", "fall": "ESTIMATE",
                           "ukemi": "ASSUMED", "head": "SOURCED" if head else "UNKNOWN"},
        }


def resolve_throw(throw: Throw, uke_points: Points, impulse_n_s: float, ukemi_skill: float = 1.0, fatigue: float = 0.0,
                  body_mass_kg: float = DEFAULT_BODY_MASS_KG, release_com_height_m: Optional[float] = None) -> ThrowEvent:
    """Resolve one attempt from uke's pose (world frame) and tori's horizontal impulse along the throw's kuzushi.

    The throw succeeds when balance is broken once the reaped or swept foot is out of the support. A failed attempt
    returns ``thrown = False`` with both margins, so the caller can open tori to a counter."""
    before = kuzushi(uke_points, throw.kuzushi, impulse_n_s, body_mass_kg)
    at_kake = kuzushi(uke_points, throw.kuzushi, impulse_n_s, body_mass_kg, removed=(throw.removed_foot,))
    if not at_kake.broken:
        return ThrowEvent(throw, before, at_kake, False, None, 0.0, 0.0, 0.0, 0.0, None, None)
    height = throw.release_com_height_m[1] if release_com_height_m is None else release_com_height_m
    fall = FallLanding(body_mass_kg)
    uk = resolve_ukemi(throw, ukemi_skill, fatigue)
    hits = False if uk.correct else ("head" in throw.first_contact or None)
    return ThrowEvent(throw, before, at_kake, True, uk, height, fall.impact_speed_m_s(height),
                      fall.total_energy_j(height), fall.trunk_energy_j(height), hits,
                      throw.head_ukemi if uk.correct else throw.head_no_ukemi)
