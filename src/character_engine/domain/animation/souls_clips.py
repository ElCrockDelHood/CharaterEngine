"""Placeholder animation clips for the Souls-like duel (STYLE-SOULS-001 step 4), on the CE-GAME-v1 game rig.

The clips are **authored and baked in Blender** (owner rule: cinematography / animation in Blender first) from this
engine-neutral description; Godot only plays the baked glTF clips by combat state. Every pose and timing value is
**PLACEHOLDER** (block-out quality, to be replaced by proper animation).

* A key pose gives, per game bone, a direction and an angle: the bone rotates about its head *towards* a world
  direction of the T-pose rest frame (``("down", 70)`` = the upper arm swings 70° down). Rotations follow the same
  convention as :mod:`..rigging.hand_poses` (rest frame, about the bone head, children inherit), so
  :func:`~..rigging.hand_poses.apply_hand_pose` gives the forward kinematics used for parity checks.
* Both hands hold the staff (``grip_staff`` from the hand pose library) in every clip.
* Clip lengths come from the Python frame data, so the state machine stays the truth: the light / heavy clips last
  exactly startup + active + recovery of the staff moves, hit = light hitstun, stagger / dodge / telegraph = the tuning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..gameplay.souls import SOULS_MOVES, SOULS_TUNING
from ..rigging.hand_poses import (
    HAND_POSES,
    Quat,
    Vec,
    _cross,
    _sub,
    _unit,
    apply_hand_pose,
    hand_pose_rotations,
    quat_axis_angle,
)

PROVENANCE = ProvenanceState.PLACEHOLDER
FPS = 60
WEAPON = "staff"                       # the arena's weapon set (Sentinel with the bo, Decision 53)
GRIP = "grip_staff"

#: World directions of the canonical T-pose rest frame (Z-up, -Y forward, left = +X).
DIRECTIONS: Mapping[str, Vec] = {"up": (0.0, 0.0, 1.0), "down": (0.0, 0.0, -1.0), "forward": (0.0, -1.0, 0.0),
                                 "back": (0.0, 1.0, 0.0), "left": (1.0, 0.0, 0.0), "right": (-1.0, 0.0, 0.0)}

Pose = Mapping[str, Tuple[str, float]]


@dataclass(frozen=True)
class Clip:
    clip_id: str
    frames: int                         # length in frames at 60 fps (last key frame)
    loop: bool
    keys: Tuple[Tuple[int, Pose], ...]  # (frame, pose overrides on top of the guard stance)
    states: Tuple[str, ...]             # SoulsCombat states (or events) that play this clip


#: Two-handed staff guard stance: the base of every key.
STANCE: Pose = {
    "upperarm_l": ("down", 55.0), "upperarm_r": ("down", 55.0),
    "lowerarm_l": ("forward", 70.0), "lowerarm_r": ("forward", 70.0),
    "spine_02": ("forward", 4.0), "thigh_l": ("forward", 8.0), "thigh_r": ("back", 8.0), "calf_l": ("back", 10.0),
}


def _light(i: int) -> Clip:
    mv = SOULS_MOVES[f"{WEAPON}_light"]
    hit = mv.startup + 1                                  # first active frame connects
    side = ("r", "l", "r")[i - 1]
    strike = {f"upperarm_{side}": ("forward", 75.0), f"lowerarm_{side}": ("forward", 15.0), "spine_02": ("forward", 10.0)}
    windup = {f"upperarm_{side}": ("back", 25.0), "spine_02": ("back", 6.0)}
    return Clip(f"light_{i}", mv.startup + mv.active + mv.recovery, False,
                ((0, {}), (mv.startup - 3, windup), (hit, strike), (hit + mv.active, strike),
                 (mv.startup + mv.active + mv.recovery, {})), (f"{WEAPON}_light#{i}",))


def _clips() -> Tuple[Clip, ...]:
    heavy = SOULS_MOVES[f"{WEAPON}_heavy"]
    hit_h = heavy.startup + 1
    t = SOULS_TUNING
    lift = {"upperarm_l": ("up", 30.0), "upperarm_r": ("up", 30.0), "lowerarm_l": ("back", 20.0),
            "lowerarm_r": ("back", 20.0), "spine_02": ("back", 10.0)}
    smash = {"upperarm_l": ("forward", 80.0), "upperarm_r": ("forward", 80.0), "lowerarm_l": ("down", 10.0),
             "lowerarm_r": ("down", 10.0), "spine_02": ("forward", 25.0), "thigh_l": ("forward", 30.0)}
    crouch = {"spine_01": ("forward", 35.0), "thigh_l": ("forward", 70.0), "thigh_r": ("forward", 70.0),
              "calf_l": ("back", 100.0), "calf_r": ("back", 100.0), "head": ("forward", 20.0)}
    dodge_n = int(t["dodge_frames"])
    stagger_n = int(t["stagger_frames"])
    hit_n = SOULS_MOVES[f"{WEAPON}_light"].hitstun
    return (
        Clip("idle", 60, True, ((0, {}), (30, {"spine_02": ("forward", 6.0)}), (60, {})), ("idle",)),
        Clip("walk", 40, True, (
            (0, {"thigh_l": ("forward", 25.0), "thigh_r": ("back", 20.0)}),
            (10, {"calf_r": ("back", 40.0)}),
            (20, {"thigh_l": ("back", 20.0), "thigh_r": ("forward", 25.0)}),
            (30, {"calf_l": ("back", 40.0)}),
            (40, {"thigh_l": ("forward", 25.0), "thigh_r": ("back", 20.0)})), ("walk",)),
        Clip("guard", 30, True, ((0, {"upperarm_l": ("forward", 60.0), "upperarm_r": ("forward", 60.0),
                                      "lowerarm_l": ("up", 70.0), "lowerarm_r": ("up", 70.0)}),
                                 (30, {"upperarm_l": ("forward", 60.0), "upperarm_r": ("forward", 60.0),
                                       "lowerarm_l": ("up", 70.0), "lowerarm_r": ("up", 70.0)})), ("guard",)),
        _light(1), _light(2), _light(3),
        Clip("heavy", heavy.startup + heavy.active + heavy.recovery, False,
             ((0, {}), (heavy.startup - 4, lift), (hit_h, smash), (hit_h + heavy.active, smash),
              (heavy.startup + heavy.active + heavy.recovery, {})), (f"{WEAPON}_heavy",)),
        Clip("dodge", dodge_n, False, ((0, {}), (dodge_n // 3, crouch), (2 * dodge_n // 3, crouch), (dodge_n, {})),
             ("dodge",)),
        Clip("hit", hit_n, False, ((0, {}), (3, {"spine_03": ("back", 15.0), "head": ("back", 12.0)}), (hit_n, {})),
             ("hitstun",)),
        Clip("stagger", stagger_n, False, (
            (0, {}), (8, {"spine_02": ("back", 22.0), "head": ("down", 20.0), "upperarm_l": ("down", 85.0),
                          "upperarm_r": ("down", 85.0)}),
            (stagger_n - 8, {"spine_02": ("back", 15.0), "head": ("down", 15.0)}), (stagger_n, {})), ("stagger",)),
        Clip("windup", int(t["telegraph_frames"]), False, ((0, {}), (int(t["telegraph_frames"]), lift)), ("telegraph",)),
    )


SOULS_CLIPS: Dict[str, Clip] = {c.clip_id: c for c in _clips()}


def clip_for(state: str, move_id: str = "", chain: int = 0) -> str:
    """Clip that plays for a SoulsCombat state (``move_start`` details pick light_1..3 / heavy)."""
    if state in ("startup", "active", "recovery"):
        if move_id.endswith("_heavy"):
            return "heavy"
        return f"light_{max(1, min(3, chain or 1))}"
    for c in SOULS_CLIPS.values():
        if state in c.states:
            return c.clip_id
    return "idle"


def key_pose(pose: Pose) -> Dict[str, Tuple[str, float]]:
    return {**STANCE, **pose}


def key_rotations(points: Mapping[str, Tuple[Vec, Vec]], pose: Pose) -> Dict[str, Quat]:
    """Rest-frame rotations of the key (stance + overrides) plus the staff grip on both hands."""
    out: Dict[str, Quat] = {}
    for side in ("L", "R"):
        out.update(hand_pose_rotations(HAND_POSES[GRIP], points, side))
    for bone, (direction, deg) in key_pose(pose).items():
        d = _unit(_sub(points[bone][1], points[bone][0]))
        axis = _cross(d, DIRECTIONS[direction])
        if math.sqrt(sum(c * c for c in axis)) < 1e-9:
            continue                                       # already pointing that way
        out[bone] = quat_axis_angle(axis, math.radians(deg))
    return out


PROBE_BONES = ("spine_02", "head", "upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r", "thigh_l", "calf_l",
               "index_03_r", "thumb_03_l")


def clip_reference(points: Mapping[str, Tuple[Vec, Vec]]) -> Dict[str, object]:
    """Engine-neutral clip table with expected bone directions at every key (parity for Blender and Godot)."""
    clips: Dict[str, object] = {}
    for c in SOULS_CLIPS.values():
        keys: List[Dict[str, object]] = []
        for frame, pose in c.keys:
            posed = apply_hand_pose(points, key_rotations(points, pose))
            dirs = {b: list(_unit(_sub(posed[b][1], posed[b][0]))) for b in PROBE_BONES}
            keys.append({"frame": frame, "directions": dirs})
        clips[c.clip_id] = {"clip_id": c.clip_id, "frames": c.frames, "seconds": c.frames / FPS, "loop": c.loop,
                            "states": list(c.states), "keys": keys}
    rest = {b: list(_unit(_sub(points[b][1], points[b][0]))) for b in PROBE_BONES}
    return {"fps": FPS, "weapon": WEAPON, "grip": GRIP, "provenance": PROVENANCE.value,
            "probe_bones": list(PROBE_BONES), "rest_directions": rest, "clips": clips}
