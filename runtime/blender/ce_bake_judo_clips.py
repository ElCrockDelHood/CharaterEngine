"""Bake the judo throws in Blender: two fighters, one action per throw and fighter, every frame (A36).

    blender -b --factory-startup --python runtime/blender/ce_bake_judo_clips.py -- --frames builds/judo/judo_frames.json \
        --out builds/judo

Reads the frame table written by ``scripts/bake_judo_clips.py`` (``ce-judo-frames/1``: per frame and fighter the object
location and rotation and the rest-frame rotation of every game bone, plus probe points from the Python solve). Builds
``CE_TORI`` and ``CE_UKE`` (bare 66-bone game armatures at the anatomical rest points, with the block body), keys one
action per throw and fighter, checks Blender's posed probe points against Python's, renders one Workbench frame per key
from the side and assembles a strip per throw, and saves ``judo_throws.blend``. Prints CE_JUDO lines; exits 1 on failure.
"""

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import bpy  # noqa: E402
from mathutils import Quaternion, Vector  # noqa: E402

from character_engine.domain.rigging.game_body import game_body_placements  # noqa: E402
from character_engine.export.gltf_game import game_skeleton_points  # noqa: E402
from character_engine.infrastructure.blender.addon import game_rig  # noqa: E402

COLORS = {"tori": (0.25, 0.45, 0.9, 1.0), "uke": (0.9, 0.35, 0.28, 1.0)}
STRIP_W, STRIP_H = 480, 360


def build_fighter(ctx, points, who):
    arm = game_rig.build_game_armature_from_points(ctx, points, f"CE_{who.upper()}")
    body = game_rig.build_game_body_mesh(ctx, arm, game_body_placements(points), f"CE_{who.upper()}_BODY")
    body.color = COLORS[who]
    arm.rotation_mode = "QUATERNION"
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    if arm.animation_data is None:
        arm.animation_data_create()
    return arm


def bake(arm, who, throw_id, rows):
    frame_rest = {b.name: b.matrix_local.to_3x3().to_quaternion() for b in arm.data.bones}
    name = f"{throw_id}.{who}"
    old = bpy.data.actions.get(name)
    if old is not None:
        bpy.data.actions.remove(old)
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    action["ce_provenance"] = "PLACEHOLDER"
    action["ce_throw"] = throw_id
    arm.animation_data.action = action
    prev_obj, prev = None, {}
    for row in rows:
        f, d = row["frame"], row[who]
        q = Quaternion(d["rotation_wxyz"])
        if prev_obj is not None and q.dot(prev_obj) < 0:          # keep the sign continuous for interpolation
            q.negate()
        prev_obj = q
        arm.rotation_quaternion, arm.location = q, Vector(d["location"])
        arm.keyframe_insert("rotation_quaternion", frame=f, group="root")
        arm.keyframe_insert("location", frame=f, group="root")
        for pb in arm.pose.bones:
            r = frame_rest[pb.name]
            bq = r.inverted() @ Quaternion(d["bones_wxyz"].get(pb.name, (1.0, 0.0, 0.0, 0.0))) @ r
            if pb.name in prev and bq.dot(prev[pb.name]) < 0:
                bq.negate()
            prev[pb.name] = bq
            pb.rotation_quaternion = bq
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
    for fc in game_rig.action_fcurves(action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"                            # every frame is keyed: the in-betweens come from Python
    return action


def parity(ctx, arms, rows):
    worst, where = 0.0, ""
    for row in rows:
        ctx.scene.frame_set(row["frame"])
        ctx.view_layer.update()
        for who, arm in arms.items():
            for bone, want in row[who]["probes"].items():
                got = arm.matrix_world @ arm.pose.bones[bone].tail
                err = math.dist(tuple(got), want)
                if err > worst:
                    worst, where = err, f"{who}.{bone}@{row['frame']}"
    return worst, where


def setup_render(ctx):
    sc = ctx.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "OBJECT"
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = STRIP_W, STRIP_H, 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    sc.world = sc.world or bpy.data.worlds.new("CE_JUDO_WORLD")
    sc.world.color = (0.93, 0.93, 0.9)                                 # light background, the bodies read better
    bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0.0, -0.8, 0.0))
    ctx.active_object.color = (0.85, 0.85, 0.8, 1.0)
    cam = bpy.data.objects.new("CE_JUDO_CAM", bpy.data.cameras.new("CE_JUDO_CAM"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 3.4
    cam.rotation_euler = (math.radians(90), 0.0, math.radians(90))     # looks along -X: fighters' Y across the frame
    sc.camera = cam
    return cam


def render_strip(ctx, cam, rows, keys, out_png):
    import numpy as np

    views = {"side": (6.0, 0.0, 90.0), "three_quarter": (4.3, -4.3, 45.0)}   # camera offset x, y and heading (deg)
    rows_px = []
    for vx, vy, heading in views.values():
        tiles = []
        cam.rotation_euler = (math.radians(90), 0.0, math.radians(heading))
        for f in keys:
            row = next(r for r in rows if r["frame"] == f)
            mid = [(row["tori"]["probes"]["pelvis"][i] + row["uke"]["probes"]["pelvis"][i]) / 2 for i in range(2)]
            cam.location = (mid[0] + vx, mid[1] + vy, 0.95)
            ctx.scene.frame_set(f)
            tmp = out_png.with_name(f"_tile_{f}.png")
            ctx.scene.render.filepath = str(tmp)
            bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(str(tmp))
            px = np.array(img.pixels[:], dtype=np.float32).reshape(STRIP_H, STRIP_W, 4)
            bpy.data.images.remove(img)
            tmp.unlink()
            tiles.append(px)
            tiles.append(np.ones((STRIP_H, 4, 4), dtype=np.float32) * 0.6)
        rows_px.append(np.concatenate(tiles[:-1], axis=1))
        rows_px.append(np.ones((4, rows_px[-1].shape[1], 4), dtype=np.float32) * 0.6)
    strip = np.concatenate(rows_px[:-1][::-1], axis=0)                 # Blender images start at the bottom row
    h, w = strip.shape[:2]
    out = bpy.data.images.new(out_png.stem, w, h, alpha=True)
    out.pixels = strip.ravel()
    out.filepath_raw, out.file_format = str(out_png), "PNG"
    out.save()
    bpy.data.images.remove(out)


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args(argv)
    data = json.loads(a.frames.read_text(encoding="utf-8"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ctx = bpy.context
    ctx.scene.render.fps = data["fps"]
    points = game_skeleton_points(pose="anatomical")
    arms = {w: build_fighter(ctx, points, w) for w in ("tori", "uke")}
    cam = None if a.no_render else setup_render(ctx)
    a.out.mkdir(parents=True, exist_ok=True)
    ok, worst_all = True, 0.0
    for throw_id, clip in data["clips"].items():
        rows = clip["frames"]
        for who, arm in arms.items():
            bake(arm, who, throw_id, rows)
        ctx.scene.frame_start, ctx.scene.frame_end = rows[0]["frame"], rows[-1]["frame"]
        worst, where = parity(ctx, arms, rows)
        worst_all = max(worst_all, worst)
        ok &= worst < 0.002
        print(f"CE_JUDO {throw_id}: {len(rows)} frames keyed for tori and uke; Blender vs Python worst {worst * 1000:.2f} mm ({where})")
        if cam is not None:
            png = a.out / f"{throw_id}_blender.png"
            render_strip(ctx, cam, rows, clip["key_frames"], png)
            print(f"CE_JUDO {throw_id}: strip {png}")
    for who, arm in arms.items():                                     # leave the first throw on, for opening the .blend
        arm.animation_data.action = bpy.data.actions[f"{next(iter(data['clips']))}.{who}"]
    blend = a.out / "judo_throws.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"CE_JUDO {'OK' if ok else 'FAIL'}: {blend}, worst {worst_all * 1000:.2f} mm, Blender {bpy.app.version_string}")
    return 0 if ok else 1


if __name__ == "__main__":
    code = main()
    if code:
        sys.exit(code)
