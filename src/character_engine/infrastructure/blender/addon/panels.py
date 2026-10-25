"""N-panel UI: View3D > Sidebar > Character Engine."""

from __future__ import annotations

import bpy

from character_engine.domain.character import TEMPLATES
from character_engine.domain.gameplay import GAMEPLAY_STYLES
from character_engine.domain.rigging import HUMANOID_RIG

from .runtime_upbge import is_upbge


class _CEPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Engine"


class CE_PT_main(_CEPanel, bpy.types.Panel):
    bl_label = "Character Engine"
    bl_idname = "CE_PT_main"

    def draw(self, context):
        props = context.scene.character_engine
        col = self.layout.column()
        arm = bpy.data.objects.get(props.armature_name)
        if arm is not None and arm.type == "ARMATURE":
            col.label(text=f"{arm.name}: {len(arm.data.bones)} bones · {arm.get('ce_template', '?')} · "
                           f"{float(arm.get('ce_stature_m', 0.0)):.2f} m · {arm.get('ce_pose', '?')}", icon="ARMATURE_DATA")
        else:
            col.label(text="No canonical armature in scene", icon="INFO")
        col.prop(props, "armature_name")


class CE_PT_body(_CEPanel, bpy.types.Panel):
    bl_label = "Body"
    bl_parent_id = "CE_PT_main"

    def draw(self, context):
        props = context.scene.character_engine
        layout = self.layout
        layout.prop(props, "template")
        t = TEMPLATES.get(props.template)
        if t is not None:
            box = layout.box()
            box.label(text=f"stature: {t.stature_provenance.value} · proportions: {t.proportion_provenance.value}",
                      icon="INFO" if t.available else "ERROR")
            if not t.available:
                box.label(text="No canonical data yet — disabled", icon="CANCEL")
        row = layout.row()
        row.prop(props, "use_template_stature")
        sub = row.row()
        sub.enabled = not props.use_template_stature
        sub.prop(props, "stature_m")
        layout.prop(props, "pose")
        layout.operator("character_engine.generate_body", icon="OUTLINER_OB_ARMATURE")


class CE_PT_tissues(_CEPanel, bpy.types.Panel):
    bl_label = "Tissues (bone → tendon → muscle → skin)"
    bl_parent_id = "CE_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        props = context.scene.character_engine
        layout = self.layout
        row = layout.row(align=True)
        row.prop(props, "tissue_bones", toggle=True)
        row.prop(props, "tissue_tendons", toggle=True)
        row = layout.row(align=True)
        row.prop(props, "tissue_muscles", toggle=True)
        row.prop(props, "tissue_skin", toggle=True)
        layout.prop(props, "prefer_asset_meshes")
        layout.prop(props, "skin_subdivisions")
        layout.operator("character_engine.generate_tissues", icon="MESH_MONKEY")
        layout.label(text="Proxies are ESTIMATE; drop realistic meshes in assets/anatomy/meshes/", icon="INFO")


class CE_PT_rig(_CEPanel, bpy.types.Panel):
    bl_label = "Rig (IK / FK)"
    bl_parent_id = "CE_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        props = context.scene.character_engine
        layout = self.layout
        arm = bpy.data.objects.get(props.armature_name)
        rigged = arm is not None and arm.get("ce_rig_id")
        if not rigged:
            layout.prop(props, "rig_ik_default")
            layout.prop(props, "rig_foot_roll")
            layout.operator("character_engine.build_rig", icon="CONSTRAINT_BONE")
            return
        layout.label(text=f"rig: {arm['ce_rig_id']}", icon="CHECKMARK")
        row = layout.row(align=True)
        row.operator("character_engine.set_ik_fk", text="All IK").value = 1.0
        row.operator("character_engine.set_ik_fk", text="All FK").value = 0.0
        col = layout.column(align=True)
        for chain in HUMANOID_RIG.ik_chains:
            if chain.fk_ik_property in arm:
                col.prop(arm, f'["{chain.fk_ik_property}"]', text=chain.chain_id, slider=True)
        for prop in ("foot_roll_L", "foot_roll_R", "breath_amplitude", "breath_rate_hz"):
            if prop in arm:
                layout.prop(arm, f'["{prop}"]', text=prop.replace("_", " "), slider=True)


class CE_PT_mocap(_CEPanel, bpy.types.Panel):
    bl_label = "Mocap"
    bl_parent_id = "CE_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        props = context.scene.character_engine
        layout = self.layout
        layout.prop(props, "bone_map")
        layout.prop(props, "bvh_path")
        layout.prop(props, "mocap_action")
        layout.prop(props, "mocap_bake")
        layout.operator("character_engine.import_mocap", icon="ARMATURE_DATA")


class CE_PT_wounds(_CEPanel, bpy.types.Panel):
    bl_label = "Wounds / simulation"
    bl_parent_id = "CE_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        props = context.scene.character_engine
        layout = self.layout
        layout.prop(props, "wound_type")
        layout.prop(props, "wound_depth_mm")
        layout.prop(props, "wound_width_mm")
        layout.prop(props, "wound_energy_j")
        layout.prop(props, "wound_bone")
        row = layout.row(align=True)
        row.operator("character_engine.apply_wound", icon="RESTRICT_SELECT_OFF")
        row.operator("character_engine.clear_wounds", text="", icon="TRASH")
        if props.last_wound_report:
            box = layout.box()
            for chunk in props.last_wound_report.split(" | "):
                box.label(text=chunk)


class CE_PT_export(_CEPanel, bpy.types.Panel):
    bl_label = "Export"
    bl_parent_id = "CE_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        props = context.scene.character_engine
        layout = self.layout
        layout.prop(props, "export_path")
        layout.operator("character_engine.export_gltf", icon="EXPORT")
        layout.operator("character_engine.export_scene_gltf", icon="SCENE_DATA")
        layout.operator("character_engine.dump_report", icon="TEXT")
        layout.separator()
        layout.operator("character_engine.add_equipment_sockets", icon="BONE_DATA")
        layout.operator("character_engine.cinematic_fullbody", icon="CAMERA_DATA")
        layout.separator()
        layout.operator("character_engine.block_dummy", icon="MESH_CAPSULE")
        layout.operator("character_engine.normalize_mesh", icon="FULLSCREEN_EXIT")


class CE_PT_runtime(_CEPanel, bpy.types.Panel):
    bl_label = "Runtime (UPBGE / Godot)"
    bl_parent_id = "CE_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        props = context.scene.character_engine
        layout = self.layout
        layout.prop(props, "runtime_target", expand=True)
        layout.prop(props, "gameplay_style")
        style = GAMEPLAY_STYLES[props.gameplay_style]
        layout.label(text=f"{len(style['moves'])} moves · lock-on {'on' if style['lock_on'] else 'off'} · "
                          f"{style['frame_rate']} Hz", icon="INFO")
        if props.runtime_target == "upbge":
            layout.label(text="UPBGE detected" if is_upbge() else "Not running inside UPBGE",
                         icon="CHECKMARK" if is_upbge() else "ERROR")
            layout.operator("character_engine.setup_upbge_scene", icon="SCENE_DATA")
            layout.operator("character_engine.attach_runtime_logic", icon="CONSTRAINT")
            layout.operator("character_engine.launch_game", icon="PLAY")
        else:
            layout.operator("character_engine.open_godot_project", icon="FILE_FOLDER")
            layout.label(text="Godot dock: addons/character_engine (runtime/godot)", icon="INFO")


CLASSES = (CE_PT_main, CE_PT_body, CE_PT_tissues, CE_PT_rig, CE_PT_mocap, CE_PT_wounds, CE_PT_export, CE_PT_runtime)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
