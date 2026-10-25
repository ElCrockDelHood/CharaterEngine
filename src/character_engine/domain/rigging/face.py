"""Face contract for CE-GAME-v1 (RIG-GAME-001 step 5): ARKit shape names, jaw and eye look-at.

* :data:`ARKIT_52` — the 52 ARKit blendshape names, the shape-name contract for every head mesh (Blender
  cinematics use all of them).
* :data:`GAME_FACE_SHAPES` — the 20-shape in-game subset approved by the owner after the GT 740M benchmark
  (A12, 2026-10-25). Shape *geometry* waits for a head mesh; only names are fixed here.
* Bones: ``jaw`` opens about the head's lateral axis; ``eye_l`` / ``eye_r`` aim at a target with clamped yaw and
  pitch. Axes come from the game bone points (lateral = eye_r → eye_l, forward = eye aim, up = forward × lateral),
  so they follow pose and stature. Angle limits are **ASSUMED** (no cited range in the repository).

Rotations are quaternions ``(w, x, y, z)`` in the frame of the given points (the head's rest frame), about the
bone head — the same convention as :mod:`.hand_poses`.
"""

from __future__ import annotations

import math
from typing import Mapping, Tuple

from ..anatomy.reference.source import ProvenanceState
from .hand_poses import Quat, Vec, _cross, _sub, _unit, quat_axis_angle, quat_mul

ARKIT_52: Tuple[str, ...] = (
    "eyeBlinkLeft", "eyeLookDownLeft", "eyeLookInLeft", "eyeLookOutLeft", "eyeLookUpLeft", "eyeSquintLeft",
    "eyeWideLeft", "eyeBlinkRight", "eyeLookDownRight", "eyeLookInRight", "eyeLookOutRight", "eyeLookUpRight",
    "eyeSquintRight", "eyeWideRight", "jawForward", "jawLeft", "jawRight", "jawOpen", "mouthClose", "mouthFunnel",
    "mouthPucker", "mouthLeft", "mouthRight", "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft",
    "mouthFrownRight", "mouthDimpleLeft", "mouthDimpleRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper", "mouthPressLeft", "mouthPressRight",
    "mouthLowerDownLeft", "mouthLowerDownRight", "mouthUpperUpLeft", "mouthUpperUpRight", "browDownLeft",
    "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "cheekPuff", "cheekSquintLeft",
    "cheekSquintRight", "noseSneerLeft", "noseSneerRight", "tongueOut",
)

#: In-game subset (owner approval 2026-10-25, decision card after A12): ≤ 20 shapes on the GT 740M.
GAME_FACE_SHAPES: Tuple[str, ...] = (
    "eyeBlinkLeft", "eyeBlinkRight", "eyeSquintLeft", "eyeSquintRight", "browDownLeft", "browDownRight",
    "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "jawOpen", "mouthClose", "mouthSmileLeft",
    "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight", "mouthFunnel", "mouthPucker", "cheekPuff",
    "noseSneerLeft", "noseSneerRight",
)

JAW_OPEN_MAX_DEG = 25.0        # ASSUMED
EYE_YAW_MAX_DEG = 35.0         # ASSUMED, left / right
EYE_PITCH_MAX_DEG = 25.0       # ASSUMED, up / down
PROVENANCE = ProvenanceState.ASSUMED


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def head_axes(points: Mapping[str, Tuple[Vec, Vec]]) -> Tuple[Vec, Vec, Vec]:
    """(lateral → left, forward, up) of the head from the eye bones."""
    lateral = _unit(_sub(points["eye_l"][0], points["eye_r"][0]))
    forward = _unit(_sub(points["eye_l"][1], points["eye_l"][0]))
    forward = _unit(_sub(forward, tuple(_dot(forward, lateral) * c for c in lateral)))  # type: ignore[arg-type]
    return lateral, forward, _cross(forward, lateral)


def jaw_rotation(points: Mapping[str, Tuple[Vec, Vec]], open_amount: float) -> Quat:
    """Jaw rotation for ``open_amount`` in [0, 1] (1 = :data:`JAW_OPEN_MAX_DEG`); the chin moves down."""
    lateral, _, _ = head_axes(points)
    return quat_axis_angle(lateral, math.radians(max(0.0, min(1.0, open_amount)) * JAW_OPEN_MAX_DEG))


def eye_look_angles(points: Mapping[str, Tuple[Vec, Vec]], eye: str, target: Vec) -> Tuple[float, float]:
    """Clamped (yaw, pitch) in degrees for ``eye`` ("eye_l" / "eye_r") aiming at ``target``.

    Yaw > 0 turns towards the character's left (+lateral), pitch > 0 looks up.
    """
    lateral, forward, up = head_axes(points)
    d = _unit(_sub(target, points[eye][0]))
    yaw = math.degrees(math.atan2(_dot(d, lateral), _dot(d, forward)))
    pitch = math.degrees(math.atan2(_dot(d, up), math.hypot(_dot(d, lateral), _dot(d, forward))))
    return (max(-EYE_YAW_MAX_DEG, min(EYE_YAW_MAX_DEG, yaw)), max(-EYE_PITCH_MAX_DEG, min(EYE_PITCH_MAX_DEG, pitch)))


def eye_look_rotation(points: Mapping[str, Tuple[Vec, Vec]], eye: str, target: Vec) -> Quat:
    """Rotation of ``eye`` that aims it at ``target`` within the clamped yaw / pitch."""
    lateral, forward, up = head_axes(points)
    yaw, pitch = eye_look_angles(points, eye, target)
    # pitch first (forward towards up, about forward x up), then yaw about up (forward towards up x forward = lateral)
    q_pitch = quat_axis_angle(_cross(forward, up), math.radians(pitch))
    q_yaw = quat_axis_angle(up, math.radians(yaw))
    return quat_mul(q_yaw, q_pitch)


def face_contract(points: Mapping[str, Tuple[Vec, Vec]]) -> dict:
    """Face block for the runtime (Godot): game shapes, limits, axes and Python reference cases (parity tests).

    Cinematic-only data (the full :data:`ARKIT_52` set) is NOT included: cinematics are authored and polished
    in Blender, and only finished game assets reach Godot (owner rule, 2026-10-25).
    """
    lateral, forward, up = head_axes(points)
    mid = tuple((a + b) / 2 for a, b in zip(points["eye_l"][0], points["eye_r"][0]))

    def at(f: float, l: float, u: float) -> Vec:
        return tuple(mid[i] + f * forward[i] + l * lateral[i] + u * up[i] for i in range(3))  # type: ignore[return-value]

    targets = {"ahead": at(1.0, 0.0, 0.0), "left_up": at(1.0, 0.5, 0.3), "clamped_right_down": at(0.2, -1.0, -1.0)}
    return {
        "shape_naming": "ARKit",
        "game_shapes": list(GAME_FACE_SHAPES),
        "jaw_bone": "jaw",
        "eye_bones": ["eye_l", "eye_r"],
        "jaw_open_max_deg": JAW_OPEN_MAX_DEG,
        "eye_yaw_max_deg": EYE_YAW_MAX_DEG,
        "eye_pitch_max_deg": EYE_PITCH_MAX_DEG,
        "provenance": PROVENANCE.value,
        "axes": {"lateral": list(lateral), "forward": list(forward), "up": list(up)},
        "reference": {
            "jaw": {str(a): list(jaw_rotation(points, a)) for a in (0.5, 1.0)},
            "eyes": {name: {"target": list(t), **{e: list(eye_look_rotation(points, e, t)) for e in ("eye_l", "eye_r")}}
                     for name, t in targets.items()},
        },
    }
