"""Serializador de Skeleton a JSON canónico usando SkeletonAssetSchemaV1."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from ..domain.anatomy.osteology.bone import Bone
from ..domain.anatomy.osteology.skeleton import Skeleton
from ..schema.skeleton_schema_v1 import (
    AssetSchemaV1,
    BoneSchemaV1,
    ContainerSchemaV1,
    SkeletonAssetSchemaV1,
    SkeletonSchemaV1,
)


class SkeletonSerializer:
    """Convierte Skeleton del dominio a SkeletonAssetSchemaV1 y a JSON v1.0."""

    SCHEMA_NAME = "character_engine.skeleton"
    SCHEMA_VERSION = "1.0"

    def __init__(self, asset_id: str = "human_adult_206", asset_name: str = "Human Skeleton"):
        self.asset_id = asset_id
        self.asset_name = asset_name

    def serialize(self, skeleton: Skeleton, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Serializa un Skeleton a dict conforme al schema v1.0."""
        # 1. Construir el schema completo
        schema_obj = self._to_schema(skeleton)

        # 2. Convertir a dict (usando el método to_dict de las dataclasses o manual)
        # Nota: SkeletonAssetSchemaV1 no tiene to_dict por defecto, así que lo construimos manualmente.
        data = {
            "schema": schema_obj.schema,
            "schema_version": schema_obj.schema_version,
            "asset": {
                "id": schema_obj.asset.id,
                "name": schema_obj.asset.name,
                "version": schema_obj.asset.version,
                "units": schema_obj.asset.units,
                "coordinate_system": schema_obj.asset.coordinate_system
            },
            "skeleton": {
                "canonical_name": schema_obj.skeleton.canonical_name,
                "name": schema_obj.skeleton.name,
                "bones": [
                    {
                        "canonical_name": b.canonical_name,
                        "name": b.name,
                        "parent": b.parent,
                        "head": b.head,
                        "tail": b.tail
                    }
                    for b in schema_obj.skeleton.bones
                ],
                "containers": [
                    {
                        "canonical_name": c.canonical_name,
                        "name": c.name,
                        "parent": c.parent
                    }
                    for c in schema_obj.skeleton.containers
                ],
                "metadata": schema_obj.skeleton.metadata
            },
            "metadata": schema_obj.metadata
        }

        # Si se proporciona ruta, escribir archivo
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")

        return data

    def _to_schema(self, skeleton: Skeleton) -> SkeletonAssetSchemaV1:
        """Convierte Skeleton a SkeletonAssetSchemaV1."""
        # Asset
        asset = AssetSchemaV1(
            id=self.asset_id,
            name=self.asset_name,
            version="1.0.0",
            units="meters",
            coordinate_system="right-handed"
        )

        # Skeleton: bones y containers
        bones = []
        containers = []

        # Recorremos los huesos en el orden del diccionario (inserción)
        # El orden original del JSON se mantiene porque el Builder inserta en el orden de la especificación.
        for bone in skeleton.get_bones().values():
            parent_name = self._get_parent_name(skeleton, bone)
            if bone.is_container:
                containers.append(ContainerSchemaV1(
                    canonical_name=bone.canonical_name,
                    name=bone.name,
                    parent=parent_name
                ))
            else:
                bones.append(BoneSchemaV1(
                    canonical_name=bone.canonical_name,
                    name=bone.name,
                    parent=parent_name,
                    head={"x": bone.head.x, "y": bone.head.y, "z": bone.head.z},
                    tail={"x": bone.tail.x, "y": bone.tail.y, "z": bone.tail.z}
                ))

        skeleton_schema = SkeletonSchemaV1(
            canonical_name=skeleton.canonical_name,
            name=skeleton.name,
            bones=bones,
            containers=containers,
            metadata=skeleton.metadata
        )

        return SkeletonAssetSchemaV1(
            schema=self.SCHEMA_NAME,
            schema_version=self.SCHEMA_VERSION,
            asset=asset,
            skeleton=skeleton_schema,
            metadata={}
        )

    def _get_parent_name(self, skeleton: Skeleton, bone: Bone) -> Optional[str]:
        if bone.parent_id is None:
            return None
        parent = skeleton.get_bone(bone.parent_id)
        return parent.canonical_name if parent else None
