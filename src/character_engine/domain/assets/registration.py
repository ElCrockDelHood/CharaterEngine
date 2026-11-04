"""Rigid (similarity) registration by landmarks — phase F1 of ``docs/architecture/ASSET_FITTING_PROPOSAL.md``.

Finds the rotation R (proper, det = +1), translation t and optional uniform scale s that minimise
``Σ |s·R·a_i + t − b_i|²`` for paired anchors a_i (asset) → b_i (canonical target). The rotation is Horn's
closed-form unit-quaternion solution (1987, "Closed-form solution of absolute orientation using unit quaternions",
J. Opt. Soc. Am. A 4:629); the scale is Umeyama's (1991, IEEE TPAMI 13:376). Both are standard least-squares
results, not tuned values. Pure Python (Jacobi eigen-solver), no numpy, no I/O.

Guards (numerical, not anatomical tolerances):

* **Nearly collinear anchors** are rejected: with all anchors on a line the roll about that line is undefined.
  The test is the ratio of the second to the first principal spread of the centred asset anchors.
* **Reflection**: a proper rotation can never mirror. With ≥ 4 non-coplanar anchors the best *improper* fit is
  also computed; if it is clearly better, the anchors describe the other side (a left asset on right targets) and
  the registration is rejected. With 3 (or coplanar) anchors chirality cannot be seen from the anchors alone —
  any reflection of a planar set equals a rotation — so the result says ``chirality_checked = False`` and the
  side must come from the asset manifest (``side``) instead.

Fitting tolerances (RMS in mm, …) are not decided here; see ``manifest.TOLERANCES`` (ESTIMATE / pending).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

Vec = Tuple[float, float, float]
Mat3 = Tuple[Vec, Vec, Vec]

# Numerical guards (dimensionless). They reject degenerate geometry, they are not fitting tolerances.
MIN_SPREAD_RATIO = 1e-3        # second / first principal spread of the asset anchors
REFLECTION_MARGIN = 1e-9       # relative SSE margin: improper fit must beat the proper one by more than this


class RegistrationError(ValueError):
    """Raised when the anchors cannot define a unique proper transform."""


@dataclass(frozen=True)
class Registration:
    rotation: Mat3                 # row-major, proper (det = +1)
    translation: Vec
    scale: float
    residuals: Tuple[float, ...]   # |s·R·a_i + t − b_i| per anchor, target units
    rms: float
    spread_ratio: float            # conditioning of the asset anchors (1 = isotropic, 0 = collinear)
    chirality_checked: bool        # True only with >= 4 non-coplanar anchors

    def apply(self, p: Sequence[float]) -> Vec:
        r, s, t = self.rotation, self.scale, self.translation
        return tuple(s * (r[i][0] * p[0] + r[i][1] * p[1] + r[i][2] * p[2]) + t[i] for i in range(3))  # type: ignore[return-value]


# ----------------------------------------------------------------------------------------------- linear algebra

def _jacobi_eigen(a: List[List[float]], sweeps: int = 100) -> Tuple[List[float], List[List[float]]]:
    """Eigen-decomposition of a real symmetric matrix. Returns (values, vectors as columns)."""
    n = len(a)
    a = [row[:] for row in a]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(sweeps):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off < 1e-30 * (1.0 + sum(a[i][i] ** 2 for i in range(n))):
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-300:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p], v[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    return [a[i][i] for i in range(n)], v


def _centroid(pts: Sequence[Vec]) -> Vec:
    n = len(pts)
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n)


def _sub(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _quat_to_matrix(w: float, x: float, y: float, z: float) -> Mat3:
    return ((w * w + x * x - y * y - z * z, 2 * (x * y - w * z), 2 * (x * z + w * y)),
            (2 * (x * y + w * z), w * w - x * x + y * y - z * z, 2 * (y * z - w * x)),
            (2 * (x * z - w * y), 2 * (y * z + w * x), w * w - x * x - y * y + z * z))


def _horn_rotation(a: Sequence[Vec], b: Sequence[Vec]) -> Mat3:
    """Proper rotation maximising Σ b_i · R a_i for centred point sets (Horn 1987)."""
    s = [[sum(p[i] * q[j] for p, q in zip(a, b)) for j in range(3)] for i in range(3)]
    (sxx, sxy, sxz), (syx, syy, syz), (szx, szy, szz) = s
    n = [[sxx + syy + szz, syz - szy, szx - sxz, sxy - syx],
         [syz - szy, sxx - syy - szz, sxy + syx, szx + sxz],
         [szx - sxz, sxy + syx, -sxx + syy - szz, syz + szy],
         [sxy - syx, szx + sxz, syz + szy, -sxx - syy + szz]]
    vals, vecs = _jacobi_eigen(n)
    k = max(range(4), key=lambda i: vals[i])
    q = [vecs[r][k] for r in range(4)]
    norm = math.sqrt(sum(c * c for c in q))
    return _quat_to_matrix(*(c / norm for c in q))


def _mul(r: Mat3, p: Sequence[float]) -> Vec:
    return (r[0][0] * p[0] + r[0][1] * p[1] + r[0][2] * p[2],
            r[1][0] * p[0] + r[1][1] * p[1] + r[1][2] * p[2],
            r[2][0] * p[0] + r[2][1] * p[1] + r[2][2] * p[2])


def spread_ratio(points: Sequence[Vec]) -> Tuple[float, float]:
    """(second / first, third / first) principal spreads (square roots of covariance eigenvalues)."""
    c = _centroid(points)
    d = [_sub(p, c) for p in points]
    cov = [[sum(p[i] * p[j] for p in d) for j in range(3)] for i in range(3)]
    vals = sorted((max(v, 0.0) for v in _jacobi_eigen(cov)[0]), reverse=True)
    if vals[0] <= 0.0:
        return 0.0, 0.0
    return math.sqrt(vals[1] / vals[0]), math.sqrt(vals[2] / vals[0])


def _fit(a: Sequence[Vec], b: Sequence[Vec], with_scale: bool) -> Tuple[Mat3, float, Vec, float]:
    ca, cb = _centroid(a), _centroid(b)
    da = [_sub(p, ca) for p in a]
    db = [_sub(p, cb) for p in b]
    r = _horn_rotation(da, db)
    s = 1.0
    if with_scale:
        num = sum(_mul(r, p)[0] * q[0] + _mul(r, p)[1] * q[1] + _mul(r, p)[2] * q[2] for p, q in zip(da, db))
        den = sum(p[0] ** 2 + p[1] ** 2 + p[2] ** 2 for p in da)
        s = num / den
    rc = _mul(r, ca)
    t = (cb[0] - s * rc[0], cb[1] - s * rc[1], cb[2] - s * rc[2])
    sse = sum(sum((s * x + ti - y) ** 2 for x, ti, y in zip(_mul(r, p), t, q)) for p, q in zip(a, b))
    return r, s, t, sse


# ----------------------------------------------------------------------------------------------- public API

def register(asset: Sequence[Sequence[float]], target: Sequence[Sequence[float]],
             with_scale: bool = True) -> Registration:
    """Similarity (or rigid, ``with_scale=False``) transform taking asset anchors onto target anchors."""
    if len(asset) != len(target):
        raise RegistrationError(f"{len(asset)} asset anchors vs {len(target)} targets")
    if len(asset) < 3:
        raise RegistrationError("at least 3 anchors are needed to fix position, rotation and roll")
    a = [(float(p[0]), float(p[1]), float(p[2])) for p in asset]
    b = [(float(p[0]), float(p[1]), float(p[2])) for p in target]
    if not all(math.isfinite(c) for p in a + b for c in p):
        raise RegistrationError("anchors must be finite")
    ratio, planar = spread_ratio(a)
    if ratio < MIN_SPREAD_RATIO:
        raise RegistrationError(f"anchors are (nearly) collinear: spread ratio {ratio:.2e} < {MIN_SPREAD_RATIO}")
    if spread_ratio(b)[0] < MIN_SPREAD_RATIO:
        raise RegistrationError("target anchors are (nearly) collinear")

    r, s, t, sse = _fit(a, b, with_scale)
    chirality = len(a) >= 4 and planar >= MIN_SPREAD_RATIO
    if chirality:
        mirrored = [(-p[0], p[1], p[2]) for p in a]
        sse_mirror = _fit(mirrored, b, with_scale)[3]
        scale_ref = sum(sum(c * c for c in _sub(q, _centroid(b))) for q in b)
        if sse_mirror + REFLECTION_MARGIN * scale_ref < sse:
            raise RegistrationError("anchors need a reflection (mirror) to match: wrong side or mirrored asset")
    if with_scale and s <= 0.0:
        raise RegistrationError("non-positive scale")

    residuals = tuple(math.dist(_apply(r, s, t, p), q) for p, q in zip(a, b))
    rms = math.sqrt(sum(e * e for e in residuals) / len(residuals))
    return Registration(r, t, s, residuals, rms, ratio, chirality)


def _apply(r: Mat3, s: float, t: Vec, p: Vec) -> Vec:
    x = _mul(r, p)
    return (s * x[0] + t[0], s * x[1] + t[1], s * x[2] + t[2])


def determinant(m: Mat3) -> float:
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


# ----------------------------------------------------------------------------------------------- mesh measures

def fit_sphere(points: Sequence[Sequence[float]]) -> Tuple[Vec, float, float]:
    """Algebraic least-squares sphere (centre, radius, RMS of |distance − radius|). Needs >= 4 non-coplanar points."""
    if len(points) < 4:
        raise RegistrationError("sphere fit needs at least 4 points")
    m = [[0.0] * 4 for _ in range(4)]
    rhs = [0.0] * 4
    for x, y, z in points:
        row = (2 * x, 2 * y, 2 * z, 1.0)
        w = x * x + y * y + z * z
        for i in range(4):
            rhs[i] += row[i] * w
            for j in range(4):
                m[i][j] += row[i] * row[j]
    sol = _solve(m, rhs)
    c = (sol[0], sol[1], sol[2])
    r2 = sol[3] + c[0] ** 2 + c[1] ** 2 + c[2] ** 2
    if r2 <= 0.0:
        raise RegistrationError("degenerate sphere fit")
    r = math.sqrt(r2)
    res = [math.dist(p, c) - r for p in points]
    return c, r, math.sqrt(sum(e * e for e in res) / len(res))


def _solve(m: List[List[float]], b: List[float]) -> List[float]:
    n = len(b)
    a = [row[:] + [b[i]] for i, row in enumerate(m)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-300:
            raise RegistrationError("singular system")
        a[col], a[piv] = a[piv], a[col]
        for r in range(n):
            if r != col:
                f = a[r][col] / a[col][col]
                a[r] = [a[r][j] - f * a[col][j] for j in range(n + 1)]
    return [a[i][n] / a[i][i] for i in range(n)]
