"""Game rig tab: CE-GAME-v1 armature, IK/FK, hand controls, hand pose library (RIG-GAME-001 step 3).

* *Build game rig* creates ``<armature>_GAME`` from the canonical armature: the 66 game bones (DEF), the IK/FK
  layer of :data:`GAME_CONTROL_RIG` (same builder as the canonical rig), and one ``MCH-anat_<BONE>`` helper per
  canonical node parented to the game bone that carries it. Every canonical bone then copies its helper
  (``COPY_TRANSFORMS`` in world space, constraint ``CE_GAME``) and the canonical bones are hidden: animate the
  game rig, the anatomical layer follows (simulation, trauma, sockets keep working).
* Hand controls per side (``Object.ce_hand_L`` / ``ce_hand_R``): curl per finger, spread, thumb opposition, palm
  cup. Changing a slider poses the hand through :func:`hand_pose_rotations` (domain), so Blender and Python
  produce the same fingers. Keyframes go on the bone rotations (*Hand pose* operator with *Insert keys*).
* Pose library (*Hand pose*) and weapon grips (*Weapon grip*: the weapon picks its grip pose).
"""

from __future__ import annotations

from typing import Dict, Tuple

import bpy
from mathutils import Quaternion, Vector

from character_engine.domain.character import load_canonical_bones
from character_engine.domain.gameplay import WEAPONS
from character_engine.domain.rigging import (
    GAME_BONES,
    GAME_CONTROL_RIG,
    HAND_POSES,
    RIG_ID,
    HandPose,
    canonical_to_game,
    game_bone_points,
    grip_pose_for_weapon,
    hand_pose_rotations,
)
from character_engine.domain.rigging.hand_poses import FINGERS

from . import build

HAND_PROPS = tuple(f"curl_{f}" for f in FINGERS) + ("spread", "opposition", "cup")
_POSE_ITEMS = [(n, n, "") for n in HAND_POSES]
_WEAPON_ITEMS = [(w, WEAPONS[w].name, "") for w in WEAPONS]
_SIDE_ITEMS = [("L", "Left", ""), ("R", "Right", "")]


def game_armature_name(canonical_name: str) -> str:
    return f"{canonical_name}_GAME"


def _canonical_dicts(arm) -> list:
    known = {b["canonical_name"] for b in load_canonical_bones()[0]}
    mw = arm.matrix_world
    return [{"canonical_name": b.name, "head": tuple(mw @ b.head_local), "tail": tuple(mw @ b.tail_local)}
            for b in arm.data.bones if b.name in known]


def rest_points(game_arm) -> Dict[str, Tuple[Vector, Vector]]:
    """Game bone rest (head, tail) in armature space, as plain tuples for the domain."""
    return {b.name: (tuple(b.head_local), tuple(b.tail_local)) for b in game_arm.data.bones if b.get("ce_game_bone")}


def build_game_rig(context, canonical_arm):
    """Create (or rebuild) the game armature driving ``canonical_arm``; returns the game armature."""
    name = game_armature_name(canonical_arm.name)
    old = bpy.data.objects.get(name)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    points = game_bone_points(_canonical_dicts(canonical_arm), load_canonical_bones()[0])
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    for coll in canonical_arm.users_collection or (context.scene.collection,):
        coll.objects.link(arm)
    arm["ce_character"] = canonical_arm.get("ce_character", canonical_arm.name)
    arm["ce_role"] = "game_armature"
    arm["ce_game_rig"] = RIG_ID
    arm["ce_drives"] = canonical_arm.name
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    for g in GAME_BONES:
        e = eb.new(g.name)
        e.head, e.tail = Vector(points[g.name][0]), Vector(points[g.name][1])
        e.parent = eb[g.parent] if g.parent else None
    to_local = arm.matrix_world.inverted() @ canonical_arm.matrix_world
    carriers = canonical_to_game()
    for cb in canonical_arm.data.bones:
        if cb.name not in carriers:
            continue
        h = eb.new(f"MCH-anat_{cb.name}")
        m = to_local @ cb.matrix_local
        h.head, h.tail = m.translation, m.translation + m.to_3x3().col[1] * max(cb.length, 1e-3)
        h.matrix = m          # roll too (the setter ignores zero-length bones, so head/tail first): copy = identity
        h.length = max(cb.length, 1e-3)
        h.use_deform = False
        h.parent = eb[carriers[cb.name]]
    bpy.ops.object.mode_set(mode="OBJECT")
    for bone in arm_data.bones:
        if bone.name.startswith("MCH-anat_"):
            build.assign_bone_layer(arm_data, bone, "MCH")
        else:
            bone["ce_game_bone"] = True
            build.assign_bone_layer(arm_data, bone, "DEF")
    build.build_control_rig(context, arm, GAME_CONTROL_RIG)
    _refine_pole_angles(context, arm)
    for pb in canonical_arm.pose.bones:
        helper = f"MCH-anat_{pb.name}"
        if helper not in arm_data.bones:
            continue
        for c in [c for c in pb.constraints if c.name == "CE_GAME"]:
            pb.constraints.remove(c)
        c = pb.constraints.new("COPY_TRANSFORMS")
        c.name = "CE_GAME"
        c.target, c.subtarget = arm, helper
        c.owner_space = c.target_space = "WORLD"
    canonical_arm["ce_driven_by"] = arm.name
    # Hide the bones, not the object: Blender does not evaluate hidden objects, so a hidden canonical
    # armature would stop following the game rig.
    for bone in canonical_arm.data.bones:
        bone.hide = True
    context.view_layer.update()
    return arm


def _refine_pole_angles(context, arm) -> None:
    """The shared builder picks pole angles on a 15 degree grid; refine them so IK at rest is a no-op."""
    import math

    for pb in arm.pose.bones:
        for ik in [c for c in pb.constraints if c.type == "IK"]:
            chain = [pb]
            while len(chain) < ik.chain_count and chain[-1].parent is not None:
                chain.append(chain[-1].parent)
            names = [b.name for b in chain]

            def err(angle, ik=ik, names=names):
                ik.pole_angle = angle
                context.view_layer.update()
                return sum((arm.pose.bones[n].head - arm.data.bones[n].head_local).length
                           + (arm.pose.bones[n].tail - arm.data.bones[n].tail_local).length for n in names)

            best = ik.pole_angle
            for step in (math.radians(1.0), math.radians(0.05), math.radians(0.0025)):
                cands = [best + k * step for k in range(-20, 21)]
                best = min(cands, key=err)
            ik.pole_angle = best
    context.view_layer.update()


def apply_hand_controls(game_arm, side: str) -> None:
    """Pose the game hand bones of ``side`` ("L"/"R") from ``game_arm.ce_hand_<side>``."""
    ctl = getattr(game_arm, f"ce_hand_{side}")
    pose = HandPose("controls", {f: getattr(ctl, f"curl_{f}") for f in FINGERS}, spread=ctl.spread,
                    opposition=ctl.opposition, cup=ctl.cup)
    bones = game_arm.data.bones
    for bone, q in hand_pose_rotations(pose, rest_points(game_arm), side).items():
        rest = bones[bone].matrix_local.to_3x3().to_quaternion()
        pb = game_arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest.inverted() @ Quaternion(q) @ rest   # armature-frame rotation -> bone space


def set_hand_pose(game_arm, side: str, pose: HandPose, insert_keys: bool = False) -> None:
    ctl = getattr(game_arm, f"ce_hand_{side}")
    ctl["_ce_batch"] = True                                   # one pose evaluation for the whole set
    for f in FINGERS:
        setattr(ctl, f"curl_{f}", float(pose.curl.get(f, 0.0)))
    ctl.spread, ctl.opposition = pose.spread, pose.opposition
    ctl["_ce_batch"] = False
    ctl.cup = pose.cup                                        # triggers apply_hand_controls
    if insert_keys:
        frame = bpy.context.scene.frame_current
        for bone in hand_pose_rotations(pose, rest_points(game_arm), side):
            game_arm.pose.bones[bone].keyframe_insert("rotation_quaternion", frame=frame, group=bone)


def _on_hand_change(self, context) -> None:
    if self.get("_ce_batch"):
        return
    obj = self.id_data
    side = "L" if self.path_from_id() == "ce_hand_L" else "R"
    if obj is not None and obj.get("ce_game_rig") == RIG_ID:
        apply_hand_controls(obj, side)


def _unit_prop(name, lo=0.0):
    return bpy.props.FloatProperty(name=name, min=lo, max=1.0, default=0.0, update=_on_hand_change)


class CEHandControls(bpy.types.PropertyGroup):
    curl_thumb: _unit_prop("Thumb curl")
    curl_index: _unit_prop("Index curl")
    curl_middle: _unit_prop("Middle curl")
    curl_ring: _unit_prop("Ring curl")
    curl_pinky: _unit_prop("Little curl")
    spread: _unit_prop("Spread", lo=-1.0)
    opposition: _unit_prop("Thumb opposition")
    cup: _unit_prop("Palm cup")


def _game_arm(context):
    props = context.scene.character_engine
    return bpy.data.objects.get(game_armature_name(props.armature_name))


class CE_OT_build_game_rig(bpy.types.Operator):
    """Build the CE-GAME-v1 game rig (66 bones, IK/FK, hand controls) driving the canonical armature"""

    bl_idname = "character_engine.build_game_rig"
    bl_label = "Build game rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        canonical = bpy.data.objects.get(context.scene.character_engine.armature_name)
        if canonical is None or canonical.type != "ARMATURE":
            self.report({"ERROR"}, "generate a body first (no canonical armature)")
            return {"CANCELLED"}
        arm = build_game_rig(context, canonical)
        self.report({"INFO"}, f"{arm.name}: {sum(1 for b in arm.data.bones if b.get('ce_game_bone'))} game bones, "
                              f"{canonical.name} hidden and driven")
        return {"FINISHED"}


class CE_OT_hand_pose(bpy.types.Operator):
    """Put a hand of the game rig in a pose of the library"""

    bl_idname = "character_engine.hand_pose"
    bl_label = "Hand pose"
    bl_options = {"REGISTER", "UNDO"}

    pose: bpy.props.EnumProperty(name="Pose", items=_POSE_ITEMS)
    side: bpy.props.EnumProperty(name="Side", items=_SIDE_ITEMS, default="R")
    insert_keys: bpy.props.BoolProperty(name="Insert keys", default=False)

    def execute(self, context):
        arm = _game_arm(context)
        if arm is None:
            self.report({"ERROR"}, "build the game rig first")
            return {"CANCELLED"}
        set_hand_pose(arm, self.side, HAND_POSES[self.pose], self.insert_keys)
        return {"FINISHED"}


class CE_OT_weapon_grip(bpy.types.Operator):
    """Close a hand of the game rig on a weapon (the weapon picks its grip pose)"""

    bl_idname = "character_engine.weapon_grip"
    bl_label = "Weapon grip"
    bl_options = {"REGISTER", "UNDO"}

    weapon_id: bpy.props.EnumProperty(name="Weapon", items=_WEAPON_ITEMS)
    side: bpy.props.EnumProperty(name="Side", items=_SIDE_ITEMS, default="R")

    def execute(self, context):
        arm = _game_arm(context)
        if arm is None:
            self.report({"ERROR"}, "build the game rig first")
            return {"CANCELLED"}
        pose = grip_pose_for_weapon(self.weapon_id)
        set_hand_pose(arm, self.side, pose)
        self.report({"INFO"}, f"{self.weapon_id} -> {pose.name} ({self.side})")
        return {"FINISHED"}


class CE_PT_game_rig(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Engine"
    bl_label = "Game rig (CE-GAME-v1)"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        col = self.layout.column()
        col.operator(CE_OT_build_game_rig.bl_idname)
        arm = _game_arm(context)
        if arm is None:
            return
        for p in GAME_CONTROL_RIG.properties:
            col.prop(arm, f'["{p}"]', text=p)
        for side in ("L", "R"):
            box = col.box()
            box.label(text=f"Hand {side}")
            ctl = getattr(arm, f"ce_hand_{side}")
            for p in HAND_PROPS:
                box.prop(ctl, p)
            row = box.row()
            op = row.operator(CE_OT_hand_pose.bl_idname, text="Pose")
            op.side = side
            op = row.operator(CE_OT_weapon_grip.bl_idname, text="Grip")
            op.side = side


CLASSES = (CEHandControls, CE_OT_build_game_rig, CE_OT_hand_pose, CE_OT_weapon_grip, CE_PT_game_rig)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Object.ce_hand_L = bpy.props.PointerProperty(type=CEHandControls)
    bpy.types.Object.ce_hand_R = bpy.props.PointerProperty(type=CEHandControls)


def unregister() -> None:
    del bpy.types.Object.ce_hand_L
    del bpy.types.Object.ce_hand_R
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
