"""T-pose (and other rest poses) as rigid rotations of canonical bone subtrees.

The canonical JSON stores the *anatomical position* (standing, arms hanging, palms
forward). Game and mocap pipelines expect a **T-pose**: arms horizontal along ±X,
palms down. A pose is a pure rigid transform of subtrees about joint centres, so
bone lengths, hierarchy and provenance are untouched.

Canonical frame: Z-up, -Y forward, +X = LEFT side (left bones have x > 0; Decision 17).
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence, Tuple

Vec = Tuple[float, float, float]
Mat = Tuple[Vec, Vec, Vec]


def _v(d) -> Vec:
    if isinstance(d, dict):
        return (float(d["x"]), float(d["y"]), float(d["z"]))
    return (float(d[0]), float(d[1]), float(d[2]))


def _d(v: Vec) -> dict:
    return {"x": round(v[0], 6), "y": round(v[1], 6), "z": round(v[2], 6)}


def _rot_x(deg: float) -> Mat:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def _rot_y(deg: float) -> Mat:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def _apply(m: Mat, v: Vec) -> Vec:
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))  # type: ignore[return-value]


def _rotate_about(m: Mat, v: Vec, pivot: Vec) -> Vec:
    rel = (v[0] - pivot[0], v[1] - pivot[1], v[2] - pivot[2])
    r = _apply(m, rel)
    return (r[0] + pivot[0], r[1] + pivot[1], r[2] + pivot[2])


def _children_index(bones: Sequence[dict]) -> Dict[str, List[str]]:
    idx: Dict[str, List[str]] = {}
    for b in bones:
        idx.setdefault(b.get("parent"), []).append(b["canonical_name"])
    return idx


def subtree(bones: Sequence[dict], roots: Iterable[str]) -> set:
    idx = _children_index(bones)
    out, stack = set(), list(roots)
    while stack:
        n = stack.pop()
        if n in out:
            continue
        out.add(n)
        stack.extend(idx.get(n, []))
    return out


def arm_subtree(bones: Sequence[dict], side: str) -> set:
    return subtree(bones, [f"HUMERUS_{side}"])


def _rotate_subtree(bones: List[dict], names: set, m: Mat, pivot: Vec) -> None:
    for b in bones:
        if b["canonical_name"] in names:
            b["head"] = _d(_rotate_about(m, _v(b["head"]), pivot))
            b["tail"] = _d(_rotate_about(m, _v(b["tail"]), pivot))


def apply_tpose(bones: Sequence[dict], palms: str = "down", abduction_deg: float = 90.0) -> List[dict]:
    """Return a deep-copied bone list in T-pose.

    ``abduction_deg``: 90 = arms horizontal (T), 45 = A-pose.
    ``palms``: ``"down"`` (game standard) or ``"forward"`` (anatomical).
    """
    out = [dict(b, head=dict(b["head"]), tail=dict(b["tail"])) for b in bones]
    by_name = {b["canonical_name"]: b for b in out}
    for side, sign in (("L", +1.0), ("R", -1.0)):
        hum = by_name.get(f"HUMERUS_{side}")
        if hum is None:
            continue
        shoulder = _v(hum["head"])
        # Arm hangs along -Z; rotate about Y so it points to sign*X.
        # R_y(+90) maps (0,0,-1) -> (-1,0,0); R_y(-90) maps it to (+1,0,0).
        arm = arm_subtree(out, side)
        _rotate_subtree(out, arm, _rot_y(-sign * abduction_deg), shoulder)
        if palms == "down" and abs(abduction_deg - 90.0) < 1e-6:
            # Pronate forearm + hand about the arm axis (world X) so the palm faces -Z.
            elbow = _v(by_name[f"HUMERUS_{side}"]["tail"])
            forearm = subtree(out, [f"RADIUS_{side}", f"ULNA_{side}"])
            _rotate_subtree(out, forearm, _rot_x(90.0), elbow)
    return out


POSES = {
    "anatomical": lambda bones: [dict(b, head=dict(b["head"]), tail=dict(b["tail"])) for b in bones],
    "tpose": lambda bones: apply_tpose(bones, palms="down", abduction_deg=90.0),
    "apose": lambda bones: apply_tpose(bones, palms="forward", abduction_deg=45.0),
}


def apply_pose(bones: Sequence[dict], pose: str) -> List[dict]:
    try:
        return POSES[pose](bones)
    except KeyError as exc:
        raise ValueError(f"unknown pose '{pose}', expected one of {sorted(POSES)}") from exc
