"""Automatic render views: front / side / back stills, contact sheet and turntable for one body job.

Builds on the *Cinematic preset: full body, Workbench* (``build.setup_fullbody_workbench``: floor, key / fill /
rim lights, camera) and on the batch body builder (``batch.build_body``). The camera orbits the body; lights
stay fixed. Spec, presets and framing maths live in ``character_engine.pipeline.render_views`` (pure Python).
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import bpy
from mathutils import Vector

from character_engine.pipeline.batch_export import BatchJob, provenance_record, sha256_file
from character_engine.pipeline.render_views import (
    VIEWS,
    RenderSpec,
    framing_distance,
    orbit_camera,
    turntable_azimuths,
)

from . import batch, build


def cuda_devices() -> list:
    """Names of the CUDA devices Cycles can see (empty when none or when Cycles is unavailable)."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        return [d.name for d in prefs.devices if d.type == "CUDA"]
    except (KeyError, TypeError, AttributeError):
        return []


def configure_engine(context, spec: RenderSpec) -> dict:
    """Apply the engine preset to the scene. Returns what was actually used (device after fallback, note)."""
    scene = context.scene
    preset = spec.preset
    scene.render.engine = preset.blender_engine
    used = {"engine": spec.engine, "blender_engine": preset.blender_engine, "samples": spec.effective_samples,
            "device": None, "note": ""}
    if spec.engine == "WORKBENCH":
        shading = scene.display.shading
        shading.light, shading.color_type = "STUDIO", "MATERIAL"     # material colours, never textures
        return used
    if scene.world is None:
        scene.world = bpy.data.worlds.new("CE_RenderWorld")
    if spec.engine == "EEVEE":
        scene.eevee.taa_render_samples = spec.effective_samples
        return used
    scene.cycles.samples = spec.effective_samples
    gpus = cuda_devices() if spec.device in ("AUTO", "GPU") else []
    if spec.device == "GPU" and not gpus:
        raise RuntimeError("CYCLES device GPU requested but Cycles sees no CUDA device on this machine; "
                           "use device CPU or AUTO")
    if gpus:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for d in prefs.devices:
            d.use = d.type == "CUDA"
        scene.cycles.device = "GPU"
        used["device"] = f"GPU (CUDA: {', '.join(gpus)})"
    else:
        scene.cycles.device = "CPU"
        used["device"] = "CPU"
        if spec.device == "AUTO":
            used["note"] = "AUTO fell back to CPU: no CUDA device"
    return used


def contact_sheet(paths, out: Path, step: int = 2) -> Path:
    """Place the stills side by side at 1/``step`` size (numpy ships with Blender)."""
    import numpy as np

    tiles = []
    for p in paths:
        img = bpy.data.images.load(str(p))
        w, h = img.size
        px = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        tiles.append(px.reshape(h, w, 4)[::step, ::step])
        bpy.data.images.remove(img)
    sheet = np.ascontiguousarray(np.concatenate(tiles, axis=1))
    h, w = sheet.shape[:2]
    img = bpy.data.images.new("CE_ContactSheet", w, h, alpha=True)
    img.pixels.foreach_set(sheet.ravel())
    img.filepath_raw, img.file_format = str(out), "PNG"
    img.save()
    bpy.data.images.remove(img)
    return out


def encode_mp4(frames_dir: Path, frame_files, out: Path, fps: int = 24) -> str:
    """Encode the PNG frames with Blender's bundled FFmpeg (sequencer, no re-render). Returns the encoder used."""
    tmp = bpy.data.scenes.new("CE_TurntableEncode")
    try:
        img = bpy.data.images.load(str(frames_dir / frame_files[0]))
        tmp.render.resolution_x, tmp.render.resolution_y = img.size
        bpy.data.images.remove(img)
        tmp.render.resolution_percentage = 100
        tmp.render.fps = fps
        seq = tmp.sequence_editor_create()
        strip = seq.sequences.new_image("frames", str(frames_dir / frame_files[0]), channel=1, frame_start=1)
        for f in frame_files[1:]:
            strip.elements.append(f)
        tmp.frame_start, tmp.frame_end = 1, len(frame_files)
        tmp.render.image_settings.file_format = "FFMPEG"
        tmp.render.ffmpeg.format, tmp.render.ffmpeg.codec = "MPEG4", "H264"
        tmp.render.filepath = str(out)
        tmp.render.use_file_extension = False
        bpy.ops.render.render(animation=True, scene=tmp.name)
    finally:
        bpy.data.scenes.remove(tmp)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"FFmpeg encode wrote no file: {out}")
    return f"Blender {bpy.app.version_string} bundled FFmpeg (MPEG4/H264, {fps} fps)"


def _frame(cam, points, resolution, azimuth: float) -> None:
    centre, dist = framing_distance(points, cam.data.lens, cam.data.sensor_width, resolution)
    cam.location, cam.rotation_euler = orbit_camera(centre, dist, azimuth)


def render_job(context, job: BatchJob, spec: RenderSpec, out_dir: Path, repo_commit: str = "") -> dict:
    """Render one body job into ``out_dir/<job>/``. Raises on failure (the caller records FAIL and goes on)."""
    t0 = time.time()
    folder = Path(out_dir) / job.name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    arm, extra = batch.build_body(context, job, repo_commit)
    scene = context.scene
    dummies = [o for o in bpy.data.objects if o.get("ce_character") == arm["ce_character"] and o.get("ce_role") == "dummy"]
    cam = build.setup_fullbody_workbench(context, arm, resolution=spec.resolution, extra_objects=dummies)
    used = configure_engine(context, spec)
    points = [tuple(p) for p in build.armature_points_world(arm)]
    for o in dummies:
        points += [tuple(o.matrix_world @ Vector(c)) for c in o.bound_box]
    times, files = {}, {}
    for view in spec.views:
        _frame(cam, points, spec.resolution, VIEWS[view])
        path = folder / f"{view}.png"
        times[view] = round(build.render_still(context, path), 2)
        files[path.name] = path
    if spec.contact_sheet:
        files["contact_sheet.png"] = contact_sheet([folder / f"{v}.png" for v in spec.views], folder / "contact_sheet.png")
    encoder = None
    if spec.turntable is not None:
        tt = spec.turntable
        scene.render.resolution_x, scene.render.resolution_y = tt.resolution
        frames_dir = folder / "turntable"
        names = []
        t = time.time()
        for i, az in enumerate(turntable_azimuths(tt.frames)):
            _frame(cam, points, tt.resolution, az)
            name = f"{i + 1:04d}.png"
            build.render_still(context, frames_dir / name)
            names.append(name)
        times["turntable"] = round(time.time() - t, 2)
        times["turntable_per_frame"] = round(times["turntable"] / tt.frames, 2)
        if tt.mp4:
            t = time.time()
            encoder = encode_mp4(frames_dir, names, folder / "turntable.mp4")
            times["mp4"] = round(time.time() - t, 2)
            files["turntable.mp4"] = folder / "turntable.mp4"
    rec = provenance_record(job, blender_version=bpy.app.version_string, addon_version=batch.ADDON_VERSION,
                            glb_sha256="", glb_bytes=0, extra=extra)
    del rec["glb_sha256"], rec["glb_bytes"]
    rec.update({"render": spec.settings(), "engine_used": used, "encoder": encoder, "seconds": times,
                "lens_mm": cam.data.lens, "camera": "orbit around the body's vertical axis; lights fixed",
                "files": {n: sha256_file(p) for n, p in files.items()}})
    (folder / "render.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return {"status": "PASS", "folder": str(folder), "engine": used, "times": times,
            "seconds": round(time.time() - t0, 2)}
