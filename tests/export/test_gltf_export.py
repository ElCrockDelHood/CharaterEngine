"""Tests for the pure-Python glTF 2.0 skeleton exporter.

The exporter is the bridge between the canonical data and Godot / UPBGE, so
these tests check the structural validity of the produced glTF (buffer
alignment, accessor bounds, skin/joint consistency) and the coordinate
conversion, not just "a file was written".
"""

import json
import struct

import pytest

from character_engine.domain.anatomy.osteology.builder import SkeletonBuilder
from character_engine.export.gltf import (
    COMPONENT_FLOAT,
    COMPONENT_UNSIGNED_INT,
    COMPONENT_UNSIGNED_SHORT,
    GLB_CHUNK_BIN,
    GLB_CHUNK_JSON,
    GLB_MAGIC,
    GltfExportOptions,
    GltfSkeletonExporter,
    canonical_to_gltf,
    export_canonical_skeleton,
    gltf_to_canonical,
    load_canonical_skeleton,
    main,
)

# ---------------------------------------------------------------------------
# Minimal structural glTF validator (no external dependency)
# ---------------------------------------------------------------------------
_COMPONENT_SIZE = {COMPONENT_FLOAT: 4, COMPONENT_UNSIGNED_SHORT: 2, COMPONENT_UNSIGNED_INT: 4}
_TYPE_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def assert_valid_gltf(doc: dict, binary: bytes) -> None:
    assert doc["asset"]["version"] == "2.0"
    assert doc["buffers"][0]["byteLength"] == len(binary)

    for view in doc["bufferViews"]:
        assert view["byteOffset"] % 4 == 0, "bufferView must be 4-byte aligned"
        assert view["byteOffset"] + view["byteLength"] <= len(binary)

    for accessor in doc["accessors"]:
        view = doc["bufferViews"][accessor["bufferView"]]
        size = _COMPONENT_SIZE[accessor["componentType"]] * _TYPE_WIDTH[accessor["type"]]
        assert accessor["byteOffset"] % _COMPONENT_SIZE[accessor["componentType"]] == 0
        assert accessor["byteOffset"] + accessor["count"] * size <= view["byteLength"]

    node_count = len(doc["nodes"])
    for node in doc["nodes"]:
        for child in node.get("children", []):
            assert 0 <= child < node_count
    for scene in doc["scenes"]:
        for root in scene["nodes"]:
            assert 0 <= root < node_count

    # Each node has at most one parent
    parents = {}
    for i, node in enumerate(doc["nodes"]):
        for child in node.get("children", []):
            assert child not in parents, f"node {child} has two parents"
            parents[child] = i

    for skin in doc.get("skins", []):
        assert len(set(skin["joints"])) == len(skin["joints"])
        ibm = doc["accessors"][skin["inverseBindMatrices"]]
        assert ibm["type"] == "MAT4" and ibm["count"] == len(skin["joints"])

    for mesh in doc.get("meshes", []):
        for prim in mesh["primitives"]:
            attrs = prim["attributes"]
            pos = doc["accessors"][attrs["POSITION"]]
            assert pos["type"] == "VEC3" and "min" in pos and "max" in pos
            count = pos["count"]
            for name, acc_index in attrs.items():
                assert doc["accessors"][acc_index]["count"] == count, name
            idx = doc["accessors"][prim["indices"]]
            assert idx["count"] % 3 == 0
            # every index must address a valid vertex
            view = doc["bufferViews"][idx["bufferView"]]
            fmt = "H" if idx["componentType"] == COMPONENT_UNSIGNED_SHORT else "I"
            values = struct.unpack_from(f"<{idx['count']}{fmt}", binary, view["byteOffset"] + idx["byteOffset"])
            assert max(values) < count
            # joints must be valid skin slots
            if "JOINTS_0" in attrs:
                jacc = doc["accessors"][attrs["JOINTS_0"]]
                jview = doc["bufferViews"][jacc["bufferView"]]
                joints = struct.unpack_from(f"<{jacc['count'] * 4}H", binary, jview["byteOffset"])
                assert max(joints) < len(doc["skins"][0]["joints"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def canonical_skeleton():
    return load_canonical_skeleton()


@pytest.fixture
def tiny_skeleton():
    """Root container + 3 bones in a chain and one sibling, in canonical Z-up."""
    spec = {
        "name": "Tiny",
        "canonical_name": "TINY",
        "containers": [{"canonical_name": "ROOT", "name": "Root", "parent": None}],
        "bones": [
            {"canonical_name": "A", "name": "A", "parent": "ROOT",
             "head": {"x": 0, "y": 0, "z": 1.0}, "tail": {"x": 0, "y": 0, "z": 1.5}},
            {"canonical_name": "B", "name": "B", "parent": "A",
             "head": {"x": 0, "y": 0, "z": 1.5}, "tail": {"x": 0, "y": -0.2, "z": 1.5}},
            {"canonical_name": "C", "name": "C", "parent": "A",
             "head": {"x": 0.3, "y": 0, "z": 1.5}, "tail": {"x": 0.6, "y": 0, "z": 1.5}},
        ],
    }
    return SkeletonBuilder().build(spec)


# ---------------------------------------------------------------------------
# Coordinate conversion
# ---------------------------------------------------------------------------
class TestCoordinateConversion:
    def test_up_axis_becomes_y(self):
        assert canonical_to_gltf((0, 0, 1)) == (0, 1, 0)

    def test_forward_neg_y_becomes_pos_z(self):
        assert canonical_to_gltf((0, -1, 0)) == (0, 0, 1)

    def test_right_axis_unchanged(self):
        assert canonical_to_gltf((1, 0, 0)) == (1, 0, 0)

    def test_roundtrip(self):
        v = (0.12, -0.34, 1.75)
        assert gltf_to_canonical(canonical_to_gltf(v)) == v

    def test_handedness_preserved(self):
        # right-handed: x cross y == z must map to x' cross y' == z'
        x, y, z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
        gx, gy, gz = map(canonical_to_gltf, (x, y, z))
        cross = (gx[1] * gy[2] - gx[2] * gy[1], gx[2] * gy[0] - gx[0] * gy[2], gx[0] * gy[1] - gx[1] * gy[0])
        assert cross == gz


# ---------------------------------------------------------------------------
# Document structure (tiny skeleton)
# ---------------------------------------------------------------------------
class TestTinySkeleton:
    def test_structure_is_valid(self, tiny_skeleton):
        doc = GltfSkeletonExporter().build(tiny_skeleton)
        assert_valid_gltf(doc.json, doc.binary)

    def test_hierarchy_preserved(self, tiny_skeleton):
        doc = GltfSkeletonExporter().build(tiny_skeleton)
        nodes = doc.json["nodes"]
        idx = doc.node_index_by_canonical
        assert set(idx) == {"ROOT", "A", "B", "C"}
        assert idx["A"] in nodes[idx["ROOT"]]["children"]
        assert set(nodes[idx["A"]]["children"]) == {idx["B"], idx["C"]}
        # Armature node (0) is the parent of the root container
        assert idx["ROOT"] in nodes[0]["children"]

    def test_translations_are_relative_and_converted(self, tiny_skeleton):
        doc = GltfSkeletonExporter().build(tiny_skeleton)
        nodes, idx = doc.json["nodes"], doc.node_index_by_canonical
        # ROOT container at centroid of its children heads -> A.head=(0,0,1) -> gltf (0,1,0)
        assert nodes[idx["ROOT"]]["translation"] == [0.0, 1.0, 0.0]
        # A relative to ROOT: zero
        assert nodes[idx["A"]]["translation"] == [0.0, 0.0, 0.0]
        # C.head (0.3,0,1.5) - A.head (0,0,1) = (0.3,0,0.5) -> gltf (0.3,0.5,0)
        assert nodes[idx["C"]]["translation"] == [0.3, 0.5, 0.0]

    def test_extras_keep_canonical_z_up_data(self, tiny_skeleton):
        doc = GltfSkeletonExporter().build(tiny_skeleton)
        b = doc.json["nodes"][doc.node_index_by_canonical["B"]]["extras"]
        assert b["head"] == [0.0, 0.0, 1.5]
        assert b["tail"] == [0.0, -0.2, 1.5]
        assert b["length"] == pytest.approx(0.2)
        assert b["is_container"] is False
        root = doc.json["nodes"][doc.node_index_by_canonical["ROOT"]]["extras"]
        assert root["is_container"] is True and root["position_policy"] == "children_centroid"

    def test_skin_joint_count_and_ibm(self, tiny_skeleton):
        doc = GltfSkeletonExporter().build(tiny_skeleton)
        skin = doc.json["skins"][0]
        assert len(skin["joints"]) == 4
        ibm = doc.json["accessors"][skin["inverseBindMatrices"]]
        view = doc.json["bufferViews"][ibm["bufferView"]]
        mats = struct.unpack_from("<64f", doc.binary, view["byteOffset"])
        # joint for "B" (world gltf pos: head (0,0,1.5) -> (0,1.5,0)) -> translation column = (0,-1.5,0)
        slot = skin["joints"].index(doc.node_index_by_canonical["B"])
        m = mats[slot * 16:(slot + 1) * 16]
        assert m[12:15] == pytest.approx((0.0, -1.5, 0.0))

    def test_mesh_has_octahedron_per_anatomical_bone(self, tiny_skeleton):
        doc = GltfSkeletonExporter().build(tiny_skeleton)
        prim = doc.json["meshes"][0]["primitives"][0]
        pos = doc.json["accessors"][prim["attributes"]["POSITION"]]
        assert pos["count"] == 3 * 6          # 6 vertices per bone
        assert doc.json["accessors"][prim["indices"]]["count"] == 3 * 8 * 3  # 8 triangles per bone

    def test_mesh_can_be_disabled(self, tiny_skeleton):
        doc = GltfSkeletonExporter(GltfExportOptions(include_bone_mesh=False)).build(tiny_skeleton)
        assert "meshes" not in doc.json
        assert len(doc.json["scenes"][0]["nodes"]) == 1
        assert_valid_gltf(doc.json, doc.binary)

    def test_keep_z_up_option(self, tiny_skeleton):
        doc = GltfSkeletonExporter(GltfExportOptions(convert_to_y_up=False)).build(tiny_skeleton)
        assert doc.json["nodes"][doc.node_index_by_canonical["ROOT"]]["translation"] == [0.0, 0.0, 1.0]
        assert doc.json["asset"]["extras"]["conversion"] == "identity"

    def test_deterministic_output(self, tiny_skeleton):
        a = GltfSkeletonExporter().build(tiny_skeleton)
        b = GltfSkeletonExporter().build(tiny_skeleton)
        assert a.json == b.json and a.binary == b.binary


# ---------------------------------------------------------------------------
# File formats
# ---------------------------------------------------------------------------
class TestFileFormats:
    def test_glb_container(self, tiny_skeleton, tmp_path):
        out = GltfSkeletonExporter().export(tiny_skeleton, tmp_path / "tiny.glb")
        data = out.read_bytes()
        magic, version, length = struct.unpack_from("<III", data, 0)
        assert magic == GLB_MAGIC and version == 2 and length == len(data)
        json_len, json_type = struct.unpack_from("<II", data, 12)
        assert json_type == GLB_CHUNK_JSON and json_len % 4 == 0
        doc = json.loads(data[20:20 + json_len].decode("utf-8"))
        bin_len, bin_type = struct.unpack_from("<II", data, 20 + json_len)
        assert bin_type == GLB_CHUNK_BIN and bin_len % 4 == 0
        binary = data[28 + json_len:28 + json_len + bin_len]
        assert_valid_gltf(doc, binary[:doc["buffers"][0]["byteLength"]])

    def test_gltf_with_external_bin(self, tiny_skeleton, tmp_path):
        out = GltfSkeletonExporter().export(tiny_skeleton, tmp_path / "tiny.gltf")
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["buffers"][0]["uri"] == "tiny.bin"
        binary = (tmp_path / "tiny.bin").read_bytes()
        assert_valid_gltf(doc, binary)

    def test_unknown_extension_rejected(self, tiny_skeleton, tmp_path):
        with pytest.raises(ValueError):
            GltfSkeletonExporter().export(tiny_skeleton, tmp_path / "tiny.fbx")


# ---------------------------------------------------------------------------
# Canonical 206-bone asset
# ---------------------------------------------------------------------------
class TestCanonicalExport:
    def test_canonical_counts(self, canonical_skeleton):
        doc = GltfSkeletonExporter().build(canonical_skeleton)
        extras = doc.json["asset"]["extras"]
        assert extras["bone_count"] == 206
        assert extras["total_nodes"] == 208
        assert len(doc.json["skins"][0]["joints"]) == 208
        # Armature + 208 joints + 1 mesh node
        assert len(doc.json["nodes"]) == 210

    def test_canonical_is_structurally_valid(self, canonical_skeleton):
        doc = GltfSkeletonExporter().build(canonical_skeleton)
        assert_valid_gltf(doc.json, doc.binary)

    def test_canonical_node_names_are_unique_canonical_names(self, canonical_skeleton):
        doc = GltfSkeletonExporter().build(canonical_skeleton)
        names = [n["name"] for n in doc.json["nodes"][1:209]]
        assert len(set(names)) == 208
        assert "ROOT_SKELETON" in names and "CRANIUM" in names and "SACRUM" in names

    def test_canonical_feet_at_ground_and_y_up(self, canonical_skeleton):
        doc = GltfSkeletonExporter().build(canonical_skeleton)
        prim = doc.json["meshes"][0]["primitives"][0]
        pos = doc.json["accessors"][prim["attributes"]["POSITION"]]
        # Y is the vertical axis after conversion: min Y ~ 0 (ground), max Y == skeleton height
        assert pos["min"][1] == pytest.approx(0.0, abs=0.05)
        assert pos["max"][1] > 1.0
        # Lateral extent is symmetric around X = 0
        assert pos["min"][0] == pytest.approx(-pos["max"][0], abs=0.05)

    def test_export_canonical_skeleton_cli(self, tmp_path, capsys):
        out = tmp_path / "human.glb"
        assert main(["--output", str(out)]) == 0
        assert out.exists() and out.stat().st_size > 10_000
        assert "glTF written" in capsys.readouterr().out

    def test_export_canonical_helper(self, tmp_path):
        out = export_canonical_skeleton(tmp_path / "human.gltf")
        assert out.exists() and (tmp_path / "human.bin").exists()

    def test_export_tpose_is_wide_and_same_height(self, tmp_path):
        from character_engine.export.gltf import load_canonical_skeleton

        anat = GltfSkeletonExporter().build(load_canonical_skeleton())
        tpose = GltfSkeletonExporter().build(load_canonical_skeleton(pose="tpose"))
        assert_valid_gltf(tpose.json, tpose.binary)
        assert tpose.json["asset"]["extras"]["total_nodes"] == 208

        def extent(doc):
            prim = doc.json["meshes"][0]["primitives"][0]
            return doc.json["accessors"][prim["attributes"]["POSITION"]]

        pa, pt = extent(anat), extent(tpose)
        assert pt["max"][1] == pytest.approx(pa["max"][1], abs=1e-3)   # same stature (Y-up)
        assert pt["max"][0] > pa["max"][0] + 0.4                       # arms spread along X
        assert pt["min"][0] == pytest.approx(-pt["max"][0], abs=0.05)

    def test_export_template_and_stature_cli(self, tmp_path):
        out = tmp_path / "child.glb"
        assert main(["--output", str(out), "--template", "human_child_5y", "--pose", "tpose"]) == 0
        assert out.exists()
        from character_engine.export.gltf import load_canonical_skeleton

        doc = GltfSkeletonExporter().build(load_canonical_skeleton(stature_m=1.65, pose="apose"))
        prim = doc.json["meshes"][0]["primitives"][0]
        pos = doc.json["accessors"][prim["attributes"]["POSITION"]]
        assert pos["max"][1] == pytest.approx(1.65, abs=2e-3)
