"""bpy adapter: leg grounding on a retarget-baked canonical action (domain: ``domain/animation/leg_ground.py``).

Runs at the end of ``build.retarget_mocap`` while the source rig is still there. Per frame: the hierarchy root is
shifted vertically so the support ankle sits at the height the source asks for, then each leg is re-solved with the
two-bone IK of ``foot_lock`` (knee pointing like the source's knee, ``TALUS`` keeping its world orientation) so the
other ankle reaches its own height. The new root location and leg rotations are keyed over the retarget keys.
"""

from __future__ import annotations

from typing import Dict, Mapping

from mathutils import Vector

from character_engine.domain.animation import foot_lock as lock_domain
from character_engine.domain.animation import leg_ground as ground_domain

from .foot_lock import LEGS, _about, _basis, _key

MIN_POLE_M = 0.01       # ESTIMATE: a source knee closer than this to its hip-ankle line keeps the current plane


def ground_legs(context, src_arm, dst_arm, mapping: Mapping[str, str], scale: float, frame_start: int,
                frame_end: int) -> Dict[str, object]:
    """Key grounded legs over ``dst_arm``'s action. ``mapping``: canonical bone -> source bone."""
    legs = {s: names for s, names in LEGS.items()
            if all(n in dst_arm.pose.bones and n in mapping for n in names)}
    if len(legs) != 2:
        return {"grounded_frames": 0, "legs": len(legs)}
    scene = context.scene
    mw, smw = dst_arm.matrix_world, src_arm.matrix_world
    inv = mw.inverted()
    pb, spb = dst_arm.pose.bones, src_arm.pose.bones
    root = next(b for b in pb if b.parent is None)
    src_rest_z = {s: (smw @ src_arm.data.bones[mapping[legs[s][2]]].head_local).z for s in legs}
    dst_rest_z = {s: (mw @ dst_arm.data.bones[legs[s][2]].head_local).z for s in legs}
    shifts, unreached = [], 0
    for f in range(frame_start, frame_end + 1):
        scene.frame_set(f)
        src = {s: [smw @ spb[mapping[n]].head for n in legs[s]] for s in legs}
        dst_z = {s: (mw @ pb[legs[s][2]].head).z for s in legs}
        g = ground_domain.plan({s: src[s][2].z for s in legs}, src_rest_z, dst_z, dst_rest_z, scale)
        world = mw @ root.matrix
        world.translation += Vector((0.0, 0.0, g.root_dz))
        root.matrix = inv @ world
        root.keyframe_insert("location", frame=f)
        context.view_layer.update()
        shifts.append(g.root_dz)
        for s, (fem, tib, tal) in legs.items():
            hip, knee, ank = mw @ pb[fem].head, mw @ pb[tib].head, mw @ pb[tal].head
            target = ank + Vector((0.0, 0.0, g.foot(s)))
            pole = ground_domain.knee_pole(*src[s], tuple(hip))
            pole = pole if (Vector(pole) - hip).length >= MIN_POLE_M else None
            ik = lock_domain.two_bone_ik(tuple(hip), tuple(knee), tuple(ank), tuple(target), pole)
            new_knee, new_ank = Vector(ik.knee), Vector(ik.ankle)
            r1 = (knee - hip).rotation_difference(new_knee - hip)
            fem_w = _about(hip, r1) @ (mw @ pb[fem].matrix)
            tib_w1 = _about(hip, r1) @ (mw @ pb[tib].matrix)
            r2 = ((_about(hip, r1) @ ank) - new_knee).rotation_difference(new_ank - new_knee)
            tib_w = _about(new_knee, r2) @ tib_w1
            tal_w = (mw @ pb[tal].matrix).copy()
            tal_w.translation = new_ank
            fem_a, tib_a, tal_a = inv @ fem_w, inv @ tib_w, inv @ tal_w
            parent = pb[fem].parent.matrix if pb[fem].parent else None
            _key(pb[fem], _basis(pb[fem].bone, fem_a, parent), f)
            _key(pb[tib], _basis(pb[tib].bone, tib_a, fem_a), f)
            _key(pb[tal], _basis(pb[tal].bone, tal_a, tib_a), f)
            unreached += 0 if ik.reached else 1
    scene.frame_set(frame_start)
    dst_arm["ce_leg_ground"] = True
    return {"grounded_frames": len(shifts), "legs": 2, "unreached": unreached,
            "root_dz_m": [round(min(shifts), 4), round(max(shifts), 4)] if shifts else None}

