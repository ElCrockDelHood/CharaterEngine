"""SkeletonValidator – 5 niveles de validación."""

import math

from ....validation.result import ValidationResult
from ....validation.validator import Validator
from .exceptions import (
    CyclicHierarchyError,
    InvalidChildError,
    InvalidGeometryError,
    InvalidParentError,
    MissingRootError,
    MultipleRootsError,
)
from .skeleton import Skeleton

DOMAIN_TOLERANCE = 1e-6
BLENDER_TOLERANCE = 1e-4

class SkeletonValidator(Validator):
    def validate(self, skeleton: Skeleton) -> ValidationResult:
        result = ValidationResult()
        result = result.merge(self._validate_syntactic(skeleton))
        if not result.is_valid:
            return result
        result = result.merge(self._validate_semantic(skeleton))
        if not result.is_valid:
            return result
        result = result.merge(self._validate_structural(skeleton))
        if not result.is_valid:
            return result
        result = result.merge(self._validate_functional(skeleton))
        if not result.is_valid:
            return result
        result = result.merge(self._validate_integration(skeleton))
        result.finish()
        return result

    def _validate_syntactic(self, skeleton: Skeleton) -> ValidationResult:
        result = ValidationResult()
        if not skeleton.name:
            result.add_error("El esqueleto debe tener un nombre")
        for bone in skeleton.get_bones().values():
            if not bone.name or not bone.canonical_name:
                result.add_error(f"Hueso {bone.id} sin nombre o nombre canónico")
            if not bone.is_container:
                if not self._is_finite_vector(bone.head):
                    result.add_error(f"Hueso {bone.name} head no finito")
                if not self._is_finite_vector(bone.tail):
                    result.add_error(f"Hueso {bone.name} tail no finito")
                if bone.length <= 0:
                    result.add_error(f"Hueso {bone.name} longitud inválida: {bone.length}")
                dist = bone.head.distance_to(bone.tail)
                if abs(bone.length - dist) > DOMAIN_TOLERANCE:
                    result.add_error(
                        f"Hueso {bone.name}: length ({bone.length}) != distance ({dist}) "
                        f"(tolerancia {DOMAIN_TOLERANCE})"
                    )
        return result

    def _is_finite_vector(self, v) -> bool:
        return all(math.isfinite(getattr(v, coord, 0)) for coord in ('x','y','z'))

    def _validate_semantic(self, skeleton: Skeleton) -> ValidationResult:
        result = ValidationResult()
        canonical_names = set()
        names = set()
        for bone in skeleton.get_bones().values():
            if bone.canonical_name in canonical_names:
                result.add_error(f"Nombre canónico duplicado: {bone.canonical_name}")
            canonical_names.add(bone.canonical_name)
            if bone.name in names:
                result.add_warning(f"Nombre duplicado: {bone.name}")
            names.add(bone.name)
        return result

    def _validate_structural(self, skeleton: Skeleton) -> ValidationResult:
        result = ValidationResult()
        try:
            skeleton._validate_invariants()
        except (CyclicHierarchyError, MissingRootError, MultipleRootsError,
                InvalidParentError, InvalidGeometryError, InvalidChildError) as e:
            result.add_error(str(e))
        max_depth = skeleton.get_max_depth()
        result.add_metric("max_depth", float(max_depth))
        if max_depth > 50:
            result.add_warning(f"Profundidad muy alta: {max_depth}")
        return result

    def _validate_functional(self, skeleton: Skeleton) -> ValidationResult:
        result = ValidationResult()
        if skeleton.get_bone_count() == 0:
            result.add_error("El esqueleto no tiene huesos anatómicos")
        roots = skeleton.get_roots()
        if not roots:
            result.add_error("No hay hueso raíz")
        else:
            result.add_metric("root_count", float(len(roots)))
        return result

    def _validate_integration(self, skeleton: Skeleton) -> ValidationResult:
        result = ValidationResult()
        result.add_info("Validación de integración: pendiente de adaptadores")
        return result

    def validate_for_blender(self, skeleton: Skeleton) -> ValidationResult:
        result = self.validate(skeleton)
        max_depth = skeleton.get_max_depth()
        if max_depth > 64:
            result.add_warning("Profundidad >64 puede ser problemática en Blender")
        for bone in skeleton.get_bones().values():
            if " " in bone.name:
                result.add_warning(f"Nombre con espacios en {bone.name}")
        return result
