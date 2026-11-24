"""Weapon clearance: how far a held weapon goes into its own wielder's body (pure Python).

The older check measured only the blade's centre line against the collision capsules, so a blade with thickness could
cross a forearm or a foot while the check still reported about 2 cm of room (measured 2026-11-15 on 11 UAL clips).
Here every part is a capsule with its real thickness and the distance is exact:

* a body segment is the block-dummy capsule (Decision 83): axis ``a``-``b`` and ``radius_m``; the visible blocks use
  the same capsules, so what this reports is what the render shows (up to the mesh tessellation);
* the weapon is a capsule along its own axis whose radius encloses its cross-section (for the square placeholder
  box, half its diagonal: conservative, a corner may report a contact the flat face does not have);
* ``gap = distance(axis, axis) - r1 - r2``: negative is penetration depth.

The gripping hand always overlaps the grip, so it is excluded by name (``grip_segments``). The weapon is split in two
(``split_weapon``): the **grip**, the first ``GRIP_LENGTH_M`` inside the fist, may also touch the gripping forearm (its
capsule overlaps the hand at the wrist by design, Decision 83, and the fist hides that contact); the **blade** must keep
``gap >= margin_m`` from every segment but the hand. No engine code, no I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

Vec = Tuple[float, float, float]

#: Default gripping-hand segments of the block dummy for a right-hand grip (``SOCKET-hand_grip.R``).
RIGHT_HAND_GRIP = ("hand.R",)
#: Length of the weapon held inside the fist, from its butt (PLACEHOLDER: about one hand breadth; no sabre measured).
GRIP_LENGTH_M = 0.10
#: Per weapon part, the extra body segments it may touch (the grip rests against the gripping forearm at the wrist).
RIGHT_GRIP_ALLOWED: Mapping[str, Tuple[str, ...]] = {"grip": ("forearm.R",)}


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


def split_weapon(weapon: Capsule, grip_length_m: float = GRIP_LENGTH_M) -> List[Capsule]:
    """``grip`` (butt to ``grip_length_m``) and ``blade`` (the rest to the tip), same radius."""
    length = math.sqrt(_dot(_sub(weapon.b, weapon.a), _sub(weapon.b, weapon.a)))
    if length <= grip_length_m:
        return [Capsule("grip", weapon.a, weapon.b, weapon.radius_m)]
    cut = _lerp(weapon.a, weapon.b, grip_length_m / length)
    return [Capsule("grip", weapon.a, cut, weapon.radius_m), Capsule("blade", cut, weapon.b, weapon.radius_m)]


def frame_contacts(weapon: Sequence[Capsule], body: Iterable[Capsule],
                   grip_segments: Sequence[str] = RIGHT_HAND_GRIP,
                   allowed: Optional[Mapping[str, Sequence[str]]] = None) -> List[Contact]:
    """Nearest approach of every weapon part to every body segment, nearest first.

    Skipped: the gripping hand for every part, and ``allowed[part]`` for that part."""
    allowed = allowed or {}
    out = [capsule_contact(w, c) for c in body if c.name not in grip_segments for w in weapon
           if c.name not in allowed.get(w.name, ())]
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
            "gap_m": round(worst.contact.gap_m, 4), "t_weapon": round(worst.contact.t_weapon, 3),
            "point": [round(x, 4) for x in worst.contact.point]},
        "segments": {k: per[k] for k in sorted(per)},
        "passed": not bad,
    }


# --------------------------------------------------------------------------- correction ----
#
# Fix for the eye, the production-line twin of Godot's CEWeaponClearance (Decision 88): the gripping hand turns at the
# wrist, carrying the weapon, by the smallest angle that clears the body. Two rules keep it from shaking:
#
# * one axis per episode (a run of bad frames whose ramps touch), taken from the deepest frame,
#   so the hand does not jump between directions inside one contact;
# * the angle ramps in and out over ``ramp`` frames (max of tents), so it never starts or stops from one frame to the
#   next.
#
# Search like Godot: 8 axes perpendicular to the weapon, ``step_deg`` steps up to ``max_deg`` (both PLACEHOLDER; the
# wrist range of motion is not modelled yet). A frame that nothing clears keeps the largest angle and is reported.

STEP_DEG = 1.0
MAX_DEG = 45.0
RAMP_FRAMES = 4
AXES = 8


@dataclass(frozen=True)
class WristFix:
    frame: int
    axis: Vec             # unit axis in world space, through the pivot
    angle_deg: float
    cleared: bool         # False: even ``max_deg`` did not clear; the angle is the most that was allowed


def _cross(p: Sequence[float], q: Sequence[float]) -> Vec:
    return (p[1] * q[2] - p[2] * q[1], p[2] * q[0] - p[0] * q[2], p[0] * q[1] - p[1] * q[0])


def _unit(p: Sequence[float]) -> Vec:
    n = math.sqrt(_dot(p, p))
    return (p[0] / n, p[1] / n, p[2] / n)


def rotate_about(p: Vec, pivot: Vec, axis: Vec, angle_rad: float) -> Vec:
    """Rodrigues rotation of ``p`` about the line through ``pivot`` along unit ``axis``."""
    v = _sub(p, pivot)
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    k = _dot(axis, v) * (1 - c)
    x = _cross(axis, v)
    return tuple(pivot[i] + v[i] * c + x[i] * s + axis[i] * k for i in range(3))


def rotate_capsule(c: Capsule, pivot: Vec, axis: Vec, angle_rad: float) -> Capsule:
    return Capsule(c.name, rotate_about(c.a, pivot, axis, angle_rad), rotate_about(c.b, pivot, axis, angle_rad),
                   c.radius_m)


def rotate_parts(parts: Sequence[Capsule], pivot: Vec, axis: Vec, angle_rad: float) -> List[Capsule]:
    return [rotate_capsule(p, pivot, axis, angle_rad) for p in parts]


def candidate_axes(weapon: Sequence[Capsule], n: int = AXES) -> List[Vec]:
    """``n`` unit axes perpendicular to the weapon (butt of the first part to tip of the last), evenly spaced."""
    d = _unit(_sub(weapon[-1].b, weapon[0].a))
    ref = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _unit(_cross(d, ref))
    v = _cross(d, u)
    return [tuple(u[i] * math.cos(2 * math.pi * k / n) + v[i] * math.sin(2 * math.pi * k / n) for i in range(3))
            for k in range(n)]


@dataclass(frozen=True)
class Rules:
    """What may touch what, and how much room is required (one object passed through the correction)."""
    grip_segments: Tuple[str, ...] = RIGHT_HAND_GRIP
    allowed: Mapping[str, Tuple[str, ...]] = field(default_factory=lambda: dict(RIGHT_GRIP_ALLOWED))
    margin_m: float = 0.0

    def contacts(self, weapon: Sequence[Capsule], body: Sequence[Capsule]) -> List[Contact]:
        return frame_contacts(weapon, body, self.grip_segments, self.allowed)

    def clear(self, weapon: Sequence[Capsule], body: Sequence[Capsule]) -> bool:
        return all(c.gap_m >= self.margin_m for c in self.contacts(weapon, body))


def clearing_angle(weapon: Sequence[Capsule], pivot: Vec, axis: Vec, body: Sequence[Capsule],
                   rules: Rules = Rules(), step_deg: float = STEP_DEG, max_deg: float = MAX_DEG) -> Optional[float]:
    """Smallest angle (degrees, multiple of ``step_deg``) about ``axis`` that clears; None when ``max_deg`` does not."""
    steps = int(round(max_deg / step_deg))
    for k in range(steps + 1):
        a = k * step_deg
        if rules.clear(rotate_parts(weapon, pivot, axis, math.radians(a)), body):
            return a
    return None


def best_axis(weapon: Sequence[Capsule], pivot: Vec, body: Sequence[Capsule], rules: Rules = Rules(),
              step_deg: float = STEP_DEG, max_deg: float = MAX_DEG) -> Tuple[Vec, Optional[float]]:
    """The candidate axis with the smallest clearing angle (ties: the first); None angle when no axis clears."""
    axes = candidate_axes(weapon)
    best: Tuple[Vec, Optional[float]] = (axes[0], None)
    for ax in axes:
        a = clearing_angle(weapon, pivot, ax, body, rules, step_deg, max_deg)
        if a is not None and (best[1] is None or a < best[1]):
            best = (ax, a)
    return best


def episodes(bad_frames: Iterable[int], gap: int = RAMP_FRAMES) -> List[List[int]]:
    """Runs of bad frames; runs separated by at most ``gap`` frames are one episode."""
    out: List[List[int]] = []
    for f in sorted(set(bad_frames)):
        if out and f - out[-1][-1] <= gap:
            out[-1].append(f)
        else:
            out.append([f])
    return out


def ramp(needed: Mapping[int, float], frames: Sequence[int], ramp_frames: int = RAMP_FRAMES) -> Dict[int, float]:
    """Max of tents: each frame's needed angle spreads to its neighbours, falling to 0 over ``ramp_frames + 1``."""
    out = {}
    for f in frames:
        a = 0.0
        for g, need in needed.items():
            d = abs(f - g)
            if d <= ramp_frames:
                a = max(a, need * (1 - d / (ramp_frames + 1)))
        out[f] = a
    return out


def plan_wrist_fix(frames: Mapping[int, Tuple[Sequence[Capsule], Vec, Sequence[Capsule]]], rules: Rules = Rules(),
                   step_deg: float = STEP_DEG, max_deg: float = MAX_DEG,
                   ramp_frames: int = RAMP_FRAMES) -> List[WristFix]:
    """Per frame (weapon parts, wrist pivot, body capsules) -> the wrist turns to apply, only where they are not zero.

    Runs whose ramps would overlap (up to ``2 * ramp_frames`` apart) are one episode, so every frame gets at most one
    turn."""
    bad = [f for f, (w, _, body) in frames.items() if not rules.clear(w, body)]
    out: List[WristFix] = []
    for ep in episodes(bad, 2 * ramp_frames):
        deepest = min(ep, key=lambda f: (rules.contacts(frames[f][0], frames[f][2])[0].gap_m, f))
        w, pivot, body = frames[deepest]
        axis, _ = best_axis(w, pivot, body, rules, step_deg, max_deg)
        needed, failed = {}, set()
        for f in ep:
            w, pivot, body = frames[f]
            a = clearing_angle(w, pivot, axis, body, rules, step_deg, max_deg)
            if a is None:
                a = max_deg
                failed.add(f)
            needed[f] = a
        span = [f for f in sorted(frames) if ep[0] - ramp_frames <= f <= ep[-1] + ramp_frames]
        for f, a in ramp(needed, span, ramp_frames).items():
            w, pivot, body = frames[f]
            if not rules.clear(rotate_parts(w, pivot, axis, math.radians(a)), body):
                # the ramp itself may push a frame that was clear into the body (the pose moves, the axis does not):
                # take the nearest angle to the ramp value that clears
                near = _nearest_clearing(w, pivot, axis, body, rules, a, step_deg, max_deg)
                if near is None:
                    failed.add(f)
                else:
                    a = near
            if a > 0:
                out.append(WristFix(f, axis, round(a, 3), f not in failed))
    return sorted(out, key=lambda x: x.frame)


def _nearest_clearing(weapon: Sequence[Capsule], pivot: Vec, axis: Vec, body: Sequence[Capsule], rules: Rules,
                      target_deg: float, step_deg: float, max_deg: float) -> Optional[float]:
    """The angle in [0, ``max_deg``] nearest to ``target_deg`` (steps of ``step_deg``) that clears, or None."""
    for k in range(int(round(max_deg / step_deg)) + 1):
        for a in (target_deg - k * step_deg, target_deg + k * step_deg):
            if 0.0 <= a <= max_deg and rules.clear(rotate_parts(weapon, pivot, axis, math.radians(a)), body):
                return a
    return None
