"""Leg quality of a retargeted clip, measured against its mocap source (pure Python; Decision 89, MO-2 and MO-3).

Input is sampled world positions per frame (canonical axes: Z-up, metres), as written by
``runtime/blender/ce_batch_retarget.py``. Nothing here reads files or imports Blender.

* **Stance** (per foot and frame) is taken from the *source*: the source foot is in contact when its lowest point
  (ankle, ball, toe tip) is within ``contact_height_m`` of its rest height. The source stands on its own ground, so
  this does not depend on how well the retarget grounded the target.
* **Sole height** (MO-2): on a stance frame, the lowest target foot point (heel, ball, toe tip) minus its rest
  height. Negative = the sole is under the ground, positive = it floats. The clip value is the median over all
  stance frames of both feet; the 95th percentile of ``|h|`` is reported beside it.
* **Knee direction** (MO-3): the direction the knee points away from the hip-ankle line, in the source and in the
  target, and the angle between them. Frames where the source leg is almost straight (knee closer than
  ``min_pole_m`` to that line, the same 1 cm as ``leg_ground.MIN_POLE_M``) carry no direction and are skipped.
  The target knee is the middle of the gap between ``FEMUR`` tail and ``TIBIA`` head.

The definitions are ESTIMATE (engineering choices, no cited source), like the thresholds they are judged against
(``domain/quality/tolerances.py``).
"""

from __future__ import annotations

import math
import statistics
from typing import Dict, List, Mapping, Optional, Sequence

Vec3 = Sequence[float]
SIDES = ("L", "R")
PROVENANCE = "ESTIMATE"
CONTACT_HEIGHT_M = 0.03     # same as clip_qa.Thresholds.contact_height_m
MIN_POLE_M = 0.01           # same as the leg grounding's straight-leg limit

SOURCE_FOOT = {"L": ("foot_l", "ball_l", "ball_l.tail"), "R": ("foot_r", "ball_r", "ball_r.tail")}
TARGET_FOOT = {"L": ("CALCANEUS_L", "TOE_PHALANX_PROXIMAL_3_L", "TOE_PHALANX_PROXIMAL_3_L.tail"),
               "R": ("CALCANEUS_R", "TOE_PHALANX_PROXIMAL_3_R", "TOE_PHALANX_PROXIMAL_3_R.tail")}
SOURCE_LEG = {"L": ("thigh_l", "calf_l", "foot_l"), "R": ("thigh_r", "calf_r", "foot_r")}


def _target_leg(frame: Mapping[str, Vec3], side: str):
    hip = frame.get(f"FEMUR_{side}")
    a, b = frame.get(f"FEMUR_{side}.tail"), frame.get(f"TIBIA_{side}")
    ankle = frame.get(f"TALUS_{side}")
    if None in (hip, a, b, ankle):
        return None
    return hip, tuple((a[i] + b[i]) / 2 for i in range(3)), ankle


def _lowest(frame: Mapping[str, Vec3], rest: Mapping[str, Vec3], names: Sequence[str]) -> Optional[float]:
    vals = [frame[n][2] - rest[n][2] for n in names if n in frame and n in rest]
    return min(vals) if vals else None


def knee_offset(hip: Vec3, knee: Vec3, ankle: Vec3):
    """Vector from the hip-ankle line to the knee (perpendicular part)."""
    axis = [ankle[i] - hip[i] for i in range(3)]
    n2 = sum(c * c for c in axis)
    rel = [knee[i] - hip[i] for i in range(3)]
    t = sum(rel[i] * axis[i] for i in range(3)) / n2 if n2 > 0 else 0.0
    return [rel[i] - t * axis[i] for i in range(3)]


def angle_deg(u: Vec3, v: Vec3) -> float:
    nu, nv = math.hypot(*u), math.hypot(*v)
    c = sum(u[i] * v[i] for i in range(3)) / (nu * nv)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile, ``q`` in [0, 100]."""
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * q / 100.0
    lo = math.floor(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def sole_heights(source: Sequence[Mapping[str, Vec3]], target: Sequence[Mapping[str, Vec3]],
                 source_rest: Mapping[str, Vec3], target_rest: Mapping[str, Vec3],
                 contact_height_m: float = CONTACT_HEIGHT_M) -> List[float]:
    """Target sole heights (m) on every source stance frame of either foot."""
    out = []
    for s, t in zip(source, target):
        for side in SIDES:
            src = _lowest(s, source_rest, SOURCE_FOOT[side])
            if src is None or src > contact_height_m:
                continue
            h = _lowest(t, target_rest, TARGET_FOOT[side])
            if h is not None:
                out.append(h)
    return out


def knee_errors(source: Sequence[Mapping[str, Vec3]], target: Sequence[Mapping[str, Vec3]],
                min_pole_m: float = MIN_POLE_M) -> List[float]:
    """Angle (deg) between source and target knee directions, per leg and frame with a bent source knee."""
    out = []
    for s, t in zip(source, target):
        for side in SIDES:
            names = SOURCE_LEG[side]
            leg = _target_leg(t, side)
            if leg is None or any(n not in s for n in names):
                continue
            src_off = knee_offset(*(s[n] for n in names))
            if math.hypot(*src_off) < min_pole_m:
                continue
            dst_off = knee_offset(*leg)
            if math.hypot(*dst_off) < 1e-9:
                out.append(90.0)      # straight target leg against a bent source: no direction, counted as wrong
                continue
            out.append(angle_deg(src_off, dst_off))
    return out


def clip_legs(source: Sequence[Mapping[str, Vec3]], target: Sequence[Mapping[str, Vec3]],
              source_rest: Mapping[str, Vec3], target_rest: Mapping[str, Vec3]) -> Dict[str, object]:
    """MO-2 / MO-3 values of one clip (``None`` where there is nothing to measure)."""
    h = sole_heights(source, target, source_rest, target_rest)
    k = knee_errors(source, target)
    rec: Dict[str, object] = {"provenance": PROVENANCE, "stance_samples": len(h), "knee_samples": len(k),
                              "sole_median_m": None, "sole_abs_p95_m": None, "knee_median_deg": None,
                              "knee_p90_deg": None}
    if h:
        rec["sole_median_m"] = round(statistics.median(h), 5)
        rec["sole_abs_p95_m"] = round(percentile([abs(x) for x in h], 95), 5)
    if k:
        rec["knee_median_deg"] = round(statistics.median(k), 3)
        rec["knee_p90_deg"] = round(percentile(k, 90), 3)
    return rec
