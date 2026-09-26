"""Tests completos del dominio osteológico (grupos A–E)."""

import pytest
from uuid import uuid4
from character_engine.domain.anatomy.osteology.bone import Bone
from character_engine.domain.anatomy.osteology.skeleton import Skeleton
from character_engine.domain.anatomy.osteology.builder import SkeletonBuilder
from character_engine.domain.anatomy.osteology.validator import SkeletonValidator
from character_engine.domain.anatomy.osteology.exceptions import *
from character_engine.math.algebra.vector3 import Vector3

# ====================================================================
# GRUPO A – Bone
# ====================================================================
class TestBone:
    def test_a1_creation(self):
        bone = Bone(name="Test", canonical_name="TEST",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0))
        assert bone.name == "Test"
        assert bone.canonical_name == "TEST"
        assert bone.length == 0.1
        assert not bone.is_container

    def test_a2_geometry(self):
        bone = Bone(name="Test", canonical_name="TEST",
                    head=Vector3(0,0,0), tail=Vector3(0,0.2,0))
        assert bone.length == 0.2
        with pytest.raises(ValueError):
            Bone(name="Test", canonical_name="TEST",
                 head=Vector3(0,0,0), tail=Vector3(0,0,0))

    def test_a3_immutability(self):
        bone = Bone(name="Test", canonical_name="TEST",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0))
        with pytest.raises(Exception):
            bone.name = "Changed"

    def test_a4_deep_metadata(self):
        meta = {"list": [1,2,3], "dict": {"a":1}}
        bone = Bone(name="Test", canonical_name="TEST",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0),
                    metadata=meta)
        with pytest.raises(TypeError):
            bone.metadata["list"] = [4,5,6]
        with pytest.raises(TypeError):
            bone.metadata["dict"]["a"] = 2

    def test_a5_serialization(self):
        bone = Bone(name="Test", canonical_name="TEST",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0))
        d = bone.to_dict()
        bone2 = Bone.from_dict(d)
        assert bone2.name == bone.name
        assert bone2.canonical_name == bone.canonical_name
        assert bone2.length == bone.length

    def test_a6_container(self):
        container = Bone(name="Root", canonical_name="ROOT",
                         head=Vector3(0,0,0), tail=Vector3(0,0,0),
                         is_container=True)
        assert container.is_container
        assert container.length == 0

# ====================================================================
# GRUPO B – Skeleton
# ====================================================================
class TestSkeleton:
    def test_b1_empty_state(self):
        sk = Skeleton()
        assert sk.get_bone_count() == 0

    def test_b2_single_root(self):
        sk = Skeleton()
        root = Bone(name="Root", canonical_name="ROOT",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0))
        sk.add_bone(root)
        assert sk.get_bone_count() == 1
        roots = sk.get_roots()
        assert len(roots) == 1
        assert roots[0].id == root.id

    def test_b3_parent_child_consistency(self):
        sk = Skeleton()
        root = Bone(name="Root", canonical_name="ROOT",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0))
        child = Bone(name="Child", canonical_name="CHILD",
                     head=Vector3(0,0.1,0), tail=Vector3(0,0.2,0),
                     parent_id=root.id)
        sk.add_bone(root)
        sk.add_bone(child)
        updated_root = sk.get_bone(root.id)
        assert child.id in updated_root.child_ids
        assert sk.get_bone(child.id).parent_id == root.id

    def test_b4_cycle_detection(self):
        # Construir ciclo real: A → B → C → A
        a_id = uuid4()
        b_id = uuid4()
        c_id = uuid4()

        a = Bone(name="A", canonical_name="A",
                 head=Vector3(0,0,0), tail=Vector3(0,0.1,0),
                 id=a_id, parent_id=c_id,
                 child_ids=frozenset({b_id}))
        b = Bone(name="B", canonical_name="B",
                 head=Vector3(0,0.1,0), tail=Vector3(0,0.2,0),
                 id=b_id, parent_id=a_id,
                 child_ids=frozenset({c_id}))
        c = Bone(name="C", canonical_name="C",
                 head=Vector3(0,0.2,0), tail=Vector3(0,0.3,0),
                 id=c_id, parent_id=b_id,
                 child_ids=frozenset({a_id}))

        with pytest.raises(CyclicHierarchyError):
            Skeleton.from_bones({a_id: a, b_id: b, c_id: c})

    def test_b5_atomic_add(self):
        sk = Skeleton()
        root = Bone(name="Root", canonical_name="ROOT",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0))
        sk.add_bone(root)
        bad = Bone(name="Bad", canonical_name="BAD",
                   head=Vector3(0,0.1,0), tail=Vector3(0,0.2,0),
                   parent_id=uuid4())
        with pytest.raises(InvalidParentError):
            sk.add_bone(bad)
        assert sk.get_bone_count() == 1

    def test_b6_atomic_remove(self):
        sk = Skeleton()
        root = Bone(name="Root", canonical_name="ROOT",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0))
        child = Bone(name="Child", canonical_name="CHILD",
                     head=Vector3(0,0.1,0), tail=Vector3(0,0.2,0),
                     parent_id=root.id)
        sk.add_bone(root); sk.add_bone(child)
        assert sk.get_bone_count() == 2

        with pytest.raises(ValueError):
            sk.remove_bone(root.id, cascade=False)
        assert sk.get_bone_count() == 2

        before = dict(sk.get_bones())
        sk.remove_bone(child.id, cascade=True)
        assert sk.get_bone_count() == 1
        assert sk.get_root().id == root.id

        with pytest.raises(ValueError):
            sk.remove_bone(root.id, cascade=True)
        assert sk.get_bone_count() == 1

    def test_b7_read_only_api(self):
        sk = Skeleton()
        root = Bone(name="Root", canonical_name="ROOT",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0))
        sk.add_bone(root)
        bones_view = sk.get_bones()
        with pytest.raises(TypeError):
            bones_view[root.id] = None

    def test_b8_container_count(self):
        sk = Skeleton()
        bone = Bone(name="Bone", canonical_name="BONE",
                    head=Vector3(0,0,0), tail=Vector3(0,0.1,0))
        container = Bone(name="Root", canonical_name="ROOT",
                         head=Vector3(0,0,0), tail=Vector3(0,0,0),
                         is_container=True)
        sk.add_bone(bone)
        sk.add_bone(container)
        assert sk.get_bone_count() == 1
        assert sk.get_total_nodes() == 2

# ====================================================================
# GRUPO C – Builder
# ====================================================================
class TestBuilder:
    def test_c1_build(self):
        spec = {
            "name": "Test",
            "canonical_name": "TEST",
            "containers": [
                {"canonical_name": "ROOT", "name": "Root"}
            ],
            "bones": [
                {"canonical_name": "BONE1", "name": "Bone1", "parent": "ROOT",
                 "head": {"x":0,"y":0,"z":0}, "tail": {"x":0,"y":0.1,"z":0}},
                {"canonical_name": "BONE2", "name": "Bone2", "parent": "BONE1",
                 "head": {"x":0,"y":0.1,"z":0}, "tail": {"x":0,"y":0.2,"z":0}}
            ]
        }
        builder = SkeletonBuilder()
        sk = builder.build(spec)
        assert sk.get_bone_count() == 2
        assert sk.get_total_nodes() == 3

    def test_c2_parent_resolution(self):
        spec = {
            "name": "Test",
            "canonical_name": "TEST",
            "containers": [
                {"canonical_name": "ROOT", "name": "Root"}
            ],
            "bones": [
                {"canonical_name": "A", "name": "A", "parent": "ROOT",
                 "head": {"x":0,"y":0,"z":0}, "tail": {"x":0,"y":0.1,"z":0}},
                {"canonical_name": "B", "name": "B", "parent": "A",
                 "head": {"x":0,"y":0.1,"z":0}, "tail": {"x":0,"y":0.2,"z":0}},
                {"canonical_name": "C", "name": "C", "parent": "B",
                 "head": {"x":0,"y":0.2,"z":0}, "tail": {"x":0,"y":0.3,"z":0}}
            ]
        }
        builder = SkeletonBuilder()
        sk = builder.build(spec)
        a = sk.get_bone_by_canonical("A")
        b = sk.get_bone_by_canonical("B")
        c = sk.get_bone_by_canonical("C")
        assert a is not None and b is not None and c is not None
        assert c.parent_id == b.id
        assert b.parent_id == a.id
        assert a.parent_id == sk.get_bone_by_canonical("ROOT").id

    def test_c3_factory_required(self):
        spec = {"name": "Test", "bones": [], "containers": []}
        builder = SkeletonBuilder()
        sk = builder.build(spec)
        assert sk.get_bone_count() == 0
        assert sk.get_total_nodes() == 0

# ====================================================================
# GRUPO D – HumanTemplate
# ====================================================================
class TestHumanTemplate:
    def test_d1_json_exists(self):
        from character_engine.domain.anatomy.templates.human import HumanTemplate
        spec = HumanTemplate.get_skeleton_spec()
        assert spec is not None
        assert "bones" in spec
        assert "containers" in spec

    def test_d2_exact_206(self):
        from character_engine.domain.anatomy.templates.human import HumanTemplate
        spec = HumanTemplate.get_skeleton_spec()
        bones = spec.get("bones", [])
        assert len(bones) == 206, f"Se esperaban 206 huesos, se obtuvieron {len(bones)}"

    def test_d3_unique_canonical_names(self):
        from character_engine.domain.anatomy.templates.human import HumanTemplate
        spec = HumanTemplate.get_skeleton_spec()
        bones = spec.get("bones", [])
        names = [b["canonical_name"] for b in bones]
        assert len(names) == len(set(names))

    def test_d4_containers_exist(self):
        from character_engine.domain.anatomy.templates.human import HumanTemplate
        spec = HumanTemplate.get_skeleton_spec()
        containers = spec.get("containers", [])
        container_names = [c["canonical_name"] for c in containers]
        assert "ROOT_SKELETON" in container_names
        assert "CRANIUM" in container_names

    def test_d5_valid_geometry(self):
        from character_engine.domain.anatomy.templates.human import HumanTemplate
        spec = HumanTemplate.get_skeleton_spec()
        bones = spec.get("bones", [])
        for bone in bones:
            h = bone.get("head", {})
            t = bone.get("tail", {})
            assert "x" in h and "y" in h and "z" in h
            assert "x" in t and "y" in t and "z" in t

    def test_d6_valid_hierarchy(self):
        from character_engine.domain.anatomy.templates.human import HumanTemplate
        spec = HumanTemplate.get_skeleton_spec()
        bones = spec.get("bones", [])
        containers = spec.get("containers", [])
        all_names = {b["canonical_name"] for b in bones} | {c["canonical_name"] for c in containers}
        for bone in bones:
            if bone.get("parent") is not None:
                assert bone["parent"] in all_names, f"Parent {bone['parent']} no existe para {bone['canonical_name']}"
        for container in containers:
            if container.get("parent") is not None:
                assert container["parent"] in all_names, f"Parent {container['parent']} no existe para {container['canonical_name']}"

    def test_d7_reproducible_load(self):
        from character_engine.domain.anatomy.templates.human import HumanTemplate
        spec1 = HumanTemplate.get_skeleton_spec()
        spec2 = HumanTemplate.get_skeleton_spec()
        assert len(spec1["bones"]) == len(spec2["bones"])
        assert spec1["bones"][0]["canonical_name"] == spec2["bones"][0]["canonical_name"]

# ====================================================================
# GRUPO E – Arquitectura
# ====================================================================
class TestArchitecture:
    def test_e1_no_bpy_import(self):
        import character_engine.domain.anatomy.osteology as osteology
        assert not hasattr(osteology, 'bpy')

    def test_e2_no_rigging_dependency(self):
        import character_engine.domain.anatomy.osteology as osteology
        modules = [m for m in dir(osteology) if 'rig' in m.lower()]
        assert len(modules) == 0