"""glTF 2.0 exporter for the canonical CHARACTER ENGINE skeleton.

Purpose
-------
Produce an engine-agnostic interchange file (``.glb`` or ``.gltf`` + ``.bin``)
directly from the domain ``Skeleton`` so the canonical asset can be loaded by
Godot 4, UPBGE/Blender, Unity, Unreal, three.js, etc. **without** depending on
any DCC tool. This module is pure Python (standard library only) and never
imports ``bpy``.

What is exported
----------------
* One glTF *node* per skeleton node (206 anatomical bones + logical
  containers), named by ``canonical_name``, with the parent/child hierarchy
  preserved. Node translations are relative to the parent joint.
* One *skin* referencing every node as a joint (with inverse bind matrices),
  which engines turn into a ``Skeleton3D`` (Godot) or an ``Armature`` (Blender).
* Optionally, one skinned *mesh*: an octahedral "bone" per anatomical bone
  (Blender-style display), 100 % weighted to its joint, so the skeleton is
  visible in any viewer and the skin is guaranteed to be consumed.
* Per-node ``extras`` carrying the **canonical** data (head/tail in Z-up
  metres, bone type, container flag) so importers can rebuild exact rest
  bones. glTF itself only stores joint positions, not bone tails.

Coordinate conversion
---------------------
Canonical: Z-up, right-handed, -Y forward, +X = character's left (metres; Decision 17).
glTF:      Y-up, right-handed, +Z forward,  +X = character's left (metres).
Conversion used (same as Blender's exporter): ``(x, y, z) -> (x, z, -y)``.

Containers
----------
Logical containers (``ROOT_SKELETON``, ``CRANIUM``) have no geometry in the
canonical data. For *presentation only* they are placed at the centroid of
their direct children's heads (or at the origin when childless). This is
flagged in ``extras.position_policy`` and never written back to canonical data.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from ..domain.anatomy.osteology.bone import Bone
from ..domain.anatomy.osteology.skeleton import Skeleton

# --------------------------------------------------------------------------
# glTF constants
# --------------------------------------------------------------------------
GLTF_VERSION = "2.0"
GENERATOR = "character_engine.export.gltf"

COMPONENT_FLOAT = 5126
COMPONENT_UNSIGNED_SHORT = 5123
COMPONENT_UNSIGNED_INT = 5125

TARGET_ARRAY_BUFFER = 34962
TARGET_ELEMENT_ARRAY_BUFFER = 34963

MODE_TRIANGLES = 4

GLB_MAGIC = 0x46546C67  # 'glTF'
GLB_CHUNK_JSON = 0x4E4F534A
GLB_CHUNK_BIN = 0x004E4942

Vec3 = Tuple[float, float, float]


# --------------------------------------------------------------------------
# Options / result
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class GltfExportOptions:
    """Exporter options."""
    include_bone_mesh: bool = True
    #: Octahedron radius as a fraction of the bone length.
    bone_thickness_ratio: float = 0.08
    #: Lower bound for the octahedron radius (metres) so tiny bones stay visible.
    min_bone_radius: float = 0.0025
    #: Convert canonical Z-up to glTF Y-up. Disable only for debugging.
    convert_to_y_up: bool = True
    scene_name: str = "CharacterEngineSkeleton"
    armature_node_name: str = "Armature"
    mesh_node_name: str = "SkeletonDisplay"


@dataclass
class GltfDocument:
    """In-memory glTF: JSON structure + single binary buffer."""
    json: Dict
    binary: bytes
    node_index_by_canonical: Dict[str, int] = field(default_factory=dict)

    def to_glb(self) -> bytes:
        """Serialize as a binary glTF container (.glb)."""
        json_bytes = json.dumps(self.json, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        json_bytes += b" " * (-len(json_bytes) % 4)
        bin_bytes = self.binary + b"\x00" * (-len(self.binary) % 4)
        total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
        out = bytearray()
        out += struct.pack("<III", GLB_MAGIC, 2, total)
        out += struct.pack("<II", len(json_bytes), GLB_CHUNK_JSON) + json_bytes
        out += struct.pack("<II", len(bin_bytes), GLB_CHUNK_BIN) + bin_bytes
        return bytes(out)

    def to_gltf(self, bin_uri: str) -> Tuple[str, bytes]:
        """Serialize as text glTF referencing an external ``.bin`` file."""
        doc = json.loads(json.dumps(self.json))
        doc["buffers"][0]["uri"] = bin_uri
        return json.dumps(doc, indent=2, ensure_ascii=False) + "\n", self.binary


# --------------------------------------------------------------------------
# Small vector helpers (tuples, no numpy)
# --------------------------------------------------------------------------
def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _length(a: Vec3) -> float:
    return math.sqrt(_dot(a, a))


def _normalize(a: Vec3) -> Vec3:
    n = _length(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 0 else (0.0, 0.0, 0.0)


def canonical_to_gltf(v: Vec3) -> Vec3:
    """Z-up (-Y forward) -> Y-up (+Z forward): (x, y, z) -> (x, z, -y)."""
    return (v[0], v[2], -v[1])


def gltf_to_canonical(v: Vec3) -> Vec3:
    """Inverse of :func:`canonical_to_gltf`: (x, y, z) -> (x, -z, y)."""
    return (v[0], -v[2], v[1])


# --------------------------------------------------------------------------
# Binary buffer builder
# --------------------------------------------------------------------------
class _BufferBuilder:
    """Accumulates typed arrays into one glTF buffer with aligned bufferViews."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.buffer_views: List[Dict] = []
        self.accessors: List[Dict] = []

    def _align(self, alignment: int = 4) -> None:
        self.data += b"\x00" * (-len(self.data) % alignment)

    def add_view(self, payload: bytes, target: Optional[int] = None, byte_stride: Optional[int] = None) -> int:
        self._align(4)
        view = {"buffer": 0, "byteOffset": len(self.data), "byteLength": len(payload)}
        if target is not None:
            view["target"] = target
        if byte_stride is not None:
            view["byteStride"] = byte_stride
        self.data += payload
        self.buffer_views.append(view)
        return len(self.buffer_views) - 1

    def add_accessor(
        self,
        view_index: int,
        component_type: int,
        count: int,
        accessor_type: str,
        minimum: Optional[Sequence[float]] = None,
        maximum: Optional[Sequence[float]] = None,
    ) -> int:
        accessor = {
            "bufferView": view_index,
            "byteOffset": 0,
            "componentType": component_type,
            "count": count,
            "type": accessor_type,
        }
        if minimum is not None:
            accessor["min"] = list(minimum)
        if maximum is not None:
            accessor["max"] = list(maximum)
        self.accessors.append(accessor)
        return len(self.accessors) - 1

    def add_float_array(self, values: Sequence[float], accessor_type: str, count: int,
                        target: Optional[int] = None, with_min_max: bool = False) -> int:
        payload = struct.pack(f"<{len(values)}f", *values)
        view = self.add_view(payload, target)
        minimum = maximum = None
        if with_min_max and count:
            width = len(values) // count
            minimum = [min(values[i::width]) for i in range(width)]
            maximum = [max(values[i::width]) for i in range(width)]
        return self.add_accessor(view, COMPONENT_FLOAT, count, accessor_type, minimum, maximum)

    def add_ushort_array(self, values: Sequence[int], accessor_type: str, count: int,
                         target: Optional[int] = None) -> int:
        payload = struct.pack(f"<{len(values)}H", *values)
        view = self.add_view(payload, target)
        return self.add_accessor(view, COMPONENT_UNSIGNED_SHORT, count, accessor_type)

    def add_uint_array(self, values: Sequence[int], accessor_type: str, count: int,
                       target: Optional[int] = None) -> int:
        payload = struct.pack(f"<{len(values)}I", *values)
        view = self.add_view(payload, target)
        return self.add_accessor(view, COMPONENT_UNSIGNED_INT, count, accessor_type)


# --------------------------------------------------------------------------
# Exporter
# --------------------------------------------------------------------------
class GltfSkeletonExporter:
    """Build a glTF 2.0 document from a domain :class:`Skeleton`."""

    def __init__(self, options: Optional[GltfExportOptions] = None) -> None:
        self.options = options or GltfExportOptions()

    # ---- public API -----------------------------------------------------
    def build(self, skeleton: Skeleton) -> GltfDocument:
        """Create the in-memory glTF document."""
        ordered = self._ordered_bones(skeleton)
        world_pos = self._world_positions(skeleton, ordered)  # canonical (Z-up) joint positions

        convert = canonical_to_gltf if self.options.convert_to_y_up else (lambda v: v)

        # -- nodes -----------------------------------------------------------
        nodes: List[Dict] = []
        node_index: Dict[UUID, int] = {}

        armature_index = 0
        nodes.append({"name": self.options.armature_node_name, "children": []})

        for bone in ordered:
            parent_pos = world_pos[bone.parent_id] if bone.parent_id else (0.0, 0.0, 0.0)
            local = convert(_sub(world_pos[bone.id], parent_pos))
            node = {
                "name": bone.canonical_name,
                "translation": [_clean(local[0]), _clean(local[1]), _clean(local[2])],
                "extras": self._bone_extras(bone, world_pos[bone.id]),
            }
            node_index[bone.id] = len(nodes)
            nodes.append(node)

        for bone in ordered:
            idx = node_index[bone.id]
            if bone.parent_id is None:
                nodes[armature_index]["children"].append(idx)
            else:
                parent_node = nodes[node_index[bone.parent_id]]
                parent_node.setdefault("children", []).append(idx)

        # -- skin ------------------------------------------------------------
        buffer = _BufferBuilder()
        joints = [node_index[b.id] for b in ordered]
        ibm_values: List[float] = []
        for bone in ordered:
            gx, gy, gz = convert(world_pos[bone.id])
            # Inverse of a pure translation, column-major 4x4
            ibm_values.extend([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -gx, -gy, -gz, 1])
        ibm_accessor = buffer.add_float_array(ibm_values, "MAT4", len(ordered))

        skin = {
            "name": f"{skeleton.canonical_name}_skin",
            "joints": joints,
            "skeleton": armature_index,
            "inverseBindMatrices": ibm_accessor,
        }

        scene_nodes = [armature_index]
        meshes: List[Dict] = []

        # -- optional display mesh ------------------------------------------
        if self.options.include_bone_mesh:
            mesh = self._build_bone_mesh(ordered, world_pos, joints, node_index, convert, buffer)
            if mesh is not None:
                meshes.append(mesh)
                mesh_node = {
                    "name": self.options.mesh_node_name,
                    "mesh": 0,
                    "skin": 0,
                }
                nodes.append(mesh_node)
                scene_nodes.append(len(nodes) - 1)

        # -- assemble --------------------------------------------------------
        anatomical = [b for b in ordered if not b.is_container]
        document = {
            "asset": {
                "version": GLTF_VERSION,
                "generator": GENERATOR,
                "extras": {
                    "source": "character_engine",
                    "skeleton_name": skeleton.name,
                    "skeleton_canonical_name": skeleton.canonical_name,
                    "skeleton_version": skeleton.version,
                    "bone_count": len(anatomical),
                    "total_nodes": len(ordered),
                    "units": "meters",
                    "canonical_coordinate_system": "Z_UP_RIGHT_HANDED_NEG_Y_FORWARD",
                    "gltf_coordinate_system": "Y_UP_RIGHT_HANDED_POS_Z_FORWARD" if self.options.convert_to_y_up else "Z_UP_RIGHT_HANDED_NEG_Y_FORWARD",
                    "conversion": "(x,y,z)->(x,z,-y)" if self.options.convert_to_y_up else "identity",
                    "extras_are_canonical_z_up": True,
                },
            },
            "scene": 0,
            "scenes": [{"name": self.options.scene_name, "nodes": scene_nodes}],
            "nodes": nodes,
            "skins": [skin],
            "meshes": meshes,
            "accessors": buffer.accessors,
            "bufferViews": buffer.buffer_views,
            "buffers": [{"byteLength": len(buffer.data)}],
        }
        if not meshes:
            del document["meshes"]

        return GltfDocument(
            json=document,
            binary=bytes(buffer.data),
            node_index_by_canonical={b.canonical_name: node_index[b.id] for b in ordered},
        )

    def export(self, skeleton: Skeleton, output_path: Path) -> Path:
        """Write ``.glb`` (binary) or ``.gltf`` + ``.bin`` depending on the extension."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        document = self.build(skeleton)

        if output_path.suffix.lower() == ".glb":
            output_path.write_bytes(document.to_glb())
        elif output_path.suffix.lower() == ".gltf":
            bin_path = output_path.with_suffix(".bin")
            text, binary = document.to_gltf(bin_path.name)
            output_path.write_text(text, encoding="utf-8")
            bin_path.write_bytes(binary)
        else:
            raise ValueError(f"Unsupported glTF extension: {output_path.suffix!r} (use .glb or .gltf)")
        return output_path

    # ---- internals ------------------------------------------------------
    @staticmethod
    def _ordered_bones(skeleton: Skeleton) -> List[Bone]:
        """Deterministic depth-first order: parents always precede children."""
        bones = skeleton.get_bones()
        by_parent: Dict[Optional[UUID], List[Bone]] = {}
        for bone in bones.values():
            by_parent.setdefault(bone.parent_id, []).append(bone)
        for children in by_parent.values():
            children.sort(key=lambda b: b.canonical_name)

        ordered: List[Bone] = []
        stack = list(reversed(by_parent.get(None, [])))
        while stack:
            bone = stack.pop()
            ordered.append(bone)
            stack.extend(reversed(by_parent.get(bone.id, [])))
        return ordered

    @staticmethod
    def _world_positions(skeleton: Skeleton, ordered: List[Bone]) -> Dict[UUID, Vec3]:
        """Canonical joint positions: bone head, or children centroid for containers."""
        positions: Dict[UUID, Vec3] = {}
        names = {b.id: b.canonical_name for b in ordered}
        # Anatomical bones first (containers depend on them)
        for bone in ordered:
            if not bone.is_container:
                positions[bone.id] = (bone.head.x, bone.head.y, bone.head.z)
        # Containers: resolve deepest first so nested containers see their children.
        # child_ids is a frozenset of random UUIDs: sum in canonical-name order so the float
        # result (and the GLB bytes) are identical on every run.
        for bone in reversed(ordered):
            if bone.is_container:
                kids = sorted((c for c in bone.child_ids if c in positions), key=lambda c: names.get(c, ""))
                child_positions = [positions[c] for c in kids]
                if child_positions:
                    n = float(len(child_positions))
                    positions[bone.id] = (
                        sum(p[0] for p in child_positions) / n,
                        sum(p[1] for p in child_positions) / n,
                        sum(p[2] for p in child_positions) / n,
                    )
                else:
                    positions[bone.id] = (0.0, 0.0, 0.0)
        return positions

    @staticmethod
    def _bone_extras(bone: Bone, joint_position: Vec3) -> Dict:
        extras = {
            "canonical_name": bone.canonical_name,
            "display_name": bone.name,
            "is_container": bone.is_container,
            "bone_type": bone.bone_type.value,
            "coordinate_system": "Z_UP_RIGHT_HANDED_NEG_Y_FORWARD",
            "units": "meters",
        }
        if bone.is_container:
            extras["position_policy"] = "children_centroid"
            extras["joint_position"] = [_clean(c) for c in joint_position]
        else:
            extras["head"] = [_clean(bone.head.x), _clean(bone.head.y), _clean(bone.head.z)]
            extras["tail"] = [_clean(bone.tail.x), _clean(bone.tail.y), _clean(bone.tail.z)]
            extras["length"] = _clean(bone.length)
        return extras

    def _build_bone_mesh(
        self,
        ordered: List[Bone],
        world_pos: Dict[UUID, Vec3],
        joints: List[int],
        node_index: Dict[UUID, int],
        convert,
        buffer: _BufferBuilder,
    ) -> Optional[Dict]:
        """One octahedron per anatomical bone, skinned 100 % to its joint."""
        joint_slot = {node: slot for slot, node in enumerate(joints)}

        positions: List[float] = []
        normals: List[float] = []
        joint_ids: List[int] = []
        weights: List[float] = []
        indices: List[int] = []

        for bone in ordered:
            if bone.is_container:
                continue
            head = convert((bone.head.x, bone.head.y, bone.head.z))
            tail = convert((bone.tail.x, bone.tail.y, bone.tail.z))
            verts, faces = _octahedron(head, tail, self.options.bone_thickness_ratio, self.options.min_bone_radius)
            base = len(positions) // 3
            center = _mul(_add(head, tail), 0.5)
            slot = joint_slot[node_index[bone.id]]
            for v in verts:
                positions.extend(v)
                normals.extend(_normalize(_sub(v, center)))
                joint_ids.extend([slot, 0, 0, 0])
                weights.extend([1.0, 0.0, 0.0, 0.0])
            for a, b, c in faces:
                indices.extend([base + a, base + b, base + c])

        vertex_count = len(positions) // 3
        if vertex_count == 0:
            return None

        pos_acc = buffer.add_float_array(positions, "VEC3", vertex_count, TARGET_ARRAY_BUFFER, with_min_max=True)
        nrm_acc = buffer.add_float_array(normals, "VEC3", vertex_count, TARGET_ARRAY_BUFFER)
        jnt_acc = buffer.add_ushort_array(joint_ids, "VEC4", vertex_count, TARGET_ARRAY_BUFFER)
        wgt_acc = buffer.add_float_array(weights, "VEC4", vertex_count, TARGET_ARRAY_BUFFER)
        if vertex_count <= 0xFFFF:
            idx_acc = buffer.add_ushort_array(indices, "SCALAR", len(indices), TARGET_ELEMENT_ARRAY_BUFFER)
        else:
            idx_acc = buffer.add_uint_array(indices, "SCALAR", len(indices), TARGET_ELEMENT_ARRAY_BUFFER)

        return {
            "name": "BoneDisplayMesh",
            "primitives": [{
                "attributes": {
                    "POSITION": pos_acc,
                    "NORMAL": nrm_acc,
                    "JOINTS_0": jnt_acc,
                    "WEIGHTS_0": wgt_acc,
                },
                "indices": idx_acc,
                "mode": MODE_TRIANGLES,
            }],
        }


def _clean(value: float) -> float:
    """Round to float32-friendly precision and drop negative zero."""
    rounded = round(float(value), 7)
    return 0.0 if rounded == 0 else rounded


def _octahedron(head: Vec3, tail: Vec3, ratio: float, min_radius: float) -> Tuple[List[Vec3], List[Tuple[int, int, int]]]:
    """Blender-style octahedral bone: tip at head, tip at tail, square ring near the head."""
    axis = _sub(tail, head)
    length = _length(axis)
    if length <= 0:
        raise ValueError("Cannot build an octahedron for a zero-length bone")
    d = _mul(axis, 1.0 / length)
    radius = max(min_radius, length * ratio)

    reference = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _normalize(_cross(d, reference))
    v = _cross(d, u)

    ring_center = _add(head, _mul(axis, 0.15))
    ring = [
        _add(ring_center, _mul(u, radius)),
        _add(ring_center, _mul(v, radius)),
        _add(ring_center, _mul(u, -radius)),
        _add(ring_center, _mul(v, -radius)),
    ]
    verts: List[Vec3] = [head, tail] + ring  # 0=head, 1=tail, 2..5=ring
    faces: List[Tuple[int, int, int]] = []
    centre = _mul(_add(head, tail), 0.5)
    for i in range(4):
        a, b = 2 + i, 2 + (i + 1) % 4
        faces.append(_outward((0, a, b), verts, centre))
        faces.append(_outward((1, b, a), verts, centre))
    return verts, faces


def _outward(face: Tuple[int, int, int], verts: List[Vec3], centre: Vec3) -> Tuple[int, int, int]:
    """Ensure counter-clockwise winding seen from outside the solid."""
    a, b, c = (verts[i] for i in face)
    normal = _cross(_sub(b, a), _sub(c, a))
    face_centre = _mul(_add(_add(a, b), c), 1.0 / 3.0)
    if _dot(normal, _sub(face_centre, centre)) < 0:
        return (face[0], face[2], face[1])
    return face


# --------------------------------------------------------------------------
# Convenience: canonical JSON -> glTF
# --------------------------------------------------------------------------
def default_canonical_json() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "anatomy" / "human_adult_206.json"


def load_canonical_skeleton(
    json_path: Optional[Path] = None,
    pose: str = "anatomical",
    template_id: Optional[str] = None,
    stature_m: Optional[float] = None,
) -> Skeleton:
    """Load the canonical JSON through the validated Loader -> Builder path.

    ``template_id`` / ``stature_m`` retarget the skeleton with
    :func:`character_engine.domain.character.build_character_bones` (published
    proportion ratios); ``pose`` applies a rigid pose transform (``anatomical`` |
    ``tpose`` | ``apose``) *before* DTO validation, so the exported hierarchy is
    still the 208-node canonical contract.
    """
    import json

    from ..domain.anatomy.osteology.builder import SkeletonBuilder
    from ..domain.anatomy.osteology.validator import SkeletonValidator
    from ..domain.anatomy.pose import apply_pose
    from ..loader import JsonLoader
    from ..pipeline.pipeline import dto_to_spec

    json_path = Path(json_path) if json_path else default_canonical_json()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    bones = data["bones"]
    if template_id or stature_m:
        from ..domain.character import build_character_bones, get_template

        params = get_template(template_id or "human_male_adult").params
        if stature_m:
            params = params.with_(stature_m=stature_m)
        params = params.with_(pose=pose)
        bones, _ = build_character_bones(params, canonical_bones=bones)
    else:
        bones = apply_pose(bones, pose)
    data = dict(data, bones=bones)
    _, skeleton_dto = JsonLoader().load_data_to_dto(data)
    skeleton = SkeletonBuilder().build(dto_to_spec(skeleton_dto))
    result = SkeletonValidator().validate(skeleton)
    if not result.is_valid:
        raise ValueError(f"Canonical skeleton failed validation: {result.errors}")
    return skeleton


def export_canonical_skeleton(
    output_path: Path,
    json_path: Optional[Path] = None,
    options: Optional[GltfExportOptions] = None,
    pose: str = "anatomical",
    template_id: Optional[str] = None,
    stature_m: Optional[float] = None,
) -> Path:
    """Export the canonical 206-bone skeleton to ``output_path`` (.glb or .gltf)."""
    skeleton = load_canonical_skeleton(json_path, pose=pose, template_id=template_id, stature_m=stature_m)
    return GltfSkeletonExporter(options).export(skeleton, Path(output_path))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ce-export-gltf",
        description="Export the canonical CHARACTER ENGINE skeleton to glTF 2.0 (.glb/.gltf) for Godot, UPBGE and other engines.",
    )
    parser.add_argument("-i", "--input", type=Path, default=None,
                        help="Canonical skeleton JSON (default: bundled human_adult_206.json)")
    parser.add_argument("-o", "--output", type=Path, default=Path("builds/gltf/human_adult_206.glb"),
                        help="Output .glb or .gltf path (default: builds/gltf/human_adult_206.glb)")
    parser.add_argument("--no-mesh", action="store_true", help="Do not include the octahedral bone display mesh")
    parser.add_argument("--keep-z-up", action="store_true", help="Do not convert to glTF Y-up (debug only)")
    parser.add_argument("--pose", choices=("anatomical", "tpose", "apose"), default="anatomical",
                        help="Rest pose of the exported skeleton (default: anatomical)")
    parser.add_argument("--template", default=None,
                        help="Character template id (e.g. human_male_adult, human_female_adult, human_child_5y)")
    parser.add_argument("--stature", type=float, default=None, help="Override stature in metres (retargets proportions)")
    args = parser.parse_args(argv)

    options = GltfExportOptions(include_bone_mesh=not args.no_mesh, convert_to_y_up=not args.keep_z_up)
    path = export_canonical_skeleton(args.output, args.input, options, pose=args.pose,
                                     template_id=args.template, stature_m=args.stature)
    print(f"glTF written: {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
