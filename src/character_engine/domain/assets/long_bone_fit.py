"""Anchor rules and canonical targets for fitting long-bone meshes (F2 of ASSET_FITTING_PROPOSAL.md).

Pure Python. Everything here is ESTIMATE: the anchor rules are proposals (see
``docs/architecture/FEMUR_ANCHOR_LANDMARKS_PROPOSAL.md`` and ``docs/audit/A20_F2_LONG_BONES_FIT.md``), the anchor
names are **not** added to the domain landmark list, and no tolerance is decided.

Asset convention (BodyParts3D, A18): metres after unit conversion, Z-up, −Y front, a LEFT bone with lateral = +X,
anatomical position (bones roughly vertical). Right bones are handled by mirroring x → −x, applying the left rule
and mirroring the anchors back.

Each bone has two joint ends (proximal → canonical ``head``, distal → canonical ``tail``). An end is either
* a single joint point (``sphere`` fit of an articular head, or ``centroid`` of an end slice), or
* a lateral / medial **pair** of extreme vertices whose midpoint is the joint centre (as ``biomechanics.json`` puts
  the knee and elbow centres equidistant from the epicondyles, ASSUMPTION).
If no end is a pair, a third ``roll`` anchor (an extreme vertex) is added so the 3 anchors are not collinear.

Canonical targets: ``head`` / ``tail`` are read from the canonical skeleton. The lateral / medial / roll targets
are not measured anywhere in the canonical data, so they are DERIVED FROM THE ASSET: the asset offset is scaled by
s0 = |head − tail| / |proximal joint − distal joint| and only its **lateral** component is kept, placed along the
canonical lateral direction ⟂ to the bone axis. Consequence (documented in A19/A20): the anchor RMS measures the
antero-posterior offset of those points from the bone's lateral plane, not an independent fit error.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .registration import fit_sphere

Vec = Tuple[float, float, float]

HEAD_OUTLIER_M = 0.003   # second sphere pass keeps points within 3 mm of the first sphere (ESTIMATE)


@dataclass(frozen=True)
class AnchorRule:
    name: str                      # proposed landmark name (bone in the name), NOT in the domain landmark list
    kind: str                      # "sphere" | "centroid" | "extreme"
    end: str                       # "proximal" | "distal"
    fraction: float                # slice of the bone height (ESTIMATE)
    half: Optional[str] = None     # sphere: "medial" | "lateral" half of the slice (by median x)
    direction: Optional[Vec] = None   # extreme: direction in the LEFT asset frame


@dataclass(frozen=True)
class EndRule:
    joint: Optional[AnchorRule] = None
    pair: Optional[Tuple[AnchorRule, AnchorRule]] = None   # (lateral, medial)


@dataclass(frozen=True)
class BoneRule:
    bone: str
    proximal: EndRule
    distal: EndRule
    roll: Optional[AnchorRule] = None
    note: str = ""

    def anchor_names(self) -> Tuple[str, ...]:
        out: List[str] = []
        for end in (self.proximal, self.distal):
            out += [end.joint.name] if end.joint else [end.pair[0].name, end.pair[1].name]
        if self.roll:
            out.append(self.roll.name)
        return tuple(out)


LAT, MED, ANT = (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)


def _pair(prefix: str, end: str, fraction: float, lat_name: str, med_name: str) -> EndRule:
    return EndRule(pair=(AnchorRule(f"{prefix}_{lat_name}", "extreme", end, fraction, direction=LAT),
                         AnchorRule(f"{prefix}_{med_name}", "extreme", end, fraction, direction=MED)))


# The femur rule is exactly the one measured in A19 (Decision 63).
RULES: Mapping[str, BoneRule] = {
    "FEMUR": BoneRule(
        "FEMUR",
        EndRule(joint=AnchorRule("femoral_head_centre", "sphere", "proximal", 0.12, half="medial")),
        _pair("femoral", "distal", 0.10, "lateral_epicondyle", "medial_epicondyle"),
        note="head = sphere on the proximal-medial 12 %; epicondyles = ±X extremes of the distal 10 %"),
    "TIBIA": BoneRule(
        "TIBIA",
        _pair("tibial", "proximal", 0.10, "lateral_condyle_edge", "medial_condyle_edge"),
        _pair("tibial", "distal", 0.08, "fibular_notch_edge", "medial_malleolus_edge"),
        note="4 anchors: ±X extremes of the proximal 10 % (condyles) and distal 8 % (fibular notch / medial malleolus)"),
    "FIBULA": BoneRule(
        "FIBULA",
        EndRule(joint=AnchorRule("fibular_head_centroid", "centroid", "proximal", 0.05)),
        EndRule(joint=AnchorRule("lateral_malleolus_centroid", "centroid", "distal", 0.05)),
        roll=AnchorRule("lateral_malleolus_lateral_point", "extreme", "distal", 0.15, direction=LAT),
        note="thin bone: the roll anchor sits only ~1 cm off the axis, so roll is weakly defined"),
    "HUMERUS": BoneRule(
        "HUMERUS",
        EndRule(joint=AnchorRule("humeral_head_centre", "sphere", "proximal", 0.12, half="medial")),
        _pair("humeral", "distal", 0.10, "lateral_epicondyle", "medial_epicondyle"),
        note="same rule as the femur: head sphere + epicondyles"),
    "RADIUS": BoneRule(
        "RADIUS",
        EndRule(joint=AnchorRule("radial_head_centroid", "centroid", "proximal", 0.05)),
        _pair("radial", "distal", 0.10, "styloid_tip", "ulnar_notch_edge"),
        note="radial head is a disc, not a sphere: centroid of the proximal 5 %"),
    "ULNA": BoneRule(
        "ULNA",
        EndRule(joint=AnchorRule("ulnar_proximal_centroid", "centroid", "proximal", 0.10)),
        EndRule(joint=AnchorRule("ulnar_head_centroid", "centroid", "distal", 0.05)),
        roll=AnchorRule("ulnar_radial_notch_lateral_point", "extreme", "proximal", 0.15, direction=LAT),
        note="proximal centroid includes the olecranon, so it sits above the elbow joint centre (ESTIMATE)"),
}


# ------------------------------------------------------------------------------------------------ geometry

def _slice(verts: Sequence[Vec], end: str, fraction: float) -> List[Vec]:
    zs = [p[2] for p in verts]
    zmin, zmax = min(zs), max(zs)
    if end == "proximal":
        return [p for p in verts if p[2] > zmax - fraction * (zmax - zmin)]
    return [p for p in verts if p[2] < zmin + fraction * (zmax - zmin)]


def extract_anchor(rule: AnchorRule, verts: Sequence[Vec]) -> Tuple[Vec, Dict[str, float]]:
    """Anchor point (LEFT asset frame) and extraction info."""
    pts = _slice(verts, rule.end, rule.fraction)
    if not pts:
        raise ValueError(f"{rule.name}: empty slice")
    if rule.kind == "sphere":
        if rule.half:
            xmed = statistics.median(p[0] for p in pts)
            pts = [p for p in pts if (p[0] < xmed) == (rule.half == "medial")]
        c1, r1, _ = fit_sphere(pts)
        kept = [p for p in pts if abs(math.dist(p, c1) - r1) < HEAD_OUTLIER_M]
        c, r, rms = fit_sphere(kept)
        return c, {"points": len(kept), "points_first_pass": len(pts), "radius_mm": r * 1e3, "sphere_rms_mm": rms * 1e3}
    if rule.kind == "centroid":
        n = len(pts)
        return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n), {"points": n}
    if rule.kind == "extreme":
        d = rule.direction
        return max(pts, key=lambda p: p[0] * d[0] + p[1] * d[1] + p[2] * d[2]), {"points": len(pts)}
    raise ValueError(f"unknown anchor kind {rule.kind}")


def extract_anchors(rule: BoneRule, verts: Sequence[Vec], side: str = "L") -> Tuple[Dict[str, Vec], Dict[str, dict]]:
    """Anchors for a bone mesh. ``side='R'``: mirror, extract with the left rule, mirror back."""
    mirror = side == "R"
    work = [(-p[0], p[1], p[2]) for p in verts] if mirror else list(verts)
    anchors: Dict[str, Vec] = {}
    info: Dict[str, dict] = {}
    rules: List[AnchorRule] = []
    for end in (rule.proximal, rule.distal):
        rules += [end.joint] if end.joint else list(end.pair)
    if rule.roll:
        rules.append(rule.roll)
    for r in rules:
        p, i = extract_anchor(r, work)
        anchors[r.name] = (-p[0], p[1], p[2]) if mirror else p
        info[r.name] = i
    return anchors, info


def _v(a, b, op):
    return tuple(op(x, y) for x, y in zip(a, b))


def _sub(a, b):
    return _v(a, b, lambda x, y: x - y)


def _add(a, b):
    return _v(a, b, lambda x, y: x + y)


def _scale(a, s):
    return tuple(x * s for x in a)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _norm(a):
    n = math.sqrt(_dot(a, a))
    return tuple(x / n for x in a)


def end_point(end: EndRule, anchors: Mapping[str, Vec]) -> Vec:
    if end.joint:
        return anchors[end.joint.name]
    lat, med = anchors[end.pair[0].name], anchors[end.pair[1].name]
    return _scale(_add(lat, med), 0.5)


def canonical_lateral(head: Vec, tail: Vec, side: str) -> Vec:
    """Canonical lateral direction ⟂ to the bone axis: ±X with the axis component removed (Decision 33)."""
    axis = _norm(_sub(head, tail))
    x = (1.0, 0.0, 0.0) if side == "L" else (-1.0, 0.0, 0.0)
    return _norm(_sub(x, _scale(axis, _dot(x, axis))))


def derive_targets(rule: BoneRule, anchors: Mapping[str, Vec], head: Vec, tail: Vec, side: str
                   ) -> Tuple[Dict[str, Vec], Dict[str, str]]:
    """Canonical targets for every anchor (head / tail measured; the rest DERIVED from the asset, ESTIMATE)."""
    a_prox, a_dist = end_point(rule.proximal, anchors), end_point(rule.distal, anchors)
    s0 = math.dist(head, tail) / math.dist(a_prox, a_dist)
    lateral = canonical_lateral(head, tail, side)
    a_lat_dir = (1.0, 0.0, 0.0) if side == "L" else (-1.0, 0.0, 0.0)
    targets: Dict[str, Vec] = {}
    prov: Dict[str, str] = {}
    for end, joint in ((rule.proximal, head), (rule.distal, tail)):
        if end.joint:
            targets[end.joint.name] = tuple(joint)
            prov[end.joint.name] = "canonical head/tail (read-only)"
        else:
            lat, med = anchors[end.pair[0].name], anchors[end.pair[1].name]
            half_w = math.dist(lat, med) * s0 / 2
            targets[end.pair[0].name] = _add(joint, _scale(lateral, half_w))
            targets[end.pair[1].name] = _sub(joint, _scale(lateral, half_w))
            prov[end.pair[0].name] = prov[end.pair[1].name] = (
                "canonical joint ± asset half-width × s0 along canonical lateral ⟂ axis — DERIVED, ESTIMATE")
    if rule.roll:
        p = anchors[rule.roll.name]
        a_axis = _sub(a_prox, a_dist)
        t = _dot(_sub(p, a_dist), a_axis) / _dot(a_axis, a_axis)          # axial parameter, 0 = distal joint
        a_lat = _norm(_sub(a_lat_dir, _scale(_norm(a_axis), _dot(a_lat_dir, _norm(a_axis)))))
        lateral_offset = _dot(_sub(p, _add(a_dist, _scale(a_axis, t))), a_lat) * s0
        targets[rule.roll.name] = _add(_add(tail, _scale(_sub(head, tail), t)), _scale(lateral, lateral_offset))
        prov[rule.roll.name] = ("canonical axis at the anchor's axial parameter + its lateral offset × s0 — DERIVED, "
                                "ESTIMATE (antero-posterior offset dropped)")
    return targets, prov


def axial_extent(verts: Sequence[Vec], head: Vec, tail: Vec) -> float:
    """Length of the vertex cloud along the canonical bone axis (max − min projection)."""
    axis = _norm(_sub(head, tail))
    proj = [_dot(p, axis) for p in verts]
    return max(proj) - min(proj)
