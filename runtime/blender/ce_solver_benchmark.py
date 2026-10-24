"""Experiment 0 — one solver benchmark case, run inside Blender 3.6 (docs/product/EXPERIMENT-0-SOLVER-BENCHMARK.md).

    blender -b --factory-startup --python runtime/blender/ce_solver_benchmark.py -- \
        --case rigid --size 100 --frames 48 --seed 7 --out result.json --render key.png

Builds one test scene from scratch (factory settings, nothing from the user's preferences), steps the
simulation frame by frame, measures it and renders one Workbench key frame. Only solvers shipped with
Blender 3.6 are used. All outputs are ESTIMATE (our own simulation); the result JSON records every
parameter and the seed. Driven by ``scripts/solver_benchmark.py`` (one process per case, with a timeout).
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import random
import sys
import tempfile
import time
from pathlib import Path

try:
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("run inside Blender: blender -b --python ...") from exc

ROOT = Path(__file__).resolve().parents[2]
SKELETON = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
GRAVITY = -9.81
KEY_FRACTION = 0.75          # key frame rendered = 75 % of the run


# ----------------------------------------------------------------------------- measuring ---

class _PMC(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def memory_mb() -> dict:
    """Current and peak working set of this Blender process (Windows only; None elsewhere)."""
    try:
        pmc = _PMC()
        pmc.cb = ctypes.sizeof(_PMC)
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p               # 64-bit handle, not a C int
        k32.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PMC), ctypes.c_ulong]
        if not k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return {"current_mb": None, "peak_mb": None}
        return {"current_mb": round(pmc.WorkingSetSize / 2**20, 1), "peak_mb": round(pmc.PeakWorkingSetSize / 2**20, 1)}
    except (AttributeError, OSError):
        return {"current_mb": None, "peak_mb": None}


# ----------------------------------------------------------------------------- scene helpers ---

def reset_scene(frames: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frames
    scene.render.fps = 24
    scene.gravity = (0.0, 0.0, GRAVITY)
    return scene


def activate(obj) -> None:
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def ground(size: float = 8.0, collision: bool = True):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    g = bpy.context.active_object
    g.name = "Ground"
    if collision:
        g.modifiers.new("Collision", "COLLISION")
    return g


def cylinder_between(p0: Vector, p1: Vector, radius: float, name: str):
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=d.length, location=(p0 + p1) / 2)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = d.normalized().to_track_quat("Z", "Y")
    return obj


def camera_and_light(target=(0, 0, 0.8), distance: float = 5.0, height: float = 2.2):
    cam_data = bpy.data.cameras.new("BenchCam")
    cam = bpy.data.objects.new("BenchCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (distance * 0.8, -distance, height)
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam


# ----------------------------------------------------------------------------- cases ---

def build_rigid(n: int, frames: int, rng: random.Random) -> dict:
    ground(size=12.0, collision=False)
    g = bpy.data.objects["Ground"]
    activate(g)
    bpy.ops.rigidbody.world_add()
    world = bpy.context.scene.rigidbody_world
    world.point_cache.frame_start, world.point_cache.frame_end = 1, frames
    bpy.ops.rigidbody.object_add()
    g.rigid_body.type = "PASSIVE"
    side = max(1, math.ceil(n ** (1 / 3)))
    spacing = 0.35
    for i in range(n):
        x, y, z = i % side, (i // side) % side, i // (side * side)
        loc = ((x - side / 2) * spacing + rng.uniform(-0.03, 0.03),
               (y - side / 2) * spacing + rng.uniform(-0.03, 0.03), 0.6 + z * spacing)
        if i % 2:
            bpy.ops.mesh.primitive_cube_add(size=0.2, location=loc)
            shape = "BOX"
        else:
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.08, depth=0.3, location=loc)
            shape = "CAPSULE"
        o = bpy.context.active_object
        o.rotation_euler = (rng.uniform(0, math.pi), rng.uniform(0, math.pi), 0)
        bpy.ops.rigidbody.object_add()
        o.rigid_body.collision_shape = shape
    camera_and_light(target=(0, 0, 0.4), distance=max(4.0, side * spacing * 2.2), height=side * spacing + 1.5)
    return {"bodies": n, "shapes": "alternating CAPSULE / BOX", "grid_side": side, "spacing_m": spacing}


def build_skeleton_proxy(min_length: float = 0.12) -> int:
    """Collision cylinders on the long bones of the canonical skeleton (read-only JSON)."""
    data = json.loads(SKELETON.read_text(encoding="utf-8"))
    count = 0
    for b in data["bones"]:
        h, t = b["head"], b["tail"]
        p0, p1 = Vector((h["x"], h["y"], h["z"])), Vector((t["x"], t["y"], t["z"]))
        if (p1 - p0).length < min_length:
            continue
        obj = cylinder_between(p0, p1, 0.045, f"Proxy_{b['canonical_name']}")
        obj.modifiers.new("Collision", "COLLISION")
        count += 1
    return count


def build_cloth(grid: int, frames: int, rng: random.Random) -> dict:
    ground()
    proxies = build_skeleton_proxy()
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=grid, y_subdivisions=grid, size=1.4, location=(0, 0, 1.95))
    cloth = bpy.context.active_object
    cloth.name = "Cloth"
    mod = cloth.modifiers.new("Cloth", "CLOTH")
    mod.point_cache.frame_start, mod.point_cache.frame_end = 1, frames
    mod.collision_settings.use_self_collision = False
    camera_and_light(target=(0, 0, 1.2), distance=3.2, height=1.8)
    return {"grid_vertices": grid * grid, "proxy_capsules": proxies, "quality_steps": mod.settings.quality,
            "self_collision": False}


def build_softbody(subdiv: int, frames: int, rng: random.Random) -> dict:
    ground()
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=0.3, location=(0, 0, 0.6))
    sphere = bpy.context.active_object
    sphere.name = "Tissue"
    mod = sphere.modifiers.new("Softbody", "SOFT_BODY")
    mod.point_cache.frame_start, mod.point_cache.frame_end = 1, frames
    mod.settings.use_goal = False
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(-1.2, 0, 0.6))
    imp = bpy.context.active_object
    imp.name = "Impactor"
    imp.modifiers.new("Collision", "COLLISION")
    imp.keyframe_insert("location", frame=1)
    imp.location = (0.6, 0, 0.6)
    imp.keyframe_insert("location", frame=max(2, frames // 3))
    camera_and_light(target=(0, 0, 0.4), distance=2.6, height=1.2)
    return {"vertices": len(sphere.data.vertices), "impactor": "keyframed cube, collision"}


def build_particles(n: int, frames: int, rng: random.Random) -> dict:
    ground()
    bpy.ops.mesh.primitive_cube_add(size=0.03, location=(0, 0, -5))
    inst = bpy.context.active_object
    inst.name = "ParticleShape"
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.25, location=(0, 0, 1.2))
    emitter = bpy.context.active_object
    emitter.name = "Breaker"
    emitter.modifiers.new("Particles", "PARTICLE_SYSTEM")
    psys = emitter.particle_systems[0]
    psys.seed = rng.randint(0, 10_000)
    s = psys.settings
    s.count, s.frame_start, s.frame_end, s.lifetime = n, 1, 2, frames + 10
    s.normal_factor, s.factor_random = 2.5, 1.0
    s.render_type, s.instance_object = "OBJECT", inst
    s.particle_size = 1.0
    psys.point_cache.frame_start, psys.point_cache.frame_end = 1, frames
    camera_and_light(target=(0, 0, 0.6), distance=4.5, height=2.2)
    return {"particles": n, "emission": "burst frames 1-2, normal velocity 2.5 m/s + random",
            "seed": psys.seed}


def build_geonodes(n: int, frames: int, rng: random.Random) -> dict:
    bpy.ops.mesh.primitive_plane_add(size=0.1, location=(0, 0, 0))
    host = bpy.context.active_object
    host.name = "SimHost"
    tree = bpy.data.node_groups.new("CE_BenchSim", "GeometryNodeTree")
    nodes, links = tree.nodes, tree.links
    tree.outputs.new("NodeSocketGeometry", "Geometry")
    out = nodes.new("NodeGroupOutput")
    pts = nodes.new("GeometryNodePoints")
    pts.inputs["Count"].default_value = n
    rnd = nodes.new("FunctionNodeRandomValue")
    rnd.data_type = "FLOAT_VECTOR"
    rnd.inputs["Min"].default_value = (-1.5, -1.5, 1.0)
    rnd.inputs["Max"].default_value = (1.5, 1.5, 3.0)
    rnd.inputs["Seed"].default_value = rng.randint(0, 10_000)
    links.new(rnd.outputs["Value"], pts.inputs["Position"])
    sim_in = nodes.new("GeometryNodeSimulationInput")
    sim_out = nodes.new("GeometryNodeSimulationOutput")
    sim_in.pair_with_output(sim_out)
    links.new(pts.outputs["Geometry"], sim_in.inputs["Geometry"])
    setpos = nodes.new("GeometryNodeSetPosition")
    fall = nodes.new("ShaderNodeVectorMath")
    fall.operation = "SCALE"
    fall.inputs[0].default_value = (0.0, 0.0, -1.5)          # constant fall speed (m/s), gameplay-style
    links.new(sim_in.outputs["Delta Time"], fall.inputs["Scale"])
    links.new(fall.outputs["Vector"], setpos.inputs["Offset"])
    links.new(sim_in.outputs["Geometry"], setpos.inputs["Geometry"])
    links.new(setpos.outputs["Geometry"], sim_out.inputs["Geometry"])
    cube = nodes.new("GeometryNodeMeshCube")
    cube.inputs["Size"].default_value = (0.03, 0.03, 0.03)
    inst = nodes.new("GeometryNodeInstanceOnPoints")
    links.new(sim_out.outputs["Geometry"], inst.inputs["Points"])
    links.new(cube.outputs["Mesh"], inst.inputs["Instance"])
    links.new(inst.outputs["Instances"], out.inputs["Geometry"])
    mod = host.modifiers.new("Sim", "NODES")
    mod.node_group = tree
    ground(collision=False)
    camera_and_light(target=(0, 0, 1.2), distance=5.0, height=2.5)
    return {"points": n, "motion": "constant fall 1.5 m/s in a simulation zone (no collision)"}


def build_fluid(resolution: int, frames: int, rng: random.Random) -> dict:
    cache = Path(tempfile.mkdtemp(prefix="ce_fluid_"))
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 1.0))
    domain = bpy.context.active_object
    domain.name = "FluidDomain"
    mod = domain.modifiers.new("Fluid", "FLUID")
    mod.fluid_type = "DOMAIN"
    ds = mod.domain_settings
    ds.domain_type = "LIQUID"
    ds.resolution_max = resolution
    ds.cache_directory = str(cache)
    ds.cache_type = "REPLAY"
    ds.cache_frame_start, ds.cache_frame_end = 1, frames
    ds.use_mesh = True
    domain.display_type = "WIRE"
    bpy.ops.mesh.primitive_cube_add(size=0.6, location=(0, 0, 1.5))
    flow = bpy.context.active_object
    flow.name = "LiquidBlock"
    fmod = flow.modifiers.new("Fluid", "FLUID")
    fmod.fluid_type = "FLOW"
    fmod.flow_settings.flow_type = "LIQUID"
    fmod.flow_settings.flow_behavior = "GEOMETRY"
    flow.hide_render = True
    camera_and_light(target=(0, 0, 0.6), distance=4.0, height=2.6)
    return {"resolution_max": resolution, "cache": "REPLAY (temporary directory)", "mesh": True}


CASES = {"rigid": build_rigid, "cloth": build_cloth, "softbody": build_softbody,
         "particles": build_particles, "geonodes": build_geonodes, "fluid": build_fluid}


# ----------------------------------------------------------------------------- run ---

def render_workbench(scene, path: Path, frame: int, resolution=(960, 540)) -> float:
    scene.frame_set(frame)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    t = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    return time.perf_counter() - t


def run_case(case: str, size: int, frames: int, seed: int, render: Path | None) -> dict:
    rng = random.Random(seed)
    scene = reset_scene(frames)
    mem0 = memory_mb()
    t0 = time.perf_counter()
    params = CASES[case](size, frames, rng)
    setup_s = time.perf_counter() - t0

    per_frame = []
    for f in range(1, frames + 1):                       # first pass: simulate (fills the point caches)
        t = time.perf_counter()
        scene.frame_set(f)
        per_frame.append(time.perf_counter() - t)
    sim_s = sum(per_frame)

    t = time.perf_counter()                               # second pass: cached evaluation (playback proxy)
    for f in range(1, frames + 1):
        scene.frame_set(f)
    replay_s = time.perf_counter() - t

    key = max(1, round(frames * KEY_FRACTION))
    render_s = render_workbench(scene, render, key) if render else None
    mem1 = memory_mb()
    return {
        "case": case, "size": size, "frames": frames, "seed": seed, "status": "ok",
        "blender": bpy.app.version_string, "provenance": "ESTIMATE",
        "conditions": {"gravity_m_s2": GRAVITY, "fps": scene.render.fps, **params},
        "setup_s": round(setup_s, 3),
        "sim_s_total": round(sim_s, 3),
        "sim_s_per_frame": round(sim_s / frames, 4),
        "sim_s_per_frame_max": round(max(per_frame), 4),
        "replay_s_per_frame": round(replay_s / frames, 4),
        "replay_fps": round(frames / replay_s, 1) if replay_s > 0 else None,
        "render_key_frame": key if render else None,
        "render_s": round(render_s, 3) if render_s is not None else None,
        "render_resolution": [960, 540] if render else None,
        "ram_start_mb": mem0["current_mb"], "ram_peak_mb": mem1["peak_mb"],
    }


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=sorted(CASES), required=True)
    ap.add_argument("--size", type=int, required=True)
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--render", type=Path, default=None)
    a = ap.parse_args(argv)
    print(f"[bench] {a.case} size={a.size} frames={a.frames} seed={a.seed}", flush=True)
    try:
        result = run_case(a.case, a.size, a.frames, a.seed, a.render)
    except Exception as exc:  # noqa: BLE001 - recorded in the result, the driver decides
        result = {"case": a.case, "size": a.size, "frames": a.frames, "seed": a.seed, "status": "error",
                  "error": f"{type(exc).__name__}: {exc}", "provenance": "ESTIMATE"}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[bench] {json.dumps(result)}", flush=True)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
