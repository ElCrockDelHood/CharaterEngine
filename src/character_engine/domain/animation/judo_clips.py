"""Paired key poses (tori and uke) for the first five judo throws, on the CE-GAME-v1 game rig (A36).

**PLACEHOLDER** block-out, authored from written descriptions of each throw and single illustrations (no motion
capture and no frame-by-frame source was used); to be judged by eye on the contact sheet
(``scripts/judo_contact_sheet.py``) and corrected before any bake.

How a key is described, so it can be edited by hand:

* **Directions**: a pose gives a game bone the direction it points to, in the fighter's own frame, with
  :func:`v` ``(fwd, left, up)``. Bones not named keep their rest rotation relative to the parent. ``trunk`` is the
  pelvis (the spine follows), ``chest`` is ``spine_02``, ``neck`` is ``neck_01``. Feet stay flat unless named.
* **Root**: where the pelvis is in the world (x, y), the turns of the whole body about world axes, in order, and the
  height: on the ground (lowest point at ``clearance``) or an explicit pelvis height while airborne.
* **Reach**: a hand or a foot is put on a point of the other fighter with two-bone IK (``foot_lock.two_bone_ik``), which
  is what makes the grips and the reaping leg actually touch.

World frame: Z up, tori starts at the origin facing -Y, uke stands in front of tori facing +Y.
The output keeps the convention of ``souls_clips`` (rest-frame rotation of each bone about its head, children
inherit), plus the root transform, so the same kind of Blender bake can consume it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Mapping, Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..rigging.game_rig import GAME_BONES
from ..rigging.hand_poses import (
    IDENTITY,
    Quat,
    Vec,
    _add,
    _cross,
    _sub,
    _unit,
    apply_hand_pose,
    quat_axis_angle,
    quat_mul,
    quat_rotate,
)
from .foot_lock import two_bone_ik

PROVENANCE = ProvenanceState.PLACEHOLDER
SCHEMA = "ce-judo-clips/1"
FPS = 60
Points = Mapping[str, Tuple[Vec, Vec]]
Pose = Mapping[str, Vec]

ALIASES: Mapping[str, str] = {"trunk": "pelvis", "chest": "spine_02", "neck": "neck_01"}
LIMBS: Mapping[str, Tuple[str, str]] = {"arm_l": ("upperarm_l", "lowerarm_l"), "arm_r": ("upperarm_r", "lowerarm_r"),
                                        "leg_l": ("thigh_l", "calf_l"), "leg_r": ("thigh_r", "calf_r")}
_FLAT = ("foot_l", "foot_r", "ball_l", "ball_r")
_AXES: Mapping[str, Vec] = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


def v(fwd: float = 0.0, left: float = 0.0, up: float = 0.0) -> Vec:
    """A direction in the fighter's own frame (rest frame: forward is -Y, left is +X, up is +Z)."""
    return _unit((left, -fwd, up))


def _conj(q: Quat) -> Quat:
    return (q[0], -q[1], -q[2], -q[3])


def _arc(a: Vec, b: Vec) -> Quat:
    """Shortest rotation that takes unit ``a`` to unit ``b``."""
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]))
    axis = _cross(a, b)
    if math.sqrt(sum(c * c for c in axis)) < 1e-9:
        if dot > 0:
            return IDENTITY
        axis = _cross(a, (1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0))
    return quat_axis_angle(axis, math.acos(dot))


@dataclass(frozen=True)
class Root:
    x: float = 0.0
    y: float = 0.0
    turns: Tuple[Tuple[str, float], ...] = ()        # (world axis, degrees), applied in order about the pelvis
    z: Optional[float] = None                        # pelvis height; None: on the ground
    clearance: float = 0.0                           # ground offset of the lowest bone point (lying: half a body depth)
    quat: Optional[Quat] = None                      # explicit rotation (in-betweens); replaces ``turns``

    def rotation(self) -> Quat:
        if self.quat is not None:
            return self.quat
        q = IDENTITY
        for axis, deg in self.turns:
            q = quat_mul(quat_axis_angle(_AXES[axis], math.radians(deg)), q)
        return q


@dataclass(frozen=True)
class Target:
    bone: str                                        # bone of the other fighter
    t: float = 0.5                                   # 0 = head of the bone, 1 = tail
    offset: Vec = (0.0, 0.0, 0.0)                    # (left, fwd, up) in the other fighter's root frame, metres
    pole: Optional[Vec] = None                       # (left, fwd, up) hint for the elbow / knee, own root frame


@dataclass(frozen=True)
class FighterKey:
    pose: Pose
    root: Root
    reach: Mapping[str, Target] = field(default_factory=dict)
    swing: Mapping[str, float] = field(default_factory=dict)    # degrees: elbow / knee turned about shoulder -> hand
    tilt: Mapping[str, Vec] = field(default_factory=dict)       # rotation vector (rad, own frame): free limb or hand / foot


@dataclass(frozen=True)
class Key:
    frame: int
    phase: str                                       # kumikata | kuzushi | tsukuri | kake | fall | landing | end
    tori: FighterKey
    uke: FighterKey


@dataclass(frozen=True)
class ThrowClip:
    throw_id: str
    keys: Tuple[Key, ...]

    @property
    def frames(self) -> int:
        return self.keys[-1].frame


def pose_rotations(points: Points, pose: Pose) -> Dict[str, Quat]:
    """Rest-frame rotation of every named bone so that it points along its direction (parents first)."""
    wanted = {ALIASES.get(k, k): d for k, d in pose.items()}
    for b in _FLAT:
        wanted.setdefault(b, _unit(_sub(points[b][1], points[b][0])))
    world: Dict[Optional[str], Quat] = {None: IDENTITY}
    out: Dict[str, Quat] = {}
    for g in GAME_BONES:
        parent = world[g.parent]
        q = IDENTITY
        if g.name in wanted:
            rest = _unit(_sub(points[g.name][1], points[g.name][0]))
            q = _arc(rest, quat_rotate(_conj(parent), _unit(wanted[g.name])))
            out[g.name] = q
        world[g.name] = quat_mul(parent, q)
    return out


def place(points: Points, body: Points, root: Root) -> Dict[str, Tuple[Vec, Vec]]:
    """Body-frame points to world: turn about the rest pelvis, move the pelvis to (x, y), then set the height."""
    pivot, m = points["pelvis"][0], _mat(root.rotation())

    def tr(p: Vec) -> Vec:
        r = _mv(m, _sub(p, pivot))
        return (r[0] + root.x, r[1] + root.y, r[2])

    out = {b: (tr(h), tr(t)) for b, (h, t) in body.items()}
    low = min(min(h[2], t[2]) for h, t in out.values())
    dz = (root.clearance - low) if root.z is None else root.z - out["pelvis"][0][2]
    return {b: ((h[0], h[1], h[2] + dz), (t[0], t[1], t[2] + dz)) for b, (h, t) in out.items()}


def _local(root: Root, d: Vec) -> Vec:
    return quat_rotate(_conj(root.rotation()), d)


def _frame_vec(root: Root, lfu: Vec) -> Vec:
    """(left, fwd, up) of a fighter's root frame as a world vector."""
    return quat_rotate(root.rotation(), (lfu[0], -lfu[1], lfu[2]))


def _mat(q: Quat) -> Tuple[float, ...]:
    """Row-major 3x3 rotation matrix of a unit quaternion (w, x, y, z)."""
    w, x, y, z = q
    return (1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y),
            2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x),
            2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y))


def _mv(m: Tuple[float, ...], v: Vec) -> Vec:
    return (m[0] * v[0] + m[1] * v[1] + m[2] * v[2], m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
            m[6] * v[0] + m[7] * v[1] + m[8] * v[2])


def forward_kinematics(points: Points, rotations: Mapping[str, Quat]) -> Dict[str, Tuple[Vec, Vec]]:
    """Same result as ``hand_poses.apply_hand_pose`` in one pass over the bones (each bone carries its parent's
    transform composed with its own rotation about its head)."""
    ident = _mat(IDENTITY)
    xf: Dict[Optional[str], Tuple[Quat, Tuple[float, ...], Vec]] = {None: (IDENTITY, ident, (0.0, 0.0, 0.0))}
    out: Dict[str, Tuple[Vec, Vec]] = {}
    for g in GAME_BONES:
        pq, pm, pt = xf[g.parent]
        h, tail = points[g.name]
        q = rotations.get(g.name)
        if q is None:
            wq, wm, wt = pq, pm, pt
        else:
            m = _mat(q)
            local_t = _sub(h, _mv(m, h))
            wq = quat_mul(pq, q)
            wm, wt = _mat(wq), _add(_mv(pm, local_t), pt)
        xf[g.name] = (wq, wm, wt)
        out[g.name] = (_add(_mv(wm, h), wt), _add(_mv(wm, tail), wt))
    for b, pts in points.items():                     # bones outside the game rig keep their rest points
        out.setdefault(b, pts)
    return out


#: Ends that the clearance solver may turn on their own (the grip or the hook stays where it is), and the head.
_TILT_BONES: Mapping[str, Tuple[str, ...]] = {"head": ("head",), "hand_l": ("hand_l",), "hand_r": ("hand_r",), "foot_l": ("foot_l", "ball_l"),
                                              "foot_r": ("foot_r", "ball_r")}


def _tilted(points: Points, fk: FighterKey, pose: Pose) -> Dict[str, Vec]:
    if not fk.tilt:
        return dict(pose)
    out = dict(pose)
    body = forward_kinematics(points, pose_rotations(points, pose))
    for limb, rv in fk.tilt.items():
        ang = math.sqrt(sum(c * c for c in rv))
        if ang < 1e-9:
            continue
        q = quat_axis_angle(tuple(c / ang for c in rv), ang)
        for bone in _TILT_BONES.get(limb, LIMBS.get(limb, ())):
            out[bone] = quat_rotate(q, _unit(_sub(body[bone][1], body[bone][0])))
    return out


def _world(points: Points, fk: FighterKey, pose: Pose) -> Dict[str, Tuple[Vec, Vec]]:
    return place(points, forward_kinematics(points, pose_rotations(points, pose)), fk.root)


_RADIUS: Dict[str, float] = {}


def body_radius(bone: str) -> float:
    """Block-body capsule radius of a game bone (``game_body``, 1.80 m adult, ESTIMATE); 0 for bones without one."""
    if not _RADIUS:
        from ..rigging.block_dummy import ENVELOPE_RADIUS_M
        from ..rigging.game_body import GAME_BODY_SEGMENTS

        _RADIUS.update({g.bone: ENVELOPE_RADIUS_M[g.region] * g.radius_scale for g in GAME_BODY_SEGMENTS})
    return _RADIUS.get(bone, 0.0)


def _target_point(other: Points, other_root: Root, t: Target, reach_from: Optional[Vec] = None, end_radius: float = 0.0) -> Vec:
    """The grip point on the other body's **surface**: the authored point, pushed out of the target capsule so that a
    hand (or shin) of ``end_radius`` rests on it instead of going in."""
    h, tail = other[t.bone]
    p = tuple(h[i] + (tail[i] - h[i]) * t.t for i in range(3))
    goal = _add(p, _frame_vec(other_root, t.offset))
    need = body_radius(t.bone) + end_radius
    if need <= 0.0:
        return goal
    ax = _sub(tail, h)
    n2 = sum(c * c for c in ax) or 1.0
    s = max(0.0, min(1.0, sum((goal[i] - h[i]) * ax[i] for i in range(3)) / n2))
    on_axis = tuple(h[i] + ax[i] * s for i in range(3))
    out = _sub(goal, on_axis)
    d = math.sqrt(sum(c * c for c in out))
    if d >= need:
        return goal
    if d < 1e-6:                                      # authored on the axis: come out towards the reaching shoulder
        if reach_from is None:
            return goal
        out = _sub(reach_from, on_axis)
        out = _sub(out, tuple(c * sum(o * a for o, a in zip(out, ax)) / n2 for c in ax))
        d = math.sqrt(sum(c * c for c in out)) or 1.0
    return _add(on_axis, tuple(c / d * need for c in out))


def _with_reach(points: Points, fk: FighterKey, other: Points, other_root: Root) -> Tuple[Pose, Dict[str, float]]:
    pose: Dict[str, Vec] = _tilted(points, fk, fk.pose)
    miss: Dict[str, float] = {}
    for _ in range(2):                                # the second pass corrects limbs whose parent moved
        mine = _world(points, fk, pose)
        for limb, tgt in fk.reach.items():
            upper, lower = LIMBS[limb]
            hip, knee, end = mine[upper][0], mine[upper][1], mine[lower][1]
            goal = _target_point(other, other_root, tgt, hip, body_radius(lower))
            pole = None if tgt.pole is None else _add(hip, _frame_vec(fk.root, tgt.pole))
            sw = fk.swing.get(limb, 0.0)
            if sw:                                        # turn the elbow / knee about the shoulder -> grip line
                axis = _unit(_sub(goal, hip))
                base = _sub(pole if pole is not None else knee, hip)
                pole = _add(hip, quat_rotate(quat_axis_angle(axis, math.radians(sw)), base))
            ik = two_bone_ik(hip, knee, end, goal, pole)
            pose[upper] = _local(fk.root, _unit(_sub(ik.knee, hip)))
            pose[lower] = _local(fk.root, _unit(_sub(ik.ankle, ik.knee)))
            miss[limb] = math.dist(ik.ankle, goal)
    return pose, miss


@dataclass(frozen=True)
class SolvedKey:
    frame: int
    phase: str
    tori: Dict[str, Tuple[Vec, Vec]]                 # world points
    uke: Dict[str, Tuple[Vec, Vec]]
    tori_pose: Pose
    uke_pose: Pose
    miss_m: Dict[str, float]                         # "tori.arm_l" -> distance left between the hand and its grip


def solve_key(points: Points, key: Key) -> SolvedKey:
    """World points of both fighters at a key, with every reach solved against the other fighter."""
    tp, up = _tilted(points, key.tori, key.tori.pose), _tilted(points, key.uke, key.uke.pose)
    tw, uw = _world(points, key.tori, tp), _world(points, key.uke, up)
    miss: Dict[str, float] = {}
    for _ in range(3):                                # grips on a moving arm settle in a few rounds
        tp, mt = _with_reach(points, key.tori, uw, key.uke.root)
        tw = _world(points, key.tori, tp)
        up, mu = _with_reach(points, key.uke, tw, key.tori.root)
        uw = _world(points, key.uke, up)
        miss = {**{f"tori.{k}": d for k, d in mt.items()}, **{f"uke.{k}": d for k, d in mu.items()}}
    return SolvedKey(key.frame, key.phase, tw, uw, tp, up, miss)


def solve_clip(points: Points, clip: ThrowClip) -> List[SolvedKey]:
    return [s for _, s in clear_clip_keys(points, clip)]


# --------------------------------------------------------------------------------------------------------------------
# Clearance: the two bodies (and each body with itself) must not go into each other (owner: "que las manifestaciones no
# se atraviesen"). A greedy search on top of the authored key: it never changes what a pose means, only how it is
# carried out -- uke is moved away from tori, an elbow or knee turns about its grip line, a free limb tilts away.

CLEAR_M = 0.005                    # ASSUMED: an overlap under 5 mm is a touch (the capsules are proxies, not skin)
AIM_M = 0.003                      # the search aims under this, so that every result is under CLEAR_M
_SWINGS = (-120.0, -80.0, -45.0, -20.0, -8.0, 8.0, 20.0, 45.0, 80.0, 120.0)
_TILTS = (0.10, 0.20, 0.40, 0.70)  # rad
_MAY_RELEASE = ("fall", "landing", "end")   # after kake tori may let go of a hold rather than push an arm through a body


def _limb_of(bone: str) -> Optional[str]:
    for limb, (upper, lower) in LIMBS.items():
        side = limb[-1]
        if bone in (upper, lower) or bone in (f"hand_{side}" if limb.startswith("arm") else f"foot_{side}",
                                              f"ball_{side}" if limb.startswith("leg") else ""):
            return limb
    return None


def _gripping_bones(fk: FighterKey) -> Tuple[str, ...]:
    """A gripping hand and its forearm may press into the gi (``GI_THICKNESS_M``); a hooking shin likewise."""
    out: List[str] = []
    for limb in fk.reach:
        out += [f"hand_{limb[-1]}", LIMBS[limb][1]] if limb.startswith("arm") else [LIMBS[limb][1], f"foot_{limb[-1]}"]
    return tuple(out)


def overlaps(key: Key, s: SolvedKey):
    """All overlaps of a solved key: (owner of bone a, owner of bone b, Penetration), deepest first."""
    from .body_clearance import penetrations, self_penetrations

    out = [("tori", "uke", x) for x in penetrations(s.tori, s.uke, _gripping_bones(key.tori), _gripping_bones(key.uke))]
    out += [("tori", "tori", x) for x in self_penetrations(s.tori)]
    out += [("uke", "uke", x) for x in self_penetrations(s.uke)]
    return sorted(out, key=lambda o: -o[2].depth_m)


_PROBES = ("pelvis", "head", "hand_l", "hand_r", "foot_l", "foot_r", "lowerarm_l", "lowerarm_r", "calf_l", "calf_r")
JUMP_M = 0.15                      # ASSUMED: a point moving more than 0.15 m in one frame (9 m/s) is penalised


def _jump(s: SolvedKey, prev: Optional[SolvedKey], frames: int = 1) -> float:
    """How far the probe points move from ``prev`` beyond ``JUMP_M`` per frame, over ``frames`` frames."""
    if prev is None:
        return 0.0
    return sum(max(0.0, math.dist(getattr(s, w)[b][1], getattr(prev, w)[b][1]) - JUMP_M * frames)
               for w in ("tori", "uke") for b in _PROBES)


Ahead = Optional[Tuple[SolvedKey, int]]          # the next key and how many frames remain to reach it


HOME_M = 0.06                      # ASSUMED: uke may be moved this far from the authored place for free


def _drift(key: Key, home: Optional[Key]) -> float:
    if home is None:
        return 0.0
    a, b = key.uke.root, home.uke.root
    dz = 0.0 if a.z is None or b.z is None else a.z - b.z
    return max(0.0, math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + dz * dz) - HOME_M)


def _cost(key: Key, s: SolvedKey, prev: Optional[SolvedKey] = None, ahead: Ahead = None,
          home: Optional[Key] = None) -> float:
    pen = sum(o[2].depth_m for o in overlaps(key, s) if o[2].depth_m > AIM_M)
    grip = sum(max(0.0, d - 0.02) for d in s.miss_m.values())            # a grip must not be given up to clear
    low = max(0.0, -min(min(h[2], e[2]) for w in (s.tori, s.uke) for h, e in w.values()))
    # going in costs more than a grip slipping a little; on in-betweens a jump from the last frame costs most
    reach_next = 0.0 if ahead is None else _jump(s, ahead[0], ahead[1])   # must still be able to reach the next key
    return 10.0 * pen + grip + 4.0 * low + 3.0 * (_jump(s, prev) + reach_next) + 4.0 * _drift(key, home)


def _with(key: Key, who: str, fk: FighterKey) -> Key:
    return replace(key, **{who: fk})


def _candidates(key: Key, s: SolvedKey, a_who: str, b_who: str, pen) -> List[Key]:
    out: List[Key] = []
    for who, bone, sign in ((a_who, pen.bone_a, -1.0), (b_who, pen.bone_b, 1.0)):
        fk = getattr(key, who)
        world = getattr(s, who)
        away = tuple(sign * c for c in pen.normal)                        # away from the other capsule
        end = next((e for e, bones in _TILT_BONES.items() if bone in bones), None)
        if end is not None:                                               # turn the hand or the foot itself
            d_end = _unit(_sub(world[bone][1], world[bone][0]))
            axis = _cross(d_end, away)
            n = math.sqrt(sum(c * c for c in axis))
            if n > 1e-6:
                axis = _local(fk.root, tuple(c / n for c in axis))
                prev = fk.tilt.get(end, (0.0, 0.0, 0.0))
                for ang in (0.35, 0.7, 1.1):
                    out.append(_with(key, who, replace(fk, tilt={**fk.tilt, end: tuple(prev[i] + axis[i] * ang for i in range(3))})))
        limb = _limb_of(bone)
        if limb is None:
            continue
        if limb in fk.reach:
            for d in _SWINGS:
                out.append(_with(key, who, replace(fk, swing={**fk.swing, limb: fk.swing.get(limb, 0.0) + d})))
            miss = s.miss_m.get(f"{who}.{limb}", 0.0)
            if key.phase in _MAY_RELEASE and miss > 0.05:                # after kake, a hold already slipping may be let go
                out.append(_with(key, who, replace(fk, reach={k: v for k, v in fk.reach.items() if k != limb})))
        else:
            upper = LIMBS[limb][0]
            d_limb = _unit(_sub(world[upper][1], world[upper][0]))
            axis = _cross(d_limb, away)
            n = math.sqrt(sum(c * c for c in axis))
            if n < 1e-6:
                continue
            axis = _local(fk.root, tuple(c / n for c in axis))
            for ang in _TILTS:
                prev = fk.tilt.get(limb, (0.0, 0.0, 0.0))
                out.append(_with(key, who, replace(fk, tilt={**fk.tilt, limb: tuple(prev[i] + axis[i] * ang for i in range(3))})))
    if a_who != b_who:
        n = pen.normal                                                    # move uke away from tori
        r = key.uke.root
        step = pen.depth_m + 0.01
        if r.z is None:
            h = math.hypot(n[0], n[1]) or 1.0
            out.append(_with(key, "uke", replace(key.uke, root=replace(r, x=r.x + n[0] / h * step, y=r.y + n[1] / h * step))))
        else:
            out.append(_with(key, "uke", replace(key.uke, root=replace(r, x=r.x + n[0] * step, y=r.y + n[1] * step,
                                                                       z=r.z + n[2] * step))))
    return out


def _push_uke(key: Key, found) -> List[Key]:
    """Move uke as one rigid body along the summed push of every overlap with tori (deepest weighs most)."""
    between = [x for a, b, x in found if a != b]
    if not between:
        return []
    v = [sum(x.normal[i] * x.depth_m for x in between) for i in range(3)]
    n = math.sqrt(sum(c * c for c in v))
    if n < 1e-9:
        return []
    r = key.uke.root
    out = []
    for scale in (0.5, 1.0, 1.5):
        step = (max(x.depth_m for x in between) + 0.01) * scale
        d = [c / n * step for c in v]
        if r.z is None:
            h = math.hypot(d[0], d[1])
            if h < 1e-6:
                continue
            root = replace(r, x=r.x + d[0] * step / h, y=r.y + d[1] * step / h)
        else:
            root = replace(r, x=r.x + d[0], y=r.y + d[1], z=r.z + d[2])
        out.append(_with(key, "uke", replace(key.uke, root=root)))
    return out


def _step(points: Points, key: Key, s: SolvedKey, cost: float, prev: Optional[SolvedKey] = None, ahead: Ahead = None,
          home: Optional[Key] = None):
    """Every candidate move for the five deepest overlaps: [(cost, key, solved)], cheapest first."""
    tried = []
    found = [o for o in overlaps(key, s) if o[2].depth_m > AIM_M]
    for cand in _push_uke(key, found):
        cs = solve_key(points, cand)
        tried.append((_cost(cand, cs, prev, ahead, home), cand, cs))
    for a_who, b_who, pen in found[:5]:
        for cand in _candidates(key, s, a_who, b_who, pen):
            cs = solve_key(points, cand)
            tried.append((_cost(cand, cs, prev, ahead, home), cand, cs))
    return sorted(tried, key=lambda x: x[0])


def clear_key(points: Points, key: Key, rounds: int = 20, lookahead: bool = True,
              prev: Optional[SolvedKey] = None, ahead: Ahead = None) -> Tuple[Key, SolvedKey]:
    """Greedy search: take the candidate move that lowers the total cost most; when none does (two overlaps trading
    against each other), try two moves in a row from the five most promising. Stops when nothing goes in."""
    home = key
    s = solve_key(points, key)
    cost = _cost(key, s, prev, ahead, home)
    for _ in range(rounds):
        if not any(o[2].depth_m > AIM_M for o in overlaps(key, s)):
            break
        tried = _step(points, key, s, cost, prev, ahead, home)
        if tried and tried[0][0] < cost - 1e-4:
            cost, key, s = tried[0]
            continue
        if not lookahead:
            break
        best = None
        for _, k1, s1 in tried[:5]:
            nxt = _step(points, k1, s1, cost, prev, ahead, home)
            if nxt and nxt[0][0] < cost - 1e-4 and (best is None or nxt[0][0] < best[0]):
                best = nxt[0]
        if best is None:
            break
        cost, key, s = best
    return key, s


_CACHE: Dict[Tuple, object] = {}


def _fingerprint(points: Points) -> Tuple:
    return tuple(sorted((b, h, e) for b, (h, e) in points.items()))


def _cached(kind: str, points: Points, clip: ThrowClip, make):
    """The search is deterministic but slow (seconds per key): keep one result per clip and rest skeleton."""
    k = (kind, clip.throw_id, id(clip), _fingerprint(points))     # id: a clip edited at run time is a new object
    if k not in _CACHE:
        _CACHE[k] = make()
    return _CACHE[k]


def clear_clip_keys(points: Points, clip: ThrowClip) -> List[Tuple[Key, SolvedKey]]:
    return list(_cached("keys", points, clip, lambda: [clear_key(points, k) for k in clip.keys]))


# --------------------------------------------------------------------------------------------------------------------
# In-betweens: every frame between two keys, with the grips re-solved so the hands stay on the gi.

def _dot4(a: Quat, b: Quat) -> float:
    return sum(x * y for x, y in zip(a, b))


def slerp(a: Quat, b: Quat, t: float) -> Quat:
    """Spherical interpolation along the shorter arc."""
    d = _dot4(a, b)
    if d < 0.0:
        b, d = tuple(-c for c in b), -d
    if d > 0.9995:
        q = tuple(x + (y - x) * t for x, y in zip(a, b))
    else:
        th = math.acos(d)
        s = math.sin(th)
        wa, wb = math.sin((1 - t) * th) / s, math.sin(t * th) / s
        q = tuple(wa * x + wb * y for x, y in zip(a, b))
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


def ease(t: float) -> float:
    """Smoothstep: zero speed at both keys (ASSUMED timing; real throws are not symmetric)."""
    return t * t * (3.0 - 2.0 * t)


def _between(points: Points, a: FighterKey, pa: Pose, wa: Points, b: FighterKey, pb: Pose, wb: Points, t: float) -> FighterKey:
    ra, rb = pose_rotations(points, pa), pose_rotations(points, pb)
    rot = {n: slerp(ra.get(n, IDENTITY), rb.get(n, IDENTITY), t) for n in set(ra) | set(rb)}
    body = apply_hand_pose(points, rot)
    named = {ALIASES.get(k, k) for k in (*pa, *pb)} | set(_FLAT)
    pose = {n: _unit(_sub(body[n][1], body[n][0])) for n in named}
    pel = [wa["pelvis"][0][i] + (wb["pelvis"][0][i] - wa["pelvis"][0][i]) * t for i in range(3)]
    grounded = a.root.z is None and b.root.z is None                       # standing or lying in both keys: stay on the mat
    clear = a.root.clearance + (b.root.clearance - a.root.clearance) * t
    root = Root(pel[0], pel[1], z=None if grounded else pel[2], clearance=clear, quat=slerp(a.root.rotation(), b.root.rotation(), t))
    reach = {k: tgt for k, tgt in a.reach.items() if b.reach.get(k) == tgt}  # only a grip held on the same point stays on
    swing = {k: a.swing.get(k, 0.0) + (b.swing.get(k, 0.0) - a.swing.get(k, 0.0)) * t for k in reach}
    return FighterKey(pose, root, reach, swing)


def _carry(built: FighterKey, fixed: FighterKey, new: FighterKey, w: float) -> FighterKey:
    """Apply to ``new`` the swing, tilt and root shift that the clearance added to ``built`` one frame earlier, scaled
    by ``w`` so that they fade out by the next key (which carries its own fixes)."""
    swing = {**new.swing, **{k: new.swing.get(k, 0.0) + w * (fixed.swing.get(k, 0.0) - built.swing.get(k, 0.0))
                             for k in fixed.swing if k in new.reach}}
    tilt = {**new.tilt, **{k: tuple(w * c for c in rv) for k, rv in fixed.tilt.items()}}
    r, rb, rf = new.root, built.root, fixed.root
    root = replace(r, x=r.x + w * (rf.x - rb.x), y=r.y + w * (rf.y - rb.y),
                   z=None if r.z is None or rf.z is None or rb.z is None else r.z + w * (rf.z - rb.z))
    reach = {k: v for k, v in new.reach.items() if k in fixed.reach}        # a hold let go stays let go
    return replace(new, swing=swing, tilt=tilt, root=root, reach=reach)


def solve_frames(points: Points, clip: ThrowClip) -> List[SolvedKey]:
    """Every frame of the clip: keys as solved, in-betweens eased and with held grips re-solved by IK."""
    return list(_cached("frames", points, clip, lambda: _solve_frames(points, clip)))


def _solve_frames(points: Points, clip: ThrowClip) -> List[SolvedKey]:
    cleared = clear_clip_keys(points, clip)
    keys = [s for _, s in cleared]
    out: List[SolvedKey] = []
    for (ka, sa), (kb, sb) in zip(cleared, cleared[1:]):
        out.append(sa)
        carry: Optional[Tuple[Key, Key]] = None                 # (as built, as cleared) of the last in-between
        for f in range(ka.frame + 1, kb.frame):
            t = ease((f - ka.frame) / (kb.frame - ka.frame))
            tori = _between(points, ka.tori, sa.tori_pose, sa.tori, kb.tori, sb.tori_pose, sb.tori, t)
            uke = _between(points, ka.uke, sa.uke_pose, sa.uke, kb.uke, sb.uke_pose, sb.uke, t)
            built = Key(f, ka.phase, tori, uke)
            if carry is not None:                                 # start from the fixes found one frame earlier
                w = (kb.frame - f) / (kb.frame - f + 1.0)
                tori, uke = _carry(carry[0].tori, carry[1].tori, tori, w), _carry(carry[0].uke, carry[1].uke, uke, w)
            s = solve_key(points, Key(f, ka.phase, tori, uke))
            prev = out[-1]
            ahead = (sb, kb.frame - f)
            if (any(o[2].depth_m > AIM_M for o in overlaps(Key(f, ka.phase, tori, uke), s))
                    or _jump(s, prev) > 0.0 or _jump(s, *ahead) > 0.0):
                k2, s = clear_key(points, Key(f, ka.phase, tori, uke), rounds=14, lookahead=True, prev=prev, ahead=ahead)
                tori, uke = k2.tori, k2.uke
            carry = (built, Key(f, ka.phase, tori, uke))
            lift = [max(0.0, -min(min(h[2], e[2]) for h, e in w.values())) for w in (s.tori, s.uke)]
            if any(lift):                                  # an airborne in-between must not dip under the mat
                tori, uke = (fk if d == 0.0 else replace(fk, root=replace(fk.root, z=fk.root.z + d)) for fk, d in zip((tori, uke), lift))
                s = solve_key(points, Key(f, ka.phase, tori, uke))
            out.append(s)
    out.append(keys[-1])
    return out


def frame_table(points: Points, clip: ThrowClip) -> List[Dict[str, object]]:
    """Per frame and fighter: object transform (world = R * rest point + location) and rest-frame bone rotations.

    This is what a bake keys: the armature object carries the root, its pose bones carry the rotations."""
    rows: List[Dict[str, object]] = []
    for s in solve_frames(points, clip):
        row: Dict[str, object] = {"frame": s.frame, "phase": s.phase}
        for who, world, pose in (("tori", s.tori, s.tori_pose), ("uke", s.uke, s.uke_pose)):
            rot = pose_rotations(points, pose)
            body = apply_hand_pose(points, rot)
            # recover the root from three body points: pelvis head, and the hip line and spine of the posed body
            q = _frame_from(body, world)
            loc = _sub(world["pelvis"][0], quat_rotate(q, body["pelvis"][0]))
            row[who] = {"location": loc, "rotation_wxyz": q, "bones_wxyz": rot}
        rows.append(row)
    return rows


def _frame_from(body: Points, world: Points) -> Quat:
    """Rotation taking the body-frame pelvis frame to the world one (both from the hip joints and the pelvis axis)."""
    def basis(pts: Points) -> Tuple[Vec, Vec, Vec]:
        x = _unit(_sub(pts["thigh_l"][0], pts["thigh_r"][0]))
        up = _sub(pts["pelvis"][1], pts["pelvis"][0])
        z = _unit(_sub(up, tuple(c * sum(u * w for u, w in zip(up, x)) for c in x)))
        return x, _cross(z, x), z
    a, b = basis(body), basis(world)
    m = [[sum(b[k][i] * a[k][j] for k in range(3)) for j in range(3)] for i in range(3)]   # R = B * A^T
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = (0.25 * s, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = ((m[2][1] - m[1][2]) / s, 0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s)
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


# --------------------------------------------------------------------------------------------------------------------
# Pose vocabulary (all PLACEHOLDER). Right-handed tori; "r" and "l" are each fighter's own right and left.

def _pose(*parts: Pose) -> Dict[str, Vec]:
    out: Dict[str, Vec] = {}
    for p in parts:
        out.update(p)
    return out


def _legs(l_thigh: Vec, l_calf: Vec, r_thigh: Vec, r_calf: Vec) -> Dict[str, Vec]:
    return {"thigh_l": l_thigh, "calf_l": l_calf, "thigh_r": r_thigh, "calf_r": r_calf}


STAND: Pose = _pose(
    {"trunk": v(0.06, 0, 1), "neck": v(0.05, 0, 1)},
    _legs(v(0.12, 0.14, -1), v(-0.12, 0, -1), v(0.12, -0.14, -1), v(-0.12, 0, -1)),
    {"upperarm_l": v(0.45, 0.2, -1), "lowerarm_l": v(1, -0.1, 0.2), "upperarm_r": v(0.45, -0.2, -1),
     "lowerarm_r": v(1, 0.1, 0.2)})
CROUCH: Pose = _pose(STAND, {"trunk": v(0.2, 0, 1)},
                     _legs(v(0.55, 0.22, -0.85), v(-0.5, 0, -0.9), v(0.55, -0.22, -0.85), v(-0.5, 0, -0.9)))
LYING: Pose = _pose(   # on the back after ushiro / mae-mawari ukemi: chin tucked, legs up, one arm slapping the mat
    {"trunk": v(0, 0, 1), "chest": v(0.12, 0, 1), "neck": v(0.6, 0, 1)},
    _legs(v(0.55, 0.2, -0.8), v(-0.2, 0, -1), v(0.7, -0.2, -0.7), v(-0.3, 0, -1)),
    {"upperarm_l": v(-0.05, 0.75, -0.65), "lowerarm_l": v(-0.05, 0.75, -0.65), "upperarm_r": v(0.5, -0.3, -0.6),
     "lowerarm_r": v(0.9, -0.1, 0.1)})
REST: Pose = _pose(LYING, {"neck": v(0.15, 0, 1)},
                   _legs(v(0.25, 0.15, -1), v(-0.25, 0, -1), v(0.1, -0.15, -1), v(-0.05, 0, -1)),
                   {"upperarm_l": v(-0.02, 0.5, -0.85), "lowerarm_l": v(-0.02, 0.4, -0.9)})

# Tori's hands on uke. Sleeve: uke's right forearm near the elbow. Lapel: the left of uke's chest, at the front.
SLEEVE = Target("lowerarm_r", 0.12, pole=(0.3, 0.0, -1.0))
LAPEL = Target("spine_03", 0.55, (0.09, 0.11, 0.0), pole=(-0.3, 0.0, -1.0))
GRIPS: Mapping[str, Target] = {"arm_l": SLEEVE, "arm_r": LAPEL}
#: Uke holds tori the same way (both right-handed): the first key only; after that uke's arms are posed.
UKE_GRIPS: Mapping[str, Target] = GRIPS

UKE_Y = -0.78                                         # uke's starting distance in front of tori, ASSUMED
FACING = (("z", 180.0),)                              # uke faces tori


def _uke(pose: Pose, x: float = 0.0, y: float = UKE_Y, turns: Tuple[Tuple[str, float], ...] = (), z: Optional[float] = None,
         clearance: float = 0.0, reach: Optional[Mapping[str, Target]] = None) -> FighterKey:
    return FighterKey(pose, Root(x, y, FACING + turns, z, clearance), reach or {})


def _tori(pose: Pose, x: float = 0.0, y: float = 0.0, turns: Tuple[Tuple[str, float], ...] = (),
          reach: Optional[Mapping[str, Target]] = GRIPS) -> FighterKey:
    return FighterKey(pose, Root(x, y, turns), reach or {})


_START = Key(0, "kumikata", _tori(STAND), _uke(STAND, reach=UKE_GRIPS))
_ARMS_UP: Pose = {"upperarm_l": v(0.8, 0.3, -0.3), "lowerarm_l": v(1, 0, 0.3), "upperarm_r": v(0.8, -0.3, -0.3),
                  "lowerarm_r": v(1, 0, 0.3)}
_HOLD_SLEEVE: Mapping[str, Target] = {"arm_l": SLEEVE}
LOW_HOLD: Pose = _pose(CROUCH, {"trunk": v(1, 0, 0.5), "neck": v(1, 0, 0.3)})      # tori supports uke's sleeve on landing
UPRIGHT: Pose = _pose(STAND, {"upperarm_l": v(0.1, 0.15, -1), "lowerarm_l": v(0.3, 0, -1), "upperarm_r": v(0.1, -0.15, -1),
                             "lowerarm_r": v(0.3, 0, -1)})


def _o_soto_gari() -> ThrowClip:
    lean = _pose(STAND, {"trunk": v(-0.3, -0.18, 1)})                      # uke on the right heel, back-right corner
    step = _pose(STAND, {"trunk": v(0.3, 0, 1)}, _legs(v(0.1, 0.1, -1), v(-0.1, 0, -1), v(0.95, -0.05, -0.45), v(0.7, 0, -0.7)))
    reap = _pose(STAND, {"trunk": v(0.9, 0, 0.6), "neck": v(0.9, 0, 0.5)},
                 _legs(v(0.05, 0.1, -1), v(-0.05, 0, -1), v(-0.75, -0.05, -0.7), v(-0.9, 0, -0.35)))
    uke_reaped = _pose(STAND, _ARMS_UP, {"trunk": v(-0.1, 0, 1), "neck": v(0.5, 0, 1)},
                       _legs(v(0.2, 0.15, -1), v(-0.3, 0, -1), v(0.95, -0.15, 0.1), v(0.8, 0, -0.5)))
    uke_air = _pose(LYING, _legs(v(0.8, 0.2, -0.4), v(0.3, 0, -1), v(0.95, -0.2, 0.2), v(0.6, 0, -0.8)))
    over = _pose(STAND, {"trunk": v(0.75, 0, 0.7)}, _legs(v(0.3, 0.15, -1), v(-0.3, 0, -1), v(-0.25, -0.15, -1), v(-0.25, 0, -1)))
    return ThrowClip("o_soto_gari", (
        _START,
        Key(12, "kuzushi", _tori(_pose(STAND, {"trunk": v(0.2, 0, 1)}), 0.20, -0.22), _uke(lean, reach=UKE_GRIPS)),
        Key(22, "tsukuri", _tori(step, 0.27, -0.50), _uke(lean, turns=(("x", 10.0),))),
        Key(32, "kake", _tori(reap, 0.27, -0.56), _uke(uke_reaped, turns=(("x", 38.0),))),
        Key(40, "fall", _tori(over, 0.27, -0.56, reach=_HOLD_SLEEVE), _uke(uke_air, y=-1.05, turns=(("x", 72.0),), z=0.45)),
        Key(48, "landing", _tori(LOW_HOLD, 0.30, -0.80, reach=_HOLD_SLEEVE), _uke(LYING, y=-1.30, turns=(("x", 90.0),), clearance=0.11)),
        Key(70, "end", _tori(UPRIGHT, 0.30, -0.80, reach=None),
            _uke(REST, y=-1.30, turns=(("x", 90.0),), clearance=0.11)),
    ))


def _o_uchi_gari() -> ThrowClip:
    lean = _pose(STAND, {"trunk": v(-0.25, 0.15, 1)}, _legs(v(0.1, 0.3, -1), v(-0.1, 0, -1), v(0.1, -0.3, -1), v(-0.1, 0, -1)))
    enter = _pose(CROUCH, {"trunk": v(0.3, 0, 1)}, _legs(v(0.3, 0.1, -1), v(-0.3, 0, -1), v(0.8, 0.05, -0.6), v(0.4, 0.3, -0.85)))
    hook = Target("calf_l", 0.45, pole=(-0.6, 0.6, -0.2))
    drive = _pose(STAND, {"trunk": v(0.8, 0, 0.7), "neck": v(0.8, 0, 0.6)}, _legs(v(-0.25, 0.1, -1), v(-0.45, 0, -0.9), v(0.6, 0, -0.8), v(0.2, 0, -1)))
    uke_hooked = _pose(STAND, _ARMS_UP, {"trunk": v(-0.15, 0, 1), "neck": v(0.5, 0, 1)},
                       _legs(v(0.9, 0.35, -0.1), v(0.6, 0.1, -0.7), v(0.15, -0.2, -1), v(-0.3, 0, -1)))
    uke_air = _pose(LYING, _legs(v(0.9, 0.4, 0.1), v(0.5, 0, -0.8), v(0.7, -0.25, -0.5), v(0.2, 0, -1)))
    return ThrowClip("o_uchi_gari", (
        _START,
        Key(12, "kuzushi", _tori(_pose(STAND, {"trunk": v(0.25, 0, 1)}), 0.0, -0.20), _uke(lean, reach=UKE_GRIPS)),
        Key(22, "tsukuri", _tori(enter, -0.03, -0.38), _uke(lean, turns=(("x", 8.0),))),
        Key(32, "kake", _tori(drive, -0.03, -0.48, reach={**GRIPS, "leg_r": hook}), _uke(uke_hooked, turns=(("x", 35.0),))),
        Key(40, "fall", _tori(drive, -0.03, -0.62, reach={**_HOLD_SLEEVE, "leg_r": hook}),   # the reap follows through
            _uke(uke_air, y=-1.10, turns=(("x", 72.0),), z=0.45)),
        Key(48, "landing", _tori(LOW_HOLD, -0.03, -0.85, reach=_HOLD_SLEEVE), _uke(LYING, y=-1.36, turns=(("x", 90.0),), clearance=0.11)),
        Key(70, "end", _tori(UPRIGHT, -0.03, -0.85, reach=None),
            _uke(REST, y=-1.36, turns=(("x", 90.0),), clearance=0.11)),
    ))


def _hip_throw(throw_id: str, right_arm: Target, load_z: float, bend: Vec, depth: Pose,
               slide: Optional[Pose] = None) -> ThrowClip:
    """O-goshi and seoi-nage share the shape: turn the back to uke, load, bend forward, uke rotates over.

    ``slide``: the right arm is still sliding round uke at tsukuri (posed, not gripping) and takes its grip at kake."""
    back = (("z", 180.0),)                                                 # tori has turned to face the same way as uke
    hands = {"arm_l": Target("lowerarm_r", 0.55, pole=(0.3, 0.0, -1.0)), "arm_r": right_arm}   # hikite pulls the sleeve to the front
    tip = _pose(STAND, {"trunk": v(0.3, 0, 1)}, _legs(v(-0.15, 0.12, -1), v(-0.4, 0, -0.9), v(-0.15, -0.12, -1), v(-0.4, 0, -0.9)))
    loaded = _pose(STAND, _ARMS_UP, {"trunk": v(0, 0, 1), "chest": v(0.3, 0, 1), "neck": v(0.3, 0, 1)},
                   _legs(v(-0.25, 0.15, -1), v(-0.5, 0, -0.8), v(-0.1, -0.15, -1), v(-0.4, 0, -0.9)))
    tucked = _pose(LYING, _legs(v(0.85, 0.2, -0.3), v(0.1, 0, -1), v(0.95, -0.2, 0.0), v(0.3, 0, -1)))
    throw = _pose(STAND, {"trunk": bend, "neck": bend}, _legs(v(0.25, 0.2, -1), v(-0.25, 0, -1), v(0.25, -0.2, -1), v(-0.25, 0, -1)))
    ty = UKE_Y + 0.31                     # tori's hips against uke's: the two pelvis capsules (0.14 m) touch, not overlap
    # hikite has uke's right arm: it is drawn forward over tori's right shoulder, never through tori's back
    drawn = {"arm_r": Target("clavicle_r", 0.9, (0.0, 0.0, 0.10), pole=(-0.5, 0.3, 0.5))}
    return ThrowClip(throw_id, (
        _START,
        Key(12, "kuzushi", _tori(_pose(STAND, {"trunk": v(-0.05, 0, 1)}), 0.0, -0.08), _uke(tip, turns=(("x", -8.0),), reach=UKE_GRIPS)),
        Key(26, "tsukuri", _tori(_pose(depth, slide or {}), -0.04, ty, back, {"arm_l": hands["arm_l"]} if slide else hands),
            _uke(tip, turns=(("x", -14.0),), reach=drawn)),
        Key(31, "tsukuri", _tori(_pose(depth), -0.04, ty, back, hands),                  # breakdown: uke lifted, not yet over
            _uke(_pose(tip, {"trunk": v(0.35, 0, 1)}), x=-0.10, y=UKE_Y - 0.10, turns=(("x", -35.0),), z=load_z + 0.05,
                 reach=drawn)),
        Key(36, "kake", _tori(throw, -0.04, ty, back, hands),
            _uke(loaded, x=-0.25, y=ty - 0.06, turns=(("x", -80.0),), z=load_z + 0.06, reach=drawn)),
        Key(40, "kake", _tori(throw, -0.04, ty, back, hands),                            # breakdown: uke goes over, high
            _uke(_pose(tucked, _ARMS_UP), x=-0.35, y=ty + 0.12, turns=(("x", -125.0),), z=load_z + 0.35)),
        Key(44, "fall", _tori(throw, -0.04, ty, back, hands), _uke(tucked, x=-0.10, y=ty + 0.45, turns=(("x", -170.0),), z=max(load_z - 0.30, 0.92))),
        Key(58, "landing", _tori(LOW_HOLD, -0.04, ty + 0.25, back, _HOLD_SLEEVE), _uke(LYING, x=-0.10, y=ty + 0.95, turns=(("x", 90.0),), clearance=0.11)),
        Key(80, "end", _tori(UPRIGHT, -0.04, ty + 0.25, back, None), _uke(REST, x=-0.10, y=ty + 0.95, turns=(("x", 90.0),), clearance=0.11)),
    ))


def _de_ashi_barai() -> ThrowClip:
    stepping = _pose(STAND, _legs(v(0.1, 0.14, -1), v(-0.1, 0, -1), v(0.4, -0.1, -0.95), v(-0.05, 0, -1)))   # right foot advancing
    sweep = Target("calf_r", 0.97, (-0.03, 0.0, 0.0), pole=(0.5, 0.6, 0.0))    # sole on the outside of the ankle
    tori_sweep = _pose(STAND, {"trunk": v(0.0, -0.12, 1)}, _legs(v(0.3, -0.3, -1), v(0, -0.3, -1), v(0.05, -0.1, -1), v(-0.05, 0, -1)))
    swept = _pose(STAND, _ARMS_UP, {"trunk": v(0, -0.1, 1)}, _legs(v(0.05, 0.1, -1), v(-0.05, 0, -1), v(0.35, 0.55, -0.75), v(0.2, 0.5, -0.8)))
    air = _pose(STAND, {"neck": v(0.2, 0.5, 1)}, _legs(v(0.3, 0.2, -1), v(-0.2, 0, -1), v(0.5, 0.5, -0.7), v(0.1, 0.3, -1)),
                {"upperarm_r": v(0.3, -0.8, -0.5), "lowerarm_r": v(0.3, -0.8, -0.5), "upperarm_l": v(0.7, 0.2, -0.5), "lowerarm_l": v(1, 0, 0.2)})
    side = _pose(air, _legs(v(0.45, 0.2, -0.9), v(-0.35, 0, -0.9), v(0.25, 0.0, -1), v(-0.2, 0, -1)),   # yoko ukemi, on the right side
                 {"neck": v(0.1, 0.45, 1), "upperarm_r": v(0.6, 0, -0.8), "lowerarm_r": v(0.6, 0, -0.8),          # right arm slaps the mat
                  "upperarm_l": v(0.5, 0.3, -0.7), "lowerarm_l": v(0.9, 0.2, -0.1)})
    pull = _pose(STAND, {"trunk": v(0.35, -0.2, 1)})
    return ThrowClip("de_ashi_barai", (
        _START,
        Key(10, "kuzushi", _tori(STAND, 0.0, 0.04), _uke(stepping, y=UKE_Y + 0.12, reach=UKE_GRIPS)),
        Key(18, "tsukuri", _tori(tori_sweep, 0.05, -0.08, reach={**GRIPS, "leg_l": sweep}), _uke(stepping, y=UKE_Y + 0.12)),
        Key(26, "kake", _tori(tori_sweep, 0.10, -0.12), _uke(swept, y=UKE_Y + 0.12, turns=(("y", 28.0),))),
        Key(33, "fall", _tori(pull, 0.15, -0.15, reach=_HOLD_SLEEVE), _uke(air, x=0.22, y=UKE_Y + 0.12, turns=(("y", 62.0),), z=0.72)),
        Key(39, "landing", _tori(LOW_HOLD, 0.30, -0.30, reach=_HOLD_SLEEVE), _uke(side, x=0.38, y=UKE_Y + 0.12, turns=(("y", 90.0),), clearance=0.10)),
        Key(61, "end", _tori(UPRIGHT, 0.30, -0.30, reach=None),
            _uke(side, x=0.38, y=UKE_Y + 0.12, turns=(("y", 90.0),), clearance=0.10)),
    ))


JUDO_CLIPS: Dict[str, ThrowClip] = {c.throw_id: c for c in (
    _hip_throw("seoi_nage", Target("upperarm_r", 0.2, (0.0, 0.0, -0.03), pole=(-0.2, 0.3, -1.0)), 1.22, v(1, 0, 0.15),
               _pose(CROUCH, {"trunk": v(0.45, 0, 1)}, _legs(v(0.7, 0.22, -0.7), v(-0.65, 0, -0.75), v(0.7, -0.22, -0.7), v(-0.65, 0, -0.75)))),
    _hip_throw("o_goshi", Target("spine_01", 0.6, (-0.08, -0.12, 0.0), pole=(-0.8, -0.3, 0.0)), 1.05, v(0.9, 0, 0.5), CROUCH,
               {"upperarm_r": v(-0.35, -0.9, -0.15), "lowerarm_r": v(-0.9, 0.45, 0.0)}),       # arm sliding round uke's back
    _o_soto_gari(), _o_uchi_gari(), _de_ashi_barai(),
)}

PROBE_BONES = ("pelvis", "head", "hand_l", "hand_r", "foot_l", "foot_r")


def clip_reference(points: Points) -> Dict[str, object]:
    """Engine-neutral table: per key and fighter, the root transform, rest-frame bone rotations and probe positions."""
    def fighter(fk: FighterKey, pose: Pose, world: Points) -> Dict[str, object]:
        rot = pose_rotations(points, pose)
        return {"root": {"pelvis": [round(c, 5) for c in world["pelvis"][0]], "rotation_wxyz": [round(c, 6) for c in fk.root.rotation()]},
                "rotations_wxyz": {b: [round(c, 6) for c in q] for b, q in sorted(rot.items())},
                "probes": {b: [round(c, 5) for c in world[b][0]] for b in PROBE_BONES}}
    clips: Dict[str, object] = {}
    for c in JUDO_CLIPS.values():
        keys = []
        for key, s in zip(c.keys, solve_clip(points, c)):
            keys.append({"frame": s.frame, "phase": s.phase, "tori": fighter(key.tori, s.tori_pose, s.tori),
                         "uke": fighter(key.uke, s.uke_pose, s.uke), "miss_m": {k: round(d, 4) for k, d in sorted(s.miss_m.items())}})
        clips[c.throw_id] = {"throw": c.throw_id, "frames": c.frames, "seconds": round(c.frames / FPS, 4), "keys": keys}
    return {"schema": SCHEMA, "fps": FPS, "provenance": PROVENANCE.value, "probe_bones": list(PROBE_BONES), "clips": clips}
