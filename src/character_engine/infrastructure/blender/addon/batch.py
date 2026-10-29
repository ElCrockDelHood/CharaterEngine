"""Batch export executor: one ``BatchJob`` (pipeline/batch_export.py) → ``<name>.glb`` + provenance sidecar.

Each job starts from an emptied scene and drives the same operators as the panel (Generate body,
Import & retarget animation) plus ``build.build_block_dummy`` / ``build.export_scene_glb``, so a batch
GLB is what a user would get by clicking through the addon with the same settings.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import bpy

from character_engine.pipeline.batch_export import BatchJob, provenance_record, resolve, sha256_file

from . import _bootstrap, bl_info, build

ADDON_VERSION = ".".join(str(v) for v in bl_info["version"])
EXPECTED_BONES = 208


def reset_scene(context) -> None:
    """Remove every object and the data blocks a previous job may have left (actions, meshes, lights, cameras…)."""
    if context.object and context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for blocks in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes, bpy.data.materials, bpy.data.collections,
                   bpy.data.lights, bpy.data.cameras):
        for block in list(blocks):
            blocks.remove(block)


def build_body(context, job: BatchJob, repo_commit: str = ""):
    """Empty the scene and build the job's armature (+ block dummy). Returns (armature, provenance extras)."""
    reset_scene(context)
    props = context.scene.character_engine
    props.template = job.template_id
    props.pose = job.pose
    # the template's own stature comes straight from the domain; only an override goes through the float property
    props.use_template_stature = not job.stature_overridden
    if job.stature_overridden:
        props.stature_m = job.stature_m
    if bpy.ops.character_engine.generate_body() != {"FINISHED"}:
        raise RuntimeError("generate_body cancelled (see the Blender log above)")
    arm = bpy.data.objects[props.armature_name]
    if len(arm.data.bones) != EXPECTED_BONES:
        raise RuntimeError(f"armature has {len(arm.data.bones)} bones, expected {EXPECTED_BONES}")
    extra = {"bones": len(arm.data.bones), "stature_m_built": round(float(arm["ce_stature_m"]), 6),
             "repo_commit": repo_commit}
    if job.mesh == "block_dummy":
        blocks, _ = build.build_block_dummy(context, arm, with_collision=False)
        extra["mesh_vertices"] = len(blocks.data.vertices)
    return arm, extra


def run_job(context, job: BatchJob, out_dir: Path, root: Path | None = None, repo_commit: str = "") -> dict:
    """Build and export one job. Raises on failure (the caller records FAIL and goes on)."""
    t0 = time.time()
    root = Path(root) if root else _bootstrap.repo_root()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    arm, extra = build_body(context, job, repo_commit)
    props = context.scene.character_engine
    if job.clip is not None:
        clip_path = resolve(root, job.clip.path)
        props.bone_map, props.bvh_path, props.mocap_action = job.clip.bone_map, str(clip_path), job.clip.clip
        props.mocap_bake = True
        if bpy.ops.character_engine.import_mocap() != {"FINISHED"}:
            raise RuntimeError(f"import_mocap cancelled for {clip_path} (see the Blender log above)")
        act = arm.animation_data.action if arm.animation_data else None
        if act is None:
            raise RuntimeError("retarget produced no action on the canonical armature")
        src = next((o for o in bpy.data.objects if o.get("ce_role") == "mocap_source" and o.type == "ARMATURE"), None)
        extra.update({
            "clip_source_sha256": sha256_file(clip_path),
            "clip_resolved": src.animation_data.action.name if src and src.animation_data and src.animation_data.action
            else None,
            "clip_frames": [int(act.frame_range[0]), int(act.frame_range[1])],
        })
    # the retarget keys every frame of every mapped bone, so keyed export keeps the motion (no forced sampling)
    glb = build.export_scene_glb(context, arm, out_dir / f"{job.name}.glb", force_sampling=job.clip is None)
    if not glb.exists() or glb.stat().st_size == 0:
        raise RuntimeError(f"exporter wrote no file: {glb}")
    digest = sha256_file(glb)
    rec = provenance_record(job, blender_version=bpy.app.version_string, addon_version=ADDON_VERSION,
                            glb_sha256=digest, glb_bytes=glb.stat().st_size, extra=extra)
    prov = out_dir / f"{job.name}.provenance.json"
    prov.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return {"status": "PASS", "glb": str(glb), "provenance": str(prov), "sha256": digest,
            "bytes": glb.stat().st_size, "seconds": round(time.time() - t0, 2)}
