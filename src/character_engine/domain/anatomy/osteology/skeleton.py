"""Skeleton – aggregate mutable con atomicidad y conteo anatómico."""

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Set
from uuid import UUID, uuid4

from .bone import Bone
from .exceptions import (
    BoneAlreadyExistsError,
    BoneNotFoundError,
    CyclicHierarchyError,
    InvalidChildError,
    InvalidGeometryError,
    InvalidParentError,
    MissingRootError,
)


@dataclass
class Skeleton:
    id: UUID = field(default_factory=uuid4)
    name: str = "Skeleton"
    canonical_name: str = "SKELETON"
    _bones: Dict[UUID, Bone] = field(default_factory=dict)
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        self._validate_invariants()

    def get_bones(self) -> Mapping[UUID, Bone]:
        return MappingProxyType(self._bones)

    def get_bone(self, bone_id: UUID) -> Optional[Bone]:
        return self._bones.get(bone_id)

    def get_bone_by_name(self, name: str) -> Optional[Bone]:
        for bone in self._bones.values():
            if bone.name == name:
                return bone
        return None

    def get_bone_by_canonical(self, canonical: str) -> Optional[Bone]:
        for bone in self._bones.values():
            if bone.canonical_name == canonical:
                return bone
        return None

    def get_roots(self) -> List[Bone]:
        return [b for b in self._bones.values() if b.is_root()]

    def get_root(self) -> Optional[Bone]:
        roots = self.get_roots()
        return roots[0] if roots else None

    def get_children(self, bone_id: UUID) -> List[Bone]:
        bone = self.get_bone(bone_id)
        if not bone:
            return []
        return [self._bones[cid] for cid in bone.child_ids if cid in self._bones]

    def get_all_descendants(self, bone_id: UUID) -> Set[UUID]:
        result = set()
        visited = set()
        stack = [bone_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            bone = self.get_bone(current)
            if bone:
                for child_id in bone.child_ids:
                    if child_id not in visited:
                        stack.append(child_id)
                        result.add(child_id)
        return result

    def get_bone_count(self) -> int:
        """Solo cuenta huesos anatómicos (excluye contenedores)."""
        return sum(1 for b in self._bones.values() if not b.is_container)

    def get_total_nodes(self) -> int:
        """Cuenta todos los nodos (incluyendo contenedores)."""
        return len(self._bones)

    def get_max_depth(self) -> int:
        max_depth = 0
        for bone in self._bones.values():
            depth = 0
            current_id = bone.id
            while current_id:
                parent = self.get_bone(current_id)
                if parent is None or parent.parent_id is None:
                    break
                current_id = parent.parent_id
                depth += 1
            if depth > max_depth:
                max_depth = depth
        return max_depth

    @classmethod
    def from_bones(cls, bones: Dict[UUID, Bone], name: str = "Skeleton",
                   canonical_name: str = "SKELETON",
                   version: str = "1.0.0",
                   metadata: Dict[str, Any] = None) -> 'Skeleton':
        skeleton = cls(
            name=name,
            canonical_name=canonical_name,
            version=version,
            metadata=metadata or {},
            created_at=datetime.now()
        )
        skeleton._bones = dict(bones)
        skeleton._validate_invariants()
        skeleton.updated_at = datetime.now()
        return skeleton

    def add_bone(self, bone: Bone) -> None:
        if bone.id in self._bones:
            raise BoneAlreadyExistsError(f"El hueso {bone.name} ya existe")
        if bone.parent_id is not None and bone.parent_id not in self._bones:
            raise InvalidParentError(f"Padre {bone.parent_id} no existe para {bone.name}")

        new_bones = dict(self._bones)
        new_bones[bone.id] = bone

        if bone.parent_id:
            parent = new_bones[bone.parent_id]
            new_parent = Bone(
                name=parent.name,
                canonical_name=parent.canonical_name,
                head=parent.head,
                tail=parent.tail,
                id=parent.id,
                parent_id=parent.parent_id,
                child_ids=frozenset(parent.child_ids | {bone.id}),
                transform=parent.transform,
                pivot=parent.pivot,
                bone_type=parent.bone_type,
                state=parent.state,
                version=parent.version,
                metadata=parent.metadata,
                created_at=parent.created_at,
                updated_at=datetime.now(),
                is_container=parent.is_container
            )
            new_bones[parent.id] = new_parent

        temp = Skeleton.from_bones(new_bones, name=self.name, canonical_name=self.canonical_name,
                                   version=self.version, metadata=self.metadata)
        self._bones = temp._bones
        self.updated_at = datetime.now()

    def remove_bone(self, bone_id: UUID, cascade: bool = False) -> None:
        if bone_id not in self._bones:
            raise BoneNotFoundError(f"Hueso {bone_id} no encontrado")

        descendants = self.get_all_descendants(bone_id)

        if not cascade and descendants:
            raise ValueError(f"El hueso tiene {len(descendants)} descendientes. Use cascade=True.")

        to_remove = {bone_id} | descendants

        # No se permite eliminar todos los huesos anatómicos de un Skeleton operativo
        anatomical_bones = [b for b in self._bones.values() if not b.is_container]
        anatomical_to_remove = [b for b in to_remove if not self._bones[b].is_container]
        if len(anatomical_bones) == len(anatomical_to_remove):
            raise ValueError("No se puede eliminar el último hueso anatómico de un Skeleton operativo")

        new_bones = {bid: b for bid, b in self._bones.items() if bid not in to_remove}

        for bid, bone in new_bones.items():
            if bone.child_ids & to_remove:
                new_bone = Bone(
                    name=bone.name,
                    canonical_name=bone.canonical_name,
                    head=bone.head,
                    tail=bone.tail,
                    id=bone.id,
                    parent_id=bone.parent_id,
                    child_ids=frozenset(cid for cid in bone.child_ids if cid not in to_remove),
                    transform=bone.transform,
                    pivot=bone.pivot,
                    bone_type=bone.bone_type,
                    state=bone.state,
                    version=bone.version,
                    metadata=bone.metadata,
                    created_at=bone.created_at,
                    updated_at=datetime.now(),
                    is_container=bone.is_container
                )
                new_bones[bid] = new_bone

        temp = Skeleton.from_bones(new_bones, name=self.name, canonical_name=self.canonical_name,
                                   version=self.version, metadata=self.metadata)
        self._bones = temp._bones
        self.updated_at = datetime.now()

    def _validate_invariants(self):
        if not self._bones:
            return

        # 1. Detectar ciclos (incluso si no hay root)
        if self._has_cycle():
            raise CyclicHierarchyError("Ciclo detectado en la jerarquía")

        # 2. Debe haber al menos un hueso anatómico
        anatomical_bones = [b for b in self._bones.values() if not b.is_container]
        if not anatomical_bones:
            raise MissingRootError("No se encontraron huesos anatómicos")

        # 3. Roots: puede haber múltiples roots, pero al menos uno debe ser anatómico
        roots = self.get_roots()
        if not roots:
            raise MissingRootError("No se encontró ningún root")

        # 4. Consistencia parent-child
        for bone in self._bones.values():
            if bone.parent_id is not None and bone.parent_id not in self._bones:
                raise InvalidParentError(f"Padre {bone.parent_id} no existe para {bone.name}")
            for child_id in bone.child_ids:
                if child_id not in self._bones:
                    raise InvalidChildError(f"Child {child_id} de {bone.name} no existe")
                child = self._bones[child_id]
                if child.parent_id != bone.id:
                    raise InvalidParentError(
                        f"Child {child.name} tiene parent_id {child.parent_id}, " +
                        f"pero está en child_ids de {bone.name}")

        # 5. Geometría básica (solo para huesos anatómicos)
        for bone in anatomical_bones:
            if bone.length <= 0:
                raise InvalidGeometryError(f"Longitud inválida para {bone.name}: {bone.length}")
    def _has_cycle(self) -> bool:
        visited: Set[UUID] = set()
        temp: Set[UUID] = set()

        def dfs(bone_id: UUID) -> bool:
            if bone_id in temp:
                return True
            if bone_id in visited:
                return False
            temp.add(bone_id)
            bone = self._bones.get(bone_id)
            if bone:
                for child_id in bone.child_ids:
                    if dfs(child_id):
                        return True
            temp.remove(bone_id)
            visited.add(bone_id)
            return False

        for bone_id in self._bones:
            if bone_id not in visited:
                if dfs(bone_id):
                    return True
        return False

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "canonical_name": self.canonical_name,
            "bones": [bone.to_dict() for bone in self._bones.values()],
            "version": self.version,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Skeleton':
        from .bone import Bone
        bones = {}
        for bone_data in data.get("bones", []):
            bone = Bone.from_dict(bone_data)
            bones[bone.id] = bone
        return cls.from_bones(
            bones,
            name=data.get("name", "Skeleton"),
            canonical_name=data.get("canonical_name", "SKELETON"),
            version=data.get("version", "1.0.0"),
            metadata=data.get("metadata", {})
        )
