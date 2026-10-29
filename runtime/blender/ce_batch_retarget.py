"""Batch retarget of a glTF animation library onto the canonical armature, run inside Blender 3.6.

    blender -b --factory-startup --python runtime/blender/ce_batch_retarget.py -- \
        --glb "C:/DEV/Assets/descargas/quaternius_ual1/extracted/.../UAL1_Standard.glb" \
        --library ual1 --variant standard --out-dir builds/animations --samples builds/animations/samples/x.json

One process per (library file, variant). The library is imported once (addon ``import_mocap``, bone map
``quaternius_ual`` by default); every clip is retargeted onto a fresh 1.80 m canonical T-pose armature with the
addon's ``retarget_mocap`` and exported as one GLB (armature only, the clip as its single animation). For QA the
script only *samples* world positions of source and canonical joints per frame and writes them to ``--samples``;
every metric is computed in pure Python (``character_engine.domain.animation.clip_qa``) by
``scripts/retarget_batch.py``. The input file is read in place (outside the repo) and never copied.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

try:
    import bpy  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("run inside Blender: blender -b --python ...") from exc

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

ARMATURE = "CE_Retarget"
# Source joints sampled (Unreal-mannequin naming of the Quaternius rigs): root carries the root motion.
SOURCE_JOINTS = ("root", "pelvis", "foot_l", "ball_l", "foot_r", "ball_r")
# Canonical bones sampled at head and tail: feet for contact / sliding / penetration, the rest for the loop seam.
TARGET_BONES = ("SACRUM", "THORACIC_8", "CERVICAL_1", "HUMERUS_L", "HUMERUS_R", "RADIUS_L", "RADIUS_R",
                "CAPITATE_L", "CAPITATE_R", "FEMUR_L", "FEMUR_R", "TIBIA_L", "TIBIA_R", "TALUS_L", "TALUS_R",
                "CALCANEUS_L", "CALCANEUS_R", "TOE_PHALANX_PROXIMAL_3_L", "TOE_PHALANX_PROXIMAL_3_R",
                "TOE_PHALANX_DISTAL_1_L", "TOE_PHALANX_DISTAL_1_R")
# Which of these points count as foot contact points is decided by the QA (scripts/retarget_batch.py).


def load_addon():
    tmp = Path(tempfile.mkdtemp(prefix="ce_addon_"))
    shutil.copytree(SRC / "character_engine" / "infrastructure" / "blender" / "addon", tmp / "character_engine_blender")
    sys.path.insert(0, str(tmp))
    import character_engine_blender  # type: ignore
    character_engine_blender.register()
    from character_engine_blender import build  # type: ignore
    return build


def _xyz(v) -> list:
    return [round(float(v.x), 5), round(float(v.y), 5), round(float(v.z), 5)]


def sample_source(src) -> dict:
    mw = src.matrix_world
    out = {}
    for n in SOURCE_JOINTS:
        pb = src.pose.bones.get(n)
        if pb is not None:
            out[n] = _xyz(mw @ pb.head)
            out[n + ".tail"] = _xyz(mw @ pb.tail)
    return out


def sample_target(dst) -> dict:
    mw = dst.matrix_world
    out = {}
    for n in TARGET_BONES:
        pb = dst.pose.bones.get(n)
        if pb is not None:
            out[n] = _xyz(mw @ pb.head)
            out[n + ".tail"] = _xyz(mw @ pb.tail)
    return out


def rest_points(arm, names, with_tail=True) -> dict:
    mw = arm.matrix_world
    out = {}
    for n in names:
        b = arm.data.bones.get(n)
        if b is not None:
            out[n] = _xyz(mw @ b.head_local)
            if with_tail:
                out[n + ".tail"] = _xyz(mw @ b.tail_local)
    return out


def export_clip(dst, path: Path) -> float:
    """Export the armature with its active action only; returns seconds."""
    for o in bpy.context.view_layer.objects:
        o.select_set(o == dst)
    bpy.context.view_layer.objects.active = dst
    path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    common = dict(filepath=str(path), export_format="GLB", use_selection=True, export_animations=True,
                  export_skins=True, export_def_bones=False, export_yup=True,
                  # the retarget keys every frame of every mapped bone, so the keys are exported as they are;
                  # forced sampling evaluates all 208 bones per frame and took ~260 s per clip on this PC
                  export_force_sampling=False)
    try:   # Blender 3.6 option name; older builds only know export_nla_strips
        bpy.ops.export_scene.gltf(**common, export_animation_mode="ACTIVE_ACTIONS")
    except TypeError:
        bpy.ops.export_scene.gltf(**common, export_nla_strips=False)
    return time.time() - t0


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", type=Path, required=True)
    ap.add_argument("--library", required=True, help="short id used in output paths (e.g. ual1)")
    ap.add_argument("--variant", required=True, choices=("standard", "rm"))
    ap.add_argument("--bone-map", default="quaternius_ual")
    ap.add_argument("--fps", type=int, default=30, help="scene fps used to turn glTF seconds into frames")
    ap.add_argument("--clips", default="", help="comma-separated substrings; only matching clips")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--samples", type=Path, required=True)
    ap.add_argument("--no-export", action="store_true")
    a = ap.parse_args(argv)

    t_start = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = a.fps, 1.0   # set BEFORE import: the importer converts s -> frames
    build = load_addon()
    from character_engine.domain.animation import get_bone_map

    props = scene.character_engine
    props.armature_name = ARMATURE
    props.template, props.pose, props.use_template_stature = "human_male_adult", "tpose", True
    assert bpy.ops.character_engine.generate_body() == {"FINISHED"}
    dst = bpy.data.objects[ARMATURE]
    bone_map = get_bone_map(a.bone_map)
    src = build.import_mocap(a.glb, bone_map, "")
    clips = json.loads(src["ce_clips"])
    wanted = [s.strip().lower() for s in a.clips.split(",") if s.strip()]
    if wanted:
        clips = [c for c in clips if any(w in c.lower() for w in wanted)]
    print(f"[retarget] {a.glb.name}: {len(clips)} clips, scene {scene.render.fps} fps, "
          f"source turned 180: {bool(src.get('ce_turned_180'))}", flush=True)

    result = {"glb": str(a.glb), "library": a.library, "variant": a.variant, "bone_map": a.bone_map,
              "fps": a.fps, "blender": bpy.app.version_string, "armature": ARMATURE,
              "stature_m": float(dst.get("ce_stature_m", 0.0)),
              "source_rest": rest_points(src, SOURCE_JOINTS), "target_rest": rest_points(dst, TARGET_BONES),
              "clips": []}
    for i, name in enumerate(clips, 1):
        clip = name[:-len("_Armature")] if name.endswith("_Armature") else name
        t0 = time.time()
        rec = {"clip": clip, "action": name}
        try:
            action = bpy.data.actions[name]
            src.animation_data.action = action
            f0, f1 = action.frame_range
            rec.update(frame_start_raw=float(f0), frame_end_raw=float(f1),
                       duration_s=round((float(f1) - float(f0)) / a.fps, 5))
            stats = build.retarget_mocap(bpy.context, src, dst, bone_map)
            rec.update(stats)
            frames = list(range(int(f0), int(f1) + 1))
            source, target = [], []
            for f in frames:
                scene.frame_set(f)
                source.append(sample_source(src))
                target.append(sample_target(dst))
            rec.update(frames=frames, source=source, target=target)
            if not a.no_export:
                scene.frame_start, scene.frame_end = frames[0], frames[-1]
                suffix = "_RM" if a.variant == "rm" else ""
                out = a.out_dir / a.library / f"{clip}{suffix}.glb"
                rec["export_s"] = round(export_clip(dst, out), 2)
                rec["glb_out"] = str(out)
                rec["glb_bytes"] = out.stat().st_size
            rec["status"] = "ok"
        except Exception as exc:  # noqa: BLE001 - one bad clip must not stop the batch
            rec.update(status="error", error=f"{type(exc).__name__}: {exc}")
        finally:
            act = dst.animation_data.action if dst.animation_data else None
            if act is not None:
                dst.animation_data.action = None
                bpy.data.actions.remove(act)
        rec["wall_s"] = round(time.time() - t0, 2)
        print(f"[retarget] {i:2d}/{len(clips)} {clip:32s} {rec['status']:5s} frames {len(rec.get('frames', []))} "
              f"{rec.get('duration_s', '?')} s  ({rec['wall_s']} s){'  ' + rec['error'] if 'error' in rec else ''}",
              flush=True)
        result["clips"].append(rec)
    result["wall_s"] = round(time.time() - t_start, 1)
    a.samples.parent.mkdir(parents=True, exist_ok=True)
    a.samples.write_text(json.dumps(result), encoding="utf-8")
    print(f"[retarget] samples: {a.samples} ({result['wall_s']} s)", flush=True)
    return 0 if all(c["status"] == "ok" for c in result["clips"]) else 1


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.exit(code)
