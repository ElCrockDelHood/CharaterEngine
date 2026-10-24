"""Stature retarget of a canonical bone list using published landmark ratios.

Pure-Python core used by ``scripts/retarget_stature.py`` (A07) and by character
templates. Three monotonic piecewise-linear Z maps (axial / arm / leg) pass exactly
through sourced landmarks; XY is scaled uniformly to the biacromial breadth.
See ``docs/audit/A07_STATURE_RETARGET_180.md`` for the method and provenance.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

SOURCE_ID = "DRILLIS_CONTINI_1966"

# Fraction of stature H (Drillis & Contini 1966 via Winter 2009 Fig. 4.1). Heights from ground.
DRILLIS_CONTINI_RATIOS: Mapping[str, float] = {
    "vertex": 1.000,
    "chin": 0.870,
    "shoulder": 0.818,
    "elbow": 0.630,
    "hip": 0.530,
    "wrist": 0.485,
    "fingertip": 0.377,
    "knee": 0.285,
    "ankle": 0.039,
    "ground": 0.000,
    "shoulder_breadth": 0.259,
}

Vec = Tuple[float, float, float]


def _v(d) -> Vec:
    if isinstance(d, dict):
        return (float(d["x"]), float(d["y"]), float(d["z"]))
    return (float(d[0]), float(d[1]), float(d[2]))


def _d(v: Vec) -> dict:
    return {"x": round(v[0], 4), "y": round(v[1], 4), "z": round(v[2], 4)}


def _subtree(bones: Sequence[dict], roots: Iterable[str]) -> set:
    children: Dict[str, List[str]] = {}
    for b in bones:
        children.setdefault(b.get("parent"), []).append(b["canonical_name"])
    out, stack = set(), list(roots)
    while stack:
        n = stack.pop()
        if n in out:
            continue
        out.add(n)
        stack.extend(children.get(n, []))
    return out


class PiecewiseLinear:
    """Monotonic piecewise-linear map through (src, dst) anchors; linear extrapolation."""

    def __init__(self, anchors: Sequence[Tuple[float, float]]):
        pts = sorted(anchors)
        for (s0, d0), (s1, d1) in zip(pts, pts[1:]):
            if s1 <= s0 or d1 <= d0:
                raise ValueError(f"anchors must be strictly increasing: {pts}")
        self.pts = pts

    def _segment(self, z: float):
        pts = self.pts
        if z <= pts[0][0]:
            return pts[0], pts[1]
        if z >= pts[-1][0]:
            return pts[-2], pts[-1]
        for a, b in zip(pts, pts[1:]):
            if a[0] <= z <= b[0]:
                return a, b
        raise AssertionError("unreachable")

    def __call__(self, z: float) -> float:
        (s0, d0), (s1, d1) = self._segment(z)
        return d0 + (z - s0) * (d1 - d0) / (s1 - s0)


def measure_landmarks(bones: Sequence[dict]) -> Dict[str, float]:
    """Read the landmark heights (m) from a bone list in anatomical position."""
    B = {b["canonical_name"]: b for b in bones}

    def z(n, k):
        return _v(B[n][k])[2]

    arm = _subtree(bones, ["HUMERUS_L", "HUMERUS_R"])
    leg = _subtree(bones, ["FEMUR_L", "FEMUR_R"])
    all_z = [_v(b[k])[2] for b in bones for k in ("head", "tail")]
    arm_z = [_v(b[k])[2] for b in bones if b["canonical_name"] in arm for k in ("head", "tail")]
    leg_z = [_v(b[k])[2] for b in bones if b["canonical_name"] in leg for k in ("head", "tail")]
    return {
        "vertex": max(all_z),
        "chin": min(z("MANDIBLE", "head"), z("MANDIBLE", "tail")),
        "shoulder": (z("HUMERUS_L", "head") + z("HUMERUS_R", "head")) / 2,
        "elbow": (z("HUMERUS_L", "tail") + z("RADIUS_L", "head")) / 2,
        "wrist": z("RADIUS_L", "tail"),
        "fingertip": min(arm_z),
        "hip": (z("FEMUR_L", "head") + z("FEMUR_R", "head")) / 2,
        "knee": (z("FEMUR_L", "tail") + z("TIBIA_L", "head")) / 2,
        "ankle": z("TIBIA_L", "tail"),
        "ground": min(leg_z),
        "shoulder_breadth": abs(_v(B["HUMERUS_L"]["head"])[0] - _v(B["HUMERUS_R"]["head"])[0]),
    }


def retarget_stature(bones: Sequence[dict], stature_m: float,
                     ratios: Mapping[str, float] = DRILLIS_CONTINI_RATIOS) -> Tuple[List[dict], dict]:
    """Return (new_bones, report). ``bones`` must be in anatomical position."""
    if stature_m <= 0:
        raise ValueError("stature must be positive")
    src = measure_landmarks(bones)
    dst = {k: r * stature_m for k, r in ratios.items()}

    axial = PiecewiseLinear([(src[k], dst[k]) for k in ("hip", "shoulder", "chin", "vertex")])
    arm = PiecewiseLinear([(src[k], dst[k]) for k in ("fingertip", "wrist", "elbow", "shoulder")])
    leg = PiecewiseLinear([(src[k], dst[k]) for k in ("ground", "ankle", "knee", "hip")])
    kxy = dst["shoulder_breadth"] / src["shoulder_breadth"]

    arm_set = _subtree(bones, ["HUMERUS_L", "HUMERUS_R"])
    leg_set = _subtree(bones, ["FEMUR_L", "FEMUR_R"])

    out: List[dict] = []
    for b in bones:
        name = b["canonical_name"]
        fz = arm if name in arm_set else leg if name in leg_set else axial
        nb = dict(b)
        for key in ("head", "tail"):
            x, y, z = _v(b[key])
            nb[key] = _d((x * kxy, y * kxy, fz(z)))
        out.append(nb)

    post = measure_landmarks(out)
    report = {
        "source_id": SOURCE_ID,
        "stature_m": stature_m,
        "ratios": dict(ratios),
        "xy_scale": round(kxy, 6),
        "regions": {
            "axial": ["hip", "shoulder", "chin", "vertex"],
            "arm": ["fingertip", "wrist", "elbow", "shoulder"],
            "leg": ["ground", "ankle", "knee", "hip"],
        },
        "landmarks": {
            k: {"before_m": round(src[k], 4), "target_m": round(dst[k], 4), "after_m": round(post[k], 4),
                "provenance": "DERIVED"}
            for k in ratios
        },
        "provenance_note": (
            "Landmark ratios PROVEN (Drillis & Contini 1966 via Winter 2009 Fig. 4.1); absolute "
            "landmark heights DERIVED for H=stature; every other bone position ESTIMATE "
            "(piecewise-linear interpolation of the previous layout); XY scale ESTIMATE."
        ),
    }
    return out, report
