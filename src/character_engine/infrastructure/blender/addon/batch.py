"""Batch export executor: one ``BatchJob`` (pipeline/batch_export.py) → ``<name>.glb`` + provenance sidecar.

Each job starts from an emptied scene and drives the panel's *Generate body* operator and the same import /
retarget functions as *Import & retarget animation* (clip chosen by exact name, ``pick_clip``) plus
``build.build_block_dummy`` / ``build.export_scene_glb``, so a batch GLB is what a user would get by clicking
through the addon with the same settings.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import bpy

from character_engine.domain.animation import get_bone_map
from character_engine.pipeline.batch_export import (
    BatchJob,
    layer_summary,
    provenance_record,
    resolve,
    sha256_file,
)

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
    elif job.mesh == "tissues":
        # the panel's Generate tissues with its default options, set explicitly so an earlier scene state cannot
        # leave a layer out: bones (asset meshes when present), tendons, muscles, skin (2 subdivisions)
        props.tissue_bones = props.tissue_tendons = props.tissue_muscles = props.tissue_skin = True
        props.prefer_asset_meshes, props.skin_subdivisions = True, 2
        if bpy.ops.character_engine.generate_tissues() != {"FINISHED"}:
            raise RuntimeError("generate_tissues cancelled (see the Blender log above)")
        extra["layers"] = tissue_layers(arm)
        extra["mesh_vertices"] = sum(v["vertices"] for v in extra["layers"].values())
    return arm, extra


def tissue_layers(arm) -> dict:
    """Per tissue layer: objects, vertices and the provenance tags the builders set, split per aspect.

    The bone layer carries one tag per bone (``ce_bone_provenance``), so its counts are bones; the other layers
    count objects. Nothing is relabelled here: the tags are read as the builders wrote them.
    """
    layers: dict = {}
    for o in bpy.data.objects:
        if o.get("ce_character") != arm["ce_character"] or o.get("ce_role") != "tissue":
            continue
        entry = layers.setdefault(o["ce_layer"], {"objects": 0, "vertices": 0, "tags": {}})
        entry["objects"] += 1
        entry["vertices"] += len(o.data.vertices)
        if "ce_muscle_count" in o:
            entry["muscles"] = int(o["ce_muscle_count"])
        tags = list(json.loads(o["ce_bone_provenance"]).values()) if "ce_bone_provenance" in o else [o["ce_provenance"]]
        for t in tags:
            entry["tags"][t] = entry["tags"].get(t, 0) + 1
    for entry in layers.values():
        entry["provenance"] = layer_summary(entry.pop("tags"))
    return dict(sorted(layers.items()))


def run_job(context, job: BatchJob, out_dir: Path, root: Path | None = None, repo_commit: str = "") -> dict:
    """Build and export one job. Raises on failure (the caller records FAIL and goes on)."""
    t0 = time.time()
    root = Path(root) if root else _bootstrap.repo_root()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    arm, extra = build_body(context, job, repo_commit)
    if job.clip is not None:
        clip_path = resolve(root, job.clip.path)
        if not clip_path.exists():
            raise FileNotFoundError(f"clip file not found: {clip_path}")
        # same steps as the Import & retarget operator; the importer chooses the clip with pick_clip
        bone_map = get_bone_map(job.clip.bone_map)
        src = build.import_mocap(clip_path, bone_map, job.clip.clip)
        rule = src.get("ce_clip_rule")
        src["ce_character"] = arm["ce_character"]
        build._link(context, src, f"{arm['ce_character']}_Mocap")
        build.retarget_mocap(context, src, arm, bone_map)
        src.hide_set(True)
        src.hide_render = True
        act = arm.animation_data.action if arm.animation_data else None
        if act is None:
            raise RuntimeError("retarget produced no action on the canonical armature")
        extra.update({
            "clip_source_sha256": sha256_file(clip_path),
            "clip_resolved": src.animation_data.action.name if src.animation_data and src.animation_data.action
            else None,
            "clip_rule": rule,
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
