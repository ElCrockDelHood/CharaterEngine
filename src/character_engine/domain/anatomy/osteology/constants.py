"""Constantes del dominio esquelético."""

from enum import Enum


class BoneState(Enum):
    CREATED = "created"
    VALIDATED = "validated"
    BUILT = "built"
    SERIALIZED = "serialized"
    IMPORTED = "imported"
    RUNTIME = "runtime"
    ARCHIVED = "archived"

class BoneType(Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"
    IRREGULAR = "irregular"
    SESAMOID = "sesamoid"
    CUSTOM = "custom"

class JointType(Enum):
    FIXED = "fixed"
    HINGE = "hinge"
    BALL = "ball"
    UNIVERSAL = "universal"
    PIVOT = "pivot"
    SADDLE = "saddle"
    CUSTOM = "custom"

class ValidationLevel(Enum):
    SYNTACTIC = "syntactic"
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"
    FUNCTIONAL = "functional"
    INTEGRATION = "integration"
