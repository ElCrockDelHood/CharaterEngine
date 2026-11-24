"""Weapon clearance: how far a held weapon goes into its own wielder's body (pure Python).

The older check measured only the blade's centre line against the collision capsules, so a blade with thickness could
cross a forearm or a foot while the check still reported about 2 cm of room (measured 2026-11-15 on 11 UAL clips).
Here every part is a capsule with its real thickness and the distance is exact:

* a body segment is the block-dummy capsule (Decision 83): axis ``a``-``b`` and ``radius_m``; the visible blocks use
  the same capsules, so what this reports is what the render shows (up to the mesh tessellation);
* the weapon is a capsule along its own axis whose radius encloses its cross-section (for the square placeholder
  box, half its diagonal: conservative, a corner may report a contact the flat face does not have);
* ``gap = distance(axis, axis) - r1 - r2``: negative is penetration depth.

The gripping hand always overlaps the grip, so it is excluded by name (``grip_segments``); every other segment of the
wielder, the gripping forearm included, must keep ``gap >= margin_m``. No engine code, no I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

Vec = Tuple[float, float, float]

#: Default gripping-hand segments of the block dummy for a right-hand grip (``SOCKET-hand_grip.R``).
RIGHT_HAND_GRIP = ("hand.R",)


@dataclass(frozen=True)
class Capsule:
    name: str
    a: Vec
    b: Vec
    radius_m: float


@dataclass(frozen=True)
class Contact:
    weapon: str
    body: str
    gap_m: float          # negative = penetration depth
    t_weapon: float       # 0 at the weapon capsule's ``a`` (grip end), 1 at ``b`` (tip)
    point: Vec            # point on the weapon axis closest to the body segment


@dataclass(frozen=True)
class Violation:
    frame: int
    contact: Contact


def _sub(p: Sequence[float], q: Sequence[float]) -> Vec:
    return (p[0] - q[0], p[1] - q[1], p[2] - q[2])


def _dot(p: Sequence[float], q: Sequence[float]) -> float:
    return p[0] * q[0] + p[1] * q[1] + p[2] * q[2]


def _lerp(p: Sequence[float], q: Sequence[float], t: float) -> Vec:
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t)


def _clamp(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def segment_closest(p1: Vec, q1: Vec, p2: Vec, q2: Vec) -> Tuple[float, float, float]:
    """Closest points of segments p1-q1 and p2-q2: (distance, s on the first, t on the second), s and t in [0, 1].

    Ericson, *Real-Time Collision Detection* (2005), section 5.1.9, including the degenerate (point) cases."""
    d1, d2, r = _sub(q1, p1), _sub(q2, p2), _sub(p1, p2)
    a, e, f = _dot(d1, d1), _dot(d2, d2), _dot(d2, r)
    eps = 1e-12
    if a <= eps and e <= eps:
        s = t = 0.0
    elif a <= eps:
        s, t = 0.0, _clamp(f / e)
    else:
        c = _dot(d1, r)
        if e <= eps:
            s, t = _clamp(-c / a), 0.0
        else:
            b = _dot(d1, d2)
            denom = a * e - b * b
            s = _clamp((b * f - c * e) / denom) if denom > eps else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                s, t = _clamp(-c / a), 0.0
            elif t > 1.0:
                s, t = _clamp((b - c) / a), 1.0
    c1, c2 = _lerp(p1, q1, s), _lerp(p2, q2, t)
    return math.sqrt(_dot(_sub(c1, c2), _sub(c1, c2))), s, t


def capsule_contact(weapon: Capsule, body: Capsule) -> Contact:
    dist, s, _ = segment_closest(weapon.a, weapon.b, body.a, body.b)
    return Contact(weapon.name, body.name, dist - weapon.radius_m - body.radius_m, s, _lerp(weapon.a, weapon.b, s))


def box_weapon(name: str, grip_end: Vec, tip: Vec, width_m: float, depth_m: Optional[float] = None) -> Capsule:
    """Capsule enclosing a straight box of cross-section ``width_m`` x ``depth_m`` (square when depth is omitted)."""
    depth = width_m if depth_m is None else depth_m
    return Capsule(name, tuple(grip_end), tuple(tip), math.hypot(width_m, depth) / 2)


def frame_contacts(weapon: Sequence[Capsule], body: Iterable[Capsule],
                   grip_segments: Sequence[str] = RIGHT_HAND_GRIP) -> List[Contact]:
    """Nearest approach of every weapon part to every body segment except the gripping hand, nearest first."""
    out = [capsule_contact(w, c) for c in body if c.name not in grip_segments for w in weapon]
    return sorted(out, key=lambda k: (k.gap_m, k.body, k.weapon))


def violations(frames: Mapping[int, Sequence[Contact]], margin_m: float = 0.0) -> List[Violation]:
    """Every (frame, contact) whose gap is under ``margin_m``, in frame order."""
    return [Violation(f, c) for f in sorted(frames) for c in frames[f] if c.gap_m < margin_m]


def summary(frames: Mapping[int, Sequence[Contact]], margin_m: float = 0.0) -> Dict[str, object]:
    """Per clip: frames measured, frames in violation, deepest contact, and per body segment its frames and depth."""
    bad = violations(frames, margin_m)
    per: Dict[str, Dict[str, object]] = {}
    for v in bad:
        e = per.setdefault(v.contact.body, {"frames": [], "deepest_m": 0.0})
        if v.frame not in e["frames"]:
            e["frames"].append(v.frame)
        e["deepest_m"] = min(e["deepest_m"], round(v.contact.gap_m, 4))
    nearest = min((c for cs in frames.values() for c in cs), key=lambda c: c.gap_m, default=None)
    worst = min(bad, key=lambda v: v.contact.gap_m, default=None)
    return {
        "frames": len(frames),
        "frames_in_violation": len({v.frame for v in bad}),
        "margin_m": margin_m,
        "nearest_gap_m": round(nearest.gap_m, 4) if nearest else None,
        "worst": None if worst is None else {
            "frame": worst.frame, "body": worst.contact.body, "weapon": worst.contact.weapon,
            "gap_m": round(worst.contact.gap_m, 4), "t_weapon": round(worst.contact.t_weapon, 3)},
        "segments": {k: per[k] for k in sorted(per)},
        "passed": not bad,
    }
