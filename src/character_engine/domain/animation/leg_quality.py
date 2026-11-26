"""Leg quality of a retargeted clip, measured against its mocap source (pure Python; Decision 89, MO-2 and MO-3).

Input is sampled world positions per frame (canonical axes: Z-up, metres), as written by
``runtime/blender/ce_batch_retarget.py``. Nothing here reads files or imports Blender.

* **Stance** (per foot and frame) is taken from the *source* and means *support* (Decision 89 amendment 3): the
  source foot's lowest point (ankle, ball, toe tip) is within ``contact_height_m`` of its rest height, the ankle moves
  at most ``STANCE_SPEED_M_S`` horizontally (a planted foot is still; a foot sliding on the floor, as in UAL Slide_*,
  is not a support), the foot is within ``STANCE_TILT_DEG`` of its rest pitch (flat, not resting on the heel or the
  toes of a lying body) and the pelvis is at most ``STANCE_PELVIS_DROP_M`` below its rest height (the legs carry the
  body: a deep crouch counts, lying on the floor does not). It does not depend on how well the retarget grounded the
  target. A clip with fewer than ``MIN_STANCE_FRAMES`` such frames is not judged (reported, not hidden).
* **Sole height** (MO-2): on a stance frame, the lowest target foot point (heel, ball, toe tip) minus its rest
  height. Negative = the sole is under the ground, positive = it floats. The clip value is the median over all
  stance frames of both feet; the 95th percentile of ``|h|`` is reported beside it.
* **Knee hinge axis** (MO-3, Decision 89 amendment 2, owner 2026-11-25): the knee's hinge axis is the normal of the
  thigh-shin plane, ``(knee - hip) x (ankle - knee)``, in the source and in the target, and the angle between the two
  axes, per leg and frame. Only frames where the source knee is bent at least ``MIN_FLEXION_DEG`` count: a straight
  leg has no plane. This needs no rest pose, so the fixed difference in how the two rigs place the knee at rest (the
  canonical rest knee sits 13.5 mm sideways of its hip-ankle line) does not count, and a straight leg cannot invent a
  direction. A target leg that stays straight while the source bends counts as 90 deg. The target knee is the middle of
  the gap between ``FEMUR`` tail and ``TIBIA`` head.

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
STANCE_SPEED_M_S = 0.25    # ESTIMATE: horizontal ankle speed of a planted foot (walk stance median 0.07 m/s)
STANCE_TILT_DEG = 20.0      # ESTIMATE: foot pitch change from rest (ankle -> ball)
STANCE_PELVIS_DROP_M = 0.5  # ESTIMATE: crouch idle drops 0.44 m; lying on the floor 0.59-0.87 m
MIN_STANCE_FRAMES = 10      # ESTIMATE: fewer support frames than this are too few for a clip median
MIN_FLEXION_DEG = 15.0      # source knee bend below which no hinge axis is judged (rest bends 3.5-4.2 deg; A89 amendment 2)

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


def _sub(a: Vec3, b: Vec3):
    return [a[i] - b[i] for i in range(3)]


def hinge(hip: Vec3, knee: Vec3, ankle: Vec3):
    """(knee flexion in degrees, unit hinge axis or ``None`` for a straight leg)."""
    u, v = _sub(knee, hip), _sub(ankle, knee)
    c = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    n = math.hypot(*c)
    return angle_deg(u, v), ([x / n for x in c] if n > 1e-12 else None)


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


def _pitch(ankle: Vec3, ball: Vec3) -> float:
    """Angle (deg) of the ankle -> ball vector below the horizontal."""
    d = [ball[i] - ankle[i] for i in range(3)]
    return math.degrees(math.atan2(-d[2], math.hypot(d[0], d[1])))


def sole_heights(source: Sequence[Mapping[str, Vec3]], target: Sequence[Mapping[str, Vec3]],
                 source_rest: Mapping[str, Vec3], target_rest: Mapping[str, Vec3],
                 contact_height_m: float = CONTACT_HEIGHT_M, dt: float = 1.0 / 30.0) -> List[float]:
    """Target sole heights (m) on every source support frame of either foot (see the module notes)."""
    out = []
    prev: Dict[str, Vec3] = {}
    pelvis_rest = (source_rest.get("pelvis") or (0.0, 0.0, None))[2]
    for s, t in zip(source, target):
        for side in SIDES:
            ankle_name, ball_name = SOURCE_FOOT[side][0], SOURCE_FOOT[side][1]
            ankle = s.get(ankle_name)
            last, prev[side] = prev.get(side), ankle
            src = _lowest(s, source_rest, SOURCE_FOOT[side])
            if src is None or src > contact_height_m or ankle is None or last is None:
                continue
            if math.hypot(ankle[0] - last[0], ankle[1] - last[1]) / dt > STANCE_SPEED_M_S:
                continue
            if ball_name in s and ankle_name in source_rest and ball_name in source_rest and abs(
                    _pitch(ankle, s[ball_name]) - _pitch(source_rest[ankle_name], source_rest[ball_name])) > STANCE_TILT_DEG:
                continue
            if pelvis_rest is not None and "pelvis" in s and s["pelvis"][2] - pelvis_rest < -STANCE_PELVIS_DROP_M:
                continue
            h = _lowest(t, target_rest, TARGET_FOOT[side])
            if h is not None:
                out.append(h)
    return out


def knee_errors(source: Sequence[Mapping[str, Vec3]], target: Sequence[Mapping[str, Vec3]],
                min_flexion_deg: float = MIN_FLEXION_DEG):
    """(angles in deg between source and target hinge axes, frames left out for a straighter source knee)."""
    out, excluded = [], 0
    for s, t in zip(source, target):
        for side in SIDES:
            names = SOURCE_LEG[side]
            leg = _target_leg(t, side)
            if leg is None or any(n not in s for n in names):
                continue
            flex, src_axis = hinge(*(s[n] for n in names))
            if flex < min_flexion_deg or src_axis is None:
                excluded += 1
                continue
            _, dst_axis = hinge(*leg)
            out.append(90.0 if dst_axis is None else angle_deg(src_axis, dst_axis))
    return out, excluded


def clip_legs(source: Sequence[Mapping[str, Vec3]], target: Sequence[Mapping[str, Vec3]],
              source_rest: Mapping[str, Vec3], target_rest: Mapping[str, Vec3],
              dt: float = 1.0 / 30.0) -> Dict[str, object]:
    """MO-2 / MO-3 values of one clip (``None`` where there is nothing to measure)."""
    h = sole_heights(source, target, source_rest, target_rest, dt=dt)
    k, excluded = knee_errors(source, target)
    rec: Dict[str, object] = {"provenance": PROVENANCE, "stance_samples": len(h), "knee_samples": len(k),
                              "knee_excluded_frames": excluded, "knee_min_flexion_deg": MIN_FLEXION_DEG,
                              "knee_reference": "hinge axis (Decision 89 amendment 2)",
                              "sole_median_m": None, "sole_abs_p95_m": None, "knee_median_deg": None,
                              "knee_p90_deg": None}
    rec["stance_rule"] = "support (Decision 89 amendment 3)"
    if len(h) >= MIN_STANCE_FRAMES:
        rec["sole_median_m"] = round(statistics.median(h), 5)
        rec["sole_abs_p95_m"] = round(percentile([abs(x) for x in h], 95), 5)
    if k:
        rec["knee_median_deg"] = round(statistics.median(k), 3)
        rec["knee_p90_deg"] = round(percentile(k, 90), 3)
    return rec
