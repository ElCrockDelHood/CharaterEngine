"""Soft-tissue layer model: bone → tendon → muscle → fat → skin (pure Python).

Provides the qualitative anatomy (which layers exist, which muscles connect which
canonical bones) with explicit provenance. Geometry is produced by engine adapters
(Blender proxies now, sculpted/scanned meshes later) from this description.
"""

from .layers import (
    BODY_REGIONS,
    REGION_OF_BONE,
    BodyRegion,
    TissueLayer,
    TissueProfile,
    region_of_bone,
    tissue_profile,
)
from .muscles import MUSCLES, MuscleSpec, muscles_attached_to

__all__ = [
    "BODY_REGIONS",
    "REGION_OF_BONE",
    "BodyRegion",
    "TissueLayer",
    "TissueProfile",
    "region_of_bone",
    "tissue_profile",
    "MUSCLES",
    "MuscleSpec",
    "muscles_attached_to",
]
