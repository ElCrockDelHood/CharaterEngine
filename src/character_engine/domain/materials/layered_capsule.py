"""Layered capsule: a block-dummy capsule split into concentric material shells.

The block-dummy capsule (``rigging/block_dummy.py``) is the skin surface. Inside it, the regional tissue profile
(``tissue/layers.py``) is laid out as concentric shells: bone core, tendon, muscle, fat, skin. Outside it, optional
garment and armour shells are added with air gaps. One signed distance to the capsule axis then answers both
"is there contact" and "which material is here".

Fitting rule (DERIVED from ESTIMATE inputs, hence ESTIMATE): the bone core radius is half the regional bone
thickness; the soft layers keep their relative thicknesses and are scaled to fill the space between the bone core
and the envelope radius. The regional profile and the envelope radius come from different estimates and do not add
up on their own, so the scale factor is reported.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..rigging.block_dummy import BlockPlacement
from ..tissue import TissueLayer, TissueProfile, tissue_profile
from .catalog import TISSUE_MATERIAL, MaterialKind

Vec = Tuple[float, float, float]

_SOFT = (TissueLayer.SKIN, TissueLayer.FAT, TissueLayer.MUSCLE, TissueLayer.TENDON)


@dataclass(frozen=True)
class Shell:
    """Annulus [r_inner, r_outer] around the capsule axis, filled with one material."""

    name: str
    material: MaterialKind
    r_inner: float
    r_outer: float
    tissue_layer: Optional[TissueLayer] = None
    z_range: Optional[Tuple[float, float]] = None   # axial extent as fractions a→b; None = whole capsule
    provenance: ProvenanceState = ProvenanceState.ESTIMATE

    @property
    def thickness(self) -> float:
        return self.r_outer - self.r_inner


@dataclass(frozen=True)
class OuterLayer:
    """Garment or armour shell spec: material, thickness and the air gap under it (m)."""

    name: str
    material: MaterialKind
    thickness_m: float
    gap_m: float
    z_range: Optional[Tuple[float, float]] = None
    provenance: ProvenanceState = ProvenanceState.ESTIMATE


@dataclass(frozen=True)
class LayeredCapsule:
    placement: BlockPlacement
    shells: Tuple[Shell, ...]           # inside → outside
    soft_scale: float                   # factor applied to the regional soft-layer thicknesses
    profile: TissueProfile              # fitted profile (thicknesses as laid out), for assess_wound

    @property
    def skin_radius(self) -> float:
        return self.placement.radius_m

    @property
    def outer_radius(self) -> float:
        return self.shells[-1].r_outer

    def shell(self, name: str) -> Shell:
        for s in self.shells:
            if s.name == name:
                return s
        raise KeyError(name)

    def axial(self, p: Vec) -> Tuple[float, float]:
        """(distance to the axis segment, axial parameter t in [0, 1] a→b)."""
        return segment_distance(p, self.placement.a, self.placement.b)

    def signed_distance(self, p: Vec, radius: Optional[float] = None) -> float:
        """Signed distance to the skin surface (or to ``radius``): negative inside."""
        d, _ = self.axial(p)
        return d - (self.skin_radius if radius is None else radius)

    def material_at(self, p: Vec) -> Optional[MaterialKind]:
        d, t = self.axial(p)
        for s in self.shells:
            if s.r_inner <= d < s.r_outer and (s.z_range is None or s.z_range[0] <= t <= s.z_range[1]):
                return s.material
        return None


def segment_distance(p: Vec, a: Vec, b: Vec) -> Tuple[float, float]:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
    ll = ab[0] * ab[0] + ab[1] * ab[1] + ab[2] * ab[2]
    t = 0.0 if ll == 0.0 else max(0.0, min(1.0, (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / ll))
    c = (a[0] + ab[0] * t - p[0], a[1] + ab[1] * t - p[1], a[2] + ab[2] * t - p[2])
    return math.sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]), t


def layered_capsule(placement: BlockPlacement, outer: Sequence[OuterLayer] = (),
                    profile: Optional[TissueProfile] = None) -> LayeredCapsule:
    profile = profile or tissue_profile(placement.region)
    r_skin = placement.radius_m
    bone_core = profile.thickness_m.get(TissueLayer.BONE, 0.0) / 2.0
    if bone_core >= r_skin:
        raise ValueError(f"bone core {bone_core} m does not fit inside envelope {r_skin} m")
    soft = [layer for layer in _SOFT if layer in profile.thickness_m]
    soft_total = sum(profile.thickness_m[layer] for layer in soft)
    scale = (r_skin - bone_core) / soft_total
    shells: List[Shell] = []
    if bone_core > 0:
        shells.append(Shell("bone", MaterialKind.BONE, 0.0, bone_core, TissueLayer.BONE))
    r = bone_core
    fitted: Dict[TissueLayer, float] = {}
    for layer in reversed(soft):                       # tendon → muscle → fat → skin
        t = profile.thickness_m[layer] * scale
        fitted[layer] = t
        r_out = r_skin if layer is TissueLayer.SKIN else r + t
        shells.append(Shell(layer.value, TISSUE_MATERIAL[layer], r, r_out, layer))
        r = r_out
    for o in outer:
        if o.gap_m > 0:
            shells.append(Shell(f"{o.name}_gap", MaterialKind.AIR, r, r + o.gap_m, None, o.z_range, o.provenance))
            r += o.gap_m
        shells.append(Shell(o.name, o.material, r, r + o.thickness_m, None, o.z_range, o.provenance))
        r += o.thickness_m
    fitted[TissueLayer.BONE] = bone_core * 2.0
    thickness = {layer: round(fitted[layer], 6) for layer in profile.layers() if layer in fitted}
    if TissueLayer.VISCERA in profile.thickness_m:
        thickness[TissueLayer.VISCERA] = profile.thickness_m[TissueLayer.VISCERA]
    ranges = {layer: ((lo * scale, hi * scale) if layer in soft else (lo, hi))
              for layer, (lo, hi) in profile.thickness_range_m.items()}
    fitted_profile = TissueProfile(region=profile.region, thickness_m=thickness, thickness_range_m=ranges,
                                   has_cavity=profile.has_cavity, provenance=ProvenanceState.ESTIMATE,
                                   notes=f"fitted to envelope radius {r_skin} m (soft scale {scale:.3f})")
    return LayeredCapsule(placement, tuple(shells), round(scale, 6), fitted_profile)
