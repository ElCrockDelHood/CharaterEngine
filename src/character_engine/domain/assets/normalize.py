"""Scale normalizer for imported meshes (owner request P2).

Brings any mesh into the canonical frame: metres, Z-up, −Y forward, origin at the ground under the
centre of the footprint, scaled to a target height. The source orientation is declared by the user
(``up`` / ``forward`` axes, e.g. glTF/FBX characters are usually ``+Y`` up and ``+Z`` forward). The
result is a 4×4 affine matrix applied to the vertices by the engine adapter.

The target height is a choice (e.g. the canonical stature), so every normalized size is at best an
ESTIMATE, never a measurement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Tuple

from ..anatomy.reference.source import ProvenanceState

Vec = Tuple[float, float, float]
Matrix3 = Tuple[Vec, Vec, Vec]
Matrix4 = Tuple[Tuple[float, float, float, float], ...]

AXES: Mapping[str, Vec] = {
    "+X": (1.0, 0.0, 0.0), "-X": (-1.0, 0.0, 0.0),
    "+Y": (0.0, 1.0, 0.0), "-Y": (0.0, -1.0, 0.0),
    "+Z": (0.0, 0.0, 1.0), "-Z": (0.0, 0.0, -1.0),
}
CANONICAL_UP = "+Z"
CANONICAL_FORWARD = "-Y"


@dataclass(frozen=True)
class Normalization:
    matrix: Matrix4                 # row-major, applied as M @ (x, y, z, 1)
    scale: float
    source_height: float            # along the declared up axis, source units
    target_height_m: float
    up: str
    forward: str
    provenance: ProvenanceState = ProvenanceState.ESTIMATE


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def axis_rotation(up: str, forward: str) -> Matrix3:
    """Rotation taking the source ``up``/``forward`` axes to canonical +Z / −Y (right-handed, det = +1)."""
    if up not in AXES or forward not in AXES:
        raise ValueError(f"axes must be one of {sorted(AXES)}")
    su, sf = AXES[up], AXES[forward]
    if abs(_dot(su, sf)) > 1e-12:
        raise ValueError(f"up {up} and forward {forward} must be perpendicular")
    cu, cf = AXES[CANONICAL_UP], AXES[CANONICAL_FORWARD]
    sr, cr = _cross(sf, su), _cross(cf, cu)
    # R = C · Sᵀ with columns (right, forward, up) of each basis
    src, dst = (sr, sf, su), (cr, cf, cu)
    rows = []
    for i in range(3):
        rows.append(tuple(sum(dst[k][i] * src[k][j] for k in range(3)) for j in range(3)))
    return tuple(rows)  # type: ignore[return-value]


def _apply3(m: Matrix3, v: Vec) -> Vec:
    return (_dot(m[0], v), _dot(m[1], v), _dot(m[2], v))


def normalization(points: Iterable[Vec], target_height_m: float, up: str = "+Z",
                  forward: str = "-Y") -> Normalization:
    """Affine matrix: rotate to canonical axes, scale to ``target_height_m``, feet on z = 0, centred in X/Y."""
    if target_height_m <= 0:
        raise ValueError("target height must be positive")
    r = axis_rotation(up, forward)
    rotated = [_apply3(r, p) for p in points]
    if not rotated:
        raise ValueError("no vertices")
    lo = [min(p[i] for p in rotated) for i in range(3)]
    hi = [max(p[i] for p in rotated) for i in range(3)]
    height = hi[2] - lo[2]
    if height <= 1e-12:
        raise ValueError("mesh has no extent along the up axis")
    s = target_height_m / height
    t = (-(lo[0] + hi[0]) / 2 * s, -(lo[1] + hi[1]) / 2 * s, -lo[2] * s)
    m = tuple(tuple(r[i][j] * s for j in range(3)) + (t[i],) for i in range(3)) + ((0.0, 0.0, 0.0, 1.0),)
    return Normalization(matrix=m, scale=s, source_height=height, target_height_m=target_height_m,
                         up=up, forward=forward)


def apply(n: Normalization, p: Vec) -> Vec:
    m = n.matrix
    return tuple(m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2] + m[i][3] for i in range(3))  # type: ignore[return-value]
