"""bpy adapter: foot locking on a retarget-baked canonical action (domain: ``domain/animation/foot_lock.py``).

Run after ``build.retarget_mocap`` on a **root-motion** clip. For every frame where a foot is in contact the
ankle (``TALUS`` head) is moved so the contact pivot (heel or ball) stays on its ground anchor; FEMUR and TIBIA are rotated with a two-bone IK
(knee kept in its bending plane) and TALUS keeps its world orientation, so the foot and toes do not tilt.
The new rotations are keyed over the retarget keys of those three bones.
"""

from __future__ import annotations

from typing import Dict, Optional

import bpy
from mathutils import Matrix, Vector

from character_engine.domain.animation import clip_qa
from character_engine.domain.animation import foot_lock as lock_domain

LEGS = {s: (f"FEMUR_{s}", f"TIBIA_{s}", f"TALUS_{s}") for s in ("L", "R")}
# contact pivots (Decision 54 foot: both at z = 0 in the rest pose): heel and ball (MTP 3)
PIVOTS = {s: (f"CALCANEUS_{s}", f"TOE_PHALANX_PROXIMAL_3_{s}") for s in ("L", "R")}


def _about(point: Vector, rot) -> Matrix:
    return Matrix.Translation(point) @ rot.to_matrix().to_4x4() @ Matrix.Translation(-point)


def _basis(bone, arm_mat: Matrix, parent_arm_mat: Optional[Matrix]):
    """Pose-basis rotation for an armature-space pose matrix (same formula as retarget_mocap)."""
    if bone.parent is None:
        return (bone.matrix_local.inverted() @ arm_mat).to_quaternion()
    rest_rel = bone.parent.matrix_local.inverted() @ bone.matrix_local
    return (rest_rel.inverted() @ parent_arm_mat.inverted() @ arm_mat).to_quaternion()


def _key(pb, q, frame: int) -> None:
    if pb.rotation_quaternion.dot(q) < 0.0:   # keep quaternion sign continuous with the retarget keys
        q = -q
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = q
    pb.keyframe_insert("rotation_quaternion", frame=frame)


def lock_feet(context, arm, settings: lock_domain.LockSettings = lock_domain.DEFAULT_LOCK,
              loop: bool = False) -> Dict[str, object]:
    """Key IK-locked legs over the active action. ``loop``: contacts cut by the first / last frame are merged
    (shifted by the hierarchy root's displacement over the clip)."""
    scene = context.scene
    action = arm.animation_data.action if arm.animation_data else None
    if action is None:
        raise RuntimeError("armature has no action to lock")
    legs = {s: names for s, names in LEGS.items()
            if all(n in arm.pose.bones for n in names + PIVOTS[s])}
    if not legs:
        return {"locked_frames": 0, "unreached_frames": 0, "legs": 0}
    f0, f1 = (int(round(v)) for v in action.frame_range)
    frames = list(range(f0, f1 + 1))
    mw = arm.matrix_world
    inv = mw.inverted()
    pts = {n: [] for s in legs for n in PIVOTS[s]}
    root = next(b for b in arm.pose.bones if b.parent is None)
    root_xy = []
    for f in frames:
        scene.frame_set(f)
        for n in pts:
            pts[n].append(tuple(mw @ arm.pose.bones[n].head))
        root_xy.append(tuple((mw @ root.head)[:2]))
    loop_shift = (root_xy[-1][0] - root_xy[0][0], root_xy[-1][1] - root_xy[0][1]) if loop else None
    rest_z = {n: (mw @ arm.data.bones[n].head_local).z for n in pts}
    offset = clip_qa.ground_offset({n: [p[2] for p in v] for n, v in pts.items()}, rest_z) or 0.0
    plans = {s: lock_domain.plan_locks({n: pts[n] for n in PIVOTS[s]}, rest_z, offset, len(frames), settings,
                                    loop_shift)
             for s in legs}
    locked = unreached = 0
    pb = arm.pose.bones
    for i, f in enumerate(frames):
        active = [s for s in legs if plans[s][i] is not None]
        if not active:
            continue
        scene.frame_set(f)
        for s in active:
            fem, tib, tal = legs[s]
            hip = mw @ pb[fem].head
            knee = mw @ pb[tib].head
            ank = mw @ pb[tal].head
            target = lock_domain.locked_target(tuple(ank), plans[s][i])
            ik = lock_domain.two_bone_ik(tuple(hip), tuple(knee), tuple(ank), target)
            new_knee, new_ank = Vector(ik.knee), Vector(ik.ankle)
            r1 = (knee - hip).rotation_difference(new_knee - hip)
            fem_w = _about(hip, r1) @ (mw @ pb[fem].matrix)
            tib_w1 = _about(hip, r1) @ (mw @ pb[tib].matrix)
            ank1 = _about(hip, r1) @ ank
            r2 = (ank1 - new_knee).rotation_difference(new_ank - new_knee)
            tib_w = _about(new_knee, r2) @ tib_w1
            tal_w = (mw @ pb[tal].matrix).copy()
            tal_w.translation = new_ank
            fem_a, tib_a, tal_a = inv @ fem_w, inv @ tib_w, inv @ tal_w
            parent = pb[fem].parent.matrix if pb[fem].parent else None
            _key(pb[fem], _basis(pb[fem].bone, fem_a, parent), f)
            _key(pb[tib], _basis(pb[tib].bone, tib_a, fem_a), f)
            _key(pb[tal], _basis(pb[tal].bone, tal_a, tib_a), f)
            locked += 1
            unreached += 0 if ik.reached else 1
    scene.frame_set(f0)
    arm["ce_foot_lock"] = True
    return {"locked_frames": locked, "unreached_frames": unreached, "legs": len(legs)}
