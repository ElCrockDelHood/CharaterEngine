"""SkeletonBuilder – construcción con contenedores lógicos."""

from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from .bone import Bone
from .skeleton import Skeleton
from .transform import Transform, BonePivot
from .constants import BoneType, BoneState
from ....math.algebra.vector3 import Vector3
from ....math.algebra.quaternion import Quaternion

class SkeletonBuilder:
    def build(self, specification: Dict[str, Any]) -> Skeleton:
        bones_data = specification.get("bones", [])
        containers_data = specification.get("containers", [])

        # Primero, construir contenedores
        temp_bones: Dict[str, Bone] = {}
        name_to_id: Dict[str, str] = {}

        # Añadir contenedores
        for container_data in containers_data:
            canonical = container_data["canonical_name"]
            if canonical in temp_bones:
                raise ValueError(f"Duplicado de canonical_name: {canonical}")
            container = self._create_container(container_data)
            temp_bones[canonical] = container
            name_to_id[canonical] = container.id.hex

        # Añadir huesos anatómicos
        for bone_data in bones_data:
            required = ['canonical_name', 'name', 'head', 'tail']
            for field in required:
                if field not in bone_data:
                    raise ValueError(f"Campo obligatorio faltante: {field} para {bone_data.get('name', 'desconocido')}")
            for coord in ['x', 'y', 'z']:
                if coord not in bone_data["head"]:
                    raise ValueError(f"head.{coord} faltante para {bone_data['canonical_name']}")
                if coord not in bone_data["tail"]:
                    raise ValueError(f"tail.{coord} faltante para {bone_data['canonical_name']}")

            canonical = bone_data["canonical_name"]
            if canonical in temp_bones:
                raise ValueError(f"Duplicado de canonical_name: {canonical}")
            bone = self._create_bone(bone_data)
            temp_bones[canonical] = bone
            name_to_id[canonical] = bone.id.hex

        # Mapa de relaciones padre-hijo
        parent_relations: Dict[str, Optional[str]] = {}
        all_items = bones_data + containers_data
        for item in all_items:
            canonical = item["canonical_name"]
            parent_name = item.get("parent")
            if parent_name and parent_name not in name_to_id:
                raise ValueError(f"Parent {parent_name} no existe para {canonical}")
            parent_relations[canonical] = parent_name

        # Construir huesos finales con relaciones
        final_bones: Dict[UUID, Bone] = {}
        child_lists: Dict[UUID, List[UUID]] = {bone.id: [] for bone in temp_bones.values()}

        for canonical, bone in temp_bones.items():
            parent_name = parent_relations.get(canonical)
            parent_id = UUID(name_to_id[parent_name]) if parent_name else None
            if parent_id:
                child_lists[parent_id].append(bone.id)
            final_bone = Bone(
                name=bone.name,
                canonical_name=bone.canonical_name,
                head=bone.head,
                tail=bone.tail,
                id=bone.id,
                parent_id=parent_id,
                child_ids=frozenset(),
                transform=bone.transform,
                pivot=bone.pivot,
                bone_type=bone.bone_type,
                state=bone.state,
                version=bone.version,
                metadata=bone.metadata,
                created_at=bone.created_at,
                is_container=bone.is_container
            )
            final_bones[bone.id] = final_bone

        # Actualizar child_ids de los padres
        for parent_id, children in child_lists.items():
            if parent_id in final_bones:
                parent = final_bones[parent_id]
                new_parent = Bone(
                    name=parent.name,
                    canonical_name=parent.canonical_name,
                    head=parent.head,
                    tail=parent.tail,
                    id=parent.id,
                    parent_id=parent.parent_id,
                    child_ids=frozenset(children),
                    transform=parent.transform,
                    pivot=parent.pivot,
                    bone_type=parent.bone_type,
                    state=parent.state,
                    version=parent.version,
                    metadata=parent.metadata,
                    created_at=parent.created_at,
                    is_container=parent.is_container
                )
                final_bones[parent_id] = new_parent

        return Skeleton.from_bones(
            final_bones,
            name=specification.get("name", "Skeleton"),
            canonical_name=specification.get("canonical_name", "SKELETON"),
            version=specification.get("version", "1.0.0"),
            metadata=specification.get("metadata", {})
        )

    def _create_bone(self, data: Dict[str, Any]) -> Bone:
        head = data.get("head", {})
        tail = data.get("tail", {})
        return Bone(
            name=data["name"],
            canonical_name=data["canonical_name"],
            head=Vector3(head["x"], head["y"], head["z"]),
            tail=Vector3(tail["x"], tail["y"], tail["z"]),
            bone_type=BoneType(data.get("bone_type", "long")),
            state=BoneState.CREATED,
            version=data.get("version", "1.0.0"),
            metadata=dict(data.get("metadata", {})),
            is_container=False
        )

    def _create_container(self, data: Dict[str, Any]) -> Bone:
        # Los contenedores no tienen geometría
        return Bone(
            name=data["name"],
            canonical_name=data["canonical_name"],
            head=Vector3(0,0,0),
            tail=Vector3(0,0,0),
            bone_type=BoneType.CUSTOM,
            state=BoneState.CREATED,
            version=data.get("version", "1.0.0"),
            metadata=dict(data.get("metadata", {})),
            is_container=True
        )
