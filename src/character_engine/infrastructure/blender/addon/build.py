"""bpy builders: armature, tissue proxies, control rig, mocap retarget, wounds.

Every function takes plain domain data (bone dicts, ``MuscleSpec``…) and produces Blender
objects tagged with custom properties (``ce_role``, ``ce_layer``, ``ce_provenance``) so the
State Auditor and the exporters can tell canonical content from proxies.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

from character_engine.domain.anatomy.osteometry import LONG_BONES, load_osteometry
from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.animation import BoneMap
from character_engine.domain.rigging import EquipmentSocket, RigDefinition, socket_points
from character_engine.domain.tissue import MUSCLES, BodyRegion, TissueLayer, region_of_bone, tissue_profile
from character_engine.domain.trauma import Wound, WoundAssessment, WoundType, assess_wound

Vec3 = Tuple[float, float, float]

# Bones excluded from proxy geometry (too small / inside cavities) and from the skin graph.
_TINY = {"STAPES", "INCUS", "MALLEUS", "LACRIMAL", "VOMER", "INFERIOR_NASAL_CONCHA", "PALATINE", "ETHMOID"}
# Approximate limb / trunk envelope radii for the skin graph (ESTIMATE, proxy only).
_SKIN_RADIUS_BY_REGION = {
    BodyRegion.HEAD: 0.085, BodyRegion.NECK: 0.06, BodyRegion.THORAX: 0.13, BodyRegion.ABDOMEN: 0.13,
    BodyRegion.PELVIS: 0.14, BodyRegion.UPPER_ARM: 0.05, BodyRegion.FOREARM: 0.04, BodyRegion.HAND: 0.018,
    BodyRegion.THIGH: 0.08, BodyRegion.LEG: 0.055, BodyRegion.FOOT: 0.03,
}


# --------------------------------------------------------------------------- helpers -------

def _v(d) -> Vector:
    return Vector((d["x"], d["y"], d["z"])) if isinstance(d, dict) else Vector(d)


def _is_tiny(name: str) -> bool:
    return any(name.startswith(t) for t in _TINY)


def _collection(context, name: str) -> bpy.types.Collection:
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        context.scene.collection.children.link(coll)
    return coll


def _link(context, obj, coll_name: str) -> None:
    coll = _collection(context, coll_name)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def _align_z(p0: Vector, p1: Vector) -> Tuple[Matrix, float]:
    axis = p1 - p0
    length = axis.length
    if length < 1e-9:
        return Matrix.Translation(p0), 0.0
    rot = axis.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    return Matrix.Translation((p0 + p1) / 2) @ rot, length


def _cone(bm, p0: Vector, p1: Vector, r0: float, r1: float, segments: int = 8) -> List:
    mat, length = _align_z(p0, p1)
    if length <= 0:
        return []
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                                radius1=max(r0, 1e-4), radius2=max(r1, 1e-4), depth=length, matrix=mat)
    return res["verts"]


def _mesh_object(context, name: str, bm, coll: str, props: Mapping[str, object]) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    _link(context, obj, coll)
    for k, val in props.items():
        obj[k] = val
    return obj


def _assign_weights(obj, groups: Dict[str, List[Tuple[int, float]]]) -> None:
    for bone, pairs in groups.items():
        vg = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
        for idx, w in pairs:
            vg.add([idx], w, "REPLACE")


def _bind(obj, armature) -> None:
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = armature
    obj.parent = armature


def _material(name: str, rgba: Tuple[float, float, float, float]):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = rgba
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgba
    return mat


# Bone layers DEF/MCH/CTRL: bone collections on Blender 4.x, armature layer index on Blender 3.6
# (no ``Armature.collections`` before 4.0). ``ce_layer`` records the role on both.
_LAYER_INDEX = {"DEF": 0, "MCH": 1, "CTRL": 2}


def assign_bone_layer(arm_data, bone, layer: str) -> None:
    bone["ce_layer"] = layer
    if hasattr(arm_data, "collections"):
        coll = arm_data.collections.get(layer) or arm_data.collections.new(layer)
        coll.assign(bone)
    else:
        idx = _LAYER_INDEX[layer]
        bone.layers = [i == idx for i in range(32)]
        arm_data.layers[idx] = True


def bone_layer_names(arm_data) -> List[str]:
    """Names of the DEF/MCH/CTRL layers that hold at least one bone (either Blender API)."""
    if hasattr(arm_data, "collections"):
        return sorted(c.name for c in arm_data.collections if c.name in _LAYER_INDEX and len(c.bones))
    return sorted(name for name, idx in _LAYER_INDEX.items() if any(b.layers[idx] for b in arm_data.bones))


def bone_points(armature) -> Dict[str, Tuple[Vector, Vector]]:
    """World-space (head, tail) of every bone from the rest pose."""
    mw = armature.matrix_world
    return {b.name: (mw @ b.head_local, mw @ b.tail_local) for b in armature.data.bones}


# --------------------------------------------------------------------------- armature ------

def clear_character(context, name: str) -> int:
    removed = 0
    for obj in list(bpy.data.objects):
        if obj.get("ce_character") == name:
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    for coll_name in (f"{name}", f"{name}_Tissues", f"{name}_Wounds", f"{name}_Mocap", f"{name}_Equipment",
                      f"{name}_Cinematic"):
        coll = bpy.data.collections.get(coll_name)
        if coll and not coll.objects and not coll.children:
            bpy.data.collections.remove(coll)
    return removed


def build_armature(context, bones: Sequence[dict], containers: Sequence[dict], name: str,
                   meta: Optional[Mapping[str, object]] = None):
    """Create the 208-node canonical armature (Z-up metres == Blender units)."""
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    _link(context, arm, name)
    arm["ce_character"] = name
    arm["ce_role"] = "canonical_armature"
    for k, val in (meta or {}).items():
        arm[k] = val if not isinstance(val, (dict, list)) else json.dumps(val)

    context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    children: Dict[str, List[dict]] = {}
    for b in bones:
        children.setdefault(b["parent"], []).append(b)

    created = {}
    for c in containers:
        e = eb.new(c["canonical_name"])
        kids = children.get(c["canonical_name"], [])
        if kids and c["canonical_name"] != "ROOT_SKELETON":
            centre = sum((_v(k["head"]) for k in kids), Vector()) / len(kids)
        else:
            centre = Vector((0.0, 0.0, 0.0))
        e.head, e.tail = centre, centre + Vector((0, 0, 0.05))
        e.use_deform = False
        created[c["canonical_name"]] = e
    for b in bones:
        e = eb.new(b["canonical_name"])
        e.head, e.tail = _v(b["head"]), _v(b["tail"])
        if (e.tail - e.head).length < 1e-5:
            e.tail = e.head + Vector((0, 0, 0.005))
        created[b["canonical_name"]] = e
    for c in containers:
        if c.get("parent"):
            created[c["canonical_name"]].parent = created[c["parent"]]
    for b in bones:
        if b.get("parent") in created:
            created[b["canonical_name"]].parent = created[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")

    for bone in arm_data.bones:
        assign_bone_layer(arm_data, bone, "DEF")
        bone["ce_canonical"] = True
    return arm


# --------------------------------------------------------------------------- tissues -------

def _asset_mesh_path(root: Path, bone: str) -> Optional[Path]:
    for ext in (".glb", ".gltf", ".obj", ".ply"):
        p = root / "assets" / "anatomy" / "meshes" / f"{bone}{ext}"
        if p.exists():
            return p
    return None


def _import_asset(path: Path):
    before = set(bpy.data.objects)
    if path.suffix in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif path.suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    elif path.suffix == ".ply":
        bpy.ops.wm.ply_import(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    return new[0] if new else None


def _fit_asset(obj, head: Vector, tail: Vector, target_length: float) -> None:
    """Scale the asset so its longest bbox axis == target_length, align it to head→tail."""
    dims = obj.dimensions
    longest = max(dims) if max(dims) > 0 else 1.0
    s = target_length / longest
    axis_idx = list(dims).index(max(dims))
    local_axis = Vector([1.0 if i == axis_idx else 0.0 for i in range(3)])
    q = local_axis.rotation_difference((tail - head).normalized())
    obj.matrix_world = Matrix.Translation((head + tail) / 2) @ q.to_matrix().to_4x4() @ Matrix.Scale(s, 4)


def build_bone_meshes(context, armature, stature_m: float, population: str = "male_white",
                      prefer_assets: bool = True, repo_root: Optional[Path] = None):
    """Proxy (or fitted asset) meshes for every bone, skinned to the armature."""
    table = load_osteometry()
    lengths = table.lengths_for_stature(stature_m, population)
    name = armature["ce_character"]
    pts = bone_points(armature)
    bm = bmesh.new()
    groups: Dict[str, List[Tuple[int, float]]] = {}
    provenance: Dict[str, str] = {}
    fitted = 0

    for bone in armature.data.bones:
        n = bone.name
        if not bone.get("ce_canonical") or n in ("ROOT_SKELETON", "CRANIUM") or _is_tiny(n):
            continue
        head, tail = pts[n]
        seg_len = (tail - head).length
        if seg_len < 1e-5:
            continue
        base = n[:-2] if n.endswith(("_L", "_R")) else n
        asset = _asset_mesh_path(repo_root, base) if (prefer_assets and repo_root) else None
        if asset is not None:
            obj = _import_asset(asset)
            if obj is not None:
                target = lengths.get(base, seg_len)
                _fit_asset(obj, head, tail, target)
                obj.name = f"{name}_BONE_{n}"
                obj["ce_character"], obj["ce_role"], obj["ce_layer"] = name, "tissue", "bone"
                obj["ce_provenance"] = "USER_INPUT"
                _link(context, obj, f"{name}_Tissues")
                vg = obj.vertex_groups.new(name=n)
                vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
                _bind(obj, armature)
                fitted += 1
                continue

        start = len(bm.verts)
        if base in lengths:
            # Osteometric maximum length centred on the joint segment; shaft diameter from the table.
            L = lengths[base]
            axis = (tail - head).normalized()
            mid = (head + tail) / 2
            p0, p1 = mid - axis * (L / 2), mid + axis * (L / 2)
            r_shaft = table.shaft_diameters_m.get(base, 0.02) / 2
            r_epi = r_shaft * 1.9
            epi = min(0.12 * L, 0.06)
            _cone(bm, p0, p0 + axis * epi, r_epi, r_shaft, segments=10)
            _cone(bm, p0 + axis * epi, p1 - axis * epi, r_shaft, r_shaft, segments=10)
            _cone(bm, p1 - axis * epi, p1, r_shaft, r_epi, segments=10)
            provenance[n] = "DERIVED_LENGTH/ESTIMATE_SHAPE"
        else:
            region = region_of_bone(n)
            thickness = tissue_profile(region).thickness_m.get(TissueLayer.BONE, 0.01)
            r = max(0.003, min(0.02, thickness * 0.6))
            _cone(bm, head, tail, r, r * 0.85, segments=6)
            provenance[n] = "ESTIMATE"
        bm.verts.ensure_lookup_table()
        groups[n] = [(i, 1.0) for i in range(start, len(bm.verts))]

    obj = _mesh_object(context, f"{name}_Bones", bm, f"{name}_Tissues", {
        "ce_character": name, "ce_role": "tissue", "ce_layer": "bone", "ce_provenance": "ESTIMATE",
        "ce_osteometry_population": population, "ce_bone_provenance": json.dumps(provenance),
    })
    obj.data.materials.append(_material("CE_Bone", (0.92, 0.88, 0.78, 1.0)))
    _assign_weights(obj, groups)
    _bind(obj, armature)
    return obj, fitted


def _point_on(head: Vector, tail: Vector, t: float) -> Vector:
    return head.lerp(tail, t)


def build_muscle_meshes(context, armature, with_tendons: bool = True):
    """Spindle proxies for the muscle catalogue, weighted between origin and insertion bones."""
    name = armature["ce_character"]
    pts = bone_points(armature)
    bm_m, bm_t = bmesh.new(), bmesh.new()
    g_m: Dict[str, List[Tuple[int, float]]] = {}
    g_t: Dict[str, List[Tuple[int, float]]] = {}
    count = 0
    for m in MUSCLES.values():
        if m.origin_bone not in pts or m.insertion_bone not in pts:
            continue
        o = _point_on(*pts[m.origin_bone], m.origin_t)
        i = _point_on(*pts[m.insertion_bone], m.insertion_t)
        total = (i - o).length
        if total < 1e-4:
            continue
        axis = (i - o) / total
        f = m.tendon_fraction if with_tendons else 0.0
        r_t = max(0.002, m.radius_m * 0.3)
        a, b = o + axis * (total * f), i - axis * (total * f)
        # belly (two cones meeting at the mid-belly)
        start = len(bm_m.verts)
        mid = (a + b) / 2
        _cone(bm_m, a, mid, r_t if with_tendons else r_t * 1.5, m.radius_m)
        _cone(bm_m, mid, b, m.radius_m, r_t if with_tendons else r_t * 1.5)
        bm_m.verts.ensure_lookup_table()
        for idx in range(start, len(bm_m.verts)):
            s = max(0.0, min(1.0, (bm_m.verts[idx].co - o).dot(axis) / total))
            g_m.setdefault(m.origin_bone, []).append((idx, 1.0 - s))
            g_m.setdefault(m.insertion_bone, []).append((idx, s))
        if with_tendons and f > 0:
            st = len(bm_t.verts)
            _cone(bm_t, o, a, r_t * 0.8, r_t, segments=6)
            bm_t.verts.ensure_lookup_table()
            g_t.setdefault(m.origin_bone, []).extend((k, 1.0) for k in range(st, len(bm_t.verts)))
            st = len(bm_t.verts)
            _cone(bm_t, b, i, r_t, r_t * 0.8, segments=6)
            bm_t.verts.ensure_lookup_table()
            g_t.setdefault(m.insertion_bone, []).extend((k, 1.0) for k in range(st, len(bm_t.verts)))
        count += 1

    muscles = _mesh_object(context, f"{name}_Muscles", bm_m, f"{name}_Tissues", {
        "ce_character": name, "ce_role": "tissue", "ce_layer": "muscle",
        "ce_provenance": "PROVEN_ATTACHMENTS/ESTIMATE_GEOMETRY", "ce_muscle_count": count})
    muscles.data.materials.append(_material("CE_Muscle", (0.55, 0.12, 0.12, 1.0)))
    _assign_weights(muscles, g_m)
    _bind(muscles, armature)
    tendons = None
    if with_tendons:
        tendons = _mesh_object(context, f"{name}_Tendons", bm_t, f"{name}_Tissues", {
            "ce_character": name, "ce_role": "tissue", "ce_layer": "tendon", "ce_provenance": "ESTIMATE"})
        tendons.data.materials.append(_material("CE_Tendon", (0.9, 0.9, 0.85, 1.0)))
        _assign_weights(tendons, g_t)
        _bind(tendons, armature)
    else:
        bm_t.free()
    return muscles, tendons, count


def _nearest_bone(point: Vector, pts: Mapping[str, Tuple[Vector, Vector]], names: Iterable[str]) -> Tuple[str, float]:
    best, best_d = "", float("inf")
    for n in names:
        h, t = pts[n]
        seg = t - h
        L2 = seg.length_squared
        u = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, (point - h).dot(seg) / L2))
        d = (point - (h + seg * u)).length
        if d < best_d:
            best, best_d = n, d
    return best, best_d


def build_skin_envelope(context, armature, subdivisions: int = 2):
    """Skin-modifier envelope over the major bones; weights = nearest bone (deterministic)."""
    name = armature["ce_character"]
    pts = bone_points(armature)
    major = [b.name for b in armature.data.bones
             if b.get("ce_canonical") and b.name not in ("ROOT_SKELETON", "CRANIUM") and not _is_tiny(b.name)
             and not any(k in b.name for k in ("PHALANX", "RIB_", "CARPAL", "SCAPHOID", "LUNATE", "TRIQUETRUM",
                                                "PISIFORM", "TRAPEZ", "CAPITATE", "HAMATE", "CUNEIFORM", "CUBOID",
                                                "NAVICULAR", "METATARSAL_2", "METATARSAL_4", "METACARPAL_2",
                                                "METACARPAL_4", "HYOID", "PATELLA", "MAXILLA", "NASAL", "ZYGOMATIC",
                                                "SPHENOID", "TEMPORAL", "PARIETAL", "FRONTAL", "OCCIPITAL", "MANDIBLE"))]
    bm = bmesh.new()
    vert_of: Dict[Tuple[float, float, float], object] = {}
    radii: Dict[object, float] = {}

    def vert(p: Vector, r: float):
        key = (round(p.x, 4), round(p.y, 4), round(p.z, 4))
        v = vert_of.get(key)
        if v is None:
            v = bm.verts.new(p)
            vert_of[key] = v
            radii[v] = r
        else:
            radii[v] = max(radii[v], r)
        return v

    for n in major:
        h, t = pts[n]
        region = region_of_bone(n)
        r = _SKIN_RADIUS_BY_REGION[region]
        v0, v1 = vert(h, r), vert(t, r)
        if v0 is not v1:
            try:
                bm.edges.new((v0, v1))
            except ValueError:
                pass
    # Head: a single fat vertex at the cranial centroid connected to CERVICAL_1.
    if "CERVICAL_1" in pts:
        skull = sum((pts[b.name][0] for b in armature.data.bones if b.name in ("FRONTAL", "OCCIPITAL", "PARIETAL_L", "PARIETAL_R")), Vector()) / 4
        vs = vert(skull, _SKIN_RADIUS_BY_REGION[BodyRegion.HEAD])
        vc = vert(pts["CERVICAL_1"][0], _SKIN_RADIUS_BY_REGION[BodyRegion.NECK])
        if vs is not vc:
            try:
                bm.edges.new((vs, vc))
            except ValueError:
                pass
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    radii_by_index = [radii[v] for v in bm.verts]
    obj = _mesh_object(context, f"{name}_Skin", bm, f"{name}_Tissues", {
        "ce_character": name, "ce_role": "tissue", "ce_layer": "skin", "ce_provenance": "ESTIMATE"})
    skin = obj.modifiers.new("Skin", "SKIN")
    skin.use_smooth_shade = True
    if obj.data.skin_vertices:
        for idx, r in enumerate(radii_by_index):
            obj.data.skin_vertices[0].data[idx].radius = (r, r)
    sub = obj.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = subdivisions
    sub.render_levels = subdivisions
    # Bake Skin + Subdivision into a real mesh (game engines and the glTF exporter need plain geometry).
    context.view_layer.update()
    depsgraph = context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
    baked.name = f"{name}_Skin"
    old = obj.data
    obj.data = baked
    obj.modifiers.clear()
    bpy.data.meshes.remove(old)
    obj.data.materials.append(_material("CE_Skin", (0.85, 0.62, 0.50, 1.0)))
    obj["ce_skin_graph_vertices"] = len(radii_by_index)
    # nearest-bone weights on the final surface (deterministic, no heat-map failures)
    groups: Dict[str, List[Tuple[int, float]]] = {}
    for idx, v in enumerate(obj.data.vertices):
        n, _ = _nearest_bone(v.co, pts, major)
        groups.setdefault(n, []).append((idx, 1.0))
    _assign_weights(obj, groups)
    _bind(obj, armature)
    return obj


# --------------------------------------------------------------------------- rig -----------

def _prop(obj, name: str, default: float) -> None:
    obj[name] = float(default)
    ui = obj.id_properties_ui(name)
    ui.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, description=f"Character Engine: {name}")


def _driver(fcurve_owner, path: str, index: int, obj, prop: str, expression: str = "var"):
    fc = fcurve_owner.driver_add(path, index) if index >= 0 else fcurve_owner.driver_add(path)
    drv = fc.driver
    drv.type = "SCRIPTED"
    var = drv.variables.new()
    var.name = "var"
    var.type = "SINGLE_PROP"
    var.targets[0].id = obj
    var.targets[0].data_path = f'["{prop}"]'
    drv.expression = expression
    return fc


def _best_pole_angle(context, armature, ik, mch_names: Sequence[str]) -> float:
    """Pick the pole angle that reproduces the rest pose (IK at rest must be a no-op)."""
    pb = armature.pose.bones
    rest = {n: (armature.data.bones[n].head_local.copy(), armature.data.bones[n].tail_local.copy()) for n in mch_names}
    best, best_err = 0.0, float("inf")
    for deg in range(-180, 180, 15):
        ik.pole_angle = math.radians(deg)
        context.view_layer.update()
        err = sum((pb[n].head - rest[n][0]).length + (pb[n].tail - rest[n][1]).length for n in mch_names)
        if err < best_err - 1e-6:
            best, best_err = math.radians(deg), err
    return best


def build_control_rig(context, armature, rig: RigDefinition, ik_default: float = 1.0,
                      foot_roll: bool = True, breath_amplitude: float = 0.0) -> Dict[str, int]:
    """Add MCH/CTRL layers, IK chains with poles, FK/IK switches, foot roll and breathing."""
    context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    eb = armature.data.edit_bones
    stats = {"ik_chains": 0, "controls": 0, "mch": 0}
    root = eb.get("ROOT_SKELETON")

    def new_bone(name, head, tail, parent=None, deform=False):
        b = eb.get(name) or eb.new(name)
        b.head, b.tail = head, tail
        b.use_deform = deform
        if parent is not None:
            b.parent = parent
        stats["mch" if name.startswith("MCH-") else "controls"] += 1
        return b

    ctrl_root = new_bone(rig.root_control, Vector((0, 0, 0)), Vector((0, -0.3, 0)))
    if root is not None:
        root.parent = ctrl_root
    plan = []  # (chain, mch_names, target_name, pole_name)
    for chain in rig.ik_chains:
        if len(chain.bones) < 2 or any(eb.get(n) is None for n in chain.bones + (chain.target_bone,)):
            continue
        first = eb[chain.bones[0]]
        mch_names = []
        prev = first.parent
        for n in chain.bones:
            src = eb[n]
            m = new_bone(f"MCH-ik_{n}", src.head.copy(), src.tail.copy(), prev)
            m.roll = src.roll
            mch_names.append(m.name)
            prev = m
        tgt_src = eb[chain.target_bone]
        tgt = new_bone(f"MCH-ik_target_{chain.chain_id}", tgt_src.head.copy(),
                       tgt_src.head + Vector((0, 0, -0.08)), ctrl_root)
        ctrl = new_bone(f"CTRL-{'hand' if chain.chain_id.startswith('arm') else 'foot'}_ik.{chain.chain_id[-1]}",
                        tgt_src.head.copy(), tgt_src.head + Vector((0, -0.12, 0)), ctrl_root)
        tgt.parent = ctrl
        mid = eb[chain.bones[1]].head.copy()
        pole = new_bone(f"MCH-pole_{chain.chain_id}", mid + Vector(chain.pole_offset_m),
                        mid + Vector(chain.pole_offset_m) + Vector((0, 0, 0.08)), ctrl_root)
        plan.append((chain, mch_names, tgt.name, pole.name, ctrl.name))
    # breathing mechanism bone
    if eb.get("STERNUM") is not None:
        st = eb["STERNUM"]
        new_bone("CTRL-breath", st.head + Vector((0, -0.15, 0)), st.head + Vector((0, -0.25, 0)), st.parent)
    bpy.ops.object.mode_set(mode="POSE")

    pb = armature.pose.bones
    arm_data = armature.data
    for bone in arm_data.bones:
        if bone.name.startswith("MCH-"):
            assign_bone_layer(arm_data, bone, "MCH")
        elif bone.name.startswith("CTRL-"):
            assign_bone_layer(arm_data, bone, "CTRL")

    for chain, mch_names, tgt_name, pole_name, _ctrl_name in plan:
        _prop(armature, chain.fk_ik_property, ik_default)
        ik = pb[mch_names[-1]].constraints.new("IK")
        ik.target, ik.subtarget = armature, tgt_name
        ik.pole_target, ik.pole_subtarget = armature, pole_name
        ik.chain_count = len(mch_names)
        ik.use_stretch = chain.stretch
        ik.pole_angle = _best_pole_angle(context, armature, ik, mch_names)
        for n, m in zip(chain.bones, mch_names):
            c = pb[n].constraints.new("COPY_TRANSFORMS")
            c.name = "CE_IK"
            c.target, c.subtarget = armature, m
            _driver(c, "influence", -1, armature, chain.fk_ik_property)
            # sibling bones sharing the parent (ULNA with RADIUS, FIBULA with TIBIA) follow the IK bone
            for main, sib in (("RADIUS", "ULNA"), ("TIBIA", "FIBULA")):
                if not n.startswith(main):
                    continue
                sib_name = n.replace(main, sib)
                if sib_name in pb:
                    cs = pb[sib_name].constraints.new("COPY_ROTATION")
                    cs.name = "CE_IK_follow"
                    cs.target, cs.subtarget = armature, m
                    cs.mix_mode = "REPLACE"
                    _driver(cs, "influence", -1, armature, chain.fk_ik_property)
        if chain.foot_roll and foot_roll:
            roll_prop = f"foot_roll_{chain.chain_id[-1]}"
            _prop(armature, roll_prop, 0.0)
            ui = armature.id_properties_ui(roll_prop)
            ui.update(min=-1.0, max=1.0, soft_min=-1.0, soft_max=1.0)
            talus = pb.get(chain.target_bone)
            if talus is not None:
                talus.rotation_mode = "XYZ"
                fc = talus.driver_add("rotation_euler", 0)
                fc.driver.type = "SCRIPTED"
                var = fc.driver.variables.new()
                var.name, var.type = "roll", "SINGLE_PROP"
                var.targets[0].id, var.targets[0].data_path = armature, f'["{roll_prop}"]'
                fc.driver.expression = "roll * 0.6"
        stats["ik_chains"] += 1

    # breathing: sinusoidal sternum/rib displacement scaled by a 0..1 amplitude property
    _prop(armature, "breath_amplitude", breath_amplitude)
    _prop(armature, "breath_rate_hz", 0.25)
    ui = armature.id_properties_ui("breath_rate_hz")
    ui.update(min=0.05, max=1.0, soft_min=0.05, soft_max=1.0)
    for n in ["STERNUM"] + [f"RIB_{i:02d}_{s}" for i in range(1, 11) for s in "LR"]:
        bone = pb.get(n)
        if bone is None:
            continue
        fc = bone.driver_add("location", 2)
        fc.driver.type = "SCRIPTED"
        va = fc.driver.variables.new()
        va.name, va.type = "amp", "SINGLE_PROP"
        va.targets[0].id, va.targets[0].data_path = armature, '["breath_amplitude"]'
        vr = fc.driver.variables.new()
        vr.name, vr.type = "rate", "SINGLE_PROP"
        vr.targets[0].id, vr.targets[0].data_path = armature, '["breath_rate_hz"]'
        gain = 0.012 if n == "STERNUM" else 0.006
        fc.driver.expression = f"amp * {gain} * sin(2 * pi * rate * frame / {context.scene.render.fps})"
    bpy.ops.object.mode_set(mode="OBJECT")
    armature["ce_rig_id"] = rig.rig_id
    return stats


# --------------------------------------------------------------------------- mocap ---------

def import_mocap(filepath: Path, bone_map: BoneMap):
    """Import a BVH (or FBX) and return the created armature."""
    before = set(bpy.data.objects)
    # bone_map.forward_axis is where the character FACES in its file; Blender's BVH importer
    # maps ``axis_forward`` to +Y, so pass the opposite axis to make the character face −Y with
    # its left at +X like the canonical skeleton (Decision 17).
    fwd = {"+Z": "-Z", "-Z": "Z", "+Y": "-Y", "-Y": "Y"}[bone_map.forward_axis]
    up = {"+Y": "Y", "+Z": "Z"}[bone_map.up_axis]
    if filepath.suffix.lower() == ".bvh":
        bpy.ops.import_anim.bvh(filepath=str(filepath), global_scale=bone_map.scale_to_m,
                                axis_forward=fwd, axis_up=up, rotate_mode="QUATERNION",
                                update_scene_fps=False, update_scene_duration=True)
    else:
        bpy.ops.import_scene.fbx(filepath=str(filepath), global_scale=bone_map.scale_to_m,
                                 automatic_bone_orientation=False)
    new = [o for o in bpy.data.objects if o not in before and o.type == "ARMATURE"]
    if not new:
        raise RuntimeError("mocap import created no armature")
    src = new[0]
    src["ce_role"] = "mocap_source"
    return src


def _hierarchy_order(bones) -> List:
    out, seen = [], set()

    def visit(b):
        if b.name in seen:
            return
        if b.parent is not None:
            visit(b.parent)
        seen.add(b.name)
        out.append(b)

    for b in bones:
        visit(b)
    return out


def retarget_mocap(context, src_arm, dst_arm, bone_map: BoneMap, frame_start: Optional[int] = None,
                   frame_end: Optional[int] = None, root_location: bool = True) -> Dict[str, int]:
    """Bake source animation onto canonical bones via rest-to-rest rotation offsets.

    For each mapped pair  dst_world(t) = src_world(t) · (src_rest⁻¹ · dst_rest).
    Unmapped canonical bones keep their rest-relative transform (children follow parents).
    """
    scene = context.scene
    action = src_arm.animation_data.action if src_arm.animation_data else None
    if action is None:
        raise RuntimeError("source armature has no animation")
    f0, f1 = action.frame_range
    frame_start = int(f0) if frame_start is None else frame_start
    frame_end = int(f1) if frame_end is None else frame_end

    mapping: Dict[str, str] = {}      # dst canonical -> src bone
    for sb in src_arm.data.bones:
        canon = bone_map.canonical(sb.name)
        if canon and canon in dst_arm.data.bones and canon not in mapping:
            mapping[canon] = sb.name
    if not mapping:
        raise RuntimeError("bone map matched no source joints")

    if dst_arm.animation_data is None:
        dst_arm.animation_data_create()
    dst_action = bpy.data.actions.new(f"{dst_arm.name}_{Path(action.name).stem}")
    dst_arm.animation_data.action = dst_action
    try:
        dst_arm.animation_data.action_slot = dst_action.slots.new(id_type="OBJECT", name=dst_arm.name)
    except (AttributeError, TypeError):
        pass  # Blender < 4.4 has no action slots

    dst_rest = {b.name: dst_arm.matrix_world @ b.matrix_local for b in dst_arm.data.bones}
    src_rest = {b.name: src_arm.matrix_world @ b.matrix_local for b in src_arm.data.bones}
    offset = {c: src_rest[s].to_3x3().inverted() @ dst_rest[c].to_3x3() for c, s in mapping.items()}
    order = _hierarchy_order(dst_arm.data.bones)
    stature_scale = 1.0
    if root_location:
        src_root = src_arm.data.bones.get(bone_map.root_joint) or src_arm.data.bones[0]
        src_h = max((b.head_local.z for b in src_arm.data.bones), default=1.0) - min((b.head_local.z for b in src_arm.data.bones), default=0.0)
        dst_h = max(b.head_local.z for b in dst_arm.data.bones) - min(b.head_local.z for b in dst_arm.data.bones)
        stature_scale = dst_h / src_h if src_h > 1e-6 else 1.0
    else:
        src_root = None

    pb = dst_arm.pose.bones
    for b in pb:
        b.rotation_mode = "QUATERNION"
    inv_dst_world = dst_arm.matrix_world.inverted()
    keyed = 0
    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)
        src_pose = {b.name: src_arm.matrix_world @ b.matrix for b in src_arm.pose.bones}
        world: Dict[str, Matrix] = {}
        for bone in order:
            n = bone.name
            rest = dst_rest[n]
            if bone.parent is not None:
                parent_world = world[bone.parent.name]
                rest_rel = dst_rest[bone.parent.name].inverted() @ rest
                default_world = parent_world @ rest_rel
            else:
                default_world = rest.copy()
            if n in mapping:
                rot = src_pose[mapping[n]].to_3x3() @ offset[n]
                m = rot.to_4x4()
                loc = default_world.to_translation()
                if root_location and src_root is not None and mapping[n] == src_root.name:
                    delta = src_pose[mapping[n]].to_translation() - src_rest[mapping[n]].to_translation()
                    loc = rest.to_translation() + delta * stature_scale
                m.translation = loc
                world[n] = m
            else:
                world[n] = default_world
            if n in mapping:
                pose_mat = inv_dst_world @ world[n]
                if bone.parent is not None:
                    parent_pose = inv_dst_world @ world[bone.parent.name]
                    rest_rel = dst_rest[bone.parent.name].inverted() @ rest
                    basis = rest_rel.inverted() @ parent_pose.inverted() @ pose_mat
                else:
                    basis = (inv_dst_world @ rest).inverted() @ pose_mat
                p = pb[n]
                p.rotation_quaternion = basis.to_quaternion()
                p.keyframe_insert("rotation_quaternion", frame=frame)
                if root_location and mapping[n] == (src_root.name if src_root else None):
                    p.location = basis.to_translation()
                    p.keyframe_insert("location", frame=frame)
                keyed += 1
    scene.frame_set(frame_start)
    dst_arm["ce_mocap_source"] = action.name
    dst_arm["ce_bone_map"] = bone_map.map_id
    return {"mapped_bones": len(mapping), "frames": frame_end - frame_start + 1, "keys": keyed}


# --------------------------------------------------------------------------- wounds --------

_SEVERITY_COLOR = {1: (0.9, 0.9, 0.2, 1), 2: (0.95, 0.6, 0.1, 1), 3: (0.9, 0.3, 0.1, 1),
                   4: (0.8, 0.1, 0.1, 1), 5: (0.5, 0.0, 0.1, 1), 6: (0.1, 0.0, 0.0, 1)}


def nearest_canonical_bone(armature, point_world: Vector) -> Tuple[str, float]:
    pts = bone_points(armature)
    names = [b.name for b in armature.data.bones if b.get("ce_canonical") and b.name not in ("ROOT_SKELETON", "CRANIUM")]
    return _nearest_bone(point_world, pts, names)


def apply_wound(context, armature, point_world: Vector, wound_type: str, depth_m: float, width_m: float,
                energy_j: Optional[float], bone: Optional[str] = None) -> WoundAssessment:
    """Assess a wound at ``point_world`` and leave a colour-coded marker with the report."""
    if not bone:
        bone, _ = nearest_canonical_bone(armature, point_world)
    wound = Wound(bone_hit=bone, wound_type=WoundType(wound_type), depth_m=depth_m, width_m=width_m,
                  energy_j=energy_j, entry_point=tuple(point_world), provenance=ProvenanceState.USER_INPUT)
    a = assess_wound(wound)
    name = armature["ce_character"]
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=max(0.006, width_m / 2))
    marker = _mesh_object(context, f"{name}_Wound_{bone}", bm, f"{name}_Wounds", {
        "ce_character": name, "ce_role": "wound", "ce_bone": bone, "ce_wound_type": wound_type,
        "ce_severity": a.severity.value, "ce_lethality": a.lethality, "ce_bleeding_rate": a.bleeding_rate,
        "ce_layers": ",".join(layer.value for layer in a.layers_breached), "ce_fracture": a.fracture,
        "ce_report": json.dumps({
            "bone": bone, "region": a.region.value, "type": wound_type, "depth_m": depth_m, "width_m": width_m,
            "severity": a.severity.value, "lethality": a.lethality, "bleeding_rate": a.bleeding_rate,
            "fracture": a.fracture, "incapacitating": a.incapacitating, "tags": list(a.tags),
            "provenance": a.provenance.value}),
    })
    marker.location = point_world
    marker.data.materials.append(_material(f"CE_Wound_S{a.severity.value}", _SEVERITY_COLOR[a.severity.value]))
    marker.parent = armature
    marker.parent_type = "BONE"
    marker.parent_bone = bone
    pbone = armature.pose.bones[bone]
    marker.matrix_parent_inverse = (armature.matrix_world @ pbone.matrix @ Matrix.Translation((0, pbone.length, 0))).inverted()
    return a


def quaternion_from_axis_angle(axis: Vec3, angle_deg: float) -> Quaternion:  # small utility for tests
    return Quaternion(Vector(axis), math.radians(angle_deg))


# --------------------------------------------------------------------------- equipment -----

# PLACEHOLDER geometry for the sabre (blade + hilt envelope) until a modelled asset exists.
SABRE_PLACEHOLDER_LENGTH_M = 0.90
SABRE_PLACEHOLDER_WIDTH_M = 0.035


def build_equipment_sockets(context, armature, sockets: Sequence[EquipmentSocket],
                            reference_bones: Sequence[dict]) -> List[str]:
    """Add one non-deforming bone per socket (MCH layer), parented to its canonical bone."""
    bones = [{"canonical_name": b.name, "head": tuple(b.head_local), "tail": tuple(b.tail_local)}
             for b in armature.data.bones if b.get("ce_canonical")]
    placed = {s.name: socket_points(s, bones, reference_bones) for s in sockets}
    context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    eb = armature.data.edit_bones
    for s in sockets:
        e = eb.get(s.name) or eb.new(s.name)
        e.head, e.tail = Vector(placed[s.name][0]), Vector(placed[s.name][1])
        e.parent = eb[s.parent_bone]
        e.use_connect = False
        e.use_deform = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for s in sockets:
        bone = armature.data.bones[s.name]
        assign_bone_layer(armature.data, bone, "MCH")
        bone["ce_role"] = "socket"
        bone["ce_provenance"] = s.provenance.value
    return [s.name for s in sockets]


def build_placeholder_sabre(context, armature, socket_name: str = "SOCKET-sabre_hip.L"):
    """Box hanging from the socket along its axis, parented to the socket bone (PLACEHOLDER)."""
    name = armature["ce_character"]
    bone = armature.data.bones[socket_name]
    mw = armature.matrix_world
    head, tail = mw @ bone.head_local, mw @ bone.tail_local
    d = (tail - head).normalized()
    u = d.cross(Vector((1.0, 0.0, 0.0)))
    u = u.normalized() if u.length > 1e-6 else d.cross(Vector((0.0, 1.0, 0.0))).normalized()
    v = d.cross(u).normalized()
    h = SABRE_PLACEHOLDER_WIDTH_M / 2
    bm = bmesh.new()
    verts = [bm.verts.new(head + d * (SABRE_PLACEHOLDER_LENGTH_M * t) + u * (h * a) + v * (h * b))
             for t in (0.0, 1.0) for a in (-1, 1) for b in (-1, 1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([verts[i] for i in f])
    obj = _mesh_object(context, f"{name}_Sabre_PLACEHOLDER", bm, f"{name}_Equipment", {
        "ce_character": name, "ce_role": "equipment", "ce_socket": socket_name,
        "ce_provenance": ProvenanceState.PLACEHOLDER.value.upper(),
        "ce_note": "Placeholder box for a cavalry sabre; replace with a modelled asset."})
    obj.data.materials.append(_material("CE_Equipment_Placeholder", (0.55, 0.55, 0.6, 1.0)))
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = socket_name
    pbone = armature.pose.bones[socket_name]
    obj.matrix_parent_inverse = (mw @ pbone.matrix @ Matrix.Translation((0, pbone.length, 0))).inverted()
    return obj


# --------------------------------------------------------------------------- cinematic -----

def armature_points_world(armature, canonical_only: bool = True) -> List[Vector]:
    mw = armature.matrix_world
    pts = []
    for pb in armature.pose.bones:
        if canonical_only and not pb.bone.get("ce_canonical"):
            continue
        pts += [mw @ pb.head, mw @ pb.tail]
    return pts


def setup_fullbody_workbench(context, armature, resolution=(1920, 1080), lens_mm: float = 50.0,
                             margin: float = 1.10, extra_objects: Sequence = ()):
    """Floor, key/fill/rim lights and a front camera framing the armature (+ extra objects)."""
    scene = context.scene
    name = armature["ce_character"]
    coll = f"{name}_Cinematic"
    pts = armature_points_world(armature)
    for o in extra_objects:
        pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre, size = (lo + hi) / 2, hi - lo

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=2.0)
    _mesh_object(context, f"{name}_Floor", bm, coll, {"ce_character": name, "ce_role": "cinematic"})

    for label, kind, loc, energy in (("Key", "AREA", (2.0, -3.0, 3.0), 400.0),
                                     ("Fill", "AREA", (-2.5, -2.5, 2.0), 150.0),
                                     ("Rim", "SPOT", (0.0, 3.0, 3.0), 300.0)):
        data = bpy.data.lights.new(f"{name}_{label}", kind)
        data.energy = energy
        light = bpy.data.objects.new(f"{name}_{label}", data)
        _link(context, light, coll)
        light.location = centre + Vector(loc)
        direction = centre - light.location
        light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        light["ce_character"], light["ce_role"] = name, "cinematic"

    cam_data = bpy.data.cameras.new(f"{name}_Camera")
    cam_data.lens = lens_mm
    cam_data.sensor_fit = "HORIZONTAL"
    cam = bpy.data.objects.new(f"{name}_Camera", cam_data)
    _link(context, cam, coll)
    half_h = math.atan(cam_data.sensor_width / 2 / lens_mm)               # horizontal half-FOV
    half_v = math.atan(math.tan(half_h) * resolution[1] / resolution[0])  # vertical half-FOV
    dist = max(size.z * margin / 2 / math.tan(half_v), size.x * margin / 2 / math.tan(half_h)) + size.y / 2
    cam.location = Vector((centre.x, lo.y - dist + size.y / 2, centre.z))
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)                    # look along +Y, up = +Z
    cam["ce_character"], cam["ce_role"] = name, "cinematic"
    scene.camera = cam

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    return cam


def render_still(context, filepath: Path) -> float:
    """Render the active camera to ``filepath``; returns the wall time in seconds."""
    import time
    filepath.parent.mkdir(parents=True, exist_ok=True)
    context.scene.render.filepath = str(filepath)
    t = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    return time.perf_counter() - t
