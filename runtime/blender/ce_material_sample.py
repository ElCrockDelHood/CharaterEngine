"""Material sample 1 — Blender scene + EEVEE / Cycles renders of the pure-Python result.

    blender -b --factory-startup --python runtime/blender/ce_material_sample.py -- \
        --input builds/material_sample/<UTC> --out builds/material_sample/<UTC> \
        --engines eevee,cycles --samples 256 --resolution 1920x1080 [--turntable 48]
    blender -b --factory-startup --python runtime/blender/ce_material_sample.py -- --gpu-probe --out <dir>

Driven by ``scripts/material_sample.py``. Blender computes nothing physical here: it draws the layered capsule
(cutaway specimen: bone, tendon, muscle, fat, skin, sleeve, bracer), the settled and cut XPBD sleeve and the blade
at its stopping depth, all read from the variant JSON files. Both variants sit side by side (unarmored on the left, seen from +X).

Materials map OpenPBR parameters from ``domain/materials/catalog.py`` onto the Principled BSDF (both the 3.x and
the 4.x+ socket names). Optical values are ASSUMED look-dev, not measurements.
Works with Blender 3.6 and 4.x / 5.x (EEVEE engine id and Principled sockets are probed at run time).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

try:
    import bmesh  # type: ignore
    import bpy  # type: ignore
    from mathutils import Matrix, Vector  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("run inside Blender: blender -b --python ...") from exc

WEDGE_HALF_ANGLE = math.radians(50.0)    # cutaway opening around +X (lateral), presentation only
SEGMENTS = 64
VARIANT_Y = {"unarmored": -0.12, "armored": 0.12}  # axes moved to x = 0, side by side in Y (presentation)


# --------------------------------------------------------------------------- materials (OpenPBR → Principled)
def _set(node, names, value):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return True
    return False


def principled_from_openpbr(name: str, opt: dict):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    rgba = lambda c: (c[0], c[1], c[2], 1.0)  # noqa: E731
    _set(bsdf, ["Base Color"], rgba(opt["base_color"]))
    _set(bsdf, ["Metallic"], opt["base_metalness"])
    _set(bsdf, ["Roughness"], opt["specular_roughness"])
    _set(bsdf, ["IOR"], opt["specular_ior"])
    sss = opt["subsurface_weight"]
    if sss > 0:
        radius = [s * opt["subsurface_radius"] for s in opt["subsurface_radius_scale"]]
        if "Subsurface Weight" in bsdf.inputs:                      # Blender 4.x+
            _set(bsdf, ["Subsurface Weight"], sss)
            _set(bsdf, ["Subsurface Scale"], 1.0)
            _set(bsdf, ["Subsurface Radius"], radius)
        else:                                                       # Blender 3.x
            _set(bsdf, ["Subsurface"], sss * opt["subsurface_radius"] * 50.0)
            _set(bsdf, ["Subsurface Radius"], [r / max(opt["subsurface_radius"], 1e-6) for r in radius])
            _set(bsdf, ["Subsurface Color"], rgba(opt["subsurface_color"]))
    if opt["fuzz_weight"] > 0:
        _set(bsdf, ["Sheen Weight", "Sheen"], opt["fuzz_weight"])
        _set(bsdf, ["Sheen Tint"], rgba(opt["fuzz_color"]) if "Sheen Weight" in bsdf.inputs else 0.5)
        _set(bsdf, ["Sheen Roughness"], opt["fuzz_roughness"])
    if opt["coat_weight"] > 0:
        _set(bsdf, ["Coat Weight", "Clearcoat"], opt["coat_weight"])
        _set(bsdf, ["Coat Roughness", "Clearcoat Roughness"], opt["coat_roughness"])
    mat["ce_provenance"] = opt.get("provenance", "assumed")
    mat["ce_openpbr"] = json.dumps(opt)
    return mat


# --------------------------------------------------------------------------- geometry
def _frame(a: Vector, b: Vector):
    """Orthonormal frame with axis u = a→b and e1 = canonical +X (lateral) projected off the axis."""
    u = (b - a).normalized()
    e1 = Vector((1.0, 0.0, 0.0))
    e1 = (e1 - u * e1.dot(u)).normalized()
    e2 = u.cross(e1)
    return u, e1, e2


def shell_sector(name: str, a: Vector, b: Vector, r_in: float, r_out: float, t0: float = 0.0, t1: float = 1.0,
                 wedge: float = WEDGE_HALF_ANGLE):
    """Closed annular sector solid around a→b, open over ±wedge around +X (the cutaway)."""
    u, e1, e2 = _frame(a, b)
    p0, p1 = a + (b - a) * t0, a + (b - a) * t1
    angs = [wedge + (2 * math.pi - 2 * wedge) * i / SEGMENTS for i in range(SEGMENTS + 1)]
    bm = bmesh.new()

    def ring(center, r):
        return [bm.verts.new(center + (e1 * math.cos(t) + e2 * math.sin(t)) * r) for t in angs]

    rings = {}
    for key, c, r in (("o0", p0, r_out), ("o1", p1, r_out), ("i0", p0, r_in), ("i1", p1, r_in)):
        rings[key] = ring(c, max(r, 1e-5))
    n = len(angs)
    for i in range(n - 1):
        bm.faces.new((rings["o0"][i], rings["o0"][i + 1], rings["o1"][i + 1], rings["o1"][i]))
        bm.faces.new((rings["i1"][i], rings["i1"][i + 1], rings["i0"][i + 1], rings["i0"][i]))
        bm.faces.new((rings["i0"][i], rings["i0"][i + 1], rings["o0"][i + 1], rings["o0"][i]))
        bm.faces.new((rings["o1"][i], rings["o1"][i + 1], rings["i1"][i + 1], rings["i1"][i]))
    for j in (0, n - 1):                                            # radial cut faces of the wedge
        bm.faces.new((rings["i0"][j], rings["o0"][j], rings["o1"][j], rings["i1"][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def sleeve_object(name: str, verts, faces, thickness: float, axis_a: Vector, axis_b: Vector, shift: Vector):
    """Sleeve mesh from the XPBD positions; faces inside the cutaway wedge are dropped so the layers show."""
    u, e1, e2 = _frame(axis_a, axis_b)
    keep = []
    for f in faces:
        c = sum((Vector(verts[i]) for i in f), Vector()) / len(f)
        rel = c - axis_a
        radial = rel - u * rel.dot(u)
        ang = math.atan2(radial.dot(e2), radial.dot(e1))
        if abs(ang) > WEDGE_HALF_ANGLE:
            keep.append(f)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(Vector(v) + shift) for v in verts], [], [tuple(f) for f in keep])
    me.update()
    for poly in me.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    sol = obj.modifiers.new("thickness", "SOLIDIFY")
    sol.thickness, sol.offset = thickness, 0.0
    obj.modifiers.new("smooth", "SUBSURF").levels = 1
    return obj


def blade_object(name: str, ends, width: float, thickness: float, strike_dir: Vector, shift: Vector):
    """Sabre section: the edge line is where the domain says it stopped; the blade body trails behind it."""
    a, b = Vector(ends[0]) + shift, Vector(ends[1]) + shift
    edge = (b - a).normalized()
    back = -strike_dir.normalized()
    side = edge.cross(back).normalized()
    centre = (a + b) / 2 + back * (width / 2)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=centre)
    obj = bpy.context.active_object
    obj.name = name
    rot = Matrix((edge, back, side)).transposed().to_4x4()
    obj.matrix_world = Matrix.Translation(centre) @ rot @ Matrix.Diagonal(((b - a).length, width, thickness, 1.0))
    bev = obj.modifiers.new("edge", "BEVEL")
    bev.width, bev.segments = thickness * 0.4, 2
    return obj


# --------------------------------------------------------------------------- scene
def build_variant(r: dict, mats: dict):
    shift = Vector((-r["placement"]["a"][0], VARIANT_Y[r["variant"]], 0.0))
    a = Vector(r["placement"]["a"]) + shift
    b = Vector(r["placement"]["b"]) + shift
    objs = []
    for s in r["shells"]:
        if s["material"] in ("air", "cloth_wool"):
            continue                                   # sleeve comes from the XPBD mesh
        t0, t1 = (s["z_range"] or (0.0, 1.0))
        o = shell_sector(f"{r['variant']}_{s['name']}", a, b, s["r_inner_m"], s["r_outer_m"], t0, t1)
        o.data.materials.append(mats[s["material"]])
        o["ce_provenance"] = s["provenance"]
        objs.append(o)
    last = r["frames"][-1]
    sl = sleeve_object(f"{r['variant']}_sleeve", last["sleeve"], r["sleeve"]["faces"],
                       r["config"]["sleeve_thickness_m"], Vector(r["placement"]["a"]), Vector(r["placement"]["b"]),
                       shift)
    sl.data.materials.append(mats["cloth_wool"])
    objs.append(sl)
    if "blade" in last:
        bl = blade_object(f"{r['variant']}_blade", last["blade"], r["config"]["blade_width_m"], 0.005,
                          Vector((0.0, 1.0, 0.0)), shift)
        bl.data.materials.append(mats["armor_steel"])
        bl["ce_provenance"] = "PLACEHOLDER sabre section"
        objs.append(bl)
    return objs, (a + b) / 2


def setup_world_and_lights(target: Vector):
    world = bpy.data.worlds.new("CE_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.022, 0.026, 1.0)
    for name, loc, energy, size in (("key", (0.9, -0.7, 1.6), 120.0, 0.6), ("fill", (-0.8, -0.9, 1.1), 35.0, 0.9),
                                    ("rim", (0.2, 0.9, 1.4), 80.0, 0.4)):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.size = energy, size
        obj = bpy.data.objects.new(name, light)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0.0, 0.0, target.z - 0.18))
    floor = bpy.context.active_object
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.05, 0.055, 1.0)
    fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
    floor.data.materials.append(fm)


def camera(name: str, location, target: Vector, lens: float):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = lens
    cam.location = location
    cam.rotation_euler = (target - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return cam


# --------------------------------------------------------------------------- engines
def eevee_id() -> str:
    items = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    return "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in items else "BLENDER_EEVEE"


def setup_cycles_device(scene) -> str:
    """Enable the first GPU backend that lists a device (OptiX, CUDA, HIP, oneAPI, Metal); else CPU."""
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return "CPU (cycles add-on preferences unavailable)"
    for backend in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue
        devices = prefs.get_devices_for_type(backend) if hasattr(prefs, "get_devices_for_type") else None
        if devices is None:
            prefs.get_devices()
            devices = [d for d in prefs.devices if d.type == backend]
        gpus = [d for d in devices if d.type == backend]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == backend
            scene.cycles.device = "GPU"
            return f"GPU {backend}: " + ", ".join(d.name for d in gpus)
    return "CPU"


def gpu_probe(out: Path) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    bpy.ops.mesh.primitive_uv_sphere_add()
    cam = camera("probe", (3.0, -3.0, 2.0), Vector((0, 0, 0)), 50.0)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = 128
    scene.cycles.samples = 16
    result = {"blender": bpy.app.version_string, "device": setup_cycles_device(scene)}
    scene.render.filepath = str(out / "gpu_probe.png")
    t = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    result["render_s"] = round(time.perf_counter() - t, 3)
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        result["all_devices"] = [{"name": d.name, "type": d.type} for d in prefs.devices]
    except KeyError:
        pass
    return result


def render_still(scene, path: Path, engine: str, samples: int, device: str) -> dict:
    scene.render.filepath = str(path)
    if engine == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    else:
        scene.render.engine = eevee_id()
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 64
        for attr in ("use_gtao", "use_ssr", "use_soft_shadows"):
            if hasattr(scene.eevee, attr):
                setattr(scene.eevee, attr, True)
    t = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    return {"path": str(path), "engine": scene.render.engine, "samples": samples if engine == "cycles" else 64,
            "device": device if engine == "cycles" else "GPU (EEVEE)", "seconds": round(time.perf_counter() - t, 2)}


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--engines", default="eevee,cycles")
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--resolution", default="1920x1080")
    ap.add_argument("--turntable", type=int, default=0)
    ap.add_argument("--gpu-probe", action="store_true")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)

    if a.gpu_probe:
        res = gpu_probe(a.out)
        (a.out / "gpu_probe.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"[material] {json.dumps(res)}", flush=True)
        return 0

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    variants = [json.loads((a.input / f"forearm_{v}.json").read_text(encoding="utf-8"))
                for v in ("unarmored", "armored")]
    mats = {row["kind"]: principled_from_openpbr(row["kind"], row["optical_openpbr"])
            for row in variants[0]["materials"] if row["optical_openpbr"]}
    centres = {}
    for r in variants:
        _, centres[r["variant"]] = build_variant(r, mats)
    target = (centres["unarmored"] + centres["armored"]) / 2
    setup_world_and_lights(target)
    wide = camera("cam_comparison", target + Vector((0.62, -0.18, 0.2)), target, 50.0)  # +X: wedges face it
    w, h = (int(x) for x in a.resolution.lower().split("x"))
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.image_settings.file_format = "PNG"
    device = setup_cycles_device(scene) if "cycles" in a.engines else "-"
    engines = [e.strip() for e in a.engines.split(",") if e.strip()]
    report = {"blender": bpy.app.version_string, "cycles_device": device, "resolution": a.resolution,
              "renders": [], "provenance": "geometry from domain JSON (ESTIMATE); optics ASSUMED"}
    for eng in engines:
        scene.camera = wide
        report["renders"].append(render_still(scene, a.out / f"comparison_{eng}.png", eng, a.samples, device))
        print(f"[material] {json.dumps(report['renders'][-1])}", flush=True)
    if "cycles" in engines:
        for v, c in centres.items():
            close = camera(f"cam_{v}", c + Vector((0.22, -0.16, 0.08)), c, 85.0)
            scene.camera = close
            report["renders"].append(render_still(scene, a.out / f"closeup_{v}_cycles.png", "cycles", a.samples,
                                                  device))
            print(f"[material] {json.dumps(report['renders'][-1])}", flush=True)
    if a.turntable > 0:
        pivot = bpy.data.objects.new("turntable_pivot", None)
        scene.collection.objects.link(pivot)
        pivot.location = target
        orbit = camera("cam_turntable", target + Vector((0.6, 0.0, 0.2)), target, 60.0)
        orbit.parent = pivot
        orbit.matrix_parent_inverse = pivot.matrix_world.inverted()
        scene.camera = orbit
        scene.render.engine = eevee_id()
        tt_dir = a.out / "turntable"
        tt_dir.mkdir(exist_ok=True)
        t = time.perf_counter()
        for i in range(a.turntable):
            pivot.rotation_euler = (0.0, 0.0, 2 * math.pi * i / a.turntable)
            scene.render.filepath = str(tt_dir / f"tt_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
        report["turntable"] = {"frames": a.turntable, "dir": str(tt_dir), "seconds": round(time.perf_counter() - t, 1)}
    blend = a.out / "material_sample.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    report["blend"] = str(blend.resolve())
    (a.out / "render_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[material] done {json.dumps({k: v for k, v in report.items() if k != 'renders'})}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
