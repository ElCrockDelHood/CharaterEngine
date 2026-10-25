"""Hand controls and pose library for the CE-GAME-v1 hands (RIG-GAME-001 step 3).

A :class:`HandPose` is a handful of animator-level controls — per-finger ``curl``, ``spread``, thumb
``opposition`` and palm ``cup`` — turned into one rotation per game hand bone by :func:`hand_pose_rotations`.
Rotations are quaternions ``(w, x, y, z)`` in the canonical frame of the *given points* (any pose or stature),
applied about each bone head; :func:`apply_hand_pose` runs the forward kinematics, so runtimes can be checked
against Python.

Axes are derived from the points: palm normal from the hand direction and the index → little-finger axis
(palm faces −Y in the anatomical position), flexion moves a finger towards the palm, spread rotates about the
palm normal, the thumb flexes across the palm. Angle limits are **ASSUMED** (order of common clinical range
values; no cited range-of-motion source in the repository — `biomechanics.json` only has the wrist).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Mapping, Tuple

from ..anatomy.reference.source import ProvenanceState

Vec = Tuple[float, float, float]
Quat = Tuple[float, float, float, float]

FINGERS = ("thumb", "index", "middle", "ring", "pinky")

#: Maximum flexion (degrees) per joint at curl = 1 — ASSUMED. Thumb: CMC, MCP, IP; fingers: MCP, PIP, DIP.
FLEXION_LIMIT_DEG: Mapping[str, Tuple[float, float, float]] = {
    "thumb": (40.0, 55.0, 80.0),
    "index": (90.0, 100.0, 80.0),
    "middle": (90.0, 100.0, 80.0),
    "ring": (90.0, 100.0, 80.0),
    "pinky": (90.0, 100.0, 80.0),
}
#: Spread (abduction) at spread = 1, degrees, signed towards the index side — ASSUMED.
SPREAD_DEG: Mapping[str, float] = {"index": 12.0, "middle": 0.0, "ring": -8.0, "pinky": -15.0}
OPPOSITION_DEG = 45.0          # thumb_01 towards the palm at opposition = 1 — ASSUMED
CUP_DEG: Mapping[str, float] = {"ring": 10.0, "pinky": 20.0}   # metacarpal flexion at cup = 1 — ASSUMED
PROVENANCE = ProvenanceState.ASSUMED


@dataclass(frozen=True)
class HandPose:
    name: str
    curl: Mapping[str, float]                 # finger -> 0 (straight) .. 1 (full flexion)
    spread: float = 0.0                       # -1 .. 1
    opposition: float = 0.0                   # thumb towards the palm, 0 .. 1
    cup: float = 0.0                          # ring / little metacarpals, 0 .. 1
    notes: str = ""
    provenance: ProvenanceState = field(default=PROVENANCE)


def _all(v: float, **over: float) -> Dict[str, float]:
    return {f: over.get(f, v) for f in FINGERS}


HAND_POSES: Dict[str, HandPose] = {p.name: p for p in (
    HandPose("rest", _all(0.0), notes="Bind pose: no rotation (identity)."),
    HandPose("relaxed", _all(0.25, thumb=0.15), spread=0.1, opposition=0.2),
    HandPose("open", _all(0.0), spread=1.0),
    HandPose("fist", _all(1.0, thumb=0.7), opposition=0.6, cup=0.6),
    HandPose("point", _all(1.0, index=0.0, thumb=0.6), opposition=0.5, cup=0.4),
    HandPose("grip_staff", _all(0.8, thumb=0.6), opposition=0.8, cup=0.3,
             notes="Power grip around a ~28 mm shaft (staff); curl values ASSUMED, not fitted to the shaft."),
    HandPose("grip_blade", _all(0.85, thumb=0.5), opposition=0.7, cup=0.5,
             notes="Hammer grip on a knife handle along the grip channel (Decision 48); ASSUMED."),
)}

#: Grip pose a weapon puts the gripping hand in.
WEAPON_GRIP_POSE: Mapping[str, str] = {"unarmed": "relaxed", "staff": "grip_staff", "short_blade": "grip_blade"}


def grip_pose_for_weapon(weapon_id: str) -> HandPose:
    return HAND_POSES[WEAPON_GRIP_POSE.get(weapon_id, "relaxed")]


# ---------------------------------------------------------------------------------- math --

def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(v: Vec) -> Vec:
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if n == 0:
        raise ValueError("zero-length vector")
    return (v[0] / n, v[1] / n, v[2] / n)


def quat_axis_angle(axis: Vec, angle_rad: float) -> Quat:
    a = _unit(axis)
    s = math.sin(angle_rad / 2.0)
    return (math.cos(angle_rad / 2.0), a[0] * s, a[1] * s, a[2] * s)


def quat_mul(q: Quat, r: Quat) -> Quat:
    w1, x1, y1, z1 = q
    w2, x2, y2, z2 = r
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def quat_rotate(q: Quat, v: Vec) -> Vec:
    p = quat_mul(quat_mul(q, (0.0, v[0], v[1], v[2])), (q[0], -q[1], -q[2], -q[3]))
    return (p[1], p[2], p[3])


IDENTITY: Quat = (1.0, 0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------------- pose --

def finger_chain(finger: str, s: str) -> Tuple[str, ...]:
    """Game bones of a finger, proximal → distal (``s`` = "l" / "r")."""
    return tuple(f"{finger}_0{i}_{s}" for i in (1, 2, 3))


def hand_frame(points: Mapping[str, Tuple[Vec, Vec]], s: str) -> Tuple[Vec, Vec, Vec]:
    """(hand direction, index-side axis, palm normal) for side ``s`` from game bone points."""
    hand_dir = _unit(_sub(points[f"hand_{s}"][1], points[f"hand_{s}"][0]))
    across = _unit(_sub(points[f"index_01_{s}"][0], points[f"pinky_01_{s}"][0]))
    sign = 1.0 if s == "l" else -1.0          # mirrored hands: same palm side
    palm = _unit(tuple(sign * c for c in _cross(hand_dir, across)))  # type: ignore[arg-type]
    return hand_dir, across, palm


def hand_pose_rotations(pose: HandPose, points: Mapping[str, Tuple[Vec, Vec]], side: str) -> Dict[str, Quat]:
    """Rotation of every game hand bone of ``side`` ("L"/"R") for ``pose``, canonical frame of ``points``."""
    s = side.lower()
    _, across, palm = hand_frame(points, s)
    out: Dict[str, Quat] = {}
    for finger in FINGERS:
        curl = max(0.0, min(1.0, pose.curl.get(finger, 0.0)))
        for i, bone in enumerate(finger_chain(finger, s)):
            d = _unit(_sub(points[bone][1], points[bone][0]))
            if finger == "thumb":
                towards = tuple(-c for c in across)          # thumb flexes across the palm (ulnar side)
            else:
                towards = palm
            q = quat_axis_angle(_cross(d, towards), math.radians(curl * FLEXION_LIMIT_DEG[finger][i]))  # type: ignore[arg-type]
            if i == 0 and finger != "thumb" and SPREAD_DEG[finger] and pose.spread:
                q = quat_mul(q, quat_axis_angle(_cross(d, across), math.radians(pose.spread * SPREAD_DEG[finger])))
            if i == 0 and finger == "thumb" and pose.opposition:
                q = quat_mul(quat_axis_angle(_cross(d, palm), math.radians(pose.opposition * OPPOSITION_DEG)), q)
            out[bone] = q
    for finger, deg in CUP_DEG.items():
        bone = f"{finger}_metacarpal_{s}"
        d = _unit(_sub(points[bone][1], points[bone][0]))
        out[bone] = quat_axis_angle(_cross(d, palm), math.radians(pose.cup * deg))
    return out


_PARENTS = None


def _parents() -> Dict[str, str]:
    global _PARENTS
    if _PARENTS is None:
        from .game_rig import GAME_BONES

        _PARENTS = {g.name: g.parent for g in GAME_BONES}
    return _PARENTS


def apply_hand_pose(points: Mapping[str, Tuple[Vec, Vec]], rotations: Mapping[str, Quat]) -> Dict[str, Tuple[Vec, Vec]]:
    """Forward kinematics: game bone points after ``rotations`` (each about its bone head, rest frame)."""
    parents = _parents()

    def posed(bone: str, p: Vec) -> Vec:
        if bone is None or bone not in rotations and not _has_rotated_ancestor(bone, rotations, parents):
            return p
        head = points[bone][0]
        q = rotations.get(bone, IDENTITY)
        return posed(parents[bone], _add(head, quat_rotate(q, _sub(p, head))))

    return {b: (posed(b, h), posed(b, t)) for b, (h, t) in points.items()}


def _has_rotated_ancestor(bone, rotations, parents) -> bool:
    b = parents.get(bone)
    while b is not None:
        if b in rotations:
            return True
        b = parents.get(b)
    return False
