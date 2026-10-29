"""Root-motion scale for retargeting (pure Python).

The retarget copies joint *rotations*, so a planted foot moves relative to the hips by an amount proportional
to the target's leg length. The root translation must be scaled by the same ratio or the feet slide:

* ``"leg"``      — hip → knee → ankle chain length of the target over the source (feet stay planted when the
                   leg angles are copied; batch QA, scripts/retarget_batch.py).
* ``"stature"``  — whole-armature height ratio (historical default of the addon retarget; on the Quaternius
                   UAL clips it over-travels ~11 % on walks, see the batch QA).
* ``"none"``     — source metres unchanged.
* ``"stance"``   — measured per clip by the caller (``stance_scale.py``); here it behaves as ``"stature"``,
                   the fallback when a clip has no stepping to measure.

The chain uses the canonical bones the mocap maps target (``FEMUR``, ``TIBIA``, ``TALUS`` heads = hip, knee,
ankle joint centres). No anatomical number is introduced here: both lengths are measured on the two rigs.
"""

from __future__ import annotations

import math
from typing import Mapping, Optional, Sequence

Vec3 = Sequence[float]
ROOT_SCALE_MODES = ("leg", "stature", "none", "stance")   # "stance": per clip, see stance_scale.py
LEG_CHAIN = ("FEMUR", "TIBIA", "TALUS")


def chain_length(points: Sequence[Vec3]) -> float:
    return sum(math.dist(points[i - 1], points[i]) for i in range(1, len(points)))


def leg_length(heads: Mapping[str, Vec3]) -> Optional[float]:
    """Mean hip → knee → ankle length over the sides present in ``heads`` (canonical names → joint centre)."""
    lengths = []
    for side in ("L", "R"):
        names = [f"{b}_{side}" for b in LEG_CHAIN]
        if all(n in heads for n in names):
            lengths.append(chain_length([heads[n] for n in names]))
    return sum(lengths) / len(lengths) if lengths else None


def root_scale(mode: str, *, src_height_m: float, dst_height_m: float, src_leg_m: Optional[float] = None,
               dst_leg_m: Optional[float] = None) -> float:
    """Factor applied to the source root translation. ``"leg"`` falls back to ``"stature"`` without a leg chain."""
    if mode not in ROOT_SCALE_MODES:
        raise ValueError(f"unknown root scale mode {mode!r}; use one of {ROOT_SCALE_MODES}")
    if mode == "none":
        return 1.0
    if mode == "leg" and src_leg_m and dst_leg_m and src_leg_m > 1e-6:
        return dst_leg_m / src_leg_m
    return dst_height_m / src_height_m if src_height_m > 1e-6 else 1.0
