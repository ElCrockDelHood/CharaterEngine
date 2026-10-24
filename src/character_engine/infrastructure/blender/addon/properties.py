"""Scene-level settings edited by the Character Engine panel."""

from __future__ import annotations

import bpy

from character_engine.domain.animation import BONE_MAPS
from character_engine.domain.character import TEMPLATES
from character_engine.domain.gameplay import GAMEPLAY_STYLES
from character_engine.domain.trauma import WoundType


def _template_items(self, context):
    items = []
    for tid, t in TEMPLATES.items():
        label = t.label if t.available else f"{t.label} — unavailable"
        items.append((tid, label, t.notes))
    return items


def _bone_map_items(self, context):
    return [(k, v.label, v.notes) for k, v in BONE_MAPS.items()]


def _style_items(self, context):
    return [(k, str(v["label"]), "") for k, v in GAMEPLAY_STYLES.items()]


_WOUND_ITEMS = [(w.value, w.value.capitalize(), "") for w in WoundType]


class CEProperties(bpy.types.PropertyGroup):
    # --- body ---
    template: bpy.props.EnumProperty(name="Template", items=_template_items)
    stature_m: bpy.props.FloatProperty(name="Stature (m)", default=1.80, min=0.4, max=2.6, precision=3)
    use_template_stature: bpy.props.BoolProperty(name="Use template stature", default=True)
    pose: bpy.props.EnumProperty(name="Rest pose", default="tpose",
                                 items=[("tpose", "T-pose", ""), ("apose", "A-pose", ""), ("anatomical", "Anatomical", "")])
    armature_name: bpy.props.StringProperty(name="Armature", default="CE_Skeleton")
    # --- tissues ---
    tissue_bones: bpy.props.BoolProperty(name="Bone meshes", default=True)
    tissue_tendons: bpy.props.BoolProperty(name="Tendons", default=True)
    tissue_muscles: bpy.props.BoolProperty(name="Muscles", default=True)
    tissue_skin: bpy.props.BoolProperty(name="Skin envelope", default=True)
    prefer_asset_meshes: bpy.props.BoolProperty(
        name="Use realistic asset meshes when available", default=True,
        description="Fit meshes from assets/anatomy/meshes/<BONE>.glb instead of proxies")
    skin_subdivisions: bpy.props.IntProperty(name="Skin subdivisions", default=2, min=0, max=4)
    # --- rig ---
    rig_ik_default: bpy.props.FloatProperty(name="IK influence", default=1.0, min=0.0, max=1.0)
    rig_foot_roll: bpy.props.BoolProperty(name="Foot roll", default=True)
    breath_amplitude: bpy.props.FloatProperty(name="Breath amplitude", default=0.0, min=0.0, max=1.0)
    # --- mocap ---
    bone_map: bpy.props.EnumProperty(name="Bone map", items=_bone_map_items)
    bvh_path: bpy.props.StringProperty(name="BVH / FBX file", subtype="FILE_PATH")
    mocap_bake: bpy.props.BoolProperty(name="Bake to action", default=True)
    # --- wounds ---
    wound_type: bpy.props.EnumProperty(name="Wound type", items=_WOUND_ITEMS, default="stab")
    wound_depth_mm: bpy.props.FloatProperty(name="Depth (mm)", default=30.0, min=0.0, max=400.0)
    wound_width_mm: bpy.props.FloatProperty(name="Width (mm)", default=10.0, min=0.0, max=300.0)
    wound_energy_j: bpy.props.FloatProperty(name="Energy (J)", default=150.0, min=0.0, max=5000.0)
    wound_bone: bpy.props.StringProperty(name="Bone (optional)", default="")
    last_wound_report: bpy.props.StringProperty(name="Last wound", default="")
    # --- export / runtime ---
    export_path: bpy.props.StringProperty(name="GLB path", subtype="FILE_PATH", default="//builds/gltf/character.glb")
    gameplay_style: bpy.props.EnumProperty(name="Gameplay style", items=_style_items)
    runtime_target: bpy.props.EnumProperty(name="Runtime", default="upbge",
                                           items=[("upbge", "UPBGE", ""), ("godot", "Godot 4", "")])


def register() -> None:
    bpy.utils.register_class(CEProperties)
    bpy.types.Scene.character_engine = bpy.props.PointerProperty(type=CEProperties)


def unregister() -> None:
    del bpy.types.Scene.character_engine
    bpy.utils.unregister_class(CEProperties)
