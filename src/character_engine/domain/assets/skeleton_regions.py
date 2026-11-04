"""Whole-skeleton, region-by-region comparison of an asset skeleton with the canonical one (F2, A22).

Pure Python. Everything here is ESTIMATE and only measures; nothing is fitted into the canonical data and no
tolerance is decided.

Method:
1. **One global similarity** (``domain/assets/registration.py``) brings the asset skeleton into the canonical frame,
   with the joint centres the canonical data actually carries for the limbs: hip, knee, shoulder and elbow, left and
   right (8 points, from the A20 femur / humerus rules: femoral and humeral head spheres, epicondyle midpoints).
   No derived target is used, so the residuals are real.
2. In that frame, **every bone** is compared with its canonical head → tail segment: the mesh centroid's distance to
   the segment, the end-slice centroids (along the canonical direction) against head and tail, the extent along the
   segment against its length, and the angle between the two axes.
3. Per **region** (pelvis, spine, thorax, shoulder girdle, arm, hand, leg, foot, skull): median / p95 / max of those
   numbers and the mean residual vector (a systematic shift of the whole region).

Many canonical segments of the axial skeleton are schematic (short vertical stubs for vertebrae, vertical segments
for skull bones), so a large distance there is a finding about the canonical layout, not a fitting error.
"""

from __future__ import annotations

import math
import statistics
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

Vec = Tuple[float, float, float]

END_FRACTION = 0.10      # slice of the extent along the canonical direction used for an end centroid (ESTIMATE)
MIN_END_POINTS = 3

SIDES = ("L", "R")
_SKULL = ("FRONTAL", "PARIETAL_L", "PARIETAL_R", "TEMPORAL_L", "TEMPORAL_R", "OCCIPITAL", "SPHENOID", "ETHMOID",
          "MAXILLA_L", "MAXILLA_R", "ZYGOMATIC_L", "ZYGOMATIC_R", "NASAL_L", "NASAL_R", "LACRIMAL_L", "LACRIMAL_R",
          "PALATINE_L", "PALATINE_R", "INFERIOR_NASAL_CONCHA_L", "INFERIOR_NASAL_CONCHA_R", "VOMER", "MANDIBLE",
          "HYOID", "MALLEUS_L", "MALLEUS_R", "INCUS_L", "INCUS_R", "STAPES_L", "STAPES_R")
_CARPALS = ("SCAPHOID", "LUNATE", "TRIQUETRUM", "PISIFORM", "TRAPEZIUM", "TRAPEZOID", "CAPITATE", "HAMATE")
_TARSALS = ("TALUS", "CALCANEUS", "NAVICULAR", "CUBOID", "CUNEIFORM_MEDIAL", "CUNEIFORM_INTERMEDIATE",
            "CUNEIFORM_LATERAL")


def _hand(s: str) -> Tuple[str, ...]:
    out = [f"{c}_{s}" for c in _CARPALS] + [f"METACARPAL_{i}_{s}" for i in range(1, 6)]
    for r in range(1, 6):
        for k in ("PROXIMAL", "INTERMEDIATE", "DISTAL"):
            if not (r == 1 and k == "INTERMEDIATE"):
                out.append(f"PHALANX_{k}_{r}_{s}")
    return tuple(out)


def _foot(s: str) -> Tuple[str, ...]:
    out = [f"{t}_{s}" for t in _TARSALS] + [f"METATARSAL_{i}_{s}" for i in range(1, 6)]
    for r in range(1, 6):
        for k in ("PROXIMAL", "INTERMEDIATE", "DISTAL"):
            if not (r == 1 and k == "INTERMEDIATE"):
                out.append(f"TOE_PHALANX_{k}_{r}_{s}")
    return tuple(out)


REGIONS: Mapping[str, Tuple[str, ...]] = {
    "pelvis": ("COXAL_L", "COXAL_R", "SACRUM", "COCCYX"),
    "spine": tuple([f"CERVICAL_{i}" for i in range(1, 8)] + [f"THORACIC_{i}" for i in range(1, 13)]
                   + [f"LUMBAR_{i}" for i in range(1, 6)]),
    "thorax": ("STERNUM",) + tuple(f"RIB_{i:02d}_{s}" for s in SIDES for i in range(1, 13)),
    "shoulder_girdle": ("CLAVICLE_L", "CLAVICLE_R", "SCAPULA_L", "SCAPULA_R"),
    "arm": tuple(f"{b}_{s}" for s in SIDES for b in ("HUMERUS", "RADIUS", "ULNA")),
    "hand": _hand("L") + _hand("R"),
    "leg": tuple(f"{b}_{s}" for s in SIDES for b in ("FEMUR", "PATELLA", "TIBIA", "FIBULA")),
    "foot": _foot("L") + _foot("R"),
    "skull": _SKULL,
}

# Joint centres used for the global similarity: (bone, end) -> canonical head / tail (measured joints of the rig)
GLOBAL_ANCHORS: Tuple[Tuple[str, str], ...] = tuple(
    (f"{b}_{s}", end) for b in ("FEMUR", "HUMERUS") for s in SIDES for end in ("proximal", "distal"))


def all_region_bones() -> Tuple[str, ...]:
    return tuple(b for bones in REGIONS.values() for b in bones)


# ------------------------------------------------------------------------------------------------ vectors

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    n = math.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def centroid(points: Sequence[Vec]) -> Vec:
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n, sum(p[2] for p in points) / n)


def point_segment_distance(p: Vec, a: Vec, b: Vec) -> float:
    ab = _sub(b, a)
    t = max(0.0, min(1.0, _dot(_sub(p, a), ab) / _dot(ab, ab)))
    return math.dist(p, (a[0] + ab[0] * t, a[1] + ab[1] * t, a[2] + ab[2] * t))


def end_centroid(points: Sequence[Vec], direction: Vec, end: str, fraction: float = END_FRACTION) -> Vec:
    """Centroid of the vertices in the ``fraction`` of the extent at one end along ``direction`` (head → tail).

    ``end='head'`` is the end opposite to ``direction``; at least ``MIN_END_POINTS`` vertices are used."""
    d = _norm(direction)
    proj = sorted(((_dot(p, d), p) for p in points), key=lambda x: x[0])
    lo, hi = proj[0][0], proj[-1][0]
    if end == "head":
        sel = [p for s, p in proj if s <= lo + fraction * (hi - lo)] or [p for _, p in proj[:MIN_END_POINTS]]
        if len(sel) < MIN_END_POINTS:
            sel = [p for _, p in proj[:MIN_END_POINTS]]
    else:
        sel = [p for s, p in proj if s >= hi - fraction * (hi - lo)]
        if len(sel) < MIN_END_POINTS:
            sel = [p for _, p in proj[-MIN_END_POINTS:]]
    return centroid(sel)


def bone_metrics(points: Sequence[Vec], head: Vec, tail: Vec) -> Dict[str, object]:
    """Compare a mesh (already in the canonical frame, metres) with its canonical head → tail segment."""
    axis = _sub(tail, head)
    length = math.sqrt(_dot(axis, axis))
    d = _norm(axis)
    c = centroid(points)
    h, t = end_centroid(points, d, "head"), end_centroid(points, d, "tail")
    proj = [_dot(p, d) for p in points]
    extent = max(proj) - min(proj)
    asset_axis = _sub(t, h)
    al = math.sqrt(_dot(asset_axis, asset_axis))
    angle = math.degrees(math.acos(max(-1.0, min(1.0, _dot(asset_axis, d) / al)))) if al > 0 else float("nan")
    return {
        "centroid_to_segment_mm": point_segment_distance(c, head, tail) * 1e3,
        "centroid_minus_midpoint_mm": [(c[i] - (head[i] + tail[i]) / 2) * 1e3 for i in range(3)],
        "head_error_mm": math.dist(h, head) * 1e3,
        "tail_error_mm": math.dist(t, tail) * 1e3,
        "canonical_length_mm": length * 1e3,
        "extent_along_axis_mm": extent * 1e3,
        "extent_over_length": extent / length,
        "axis_angle_deg": angle,
    }


def stats(values: Sequence[float]) -> Dict[str, float]:
    v = sorted(x for x in values if x == x)
    if not v:
        return {"n": 0}
    return {"n": len(v), "min": v[0], "median": statistics.median(v), "p95": v[int(0.95 * (len(v) - 1))],
            "max": v[-1], "mean": statistics.mean(v)}


def region_summary(metrics: Mapping[str, Mapping[str, object]], bones: Sequence[str]) -> Dict[str, object]:
    present = [b for b in bones if b in metrics]
    shift = [0.0, 0.0, 0.0]
    for b in present:
        for i in range(3):
            shift[i] += metrics[b]["centroid_minus_midpoint_mm"][i] / len(present)
    after_shift = [math.dist(metrics[b]["centroid_minus_midpoint_mm"], shift) for b in present]
    return {
        "bones": len(bones), "fitted": len(present), "missing": [b for b in bones if b not in metrics],
        # centroid vs segment midpoint once the region's mean shift is removed: layout inside the region
        "centroid_to_midpoint_after_region_shift_mm": stats(after_shift),
        "centroid_to_segment_mm": stats([metrics[b]["centroid_to_segment_mm"] for b in present]),
        "head_error_mm": stats([metrics[b]["head_error_mm"] for b in present]),
        "tail_error_mm": stats([metrics[b]["tail_error_mm"] for b in present]),
        "extent_over_length": stats([metrics[b]["extent_over_length"] for b in present]),
        "axis_angle_deg": stats([metrics[b]["axis_angle_deg"] for b in present]),
        "mean_centroid_shift_mm": shift if present else None,
    }


# ------------------------------------------------------------------------------------------------ pelvis landmarks

def pelvis_landmarks(coxal_left: Sequence[Vec], coxal_right: Sequence[Vec]) -> Dict[str, Vec]:
    """Proposed pelvic landmarks from hip-bone meshes (asset frame: Z-up, −Y front, left = +X). ESTIMATE.

    ASIS = most anterior vertex of the upper 40 % of each hip bone; PSIS = most posterior vertex of the upper 40 %;
    pubic symphysis = midpoint of the most medial vertices of the lower 30 % of each hip bone."""
    out: Dict[str, Vec] = {}
    for side, pts, medial in (("L", coxal_left, -1.0), ("R", coxal_right, 1.0)):
        zs = [p[2] for p in pts]
        zmin, zmax = min(zs), max(zs)
        upper = [p for p in pts if p[2] > zmax - 0.40 * (zmax - zmin)]
        lower = [p for p in pts if p[2] < zmin + 0.30 * (zmax - zmin)]
        out[f"asis_{side}"] = min(upper, key=lambda p: p[1])
        out[f"psis_{side}"] = max(upper, key=lambda p: p[1])
        out[f"pubic_medial_{side}"] = max(lower, key=lambda p: medial * p[0])
    l, r = out["pubic_medial_L"], out["pubic_medial_R"]
    out["pubic_symphysis"] = ((l[0] + r[0]) / 2, (l[1] + r[1]) / 2, (l[2] + r[2]) / 2)
    return out


def pelvis_dimensions(lm: Mapping[str, Vec], hip_l: Vec, hip_r: Vec) -> Dict[str, float]:
    """Distances (mm) between proposed landmarks and the hip joint centres; no coordinates."""
    mid_asis = centroid([lm["asis_L"], lm["asis_R"]])
    mid_psis = centroid([lm["psis_L"], lm["psis_R"]])
    return {
        "inter_asis_width_mm": math.dist(lm["asis_L"], lm["asis_R"]) * 1e3,
        "inter_psis_width_mm": math.dist(lm["psis_L"], lm["psis_R"]) * 1e3,
        "pelvic_depth_asis_psis_mm": math.dist(mid_asis, mid_psis) * 1e3,
        "inter_hip_centre_width_mm": math.dist(hip_l, hip_r) * 1e3,
        "symphysis_to_mid_asis_mm": math.dist(lm["pubic_symphysis"], mid_asis) * 1e3,
    }


def anchor_targets(joints: Mapping[str, Tuple[Vec, Vec]]) -> List[Vec]:
    """Canonical targets of ``GLOBAL_ANCHORS`` (head for proximal, tail for distal)."""
    return [joints[b][0] if end == "proximal" else joints[b][1] for b, end in GLOBAL_ANCHORS]


def missing_in(mapping: Mapping[str, Optional[str]]) -> List[str]:
    return [b for b in all_region_bones() if not mapping.get(b)]
