"""DTO para esqueletos. No contiene lógica de dominio. Solo transporte de datos entre capas."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BoneDTO:
    """Representación de un hueso anatómico en el contrato externo."""
    canonical_name: str
    name: str
    parent: Optional[str] = None
    head: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    tail: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})


@dataclass
class ContainerDTO:
    """Nodo lógico (contenedor) para jerarquía de rigging."""
    canonical_name: str
    name: str
    parent: Optional[str] = None


@dataclass
class SkeletonDTO:
    """DTO completo de un esqueleto."""
    canonical_name: str
    name: str
    bones: List[BoneDTO] = field(default_factory=list)
    containers: List[ContainerDTO] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetDTO:
    """Metadatos del asset."""
    id: str
    name: str
    version: str = "1.0.0"
    units: str = "meters"
    coordinate_system: str = "right-handed"
