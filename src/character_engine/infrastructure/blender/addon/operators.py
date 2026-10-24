"""Operators exposed by the Character Engine panel."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

from character_engine.domain.animation import get_bone_map
from character_engine.domain.character import (
    CharacterParameters,
    build_character_bones,
    get_template,
    load_canonical_bones,
)
from character_engine.domain.rigging import HUMANOID_RIG

from . import _bootstrap, build


def _ce(context):
    return context.scene.character_engine


def _armature(context):
    props = _ce(context)
    obj = bpy.data.objects.get(props.armature_name)
    if obj is None or obj.type != "ARMATURE":
        obj = context.active_object if context.active_object and context.active_object.type == "ARMATURE" else None
    return obj


def _report_exc(op, exc):
    op.report({"ERROR"}, f"{type(exc).__name__}: {exc}")
    traceback.print_exc()
    return {"CANCELLED"}


class CE_OT_generate_body(bpy.types.Operator):
    """Build the canonical 208-node armature for the selected template, stature and pose"""

    bl_idname = "character_engine.generate_body"
    bl_label = "Generate body"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = _ce(context)
        try:
            template = get_template(props.template)
            if not template.available:
                self.report({"ERROR"}, f"{template.label}: {template.notes}")
                return {"CANCELLED"}
            params: CharacterParameters = template.params.with_(pose=props.pose)
            if not props.use_template_stature:
                params = params.with_(stature_m=props.stature_m)
            else:
                props.stature_m = params.stature_m
            bones, containers = load_canonical_bones()
            posed, report = build_character_bones(params, canonical_bones=bones)
            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            build.clear_character(context, props.armature_name)
            arm = build.build_armature(context, posed, containers, props.armature_name, meta={
                "ce_template": template.template_id, "ce_stature_m": params.stature_m, "ce_pose": params.pose,
                "ce_sex": params.sex.value, "ce_age_years": params.age_years,
                "ce_stature_provenance": template.stature_provenance.value,
                "ce_proportion_provenance": template.proportion_provenance.value,
                "ce_source_id": template.source_id, "ce_retarget_report": report,
            })
            self.report({"INFO"}, f"{template.label}: {len(arm.data.bones)} bones, {params.pose}, {params.stature_m:.3f} m")
            return {"FINISHED"}
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            return _report_exc(self, exc)


class CE_OT_generate_tissues(bpy.types.Operator):
    """Generate bone / tendon / muscle / skin layers for the active canonical armature"""

    bl_idname = "character_engine.generate_tissues"
    bl_label = "Generate tissues"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = _ce(context)
        arm = _armature(context)
        if arm is None:
            self.report({"ERROR"}, "No canonical armature: generate a body first")
            return {"CANCELLED"}
        try:
            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            for obj in list(bpy.data.objects):
                if obj.get("ce_character") == arm["ce_character"] and obj.get("ce_role") == "tissue":
                    bpy.data.objects.remove(obj, do_unlink=True)
            stature = float(arm.get("ce_stature_m", 1.80))
            population = "female_white" if arm.get("ce_sex") == "female" else "male_white"
            msgs = []
            if props.tissue_bones:
                _, fitted = build.build_bone_meshes(context, arm, stature, population, props.prefer_asset_meshes,
                                                    _bootstrap.repo_root())
                msgs.append(f"bones ({fitted} asset meshes fitted)")
            if props.tissue_muscles:
                _, _, n = build.build_muscle_meshes(context, arm, with_tendons=props.tissue_tendons)
                msgs.append(f"{n} muscles" + (" + tendons" if props.tissue_tendons else ""))
            if props.tissue_skin:
                build.build_skin_envelope(context, arm, props.skin_subdivisions)
                msgs.append("skin")
            self.report({"INFO"}, "Tissues: " + ", ".join(msgs))
            return {"FINISHED"}
        except Exception as exc:  # noqa: BLE001
            return _report_exc(self, exc)


class CE_OT_build_rig(bpy.types.Operator):
    """Add the IK/FK control layer (poles, switches, foot roll, breathing) to the canonical armature"""

    bl_idname = "character_engine.build_rig"
    bl_label = "Build IK/FK rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = _ce(context)
        arm = _armature(context)
        if arm is None:
            self.report({"ERROR"}, "No canonical armature")
            return {"CANCELLED"}
        if arm.get("ce_rig_id"):
            self.report({"WARNING"}, "Rig already built on this armature")
            return {"CANCELLED"}
        try:
            stats = build.build_control_rig(context, arm, HUMANOID_RIG, props.rig_ik_default, props.rig_foot_roll,
                                            props.breath_amplitude)
            self.report({"INFO"}, f"Rig: {stats['ik_chains']} IK chains, {stats['mch']} MCH, {stats['controls']} CTRL")
            return {"FINISHED"}
        except Exception as exc:  # noqa: BLE001
            return _report_exc(self, exc)


class CE_OT_set_ik_fk(bpy.types.Operator):
    """Set every FK/IK switch of the rig to the given value"""

    bl_idname = "character_engine.set_ik_fk"
    bl_label = "Set IK/FK"
    value: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    def execute(self, context):
        arm = _armature(context)
        if arm is None or not arm.get("ce_rig_id"):
            self.report({"ERROR"}, "No rigged canonical armature")
            return {"CANCELLED"}
        for chain in HUMANOID_RIG.ik_chains:
            if chain.fk_ik_property in arm:
                arm[chain.fk_ik_property] = self.value
        arm.update_tag()
        context.view_layer.update()
        return {"FINISHED"}


class CE_OT_import_mocap(bpy.types.Operator):
    """Import a BVH/FBX clip and retarget it onto the canonical armature through the selected bone map"""

    bl_idname = "character_engine.import_mocap"
    bl_label = "Import & retarget mocap"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = _ce(context)
        arm = _armature(context)
        if arm is None:
            self.report({"ERROR"}, "No canonical armature")
            return {"CANCELLED"}
        path = Path(bpy.path.abspath(props.bvh_path))
        if not path.exists():
            self.report({"ERROR"}, f"file not found: {path}")
            return {"CANCELLED"}
        try:
            bone_map = get_bone_map(props.bone_map)
            src = build.import_mocap(path, bone_map)
            src["ce_character"] = arm["ce_character"]
            build._link(context, src, f"{arm['ce_character']}_Mocap")
            stats = build.retarget_mocap(context, src, arm, bone_map)
            if props.mocap_bake:
                src.hide_set(True)
                src.hide_render = True
            self.report({"INFO"}, f"Mocap: {stats['mapped_bones']} bones, {stats['frames']} frames ({bone_map.label})")
            return {"FINISHED"}
        except Exception as exc:  # noqa: BLE001
            return _report_exc(self, exc)


class CE_OT_apply_wound(bpy.types.Operator):
    """Click on the character to inflict a wound; assessment uses the tissue-layer model"""

    bl_idname = "character_engine.apply_wound"
    bl_label = "Apply wound (click)"
    bl_options = {"REGISTER", "UNDO"}

    location: bpy.props.FloatVectorProperty(size=3, default=(0.0, 0.0, 0.0))
    use_location: bpy.props.BoolProperty(default=False)

    def invoke(self, context, event):
        region, rv3d = context.region, context.region_data
        if region is None or rv3d is None:
            return self.execute(context)
        coord = (event.mouse_region_x, event.mouse_region_y)
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        hit, loc, _n, _i, obj, _m = context.scene.ray_cast(context.view_layer.depsgraph, origin, direction)
        if not hit:
            self.report({"WARNING"}, "Nothing under the cursor")
            return {"CANCELLED"}
        self.location, self.use_location = loc, True
        return self.execute(context)

    def execute(self, context):
        props = _ce(context)
        arm = _armature(context)
        if arm is None:
            self.report({"ERROR"}, "No canonical armature")
            return {"CANCELLED"}
        try:
            if self.use_location:
                point = Vector(self.location)
            elif props.wound_bone and props.wound_bone in arm.data.bones:
                b = arm.data.bones[props.wound_bone]
                point = arm.matrix_world @ ((b.head_local + b.tail_local) / 2)
            else:
                point = context.scene.cursor.location.copy()
            bone = props.wound_bone if props.wound_bone in arm.data.bones else None
            a = build.apply_wound(context, arm, point, props.wound_type, props.wound_depth_mm / 1000.0,
                                  props.wound_width_mm / 1000.0, props.wound_energy_j or None, bone)
            props.last_wound_report = (
                f"{a.wound.bone_hit} [{a.region.value}] {a.wound.wound_type.value}: "
                f"{'>'.join(layer.value for layer in a.layers_breached)} | AIS {a.severity.value} "
                f"| lethality {a.lethality:.2f} | bleed {a.bleeding_rate:.1f}"
                f"{' | FRACTURE' if a.fracture else ''}{' | LETHAL RISK' if a.is_lethal else ''}"
            )
            self.report({"INFO"}, props.last_wound_report)
            return {"FINISHED"}
        except Exception as exc:  # noqa: BLE001
            return _report_exc(self, exc)


class CE_OT_clear_wounds(bpy.types.Operator):
    bl_idname = "character_engine.clear_wounds"
    bl_label = "Clear wounds"

    def execute(self, context):
        arm = _armature(context)
        n = 0
        for obj in list(bpy.data.objects):
            if obj.get("ce_role") == "wound" and (arm is None or obj.get("ce_character") == arm.get("ce_character")):
                bpy.data.objects.remove(obj, do_unlink=True)
                n += 1
        _ce(context).last_wound_report = ""
        self.report({"INFO"}, f"removed {n} wounds")
        return {"FINISHED"}


class CE_OT_export_gltf(bpy.types.Operator):
    """Export the canonical skeleton (current template/pose) to glTF through the pure-Python exporter"""

    bl_idname = "character_engine.export_gltf"
    bl_label = "Export canonical GLB"

    def execute(self, context):
        props = _ce(context)
        try:
            from character_engine.export.gltf import export_canonical_skeleton

            out = Path(bpy.path.abspath(props.export_path))
            if not out.is_absolute():
                out = _bootstrap.repo_root() / out
            out.parent.mkdir(parents=True, exist_ok=True)
            stature = None if props.use_template_stature else props.stature_m
            path = export_canonical_skeleton(out, pose=props.pose, template_id=props.template, stature_m=stature)
            self.report({"INFO"}, f"GLB written: {path}")
            return {"FINISHED"}
        except Exception as exc:  # noqa: BLE001
            return _report_exc(self, exc)


class CE_OT_export_scene_gltf(bpy.types.Operator):
    """Export the whole character (armature + tissues + animation) with Blender's glTF exporter"""

    bl_idname = "character_engine.export_scene_gltf"
    bl_label = "Export scene GLB"

    def execute(self, context):
        props = _ce(context)
        arm = _armature(context)
        if arm is None:
            self.report({"ERROR"}, "No canonical armature")
            return {"CANCELLED"}
        out = Path(bpy.path.abspath(props.export_path))
        if not out.is_absolute():
            out = _bootstrap.repo_root() / out
        out = out.with_name(out.stem + "_scene.glb")
        out.parent.mkdir(parents=True, exist_ok=True)
        for obj in bpy.data.objects:
            obj.select_set(obj.get("ce_character") == arm["ce_character"] and obj.get("ce_role") != "mocap_source"
                           and obj.visible_get())
        kwargs = dict(filepath=str(out), use_selection=True, export_format="GLB", export_animations=True,
                      export_skins=True, export_yup=True)
        try:
            bpy.ops.export_scene.gltf(**kwargs, export_animation_mode="ACTIVE_ACTIONS")
        except TypeError:   # older exporter without export_animation_mode
            bpy.ops.export_scene.gltf(**kwargs)
        self.report({"INFO"}, f"scene GLB written: {out}")
        return {"FINISHED"}


class CE_OT_dump_report(bpy.types.Operator):
    """Print a JSON summary of the character (bones, tissues, wounds, rig) to the console"""

    bl_idname = "character_engine.dump_report"
    bl_label = "Print character report"

    def execute(self, context):
        arm = _armature(context)
        if arm is None:
            self.report({"ERROR"}, "No canonical armature")
            return {"CANCELLED"}
        name = arm["ce_character"]
        objs = [o for o in bpy.data.objects if o.get("ce_character") == name]
        report = {
            "armature": arm.name, "bones": len(arm.data.bones),
            "canonical_bones": sum(1 for b in arm.data.bones if b.get("ce_canonical")),
            "template": arm.get("ce_template"), "stature_m": arm.get("ce_stature_m"), "pose": arm.get("ce_pose"),
            "rig": arm.get("ce_rig_id"), "mocap": arm.get("ce_mocap_source"),
            "tissues": {o["ce_layer"]: len(o.data.vertices) for o in objs if o.get("ce_role") == "tissue"},
            "wounds": [json.loads(o["ce_report"]) for o in objs if o.get("ce_role") == "wound"],
        }
        print(json.dumps(report, indent=2))
        self.report({"INFO"}, f"{report['bones']} bones, {len(report['tissues'])} tissue layers, {len(report['wounds'])} wounds")
        return {"FINISHED"}


CLASSES = (
    CE_OT_generate_body, CE_OT_generate_tissues, CE_OT_build_rig, CE_OT_set_ik_fk, CE_OT_import_mocap,
    CE_OT_apply_wound, CE_OT_clear_wounds, CE_OT_export_gltf, CE_OT_export_scene_gltf, CE_OT_dump_report,
)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
