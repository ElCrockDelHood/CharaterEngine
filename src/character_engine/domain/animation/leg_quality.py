"""Leg quality of a retargeted clip, measured against its mocap source (pure Python; Decision 89, MO-2 and MO-3).

Input is sampled world positions per frame (canonical axes: Z-up, metres), as written by
``runtime/blender/ce_batch_retarget.py``. Nothing here reads files or imports Blender.

* **Stance** (per foot and frame) is taken from the *source*: the source foot is in contact when its lowest point
  (ankle, ball, toe tip) is within ``contact_height_m`` of its rest height. The source stands on its own ground, so
  this does not depend on how well the retarget grounded the target.
* **Sole height** (MO-2): on a stance frame, the lowest target foot point (heel, ball, toe tip) minus its rest
  height. Negative = the sole is under the ground, positive = it floats. The clip value is the median over all
  stance frames of both feet; the 95th percentile of ``|h|`` is reported beside it.
* **Knee direction** (MO-3, relative to rest; owner 2026-11-25): how far the knee has moved away from the hip-ankle
  line *since the rest pose*, in the source and in the target, and the angle between the two. Per leg the rest
  offset (knee minus its hip-ankle line, rest pose) is turned with the leg axis (the smallest rotation taking the
  rest hip->ankle direction to the current one) and subtracted from the current offset, so a fixed difference in how
  the two rigs point their knees at rest does not count (the canonical rest knee sits 13.5 mm *sideways* of its
  line, the source's 15 mm forward: 90 deg apart). The rest offset is carried by the thigh's full rotation from rest
  (head->tail axis plus the sampled local X axis, point ``<thigh>.x``), so a twist of the hip turns it too; without
  that point it falls back to the smallest rotation of the hip-ankle axis, which ignores the twist. Frames where the source has moved its knee less
  than ``min_pole_m`` (1 cm, as ``leg_ground.MIN_POLE_M``) carry no direction and are skipped. The target knee is the
  middle of the gap between ``FEMUR`` tail and ``TIBIA`` head. Without rest points the plain offsets are compared.

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


def _thigh(points: Optional[Mapping[str, Vec3]], name: str):
    """(head, tail, x-axis point) of a sampled thigh bone, or None when the axis point was not sampled."""
    if not points or any(k not in points for k in (name, name + ".tail", name + ".x")):
        return None
    return points[name], points[name + ".tail"], points[name + ".x"]


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


def _rotate_min(v: Vec3, a: Vec3, b: Vec3):
    """``v`` turned by the smallest rotation that takes direction ``a`` to direction ``b`` (Rodrigues)."""
    na, nb = math.hypot(*a), math.hypot(*b)
    a, b = [x / na for x in a], [x / nb for x in b]
    k = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    s, c = math.hypot(*k), sum(a[i] * b[i] for i in range(3))
    if s < 1e-12:
        return list(v) if c > 0 else [-x for x in v]
    k = [x / s for x in k]
    kv = [k[1] * v[2] - k[2] * v[1], k[2] * v[0] - k[0] * v[2], k[0] * v[1] - k[1] * v[0]]
    kd = sum(k[i] * v[i] for i in range(3))
    return [v[i] * c + kv[i] * s + k[i] * kd * (1 - c) for i in range(3)]


def _frame(head: Vec3, tail: Vec3, xpt: Vec3):
    """Orthonormal frame (rows x, y, z) of a bone: y along head->tail, x from the sampled X-axis point."""
    y = [tail[i] - head[i] for i in range(3)]
    ny = math.hypot(*y)
    y = [c / ny for c in y]
    x = [xpt[i] - head[i] for i in range(3)]
    d = sum(x[i] * y[i] for i in range(3))
    x = [x[i] - d * y[i] for i in range(3)]
    nx = math.hypot(*x)
    x = [c / nx for c in x]
    z = [x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]]
    return x, y, z


def _transport(v: Vec3, rest_frame, frame):
    """``v`` carried by the rotation that takes ``rest_frame`` to ``frame``."""
    local = [sum(v[i] * axis[i] for i in range(3)) for axis in rest_frame]
    return [sum(local[k] * frame[k][i] for k in range(3)) for i in range(3)]


def flexion_offset(leg, rest_leg, thigh=None, rest_thigh=None):
    """Knee offset from the hip-ankle line minus the rest offset carried from rest (relative to rest).

    ``thigh`` / ``rest_thigh``: (head, tail, x-axis point) of the thigh bone; without them the rest offset turns with
    the smallest rotation of the hip-ankle axis."""
    off = knee_offset(*leg)
    if rest_leg is None:
        return off
    if thigh is not None and rest_thigh is not None:
        rest_off = _transport(knee_offset(*rest_leg), _frame(*rest_thigh), _frame(*thigh))
    else:
        rest_off = _rotate_min(knee_offset(*rest_leg), [rest_leg[2][i] - rest_leg[0][i] for i in range(3)],
                               [leg[2][i] - leg[0][i] for i in range(3)])
    d = [off[i] - rest_off[i] for i in range(3)]
    return knee_offset(leg[0], [leg[0][i] + d[i] for i in range(3)], leg[2]) if any(d) else d


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
                min_pole_m: float = MIN_POLE_M, source_rest: Optional[Mapping[str, Vec3]] = None,
                target_rest: Optional[Mapping[str, Vec3]] = None) -> List[float]:
    """Angle (deg) between source and target knee directions, per leg and frame with a bent source knee.

    With both rest pose mappings the directions are relative to rest (:func:`flexion_offset`)."""
    out = []
    relative = source_rest is not None and target_rest is not None
    for s, t in zip(source, target):
        for side in SIDES:
            names = SOURCE_LEG[side]
            leg = _target_leg(t, side)
            if leg is None or any(n not in s for n in names):
                continue
            src_rest = tuple(source_rest[n] for n in names) if relative and all(n in source_rest for n in names) else None
            dst_rest = _target_leg(target_rest, side) if relative else None
            if relative and (src_rest is None or dst_rest is None):
                continue
            src_off = flexion_offset(tuple(s[n] for n in names), src_rest,
                                     _thigh(s, names[0]), _thigh(source_rest, names[0]) if relative else None)
            if math.hypot(*src_off) < min_pole_m:
                continue
            fem = f"FEMUR_{side}"
            dst_off = flexion_offset(leg, dst_rest, _thigh(t, fem), _thigh(target_rest, fem) if relative else None)
            if math.hypot(*dst_off) < 1e-9:
                out.append(90.0)      # straight target leg against a bent source: no direction, counted as wrong
                continue
            out.append(angle_deg(src_off, dst_off))
    return out


def clip_legs(source: Sequence[Mapping[str, Vec3]], target: Sequence[Mapping[str, Vec3]],
              source_rest: Mapping[str, Vec3], target_rest: Mapping[str, Vec3]) -> Dict[str, object]:
    """MO-2 / MO-3 values of one clip (``None`` where there is nothing to measure)."""
    h = sole_heights(source, target, source_rest, target_rest)
    k = knee_errors(source, target, source_rest=source_rest, target_rest=target_rest)
    rec: Dict[str, object] = {"provenance": PROVENANCE, "stance_samples": len(h), "knee_samples": len(k),
                              "knee_reference": "relative to rest (Decision 89 amendment)",
                              "sole_median_m": None, "sole_abs_p95_m": None, "knee_median_deg": None,
                              "knee_p90_deg": None}
    if h:
        rec["sole_median_m"] = round(statistics.median(h), 5)
        rec["sole_abs_p95_m"] = round(percentile([abs(x) for x in h], 95), 5)
    if k:
        rec["knee_median_deg"] = round(statistics.median(k), 3)
        rec["knee_p90_deg"] = round(percentile(k, 90), 3)
    return rec
