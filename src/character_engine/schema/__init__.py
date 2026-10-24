"""Módulo de schemas para el contrato público del Character Engine.

Contiene la definición formal del formato de intercambio (v1.0).
"""

from .skeleton_schema_v1 import (
    AssetSchemaV1,
    BoneSchemaV1,
    ContainerSchemaV1,
    SkeletonAssetSchemaV1,
    SkeletonSchemaV1,
)

__all__ = [
    "SkeletonAssetSchemaV1",
    "BoneSchemaV1",
    "ContainerSchemaV1",
    "SkeletonSchemaV1",
    "AssetSchemaV1",
]
