"""Foot locking for retargeted root-motion clips (pure Python): contact plan + two-bone IK geometry.

Copied joint rotations on a rig with other leg proportions make a planted foot drift (batch QA 2026-10-29:
no root scale removes it). Foot locking holds the ankle at one world point while the foot is in contact and
re-solves hip → knee → ankle so the ankle reaches it:

* :func:`plan_locks` — per frame, the ankle XY correction that keeps the foot's contact pivot (heel or ball,
  whichever is lowest) on a fixed ground anchor, and a blend weight (1 in contact, ramping to 0 over
  ``blend_frames``). Z is never changed, so the heel → ball roll of the clip is kept.
* :func:`two_bone_ik` — new knee and ankle for a target, knee kept in its current bending plane.

World space only: on an in-place clip the planted foot *should* move backwards, so locking applies to the
root-motion variant. Thresholds are ESTIMATE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence, Tuple

Vec3 = Sequence[float]


@dataclass(frozen=True)
class LockSettings:
    contact_height_m: float = 0.03   # ESTIMATE, same as clip_qa
    blend_frames: int = 2            # ESTIMATE: frames of ramp before / after each contact phase
    min_phase_frames: int = 2        # ESTIMATE: shorter contacts are not locked
    # ESTIMATE: a phase needing a larger correction is intended motion (slides, shuffles, low crouch steps
    # merged into one "contact", no ground when swimming) and is left as retargeted. Walk / jog need <= 7 cm.
    max_correction_m: float = 0.10


DEFAULT_LOCK = LockSettings()


@dataclass(frozen=True)
class Lock:
    dx: float          # XY correction of the ankle that puts the contact pivot back on its anchor
    dy: float
    weight: float


def _phases(contacts: Sequence[bool]) -> List[Tuple[int, int]]:
    out, start = [], None
    for i, c in enumerate(list(contacts) + [False]):
        if c and start is None:
            start = i
        elif not c and start is not None:
            out.append((start, i - 1))
            start = None
    return out


def plan_locks(pivots: Mapping[str, Sequence[Vec3]], rest_z: Mapping[str, float], offset: float,
               n_frames: int, settings: LockSettings = DEFAULT_LOCK,
               loop_shift: Optional[Tuple[float, float]] = None) -> List[Optional[Lock]]:
    """Per frame: ``Lock`` (ankle correction + weight) or None.

    ``pivots`` are the foot's ground points (heel, ball...). The foot is in contact when any pivot is within
    ``contact_height_m`` of its flat-foot height (after the clip ground offset). On each contact frame the pivots
    on the ground carry the contact; each pivot's anchor is its mean XY over the phase frames it carries, and the
    ankle is moved by the mean (anchor − pivot) of the carriers, so the foot rolls heel → ball about fixed ground
    points without flipping between anchors when both touch.

    ``loop_shift`` (looping clip): the XY root displacement of one cycle. A contact phase cut by the clip's
    first and last frame is then one phase: the last-frame segment is shifted back by it to share one anchor.
    """
    names = [n for n in pivots if n in rest_z and len(pivots[n]) == n_frames]
    if not names:
        return [None] * n_frames
    th = settings.contact_height_m
    rel = {n: [pivots[n][i][2] - rest_z[n] - offset for i in range(n_frames)] for n in names}
    contacts = [any(rel[n][i] <= th for n in names) for i in range(n_frames)]
    plan: List[Optional[Lock]] = [None] * n_frames
    phases = [list(range(s, e + 1)) for s, e in _phases(contacts)]
    # frame index -> XY shift that brings it into the coordinates of the phase's anchor
    shift = {i: (0.0, 0.0) for i in range(n_frames)}
    if loop_shift is not None and len(phases) > 1 and phases[0][0] == 0 and phases[-1][-1] == n_frames - 1:
        tail = phases.pop()
        for i in tail:
            shift[i] = (-loop_shift[0], -loop_shift[1])
        phases[0] = tail + phases[0]
    for frames in phases:
        if len(frames) < settings.min_phase_frames:
            continue
        # carriers: every pivot on the ground (or the lowest one when the foot is only near it)
        carrier = {i: [n for n in names if rel[n][i] <= th] or [min(names, key=lambda n, i=i: rel[n][i])]
                   for i in frames}
        anchor = {}
        for n in {n for cs in carrier.values() for n in cs}:
            idx = [i for i, cs in carrier.items() if n in cs]
            anchor[n] = (sum(pivots[n][i][0] + shift[i][0] for i in idx) / len(idx),
                         sum(pivots[n][i][1] + shift[i][1] for i in idx) / len(idx))
        delta = {}
        for i, cs in carrier.items():   # mean correction of the pivots on the ground: no flip between anchors
            dx = [anchor[c][0] - shift[i][0] - pivots[c][i][0] for c in cs]
            dy = [anchor[c][1] - shift[i][1] - pivots[c][i][1] for c in cs]
            delta[i] = (sum(dx) / len(dx), sum(dy) / len(dy))
        if max(math.hypot(*d) for d in delta.values()) > settings.max_correction_m:
            continue
        for i in frames:
            plan[i] = Lock(delta[i][0], delta[i][1], 1.0)
        first, last = frames[0], frames[-1]
        for k in range(1, settings.blend_frames + 1):
            w = 1.0 - k / (settings.blend_frames + 1)
            for i, edge in ((first - k, first), (last + k, last)):
                if 0 <= i < n_frames and (plan[i] is None or plan[i].weight < w):
                    plan[i] = Lock(delta[edge][0], delta[edge][1], w)
    return plan


def locked_target(ankle: Vec3, lock: Lock) -> Tuple[float, float, float]:
    """Ankle target: XY moved by the weighted correction, Z unchanged."""
    return (ankle[0] + lock.dx * lock.weight, ankle[1] + lock.dy * lock.weight, ankle[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return math.sqrt(_dot(a, a))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


@dataclass(frozen=True)
class IKResult:
    knee: Tuple[float, float, float]
    ankle: Tuple[float, float, float]
    reached: bool                    # False when the target was out of reach (ankle clamped on the line)


def two_bone_ik(hip: Vec3, knee: Vec3, ankle: Vec3, target: Vec3, pole: Optional[Vec3] = None) -> IKResult:
    """Knee and ankle so that |hip−knee| and |knee−ankle| keep their lengths and the ankle reaches ``target``.

    The knee stays on the side of the hip→target line where it currently is (or towards ``pole``).
    """
    a, b = _norm(_sub(knee, hip)), _norm(_sub(ankle, knee))
    to_t = _sub(target, hip)
    d_raw = _norm(to_t)
    if a < 1e-9 or b < 1e-9 or d_raw < 1e-9:
        return IKResult(tuple(knee), tuple(ankle), False)
    lo, hi = abs(a - b) + 1e-6, a + b - 1e-6
    d = min(max(d_raw, lo), hi)
    u = _mul(to_t, 1.0 / d_raw)
    side = _sub(pole, hip) if pole is not None else _sub(knee, hip)
    v = _sub(side, _mul(u, _dot(side, u)))
    if _norm(v) < 1e-9:                       # knee on the line: any perpendicular
        v = _cross(u, (1.0, 0.0, 0.0) if abs(u[0]) < 0.9 else (0.0, 1.0, 0.0))
    v = _mul(v, 1.0 / _norm(v))
    cos_a = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
    sin_a = math.sqrt(1.0 - cos_a * cos_a)
    new_knee = _add(hip, _add(_mul(u, a * cos_a), _mul(v, a * sin_a)))
    new_ankle = _add(hip, _mul(u, d))
    return IKResult(new_knee, new_ankle, lo <= d_raw <= hi)
