"""Excepciones del dominio esquelético."""

from character_engine.exceptions.domain_error import DomainError


class SkeletonError(DomainError):
    pass

class BoneNotFoundError(SkeletonError):
    pass

class BoneAlreadyExistsError(SkeletonError):
    pass

class CyclicHierarchyError(SkeletonError):
    pass

class InvalidGeometryError(SkeletonError):
    pass

class InvalidParentError(SkeletonError):
    pass

class InvalidChildError(SkeletonError):
    pass

class MissingRootError(SkeletonError):
    pass

class MultipleRootsError(SkeletonError):
    pass

class DuplicateChildError(SkeletonError):
    pass

class BoneValidationError(SkeletonError):
    pass
