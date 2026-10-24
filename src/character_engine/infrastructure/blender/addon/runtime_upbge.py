"""Runtime tab: set up a UPBGE gameplay scene (Shenmue-style combat) or point to the Godot project.

UPBGE-specific API (``obj.game``, ``bpy.ops.logic.python_component_register``) is detected at
runtime so the same addon loads in vanilla Blender (the buttons then explain what is missing).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import bpy

from character_engine.domain.gameplay import GAMEPLAY_STYLES

from . import _bootstrap

COMPONENT_MODULE = "ce_combat"          # runtime/upbge/components/ce_combat.py
COMPONENT_CLASS = "CEFighter"


def is_upbge() -> bool:
    has_game = "game" in bpy.types.Object.bl_rna.properties
    return has_game and hasattr(bpy.ops, "logic") and hasattr(bpy.ops.logic, "python_component_register")


def _ensure_component_text(context) -> bool:
    """UPBGE resolves components from the .blend's text blocks or sys.path; copy the module in."""
    src = _bootstrap.repo_root() / "runtime" / "upbge" / "components" / f"{COMPONENT_MODULE}.py"
    if not src.exists():
        return False
    text = bpy.data.texts.get(f"{COMPONENT_MODULE}.py")
    if text is None:
        text = bpy.data.texts.new(f"{COMPONENT_MODULE}.py")
    text.clear()
    text.write(src.read_text(encoding="utf-8"))
    # Also copy the shared pure-Python combat module next to the .blend when it is saved.
    if bpy.data.filepath:
        dst_dir = Path(bpy.data.filepath).parent / "ce_runtime"
        dst_dir.mkdir(exist_ok=True)
        shutil.copy(src, dst_dir / f"{COMPONENT_MODULE}.py")
    return True


def _game_property(obj, name: str, value) -> None:
    """Create/overwrite a BGE game property (read by ``ce_combat.run`` at game start)."""
    prop = obj.game.properties.get(name)
    if prop is None:
        bpy.ops.object.game_property_new(type={bool: "BOOL", float: "FLOAT", int: "INT"}.get(type(value), "STRING"),
                                         name=name)
        prop = obj.game.properties[name]
    prop.value = value


def _wire_logic_bricks(obj) -> None:
    """Always(pulse) → Python controller (module ``ce_combat.run``). Works headless."""
    bpy.ops.logic.sensor_add(type="ALWAYS", name="CE_Always", object=obj.name)
    sensor = obj.game.sensors["CE_Always"]
    sensor.use_pulse_true_level = True
    bpy.ops.logic.controller_add(type="PYTHON", name="CE_Combat", object=obj.name)
    controller = obj.game.controllers["CE_Combat"]
    controller.mode = "MODULE"
    controller.module = f"{COMPONENT_MODULE}.run"
    sensor.link(controller)


def _attach_component(obj, name: str, style: str, is_player: bool) -> str:
    """Bind ``ce_combat`` to the object.

    UI: Python component (falls back to logic bricks). Background/headless: UPBGE 0.50's
    ``logic.*`` operators crash without a window, so only game properties are written and
    the binding is marked ``deferred`` — *Attach runtime logic* completes it in the UI.
    """
    for key, value in (("fighter_id", name), ("is_player", is_player), ("style", style),
                       ("stature_m", 1.80), ("move_speed", 2.0), ("ai_aggression", 0.02),
                       ("autoplay_frames", 0), ("report_path", "")):
        _game_property(obj, key, value)
    obj["ce_component"] = f"{COMPONENT_MODULE}.{COMPONENT_CLASS}"
    if bpy.app.background:
        return "deferred"
    try:
        bpy.ops.logic.python_component_register(component_name=f"{COMPONENT_MODULE}.{COMPONENT_CLASS}")
        comp = obj.game.components[-1]
        for arg in comp.properties:
            if arg.name in ("fighter_id", "is_player", "style"):
                arg.value = {"fighter_id": name, "is_player": is_player, "style": style}[arg.name]
        return "component"
    except Exception as exc:  # noqa: BLE001 - fall back to bricks
        obj["ce_component_error"] = str(exc)
    _wire_logic_bricks(obj)
    return "logic_bricks"


def _fighter(context, name: str, location, style: str, is_player: bool):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=1.8, location=(location[0], location[1], 0.9))
    obj = context.active_object
    obj.name = name
    obj["ce_role"] = "fighter"
    obj["ce_fighter_id"] = name
    obj["ce_gameplay_style"] = style
    obj["ce_is_player"] = is_player
    if is_upbge():
        g = obj.game
        g.physics_type = "CHARACTER"
        g.use_collision_bounds = True
        g.collision_bounds_type = "CAPSULE"
        obj["ce_logic_binding"] = _attach_component(obj, name, style, is_player)
    return obj


class CE_OT_setup_upbge_scene(bpy.types.Operator):
    """Create ground, camera, player and opponent with the CEFighter component (UPBGE)"""

    bl_idname = "character_engine.setup_upbge_scene"
    bl_label = "Set up UPBGE gameplay scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.character_engine
        style = props.gameplay_style
        if not GAMEPLAY_STYLES[style]["moves"]:
            self.report({"WARNING"}, f"{GAMEPLAY_STYLES[style]['label']} has no moves yet; using it as a stub")
        for obj in list(bpy.data.objects):
            if obj.get("ce_role") in ("fighter", "arena"):
                bpy.data.objects.remove(obj, do_unlink=True)
        bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0, 0, 0))
        ground = context.active_object
        ground.name = "CE_Arena"
        ground["ce_role"] = "arena"
        if is_upbge():
            ground.game.physics_type = "STATIC"
            ground.game.use_collision_bounds = True
        has_component = _ensure_component_text(context) if is_upbge() else False
        player = _fighter(context, "player", (0.0, 0.8, 0.0), style, True)
        _fighter(context, "opponent", (0.0, -0.8, 0.0), style, False)
        if not any(o.type == "CAMERA" for o in context.scene.objects):
            bpy.ops.object.camera_add(location=(4.0, 4.0, 2.2), rotation=(1.2, 0.0, 2.36))
            context.scene.camera = context.active_object
        arm = bpy.data.objects.get(props.armature_name)
        if arm is not None:
            player["ce_armature"] = arm.name
        context.scene["ce_gameplay_style"] = style
        if is_upbge():
            msg = "UPBGE scene ready" + ("" if has_component else " (component module not found in runtime/upbge/components)")
        else:
            msg = "Scene stubs created; open this file in UPBGE to attach the CEFighter component"
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class CE_OT_attach_runtime_logic(bpy.types.Operator):
    """Attach the CEFighter component / logic bricks to fighters whose binding is deferred (UI only)"""

    bl_idname = "character_engine.attach_runtime_logic"
    bl_label = "Attach runtime logic"

    @classmethod
    def poll(cls, context):
        return is_upbge() and not bpy.app.background

    def execute(self, context):
        _ensure_component_text(context)
        done = []
        for obj in bpy.data.objects:
            if obj.get("ce_role") == "fighter" and obj.get("ce_logic_binding") in (None, "deferred"):
                context.view_layer.objects.active = obj
                obj["ce_logic_binding"] = _attach_component(obj, obj["ce_fighter_id"], obj["ce_gameplay_style"],
                                                            bool(obj["ce_is_player"]))
                done.append(f"{obj.name}:{obj['ce_logic_binding']}")
        self.report({"INFO"}, "attached " + ", ".join(done) if done else "nothing to attach")
        return {"FINISHED"}


class CE_OT_launch_game(bpy.types.Operator):
    """Start the embedded game engine (UPBGE only)"""

    bl_idname = "character_engine.launch_game"
    bl_label = "Play (embedded)"

    @classmethod
    def poll(cls, context):
        return is_upbge() and hasattr(bpy.ops.view3d, "game_start")

    def execute(self, context):
        bpy.ops.view3d.game_start()
        return {"FINISHED"}


class CE_OT_open_godot_project(bpy.types.Operator):
    """Show where the Godot runtime lives and how to launch it"""

    bl_idname = "character_engine.open_godot_project"
    bl_label = "Godot project info"

    def execute(self, context):
        root = _bootstrap.repo_root()
        self.report({"INFO"}, f"Godot project: {root / 'runtime' / 'godot' / 'project.godot'} — "
                              "run scripts/godot_headless_tests.py or open it in Godot 4.7")
        return {"FINISHED"}


CLASSES = (CE_OT_setup_upbge_scene, CE_OT_attach_runtime_logic, CE_OT_launch_game, CE_OT_open_godot_project)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
