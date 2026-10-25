"""Headless end-to-end test of the Character Engine addon (runs inside Blender *or* UPBGE).

    blender -b --python runtime/blender/ce_addon_headless_test.py -- --engine blender \
        --report builds/tests/blender_addon_report.json --save builds/tests/blender_addon.blend

Exit code 0 = every check passed. The report JSON lists each check with PASS/FAIL and details.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

try:
    import bpy  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("run inside Blender/UPBGE: blender -b --python ...") from exc

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

RESULTS = []
T0 = time.time()


def check(name: str, fn):
    t = time.time()
    try:
        detail = fn()
        RESULTS.append({"check": name, "status": "PASS", "detail": detail, "seconds": round(time.time() - t, 2)})
        print(f"  PASS  {name}  {detail if detail is not None else ''}", flush=True)
    except Exception as exc:  # noqa: BLE001
        RESULTS.append({"check": name, "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}",
                        "trace": traceback.format_exc(), "seconds": round(time.time() - t, 2)})
        print(f"  FAIL  {name}  {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="blender")
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--save", type=Path, default=None)
    ap.add_argument("--bvh", type=Path, default=None)
    ap.add_argument("--skip-skin", action="store_true")
    ap.add_argument("--skip", default="", help="comma-separated check keywords to skip (debug)")
    return ap.parse_args(argv)


def skipped(args, keyword: str) -> bool:
    return keyword in [s.strip() for s in args.skip.split(",") if s.strip()]


# ----------------------------------------------------------------------------- addon load ---

def load_addon():
    src_addon = SRC / "character_engine" / "infrastructure" / "blender" / "addon"
    tmp = Path(tempfile.mkdtemp(prefix="ce_addon_"))
    shutil.copytree(src_addon, tmp / "character_engine_blender")
    sys.path.insert(0, str(tmp))
    import character_engine_blender  # type: ignore

    character_engine_blender.register()
    return character_engine_blender


def write_synthetic_bvh(path: Path, frames: int = 30) -> Path:
    """Mixamo-named T-pose skeleton (cm, Y-up) with the left arm swinging down."""
    def joint(name, offset, children, indent=1):
        pad = "  " * indent
        s = f"{pad}JOINT {name}\n{pad}{{\n{pad}  OFFSET {offset[0]} {offset[1]} {offset[2]}\n"
        s += f"{pad}  CHANNELS 3 Zrotation Xrotation Yrotation\n"
        if children:
            for c in children:
                s += joint(*c, indent=indent + 1)
        else:
            s += f"{pad}  End Site\n{pad}  {{\n{pad}    OFFSET 0 -10 0\n{pad}  }}\n"
        return s + f"{pad}}}\n"

    arm = lambda side, sx: (f"{side}Shoulder", (sx * 6, 15, 0), [  # noqa: E731
        (f"{side}Arm", (sx * 12, 0, 0), [(f"{side}ForeArm", (sx * 28, 0, 0), [(f"{side}Hand", (sx * 26, 0, 0), [])])])])
    leg = lambda side, sx: (f"{side}UpLeg", (sx * 9, -5, 0), [(f"{side}Leg", (0, -45, 0), [(f"{side}Foot", (0, -42, 0), [])])])  # noqa: E731
    tree = [("Spine", (0, 10, 0), [("Spine1", (0, 12, 0), [("Spine2", (0, 12, 0), [
        ("Neck", (0, 15, 0), [("Head", (0, 10, 0), [])]), arm("Left", 1), arm("Right", -1)])])]),
        leg("Left", 1), leg("Right", -1)]
    txt = "HIERARCHY\nROOT Hips\n{\n  OFFSET 0 0 0\n  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation\n"
    for c in tree:
        txt += joint(*c, indent=1)
    txt += "}\nMOTION\n"
    n_joints = 1 + 3 + 2 + 4 * 2 + 3 * 2
    txt += f"Frames: {frames}\nFrame Time: 0.0333333\n"
    for f in range(frames):
        vals = [0.0, 95.0, 0.0, 0.0, 0.0, 0.0]         # Hips: standing at 95 cm
        rest = [0.0] * (3 * (n_joints - 1))
        # LeftArm is the 9th joint in depth-first order (Hips, Spine, Spine1, Spine2, Neck, Head, LeftShoulder, LeftArm)
        left_arm_index = 7 - 1
        rest[left_arm_index * 3 + 0] = -70.0 * f / max(1, frames - 1)   # Z rotation: swing arm down
        txt += " ".join(f"{v:.4f}" for v in vals + rest) + "\n"
    path.write_text(txt, encoding="utf-8")
    return path


# ----------------------------------------------------------------------------- checks -------

def main(reset: bool = True) -> int:
    args = parse_args()
    mode = "background" if bpy.app.background else "UI"
    print(f"== Character Engine addon test ({args.engine}, Blender {bpy.app.version_string}, {mode}) ==", flush=True)
    if reset:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    ctx = bpy.context
    scene = ctx.scene

    addon = {}

    def _load():
        addon["mod"] = load_addon()
        assert hasattr(bpy.ops.character_engine, "generate_body")
        assert hasattr(scene, "character_engine")
        return f"registered {len(addon['mod'].operators.CLASSES)} operators"
    check("addon registers", _load)
    if not addon:
        return finish(args)

    props = scene.character_engine

    def _body():
        props.template = "human_male_adult"
        props.pose = "tpose"
        props.use_template_stature = True
        res = bpy.ops.character_engine.generate_body()
        assert res == {"FINISHED"}, res
        arm = bpy.data.objects[props.armature_name]
        assert len(arm.data.bones) == 208, len(arm.data.bones)
        names = {b.name for b in arm.data.bones}
        for req in ("ROOT_SKELETON", "CRANIUM", "SACRUM", "FEMUR_L", "PHALANX_DISTAL_5_R", "STAPES_L"):
            assert req in names, req
        zs = [(arm.matrix_world @ b.head_local).z for b in arm.data.bones] + [(arm.matrix_world @ b.tail_local).z for b in arm.data.bones]
        assert abs(max(zs) - 1.80) < 2e-3, max(zs)
        assert abs(min(zs)) < 2e-3, min(zs)
        hum = arm.data.bones["HUMERUS_L"]
        assert abs(hum.tail_local.z - hum.head_local.z) < 2e-3, "T-pose humerus not horizontal"
        assert hum.tail_local.x > hum.head_local.x + 0.25, "left arm must point to +X (Decision 17)"
        assert arm["ce_template"] == "human_male_adult" and arm["ce_pose"] == "tpose"
        return f"208 bones, vertex {max(zs):.3f} m"
    check("generate body (male 1.80 T-pose)", _body)

    def _female():
        props.template = "human_female_adult"
        props.use_template_stature = False
        props.stature_m = 1.65
        assert bpy.ops.character_engine.generate_body() == {"FINISHED"}
        arm = bpy.data.objects[props.armature_name]
        top = max(max(b.head_local.z, b.tail_local.z) for b in arm.data.bones)
        assert abs(top - 1.65) < 2e-3, top
        assert arm["ce_sex"] == "female"
        return f"vertex {top:.3f} m"
    if not skipped(args, "bodies"):
        check("generate body (female 1.65 custom stature)", _female)

    def _child():
        props.template = "human_child_5y"
        props.use_template_stature = True
        assert bpy.ops.character_engine.generate_body() == {"FINISHED"}
        arm = bpy.data.objects[props.armature_name]
        top = max(max(b.head_local.z, b.tail_local.z) for b in arm.data.bones)
        assert abs(top - 1.10) < 2e-3, top
        assert arm["ce_proportion_provenance"] == "placeholder"
        return f"vertex {top:.3f} m, proportions flagged PLACEHOLDER"
    if not skipped(args, "bodies"):
        check("generate body (child 5y, PLACEHOLDER proportions)", _child)

    def _horse():
        props.template = "horse_adult"
        try:
            res = bpy.ops.character_engine.generate_body()
        except RuntimeError as exc:      # background mode turns report({'ERROR'}) into an exception
            assert "No canonical equine" in str(exc), exc
            res = {"CANCELLED"}
        assert res == {"CANCELLED"}, res
        assert props.armature_name not in bpy.data.objects or bpy.data.objects[props.armature_name]["ce_template"] != "horse_adult"
        return "refused (no canonical equine data)"
    if not skipped(args, "bodies"):
        check("animal template refuses without data", _horse)

    def _male_again():
        props.template = "human_male_adult"
        props.use_template_stature = True
        props.pose = "tpose"
        assert bpy.ops.character_engine.generate_body() == {"FINISHED"}
        return "rebuilt male 1.80"
    if not skipped(args, "bodies"):
        check("rebuild male base", _male_again)

    def _tissues():
        props.tissue_bones = props.tissue_muscles = props.tissue_tendons = True
        props.tissue_skin = not args.skip_skin
        props.skin_subdivisions = 1
        res = bpy.ops.character_engine.generate_tissues()
        assert res == {"FINISHED"}, res
        arm = bpy.data.objects[props.armature_name]
        bones = bpy.data.objects[f"{arm.name}_Bones"]
        muscles = bpy.data.objects[f"{arm.name}_Muscles"]
        tendons = bpy.data.objects[f"{arm.name}_Tendons"]
        assert len(bones.vertex_groups) >= 150, len(bones.vertex_groups)
        assert muscles["ce_muscle_count"] == 50, muscles["ce_muscle_count"]
        assert len(muscles.data.vertices) > 1000 and len(tendons.data.vertices) > 500
        assert any(m.type == "ARMATURE" and m.object == arm for m in bones.modifiers)
        # femur proxy extent == Trotter (1970) maximum length for 1.80 m
        vg = bones.vertex_groups["FEMUR_L"]
        b = arm.data.bones["FEMUR_L"]
        axis = (b.tail_local - b.head_local).normalized()
        proj = [v.co.dot(axis) for v in bones.data.vertices if any(g.group == vg.index for g in v.groups)]
        L = max(proj) - min(proj)
        assert abs(L - 0.4983) < 3e-3, L
        detail = f"bone groups {len(bones.vertex_groups)}, muscles 50, femur proxy {L:.4f} m"
        if props.tissue_skin:
            skin = bpy.data.objects[f"{arm.name}_Skin"]
            assert [m.type for m in skin.modifiers] == ["ARMATURE"], [m.type for m in skin.modifiers]
            assert len(skin.data.vertices) > 2000 and len(skin.data.polygons) > 2000, len(skin.data.vertices)
            assert len(skin.vertex_groups) > 20
            detail += f", skin {len(skin.data.vertices)} verts / {len(skin.data.polygons)} faces (baked)"
        return detail
    check("generate tissues (bones/tendons/muscles/skin)", _tissues)

    def _rig():
        props.rig_ik_default = 1.0
        props.rig_foot_roll = True
        res = bpy.ops.character_engine.build_rig()
        assert res == {"FINISHED"}, res
        arm = bpy.data.objects[props.armature_name]
        assert arm["ce_rig_id"] == "humanoid_ce_v1"
        for n in ("MCH-ik_HUMERUS_L", "MCH-ik_RADIUS_L", "MCH-ik_target_arm_L", "MCH-pole_arm_L",
                  "CTRL-hand_ik.L", "CTRL-foot_ik.R", "MCH-ik_FEMUR_R", "CTRL-root", "CTRL-breath"):
            assert n in arm.data.bones, n
        ik = [c for c in arm.pose.bones["MCH-ik_RADIUS_L"].constraints if c.type == "IK"]
        assert ik and ik[0].pole_subtarget == "MCH-pole_arm_L" and ik[0].chain_count == 2
        ct = [c for c in arm.pose.bones["HUMERUS_L"].constraints if c.type == "COPY_TRANSFORMS"]
        assert ct and ct[0].subtarget == "MCH-ik_HUMERUS_L"
        for prop in ("arm_ik_L", "leg_ik_R", "foot_roll_L", "breath_amplitude"):
            assert prop in arm, prop
        layers = set(addon["mod"].build.bone_layer_names(arm.data))   # collections (4.x) or layers (3.6)
        assert {"DEF", "MCH", "CTRL"} <= layers, layers
        assert arm.data.bones["HUMERUS_L"]["ce_layer"] == "DEF" and arm.data.bones["CTRL-root"]["ce_layer"] == "CTRL"
        return f"{len(arm.data.bones)} bones incl. MCH/CTRL, layers {sorted(layers)}"
    check("build IK/FK rig", _rig)

    def _ik_switch():
        arm = bpy.data.objects[props.armature_name]
        ctx.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="POSE")
        hand = arm.pose.bones["CTRL-hand_ik.L"]
        hum = arm.pose.bones["HUMERUS_L"]

        def switch(value):
            arm["arm_ik_L"] = value
            arm.update_tag()
            scene.frame_set(scene.frame_current)

        switch(0.0)                                   # pure FK = true rest
        rest_tail = (arm.matrix_world @ hum.tail).copy()
        switch(1.0)                                   # IK at rest must be a no-op (pole angle auto-tuned)
        ik_rest_dev = ((arm.matrix_world @ hum.tail) - rest_tail).length
        hand.location.y -= 0.25
        hand.location.z -= 0.15
        switch(1.0)
        moved_ik = ((arm.matrix_world @ hum.tail) - rest_tail).length
        switch(0.0)
        moved_fk = ((arm.matrix_world @ hum.tail) - rest_tail).length
        hand.location = (0, 0, 0)
        switch(1.0)
        bpy.ops.object.mode_set(mode="OBJECT")
        assert ik_rest_dev < 0.02, f"IK at rest deviates {ik_rest_dev:.4f} m"
        assert moved_ik > 0.02, f"IK did not move humerus ({moved_ik:.4f})"
        assert moved_fk < 1e-4, f"FK should ignore IK target ({moved_fk:.4f})"
        return f"IK rest deviation {ik_rest_dev * 1000:.1f} mm, IK displacement {moved_ik:.3f} m, FK {moved_fk:.4f} m"
    if not skipped(args, "ik"):
        check("IK/FK switch drives humerus", _ik_switch)

    def _breath():
        arm = bpy.data.objects[props.armature_name]
        arm["breath_amplitude"] = 1.0
        arm.update_tag()
        st = arm.pose.bones["STERNUM"]
        scene.frame_set(1)
        a = st.location.copy()
        scene.frame_set(int(scene.render.fps))   # quarter period at 0.25 Hz → peak
        b = st.location.copy()
        arm["breath_amplitude"] = 0.0
        arm.update_tag()
        scene.frame_set(1)
        assert (a - b).length > 0.005, (a - b).length
        return f"sternum excursion {(a - b).length * 1000:.1f} mm"
    if not skipped(args, "breath"):
        check("breathing driver animates sternum", _breath)

    def _wound_thigh():
        arm = bpy.data.objects[props.armature_name]
        props.wound_type = "stab"
        props.wound_depth_mm = 60.0
        props.wound_width_mm = 15.0
        props.wound_energy_j = 0.0
        props.wound_bone = "FEMUR_L"
        res = bpy.ops.character_engine.apply_wound()
        assert res == {"FINISHED"}, res
        marker = next(o for o in bpy.data.objects if o.get("ce_role") == "wound" and o["ce_bone"] == "FEMUR_L")
        rep = json.loads(marker["ce_report"])
        assert rep["region"] == "thigh", rep
        assert rep["severity"] >= 2 and "haemorrhage" in rep["tags"], rep     # deep muscle stab: AIS 2+
        assert "muscle" in marker["ce_layers"], marker["ce_layers"]
        assert marker.parent == arm and marker.parent_bone == "FEMUR_L"
        return props.last_wound_report
    check("wound: thigh stab 60 mm", _wound_thigh)

    def _wound_head():
        props.wound_type = "gunshot"
        props.wound_depth_mm = 90.0
        props.wound_width_mm = 9.0
        props.wound_energy_j = 800.0
        props.wound_bone = "FRONTAL"
        assert bpy.ops.character_engine.apply_wound() == {"FINISHED"}
        marker = next(o for o in bpy.data.objects if o.get("ce_role") == "wound" and o["ce_bone"] == "FRONTAL")
        rep = json.loads(marker["ce_report"])
        assert rep["severity"] >= 5 and rep["lethality"] >= 0.5 and "cavity_penetration" in rep["tags"]
        return props.last_wound_report
    if not skipped(args, "wounds"):
        check("wound: cranial gunshot is lethal risk", _wound_head)

    def _wound_click_location():
        arm = bpy.data.objects[props.armature_name]
        props.wound_bone = ""
        props.wound_type = "laceration"
        props.wound_depth_mm = 8.0
        props.wound_width_mm = 40.0
        b = arm.data.bones["TIBIA_R"]
        p = arm.matrix_world @ ((b.head_local + b.tail_local) / 2)
        assert bpy.ops.character_engine.apply_wound(location=tuple(p), use_location=True) == {"FINISHED"}
        marker = [o for o in bpy.data.objects if o.get("ce_role") == "wound"][-1]
        assert marker["ce_bone"] == "TIBIA_R", marker["ce_bone"]
        return f"nearest bone resolved: {marker['ce_bone']}"
    if not skipped(args, "wounds"):
        check("wound: nearest-bone resolution from a 3D point", _wound_click_location)

    def _mocap():
        if not hasattr(bpy.ops.import_anim, "bvh"):
            import addon_utils
            addon_utils.enable("io_anim_bvh", default_set=False)
        assert hasattr(bpy.ops.import_anim, "bvh"), "BVH importer unavailable"
        bvh = args.bvh or write_synthetic_bvh(Path(tempfile.gettempdir()) / "ce_synthetic_tpose.bvh")
        props.bone_map = "mixamo"
        props.bvh_path = str(bvh)
        arm = bpy.data.objects[props.armature_name]
        arm["arm_ik_L"] = 0.0   # FK so mocap drives the DEF bones directly
        arm["arm_ik_R"] = 0.0
        res = bpy.ops.character_engine.import_mocap()
        assert res == {"FINISHED"}, res
        assert arm.animation_data and arm.animation_data.action, "no action on canonical armature"
        act = arm.animation_data.action
        assert arm["ce_bone_map"] == "mixamo"
        hum = arm.pose.bones["HUMERUS_L"]
        scene.frame_set(1)
        ctx.view_layer.update()
        t1 = (arm.matrix_world @ hum.tail).copy()
        scene.frame_set(int(act.frame_range[1]))
        ctx.view_layer.update()
        t2 = (arm.matrix_world @ hum.tail).copy()
        # Decision 17: sides must not cross. The source LeftArm and the canonical HUMERUS_L must be
        # on the same side (+X) and point the same way at the start and end of the clip.
        src = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o is not arm and "LeftArm" in o.pose.bones)
        sarm = src.pose.bones["LeftArm"]
        dirs = []
        for f in (1, int(act.frame_range[1])):
            scene.frame_set(f)
            ctx.view_layer.update()
            sd = ((src.matrix_world @ sarm.tail) - (src.matrix_world @ sarm.head)).normalized()
            dd = ((arm.matrix_world @ hum.tail) - (arm.matrix_world @ hum.head)).normalized()
            dirs.append((sd, dd))
        scene.frame_set(1)
        assert (arm.matrix_world @ hum.head).x > 0 and (src.matrix_world @ sarm.head).x > 0, \
            f"left arm sides differ: HUMERUS_L x={(arm.matrix_world @ hum.head).x:.3f}, LeftArm x={(src.matrix_world @ sarm.head).x:.3f}"
        for sd, dd in dirs:
            assert sd.dot(dd) > 0.9, f"HUMERUS_L direction {tuple(round(c, 2) for c in dd)} != LeftArm {tuple(round(c, 2) for c in sd)}"
        assert (t1 - t2).length > 0.05, f"humerus did not follow mocap ({(t1 - t2).length:.4f})"
        assert t2.z < t1.z, "left arm should swing downwards"
        arm["arm_ik_L"] = arm["arm_ik_R"] = 1.0
        return f"action {act.name}, frames {act.frame_range[0]:.0f}-{act.frame_range[1]:.0f}, humerus tail Δ {(t1 - t2).length:.3f} m"
    def _write_synthetic_ue_glb(path: Path) -> Path:
        """Unreal-mannequin-named rig (Quaternius UAL style, metres) with two clips, exported to .glb."""
        import math as _math

        from mathutils import Quaternion as _Quat
        from mathutils import Vector as _Vec
        before = set(bpy.data.objects)
        data = bpy.data.armatures.new("UE_Test")
        rig = bpy.data.objects.new("UE_Test", data)
        scene.collection.objects.link(rig)
        ctx.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        spec = [("pelvis", None, (0, 0, 0.95), (0, 0, 1.05)), ("spine_01", "pelvis", (0, 0, 1.05), (0, 0, 1.18)),
                ("spine_02", "spine_01", (0, 0, 1.18), (0, 0, 1.32)), ("spine_03", "spine_02", (0, 0, 1.32), (0, 0, 1.45)),
                ("neck_01", "spine_03", (0, 0, 1.45), (0, 0, 1.55)), ("Head", "neck_01", (0, 0, 1.55), (0, 0, 1.75))]
        for s, x in (("l", 1), ("r", -1)):
            spec += [(f"clavicle_{s}", "spine_03", (0.02 * x, 0, 1.43), (0.15 * x, 0, 1.43)),
                     (f"upperarm_{s}", f"clavicle_{s}", (0.15 * x, 0, 1.43), (0.43 * x, 0, 1.43)),
                     (f"lowerarm_{s}", f"upperarm_{s}", (0.43 * x, 0, 1.43), (0.70 * x, 0, 1.43)),
                     (f"hand_{s}", f"lowerarm_{s}", (0.70 * x, 0, 1.43), (0.80 * x, 0, 1.43)),
                     (f"thigh_{s}", "pelvis", (0.10 * x, 0, 0.95), (0.10 * x, 0, 0.50)),
                     (f"calf_{s}", f"thigh_{s}", (0.10 * x, 0, 0.50), (0.10 * x, 0, 0.08)),
                     (f"foot_{s}", f"calf_{s}", (0.10 * x, 0, 0.08), (0.10 * x, -0.12, 0.02))]
        try:
            for name, parent, h, t in spec:
                eb = data.edit_bones.new(name)
                eb.head, eb.tail = _Vec(h), _Vec(t)
                if parent:
                    eb.parent = data.edit_bones[parent]
                    eb.use_connect = False
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")
        rig.animation_data_create()
        idle = bpy.data.actions.new("Idle_Test")
        rig.animation_data.action = idle
        for b in rig.pose.bones:
            b.rotation_mode = "QUATERNION"
            b.keyframe_insert("rotation_quaternion", frame=1)
        track = rig.animation_data.nla_tracks.new()
        track.strips.new("Idle_Test", 1, idle)
        swing = bpy.data.actions.new("Swing_Test")
        rig.animation_data.action = swing
        ua = rig.pose.bones["upperarm_l"]
        ua.rotation_quaternion = _Quat()
        ua.keyframe_insert("rotation_quaternion", frame=1)
        ua.rotation_quaternion = _Quat((0.0, 0.0, 1.0), _math.radians(-70))  # arm swings down/forward
        ua.keyframe_insert("rotation_quaternion", frame=12)
        for o in ctx.selected_objects:
            o.select_set(False)
        rig.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_animations=True)
        for o in set(bpy.data.objects) - before:
            bpy.data.objects.remove(o, do_unlink=True)
        for a in (idle, swing):
            bpy.data.actions.remove(a)
        return path

    def _gltf_animation():
        glb = _write_synthetic_ue_glb(Path(tempfile.gettempdir()) / "ce_synthetic_ue.glb")
        arm = bpy.data.objects[props.armature_name]
        arm["arm_ik_L"] = 0.0
        props.bone_map, props.bvh_path, props.mocap_action = "quaternius_ual", str(glb), "swing"
        res = bpy.ops.character_engine.import_mocap()
        assert res == {"FINISHED"}, res
        src = next(o for o in bpy.data.objects if o.get("ce_role") == "mocap_source" and o.type == "ARMATURE"
                   and "upperarm_l" in o.data.bones)
        clips = json.loads(src["ce_clips"])
        assert any("Swing" in c for c in clips) and any("Idle" in c for c in clips), clips
        assert "Swing" in src.animation_data.action.name, src.animation_data.action.name
        act = arm.animation_data.action
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        hum = arm.pose.bones["HUMERUS_L"]
        scene.frame_set(f0)
        ctx.view_layer.update()
        t0 = (arm.matrix_world @ hum.tail).copy()
        scene.frame_set(f1)
        ctx.view_layer.update()
        t1 = (arm.matrix_world @ hum.tail).copy()
        assert (t1 - t0).length > 0.1, f"humerus barely moved: {(t1 - t0).length:.3f} m"
        assert t0.x > 0 and t1.x > 0, f"left arm crossed to -X: {t0.x:.3f}, {t1.x:.3f}"
        props.mocap_action = ""
        return (f"glb clips {clips}; retargeted '{src.animation_data.action.name}' frames {f0}-{f1}, "
                f"HUMERUS_L tail moved {(t1 - t0).length:.3f} m, stays on +X")

    if not skipped(args, "mocap"):
        check("mocap: BVH import + retarget (mixamo map)", _mocap)
        check("animation: glTF import + clip choice + retarget (quaternius_ual map)", _gltf_animation)

    out_dir = ROOT / "builds" / "tests"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _export():
        props.export_path = str(out_dir / f"{args.engine}_addon_canonical.glb")
        assert bpy.ops.character_engine.export_gltf() == {"FINISHED"}
        p = Path(props.export_path)
        assert p.exists() and p.stat().st_size > 10_000
        return f"{p.name} {p.stat().st_size} bytes"
    if not skipped(args, "canonical_export"):
        check("export canonical GLB (pure-Python exporter)", _export)

    def _export_scene():
        bpy.ops.object.select_all(action="DESELECT")
        assert bpy.ops.character_engine.export_scene_gltf() == {"FINISHED"}
        p = out_dir / f"{args.engine}_addon_canonical_scene.glb"
        assert p.exists() and p.stat().st_size > 50_000, p
        return f"{p.name} {p.stat().st_size} bytes"
    if not skipped(args, "scene_export"):
        check("export full scene GLB (Blender exporter)", _export_scene)

    def _report_op():
        assert bpy.ops.character_engine.dump_report() == {"FINISHED"}
        return "printed"
    check("character report operator", _report_op)

    upbge = addon["mod"].runtime_upbge.is_upbge()

    def _runtime():
        props.gameplay_style = "shenmue"
        props.runtime_target = "upbge"
        res = bpy.ops.character_engine.setup_upbge_scene()
        assert res == {"FINISHED"}, res
        player, opp = bpy.data.objects["player"], bpy.data.objects["opponent"]
        assert player["ce_gameplay_style"] == "shenmue" and not opp["ce_is_player"]
        if upbge:
            assert player.game.physics_type == "CHARACTER"
            binding = player["ce_logic_binding"]
            assert player.game.properties["fighter_id"].value == "player"
            assert not opp.game.properties["is_player"].value
            assert "ce_combat.py" in bpy.data.texts
            if binding == "deferred":
                assert bpy.app.background
                return ("UPBGE headless: game properties + ce_combat text block written; component/bricks deferred "
                        "(UPBGE 0.50 logic operators crash in background mode)")
            if binding == "component":
                comps = [c.name for c in player.game.components]
                assert comps, f"no component attached: {player.get('ce_component_error')}"
                return f"UPBGE component {comps}"
            if binding == "deferred" and not bpy.app.background:
                raise AssertionError("UI mode should have attached a component or bricks")
            ctrl = player.game.controllers["CE_Combat"]
            assert ctrl.type == "PYTHON" and ctrl.module == "ce_combat.run"
            assert player.game.sensors["CE_Always"].use_pulse_true_level
            return "UPBGE logic bricks: Always(pulse) -> Python module ce_combat.run (component op is UI-only)"
        return "vanilla Blender: stubs only (no bge)"
    check("runtime: UPBGE gameplay scene set-up", _runtime)

    def _combat_domain_in_engine():
        from character_engine.domain.gameplay import CombatInput, Fighter, ShenmueCombat

        sim = ShenmueCombat([Fighter("a", (0, 0, 0)), Fighter("b", (0, -0.7, 0))])
        sim.feed("a", CombatInput(punch=True))
        for _ in range(20):
            sim.step()
        assert sim.hits and sim.hits[0].bone_hit == "MANDIBLE"
        return f"jab landed at frame {sim.hits[0].frame} inside {args.engine} python {sys.version.split()[0]}"
    check("shared combat domain runs in engine python", _combat_domain_in_engine)

    if upbge:
        def _component_import():
            comp_dir = ROOT / "runtime" / "upbge" / "components"
            sys.path.insert(0, str(comp_dir))
            import importlib
            mod = importlib.import_module("ce_combat")
            assert hasattr(mod, "CEFighter") and "fighter_id" in mod.CEFighter.args
            assert callable(mod.run)
            return "ce_combat.CEFighter + ce_combat.run importable"
        check("UPBGE component module imports", _component_import)

        def _brick_simulation():
            """Drive ce_combat.run with stub KX objects for 120 frames: player jabs, opponent AI."""
            import importlib

            from mathutils import Vector

            mod = importlib.import_module("ce_combat")
            mod.reset()

            class StubObj(dict):
                def __init__(self, name, pos):
                    super().__init__()
                    self.name, self.worldPosition = name, Vector(pos)

                def applyMovement(self, d, local=False):
                    self.worldPosition += Vector(d)

            class Cont:
                def __init__(self, owner):
                    self.owner = owner

            player = StubObj("player", (0.0, 0.7, 0.0))
            player.update({"fighter_id": "player", "is_player": True})
            opp = StubObj("opponent", (0.0, 0.0, 0.0))
            opp.update({"fighter_id": "opponent", "is_player": False, "ai_aggression": 0.0})
            # player is driven with explicit keys (no bge keyboard headless)
            mod.run(Cont(opp))
            logic_player = mod.FighterLogic(player, {"fighter_id": "player", "is_player": True})
            keys = {"w": False, "s": False, "a": False, "d": False, "punch": False, "kick": False, "throw": False, "guard": False}
            for frame in range(120):
                k = dict(keys, punch=(frame % 20 == 0))
                logic_player.update(k)
                mod.run(Cont(opp))
            sim = mod.shared_sim()
            assert sim.hits, "no hits registered through the brick entry point"
            assert opp["ce_health"] < 100.0 and opp["ce_state"] in ("hitstun", "idle", "ko", "knockdown")
            return f"{len(sim.hits)} hits, opponent health {opp['ce_health']:.1f}, state {opp['ce_state']}"
        check("UPBGE brick entry point runs the shared simulation", _brick_simulation)

    player_exe = Path(bpy.app.binary_path).with_name("blenderplayer.exe")
    if upbge and player_exe.exists() and not skipped(args, "player"):
        def _blenderplayer_game():
            """Save a game .blend and run it in blenderplayer: CEFighter autoplay jabs for 180 frames,
            writes a JSON summary and calls bge.logic.endGame() (the player closes itself)."""
            import os
            import subprocess

            report = out_dir / f"{args.engine}_game_autoplay.json"
            if report.exists():
                report.unlink()
            player = bpy.data.objects["player"]
            player.game.properties["autoplay_frames"].value = 180
            player.game.properties["report_path"].value = str(report)
            for comp in player.game.components:
                for prop in comp.properties:
                    if prop.name == "autoplay_frames":
                        prop.value = 180
                    elif prop.name == "report_path":
                        prop.value = str(report)
            if player["ce_logic_binding"] == "deferred":
                return "skipped: fighters have no component/bricks in background mode (run the UPBGE suite in UI mode)"
            blend = out_dir / f"{args.engine}_game_smoke.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()), copy=True)
            env = {**os.environ, "CHARACTER_ENGINE_SRC": str(SRC)}
            proc = subprocess.run([str(player_exe), "-w", "640", "480", "0", "0", str(blend.resolve())],
                                  capture_output=True, text=True, timeout=120, env=env)
            log = out_dir / f"{args.engine}_blenderplayer.log"
            log.write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
            assert report.exists(), f"blenderplayer exit {proc.returncode}; no autoplay report (see {log.name})"
            data = json.loads(report.read_text(encoding="utf-8"))
            assert data["hits"] > 0, data
            assert data["fighters"]["opponent"]["health"] < 100.0, data
            return (f"blenderplayer exit {proc.returncode}: {data['frames']} frames, {data['hits']} hits, "
                    f"opponent health {data['fighters']['opponent']['health']}")
        check("UPBGE blenderplayer: autoplay combat smoke", _blenderplayer_game)

    # ------------------------------------------------- CINE-GR-001 step 1: sockets + cinematic ---
    import math

    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Quaternion, Vector

    sockets = (("SOCKET-sabre_hip.L", "COXAL_L"), ("SOCKET-hand_grip.R", "METACARPAL_3_R"))

    def _socket_follow(pose):
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for o in list(scene.objects):             # clean stage (earlier checks leave arena/fighters)
            bpy.data.objects.remove(o, do_unlink=True)
        props.template, props.use_template_stature, props.pose = "human_male_adult", True, pose
        assert bpy.ops.character_engine.generate_body() == {"FINISHED"}
        assert bpy.ops.character_engine.add_equipment_sockets(with_sabre=True) == {"FINISHED"}
        arm = bpy.data.objects[props.armature_name]
        sabre = bpy.data.objects[f"{arm.name}_Sabre_PLACEHOLDER"]
        assert sabre["ce_provenance"] == "PLACEHOLDER" and sabre.parent_bone == "SOCKET-sabre_hip.L"
        ctx.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="POSE")
        worst = 0.0
        for sname, parent in sockets:
            bone = arm.data.bones[sname]
            assert bone.parent.name == parent and bone["ce_layer"] == "MCH" and not bone.use_deform
            sb, pb = arm.pose.bones[sname], arm.pose.bones[parent]
            s0, p0, o0 = arm.matrix_world @ sb.matrix, arm.matrix_world @ pb.matrix, sabre.matrix_world.copy()
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(25)) @ Quaternion((0, 0, 1), math.radians(-15))
            ctx.view_layer.update()
            s1, p1, o1 = arm.matrix_world @ sb.matrix, arm.matrix_world @ pb.matrix, sabre.matrix_world.copy()
            dp, ds = p1 @ p0.inverted(), s1 @ s0.inverted()
            mats = [ds] + ([o1 @ o0.inverted()] if sname == "SOCKET-sabre_hip.L" else [])
            for m in mats:
                worst = max(worst, max(abs(dp[i][j] - m[i][j]) for i in range(4) for j in range(4)))
            pb.rotation_quaternion = (1, 0, 0, 0)
            ctx.view_layer.update()
        bpy.ops.object.mode_set(mode="OBJECT")
        assert worst < 1e-5, f"socket/sabre delta differs from parent delta by {worst:.2e}"
        return f"{pose}: sockets on MCH, max |Δsocket − Δparent| = {worst:.1e} (sabre included)"

    if not skipped(args, "cinematic"):
        check("CINE-GR-001 (b) sockets follow parents — T-pose", lambda: _socket_follow("tpose"))
        check("CINE-GR-001 (b) sockets follow parents — anatomical", lambda: _socket_follow("anatomical"))

    def _sabre_clear():
        props.tissue_bones, props.tissue_muscles, props.tissue_tendons, props.tissue_skin = True, False, False, False
        assert bpy.ops.character_engine.generate_tissues() == {"FINISHED"}
        arm = bpy.data.objects[props.armature_name]
        bones, sabre = bpy.data.objects[f"{arm.name}_Bones"], bpy.data.objects[f"{arm.name}_Sabre_PLACEHOLDER"]
        sw = [sabre.matrix_world @ Vector(c) for c in sabre.bound_box]
        slo = [min(p[k] for p in sw) for k in range(3)]
        shi = [max(p[k] for p in sw) for k in range(3)]
        groups = {}
        mw = bones.matrix_world
        for v in bones.data.vertices:
            p = mw @ v.co
            for g in v.groups:
                groups.setdefault(g.group, []).append(p)
        overlaps = []
        for gi, pts in groups.items():
            lo = [min(p[k] for p in pts) for k in range(3)]
            hi = [max(p[k] for p in pts) for k in range(3)]
            if all(lo[k] <= shi[k] and hi[k] >= slo[k] for k in range(3)):
                overlaps.append(bones.vertex_groups[gi].name)
        assert not overlaps, f"sabre AABB overlaps bone proxies: {overlaps}"
        return (f"sabre AABB x[{slo[0]:.3f},{shi[0]:.3f}] y[{slo[1]:.3f},{shi[1]:.3f}] z[{slo[2]:.3f},{shi[2]:.3f}] "
                f"clear of {len(groups)} bone proxy AABBs")

    def _cinematic():
        out = ROOT / "builds" / "renders" / f"{args.engine}_CINE-GR-001_fullbody.png"
        res = bpy.ops.character_engine.cinematic_fullbody(render=True, filepath=str(out))
        assert res == {"FINISHED"}, res
        arm, cam = bpy.data.objects[props.armature_name], scene.camera
        canonical = [b for b in arm.pose.bones if b.bone.get("ce_canonical")]
        outside = []
        for b in canonical:
            for p in (arm.matrix_world @ b.head, arm.matrix_world @ b.tail):
                c = world_to_camera_view(scene, cam, p)
                if not (0.0 <= c.x <= 1.0 and 0.0 <= c.y <= 1.0 and c.z > 0.0):
                    outside.append(b.name)
        assert len(canonical) == 208 and not outside, (len(canonical), outside[:10])
        # nothing that is not part of this character may stand between the camera and its bones
        depsgraph, origin, occluders = ctx.evaluated_depsgraph_get(), cam.matrix_world.translation, set()
        for b in canonical:
            target = arm.matrix_world @ b.head
            ray = target - origin
            hit, _loc, _n, _i, obj, _m = scene.ray_cast(depsgraph, origin, ray.normalized(), distance=ray.length)
            if hit and obj.get("ce_character") != arm.name:
                occluders.add(obj.name)
        assert not occluders, f"camera view occluded by {sorted(occluders)}"
        info = json.loads(arm["ce_last_render"])
        assert out.exists() and out.stat().st_size > 10_000, out
        assert info["seconds"] <= 30.0, f"render took {info['seconds']} s"
        return (f"(a) 208/208 bones in frame; (d) Workbench {scene.render.resolution_x}x{scene.render.resolution_y} "
                f"render {info['seconds']} s -> {out}")

    if not skipped(args, "cinematic"):
        check("CINE-GR-001 (c) placeholder sabre clear of skeleton proxies", _sabre_clear)
        check("CINE-GR-001 (a)+(d) full-body Workbench camera and render", _cinematic)

    def _centre(obj, depsgraph=None):
        if depsgraph is not None:
            ev = obj.evaluated_get(depsgraph)
            me = ev.to_mesh()
            pts = [obj.matrix_world @ v.co for v in me.vertices]
            ev.to_mesh_clear()
        else:
            pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        return sum(pts, Vector()) / len(pts)

    def _block_dummy():
        arm = bpy.data.objects[props.armature_name]
        assert bpy.ops.character_engine.block_dummy(with_collision=True) == {"FINISHED"}
        blocks = bpy.data.objects[f"{arm.name}_Blocks"]
        cols = [o for o in bpy.data.objects if o.get("ce_character") == arm.name and o.get("ce_role") == "collision"]
        assert len(cols) == 17, len(cols)
        bad = [v.index for v in blocks.data.vertices if len(v.groups) != 1 or abs(v.groups[0].weight - 1.0) > 1e-6]
        assert not bad, f"{len(bad)} vertices not 100 % weighted to one bone"
        assert all(o.modifiers.get("Collision") for o in cols)
        # pose the left upper arm: its block vertices and its collision capsule must follow the bone
        action = arm.animation_data.action if arm.animation_data else None
        if action:
            arm.animation_data.action = None
        arm["arm_ik_L"] = 0.0
        pb = arm.pose.bones["HUMERUS_L"]
        mode = pb.rotation_mode
        pb.rotation_mode = "QUATERNION"
        col = bpy.data.objects[f"{arm.name}_COL_upper_arm.L"]
        group = blocks.vertex_groups["HUMERUS_L"].index
        idx = [v.index for v in blocks.data.vertices if v.groups[0].group == group]

        def group_centre():
            dg = ctx.evaluated_depsgraph_get()
            ev = blocks.evaluated_get(dg)
            me = ev.to_mesh()
            c = sum((blocks.matrix_world @ me.vertices[i].co for i in idx), Vector()) / len(idx)
            ev.to_mesh_clear()
            return c
        ctx.view_layer.update()
        c0, k0 = _centre(col), group_centre()
        pb.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(60))
        ctx.view_layer.update()
        c1, k1 = _centre(col), group_centre()
        pb.rotation_quaternion = Quaternion()
        pb.rotation_mode = mode
        if action:
            arm.animation_data.action = action
        ctx.view_layer.update()
        moved_col, moved_blk = (c1 - c0).length, (k1 - k0).length
        assert moved_col > 0.05 and moved_blk > 0.05, (moved_col, moved_blk)
        assert (c1 - k1).length < 0.02, f"collision capsule and block diverge: {(c1 - k1).length:.4f} m"
        # Workbench sample render with the dummy only (other character layers hidden from render)
        hidden = [o for o in bpy.data.objects if o.get("ce_character") == arm.name
                  and o.get("ce_role") not in ("dummy",) and o.type == "MESH" and not o.hide_render]
        for o in hidden:
            o.hide_render = True
        out = ROOT / "builds" / "renders" / f"{args.engine}_block_dummy.png"
        res = bpy.ops.character_engine.cinematic_fullbody(render=True, filepath=str(out))
        for o in hidden:
            o.hide_render = False
        assert res == {"FINISHED"} and out.exists(), res
        return (f"{len(blocks.vertex_groups)} bones, {len(blocks.data.vertices)} vertices 100 % weighted, "
                f"{len(cols)} collision capsules; HUMERUS_L 60 deg -> capsule moved {moved_col:.3f} m, "
                f"block {moved_blk:.3f} m; render {out.name}")

    def _normalize():
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(5.0, 90.0, 3.0))
        obj = ctx.active_object
        obj.name = "CE_test_import_yup"
        obj.scale = (40.0, 180.0, 20.0)            # a Y-up "character" 180 units tall, +Z forward
        for o in ctx.selected_objects:
            o.select_set(o is obj)
        res = bpy.ops.character_engine.normalize_mesh(target_height_m=1.75, up="+Y", forward="+Z")
        assert res == {"FINISHED"}, res
        pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
        lo = [min(p[k] for p in pts) for k in range(3)]
        hi = [max(p[k] for p in pts) for k in range(3)]
        info = json.loads(obj["ce_normalized"])
        bpy.data.objects.remove(obj, do_unlink=True)
        assert abs(lo[2]) < 1e-6 and abs(hi[2] - 1.75) < 1e-6, (lo, hi)
        assert abs(lo[0] + hi[0]) < 1e-6 and abs(lo[1] + hi[1]) < 1e-6, (lo, hi)
        assert abs((hi[1] - lo[1]) - 20.0 * 1.75 / 180.0) < 1e-6, "source Z (forward) must become canonical Y depth"
        return f"Y-up 180-unit box -> z [0, {hi[2]:.3f}] m, centred, scale {info['scale']:.5f}, {info['provenance']}"

    if not skipped(args, "dummy"):
        check("P1 block dummy: blocks 100 % weighted, collision capsules follow the bones, render", _block_dummy)
        check("P2 normalize mesh: Y-up import to canonical metres at target height", _normalize)

    if args.save:
        def _save():
            args.save.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(args.save.resolve()))
            assert args.save.exists()
            return f"{args.save} {args.save.stat().st_size // 1024} kB"
        check("save .blend", _save)

    return finish(args)


def finish(args) -> int:
    failed = [r for r in RESULTS if r["status"] == "FAIL"]
    summary = {
        "engine": args.engine, "blender_version": bpy.app.version_string, "python": sys.version.split()[0],
        "passed": len(RESULTS) - len(failed), "failed": len(failed), "seconds": round(time.time() - T0, 1),
        "results": RESULTS,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"== {args.engine}: {summary['passed']} passed, {summary['failed']} failed in {summary['seconds']} s ==")
    return 1 if failed else 0


def _ui_runner():
    """UI mode: wait for the window, run everything under a VIEW_3D context override, quit."""
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        win = bpy.context.window_manager.windows[0]
        area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
        region = next(r for r in area.regions if r.type == "WINDOW")
        with bpy.context.temp_override(window=win, screen=win.screen, area=area, region=region):
            code = main(reset=False)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        code = 2
    print(f"== exiting Blender (code {code}) ==", flush=True)
    sys.stdout.flush()

    def _quit():
        bpy.ops.wm.quit_blender()
        return None

    bpy.app.timers.register(_quit, first_interval=0.5)   # quit outside the override/timer that ran the tests
    return None


if __name__ == "__main__":
    if bpy.app.background:
        code = main()
        sys.stdout.flush()
        sys.exit(code)
    bpy.app.timers.register(_ui_runner, first_interval=1.5)
