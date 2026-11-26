"""Leg grounding for retargeted clips (pure Python, Decision 85).

Copying joint rotations onto a skeleton with other leg proportions puts the feet at the wrong height: the batch
QA found idle soles 2.5 cm under the ground, walk 3.4 cm, and the crouch idle hovering 23 cm above it, with the
knees turned up to 26 deg away from the source's. Grounding fixes it frame by frame from the source:

* each ankle's wanted height is its rest height plus the source ankle's lift over its own rest height, scaled
  like the root motion (``ankle_targets``): a planted foot stays on the ground, a jump keeps its lift;
* the **support** foot (the source's lower one) sets a vertical shift of the whole body (``plan``), so stance
  and crouch depth come from the pelvis, as in the source, not from bending one leg;
* the other foot keeps its own difference, reached with the two-bone IK of ``foot_lock`` with the knee pointing
  where the source's knee points.

* the source's own ground error is not copied (Decision 89 amendment 3): when the source's support foot is within
  ``CONTACT_BAND_M`` of its ground (its lowest point, not only the ankle), it is in contact, so the body is shifted by
  that error too and our support foot rests on the ground. A clip whose source foot floats 1.1 cm or sinks 1 cm while
  standing (UAL Sword_Heavy_Combo, Zombie_Walk) no longer passes that to our feet. Beyond the band (a jump) nothing
  changes. When *both* source feet are in contact, the body goes as low as the foot that needs it most, so both of
  ours reach the ground: before, a landing set the body from one foot and the other leg could not reach and went
  straight while the source's knee was bent 21-27 deg (UAL Jump_Land, NinjaJump_Land).

Only heights change: the horizontal path of root and feet is the retarget's (``foot_lock`` handles sliding).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

Vec3 = Sequence[float]
SIDES = ("L", "R")
CONTACT_BAND_M = 0.03     # ESTIMATE: same as the clip QA contact height (clip_qa.Thresholds.contact_height_m)


@dataclass(frozen=True)
class GroundPlan:
    root_dz: float                            # vertical shift of the whole body (m)
    foot_dz: Tuple[Tuple[str, float], ...]    # per side, the ankle's remaining shift after root_dz (m)
    support: str                              # side whose foot carries the body

    def foot(self, side: str) -> float:
        return dict(self.foot_dz)[side]


def ankle_targets(src_ankle_z: Mapping[str, float], src_rest_z: Mapping[str, float],
                  dst_rest_z: Mapping[str, float], scale: float) -> dict:
    """Wanted ankle heights: rest height plus the source's lift over its rest, scaled like the root motion."""
    return {s: dst_rest_z[s] + (src_ankle_z[s] - src_rest_z[s]) * scale for s in src_ankle_z}


def plan(src_ankle_z: Mapping[str, float], src_rest_z: Mapping[str, float], dst_ankle_z: Mapping[str, float],
         dst_rest_z: Mapping[str, float], scale: float,
         src_ground_error: Optional[Mapping[str, float]] = None) -> GroundPlan:
    """Body shift from the support foot, then what each ankle still has to move.

    ``src_ground_error``: per side, the source foot's lowest point minus its rest height. Within ``CONTACT_BAND_M`` on
    the support side it is the source's own error and is taken off the body shift (the feet keep their difference)."""
    want = ankle_targets(src_ankle_z, src_rest_z, dst_rest_z, scale)
    delta = {s: want[s] - dst_ankle_z[s] for s in want}
    support = min(want, key=lambda s: (src_ankle_z[s] - src_rest_z[s], s))
    err = src_ground_error or {}
    planted = [s for s in delta if err.get(s) is not None and abs(err[s]) <= CONTACT_BAND_M]
    # a foot in contact aims at the ground, not at the source's own error (scaled like everything else)
    adj = {s: delta[s] - err[s] * scale if s in planted else delta[s] for s in delta}
    root = min(adj[s] for s in planted) if planted else delta[support]   # low enough for every foot in contact
    return GroundPlan(root, tuple((s, adj[s] - root) for s in sorted(adj)), support)


def _cross(a: Vec3, b: Vec3):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def onto_source_leg_plane(src_hip: Vec3, src_knee: Vec3, src_ankle: Vec3, dst_hip: Vec3,
                          dst_target: Vec3) -> Tuple[float, float, float]:
    """Our ankle target moved, by the shortest path, onto the source's leg plane through our hip (Decision 89
    amendment 4). Used only for a foot in the air: nothing on the ground fixes where it goes, so our knee can then bend
    about the source's hinge axis exactly. The copied shin rotation leaves our ankle up to 6 deg out of that plane,
    which a deep bend turns into a 7 deg tilt of the knee (UAL NinjaJump_Idle_Loop, NinjaJump_Start). An almost straight
    source leg has no plane: the target is returned unchanged."""
    u = [src_knee[i] - src_hip[i] for i in range(3)]
    v = [src_ankle[i] - src_knee[i] for i in range(3)]
    axis = _cross(u, v)
    na = math.hypot(*axis)
    if na < 1e-9 * max(1.0, math.hypot(*u) * math.hypot(*v)):
        return tuple(dst_target)
    axis = [c / na for c in axis]
    k = sum((dst_target[i] - dst_hip[i]) * axis[i] for i in range(3))
    return tuple(dst_target[i] - k * axis[i] for i in range(3))


def knee_pole(src_hip: Vec3, src_knee: Vec3, src_ankle: Vec3, dst_hip: Vec3,
              dst_target: Optional[Vec3] = None) -> Tuple[float, float, float]:
    """A pole point for the IK so the knee turns like the source's (the copied rotations leave it up to 26 deg off on
    a straight leg).

    With ``dst_target`` (where our ankle is going) the knee bends about the source's *hinge axis*, the normal of its
    thigh-shin plane, as far as our leg can (Decision 89 amendment 4): the axis is projected onto the plane square to
    our hip -> target line, and the pole points along ``line x axis``. On a deeply bent knee our hip -> ankle line can
    turn 25 deg away from the source's, and the plain offset below then tilted our knee plane by about 7 deg (UAL
    NinjaJump_Idle_Loop, NinjaJump_Start). Without ``dst_target``, or for an almost straight source leg, the pole is the
    source knee's offset from the middle of its hip-ankle line, moved to our hip."""
    mid = tuple((src_hip[i] + src_ankle[i]) / 2 for i in range(3))
    d = tuple(src_knee[i] - mid[i] for i in range(3))
    plain = tuple(dst_hip[i] + d[i] for i in range(3))
    if dst_target is None:
        return plain
    u = [src_knee[i] - src_hip[i] for i in range(3)]
    v = [src_ankle[i] - src_knee[i] for i in range(3)]
    axis = _cross(u, v)
    line = [dst_target[i] - dst_hip[i] for i in range(3)]
    na, nl = math.hypot(*axis), math.hypot(*line)
    if na < 1e-9 * max(1.0, math.hypot(*u) * math.hypot(*v)) or nl < 1e-9:
        return plain
    axis, line = [c / na for c in axis], [c / nl for c in line]
    k = sum(axis[i] * line[i] for i in range(3))
    axis = [axis[i] - k * line[i] for i in range(3)]
    n = math.hypot(*axis)
    if n < 1e-6:
        return plain
    side = _cross(line, [c / n for c in axis])                  # where the knee points, square to our line
    size = max(math.hypot(*d), 0.05)
    return tuple(dst_hip[i] + side[i] * size for i in range(3))
