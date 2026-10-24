"""Importador de DTO a Blender con asignación de padres en dos pasos."""

from pathlib import Path
from typing import Any, Optional

from ...domain.anatomy.osteology.skeleton import Skeleton

# Imports correctos: subir tres niveles para llegar a character_engine
from ...dto import SkeletonDTO


class BlenderImporter:
    """Importa un Skeleton a Blender como Armature (dos pasos: creación, luego padres)."""

    def __init__(self):
        self._armature = None
        self._bone_map = {}

    def import_from_dto(self, skeleton_dto: SkeletonDTO) -> bool:
        try:
            import bpy
            from mathutils import Vector
        except ImportError:
            raise ImportError("Este módulo solo puede ejecutarse dentro de Blender.")

        # Crear Armature
        armature_data = bpy.data.armatures.new(skeleton_dto.name)
        self._armature = bpy.data.objects.new(skeleton_dto.name, armature_data)
        bpy.context.scene.collection.objects.link(self._armature)
        bpy.context.view_layer.objects.active = self._armature
        bpy.ops.object.mode_set(mode='EDIT')

        # PASO 1: Crear todos los EditBones (huesos + contenedores)
        self._bone_map = {}
        all_bones = list(skeleton_dto.bones) + list(skeleton_dto.containers)
        for bone_dto in all_bones:
            edit_bone = self._armature.data.edit_bones.new(bone_dto.canonical_name)
            self._bone_map[bone_dto.canonical_name] = edit_bone

        # PASO 2: Asignar geometría y padres
        for bone_dto in skeleton_dto.bones:
            edit_bone = self._bone_map.get(bone_dto.canonical_name)
            if not edit_bone:
                continue
            head = Vector((bone_dto.head["x"], bone_dto.head["y"], bone_dto.head["z"]))
            tail = Vector((bone_dto.tail["x"], bone_dto.tail["y"], bone_dto.tail["z"]))
            edit_bone.head = head
            edit_bone.tail = tail
            if bone_dto.parent:
                parent = self._bone_map.get(bone_dto.parent)
                if parent:
                    edit_bone.parent = parent

        for container_dto in skeleton_dto.containers:
            edit_bone = self._bone_map.get(container_dto.canonical_name)
            if not edit_bone:
                continue
            edit_bone.head = Vector((0, 0, 0))
            edit_bone.tail = Vector((0, 0, 0.01))
            if container_dto.parent:
                parent = self._bone_map.get(container_dto.parent)
                if parent:
                    edit_bone.parent = parent

        bpy.ops.object.mode_set(mode='OBJECT')
        return True

    def import_from_skeleton(self, skeleton: Skeleton) -> bool:
        import json
        import os
        import tempfile

        from ...loader import JsonLoader
        from ...serialization import SkeletonSerializer

        serializer = SkeletonSerializer()
        schema_data = serializer.serialize(skeleton)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(schema_data, f, indent=2, ensure_ascii=False)
            tmp_path = Path(f.name)

        try:
            loader = JsonLoader()
            _, skeleton_dto = loader.load_to_dto(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        return self.import_from_dto(skeleton_dto)
