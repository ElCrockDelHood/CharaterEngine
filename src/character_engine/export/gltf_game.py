"""glTF 2.0 export of the CE-GAME-v1 game skeleton (66 bones, RIG-GAME-001 step 1).

Same conventions as :mod:`character_engine.export.gltf`: Z-up canonical → glTF Y-up ``(x, y, z) → (x, z, -y)``,
joints as translation-only nodes at the bone heads, inverse bind matrices from the head positions, an optional
octahedral display mesh skinned 100 % per joint. Node ``extras`` carry the canonical Z-up head / tail, the
canonical bones the game bone covers and its provenance; the asset ``extras`` carry the full canonical → game map.
Pure Python, stdlib only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from ..domain.rigging.game_rig import GAME_BONES, RIG_ID, canonical_to_game, game_bone_points
from .gltf import (
    GENERATOR,
    GLTF_VERSION,
    MODE_TRIANGLES,
    TARGET_ARRAY_BUFFER,
    TARGET_ELEMENT_ARRAY_BUFFER,
    GltfDocument,
    GltfExportOptions,
    Vec3,
    _add,
    _BufferBuilder,
    _clean,
    _mul,
    _normalize,
    _octahedron,
    _sub,
    canonical_to_gltf,
    default_canonical_json,
    load_canonical_bone_data,
)

DEFAULT_GAME_GLB = Path("builds/gltf/human_game_v1.glb")


def build_game_document(points: Dict[str, tuple], options: Optional[GltfExportOptions] = None) -> GltfDocument:
    """glTF document for game bone ``points`` (name -> (head, tail), canonical Z-up)."""
    options = options or GltfExportOptions()
    convert = canonical_to_gltf if options.convert_to_y_up else (lambda v: v)
    nodes: List[Dict] = [{"name": options.armature_node_name, "children": []}]
    index: Dict[str, int] = {}
    for g in GAME_BONES:                       # parents are declared before children (validated)
        head, tail = points[g.name]
        parent_head = points[g.parent][0] if g.parent else (0.0, 0.0, 0.0)
        local = convert(_sub(head, parent_head))
        index[g.name] = len(nodes)
        nodes.append({
            "name": g.name,
            "translation": [_clean(c) for c in local],
            "extras": {
                "ce_rig": RIG_ID,
                "head": [_clean(c) for c in head],
                "tail": [_clean(c) for c in tail],
                "covers": list(g.covers),
                "group": g.group,
                "provenance": g.provenance.value,
            },
        })
        (nodes[index[g.parent]].setdefault("children", []) if g.parent else nodes[0]["children"]).append(index[g.name])

    buffer = _BufferBuilder()
    joints = [index[g.name] for g in GAME_BONES]
    ibm: List[float] = []
    for g in GAME_BONES:
        x, y, z = convert(points[g.name][0])
        ibm.extend([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1])
    skin = {"name": f"{RIG_ID}_skin", "joints": joints, "skeleton": 0,
            "inverseBindMatrices": buffer.add_float_array(ibm, "MAT4", len(joints))}

    scene_nodes = [0]
    meshes: List[Dict] = []
    if options.include_bone_mesh:
        meshes.append(_display_mesh(points, convert, options, buffer))
        nodes.append({"name": options.mesh_node_name, "mesh": 0, "skin": 0})
        scene_nodes.append(len(nodes) - 1)

    document = {
        "asset": {
            "version": GLTF_VERSION,
            "generator": GENERATOR,
            "extras": {
                "source": "character_engine",
                "rig_id": RIG_ID,
                "bone_count": len(GAME_BONES),
                "units": "meters",
                "canonical_coordinate_system": "Z_UP_RIGHT_HANDED_NEG_Y_FORWARD",
                "gltf_coordinate_system": "Y_UP_RIGHT_HANDED_POS_Z_FORWARD" if options.convert_to_y_up
                else "Z_UP_RIGHT_HANDED_NEG_Y_FORWARD",
                "conversion": "(x,y,z)->(x,z,-y)" if options.convert_to_y_up else "identity",
                "extras_are_canonical_z_up": True,
                "canonical_to_game": dict(sorted(canonical_to_game().items())),
            },
        },
        "scene": 0,
        "scenes": [{"name": f"{RIG_ID}_scene", "nodes": scene_nodes}],
        "nodes": nodes,
        "skins": [skin],
        "meshes": meshes,
        "accessors": buffer.accessors,
        "bufferViews": buffer.buffer_views,
        "buffers": [{"byteLength": len(buffer.data)}],
    }
    if not meshes:
        del document["meshes"]
    return GltfDocument(json=document, binary=bytes(buffer.data), node_index_by_canonical=index)


def _display_mesh(points, convert, options: GltfExportOptions, buffer: _BufferBuilder) -> Dict:
    positions: List[float] = []
    normals: List[float] = []
    joint_ids: List[int] = []
    weights: List[float] = []
    indices: List[int] = []
    for slot, g in enumerate(GAME_BONES):
        head, tail = (convert(p) for p in points[g.name])
        verts, faces = _octahedron(head, tail, options.bone_thickness_ratio, options.min_bone_radius)
        base = len(positions) // 3
        centre: Vec3 = _mul(_add(head, tail), 0.5)
        for v in verts:
            positions.extend(v)
            normals.extend(_normalize(_sub(v, centre)))
            joint_ids.extend([slot, 0, 0, 0])
            weights.extend([1.0, 0.0, 0.0, 0.0])
        for a, b, c in faces:
            indices.extend([base + a, base + b, base + c])
    n = len(positions) // 3
    return {
        "name": "GameBoneDisplayMesh",
        "primitives": [{
            "attributes": {
                "POSITION": buffer.add_float_array(positions, "VEC3", n, TARGET_ARRAY_BUFFER, with_min_max=True),
                "NORMAL": buffer.add_float_array(normals, "VEC3", n, TARGET_ARRAY_BUFFER),
                "JOINTS_0": buffer.add_ushort_array(joint_ids, "VEC4", n, TARGET_ARRAY_BUFFER),
                "WEIGHTS_0": buffer.add_float_array(weights, "VEC4", n, TARGET_ARRAY_BUFFER),
            },
            "indices": buffer.add_ushort_array(indices, "SCALAR", len(indices), TARGET_ELEMENT_ARRAY_BUFFER),
            "mode": MODE_TRIANGLES,
        }],
    }


def game_skeleton_points(json_path: Optional[Path] = None, pose: str = "anatomical",
                         template_id: Optional[str] = None, stature_m: Optional[float] = None) -> Dict[str, tuple]:
    """Game bone points for the canonical skeleton after the same retarget / pose as the canonical exporter."""
    data = load_canonical_bone_data(json_path, pose=pose, template_id=template_id, stature_m=stature_m)
    reference = json.loads(Path(json_path or default_canonical_json()).read_text(encoding="utf-8"))["bones"]
    return game_bone_points(data["bones"], reference)


def export_game_skeleton(output_path: Path, json_path: Optional[Path] = None,
                         options: Optional[GltfExportOptions] = None, pose: str = "anatomical",
                         template_id: Optional[str] = None, stature_m: Optional[float] = None) -> Path:
    """Write the CE-GAME-v1 skeleton to ``output_path`` (.glb or .gltf + .bin)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = build_game_document(game_skeleton_points(json_path, pose, template_id, stature_m), options)
    if output_path.suffix.lower() == ".glb":
        output_path.write_bytes(doc.to_glb())
    elif output_path.suffix.lower() == ".gltf":
        bin_path = output_path.with_suffix(".bin")
        text, binary = doc.to_gltf(bin_path.name)
        output_path.write_text(text, encoding="utf-8")
        bin_path.write_bytes(binary)
    else:
        raise ValueError(f"Unsupported glTF extension: {output_path.suffix!r} (use .glb or .gltf)")
    return output_path
