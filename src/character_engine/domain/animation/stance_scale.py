"""Per-clip root scale from the measured stance speed (pure Python).

A copied joint rotation moves a planted foot backwards relative to the hips at a speed set by the rig's own
proportions; on the canonical armature that speed is ~1.0× the source on walks and ~1.15× on runs (batch QA
2026-10-29), so no constant ratio keeps every gait planted. This module measures, for one clip, how fast the
planted feet move relative to the hips on the source and on the retargeted canonical armature; the ratio is the
root scale that keeps them planted (retarget_mocap ``root_scale_mode="stance"``).

Frames are world positions per point name plus a ``hips`` entry. A point is planted when it is within
``contact_height_m`` of its lowest height in the clip (``clip_qa.detect_contacts`` with the clip's ground offset).
Every threshold here is an ESTIMATE.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from .clip_qa import detect_contacts, ground_offset

Vec3 = Sequence[float]
HIPS = "hips"
CONTACT_HEIGHT_M = 0.03     # ESTIMATE (same as clip_qa)
MIN_SPEED_M_S = 0.1         # ESTIMATE: below this the feet do not step (idle, seated): no stance scale
MIN_STEPS = 3               # ESTIMATE: contact frame pairs needed on each rig
SCALE_BOUNDS = (0.5, 2.0)   # ESTIMATE: outside this the measurement is rejected


@dataclass(frozen=True)
class StanceSpeed:
    speed_m_s: Optional[float]   # median planted-foot speed relative to the hips
    steps: int


def stance_speed(frames: Sequence[Mapping[str, Vec3]], rest: Mapping[str, Vec3], points: Sequence[str],
                 dt: float, contact_height_m: float = CONTACT_HEIGHT_M) -> StanceSpeed:
    names = [p for p in points if p in rest and frames and p in frames[0]]
    if not names or not frames or HIPS not in frames[0] or dt <= 0:
        return StanceSpeed(None, 0)
    heights = {n: [f[n][2] for f in frames] for n in names}
    offset = ground_offset(heights, {n: rest[n][2] for n in names})
    speeds = []
    for n in names:
        contacts = detect_contacts(heights[n], rest[n][2], offset, contact_height_m)
        rel = [(f[n][0] - f[HIPS][0], f[n][1] - f[HIPS][1]) for f in frames]
        speeds += [((rel[i][0] - rel[i - 1][0]) ** 2 + (rel[i][1] - rel[i - 1][1]) ** 2) ** 0.5 / dt
                   for i in range(1, len(frames)) if contacts[i - 1] and contacts[i]]
    return StanceSpeed(statistics.median(speeds) if speeds else None, len(speeds))


@dataclass(frozen=True)
class StanceScale:
    scale: Optional[float]       # None = no usable measurement (caller falls back)
    source: StanceSpeed
    target: StanceSpeed
    reason: str


def stance_scale(src_frames, src_rest, src_points, dst_frames, dst_rest, dst_points, dt: float) -> StanceScale:
    """Target / source planted-foot speed relative to the hips, or ``scale=None`` with the reason."""
    s = stance_speed(src_frames, src_rest, src_points, dt)
    t = stance_speed(dst_frames, dst_rest, dst_points, dt)
    if s.speed_m_s is None or t.speed_m_s is None or min(s.steps, t.steps) < MIN_STEPS:
        return StanceScale(None, s, t, "too few planted frames")
    if s.speed_m_s < MIN_SPEED_M_S or t.speed_m_s < MIN_SPEED_M_S:
        return StanceScale(None, s, t, "feet do not step")
    ratio = t.speed_m_s / s.speed_m_s
    if not SCALE_BOUNDS[0] <= ratio <= SCALE_BOUNDS[1]:
        return StanceScale(None, s, t, f"ratio {ratio:.3f} outside {SCALE_BOUNDS}")
    return StanceScale(ratio, s, t, "measured")
