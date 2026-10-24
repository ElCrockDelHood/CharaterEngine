"""Schema v1.0 para el formato de intercambio de esqueletos.

Este modelo refleja el contrato público, no la implementación interna.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BoneSchemaV1:
    """Hueso en el contrato público v1.0."""
    canonical_name: str
    name: str
    parent: Optional[str] = None
    head: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    tail: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})


@dataclass
class ContainerSchemaV1:
    """Contenedor lógico en el contrato público v1.0."""
    canonical_name: str
    name: str
    parent: Optional[str] = None


@dataclass
class SkeletonSchemaV1:
    """Esqueleto en el contrato público v1.0."""
    canonical_name: str
    name: str
    bones: List[BoneSchemaV1] = field(default_factory=list)
    containers: List[ContainerSchemaV1] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetSchemaV1:
    """Metadatos del asset en el contrato público v1.0."""
    id: str
    name: str
    version: str = "1.0.0"
    units: str = "meters"
    coordinate_system: str = "right-handed"


@dataclass
class SkeletonAssetSchemaV1:
    """Schema completo v1.0."""
    schema: str = "character_engine.skeleton"
    schema_version: str = "1.0"
    asset: AssetSchemaV1 = field(default_factory=AssetSchemaV1)
    skeleton: SkeletonSchemaV1 = field(default_factory=SkeletonSchemaV1)
    metadata: Dict[str, Any] = field(default_factory=dict)
