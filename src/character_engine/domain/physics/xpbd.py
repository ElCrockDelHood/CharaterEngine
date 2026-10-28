"""Small XPBD solver (pure Python, deterministic): particles, distance constraints, capsule colliders.

Extended Position-Based Dynamics with the "small steps" scheme (Macklin, Storey et al. 2019: many substeps, one
constraint iteration each, Lagrange multipliers reset per substep). Compliance α (m/N) is the inverse stiffness;
α = 0 is a rigid constraint. Units: metres, kilograms, seconds. Canonical frame: Z-up.

Determinism: plain Python floats and a fixed (seeded) constraint order. ``state_hash`` hashes the
positions rounded to 1e-9 m so two runs with the same inputs give the same hash.

This is the reference solver for small samples and tests. Engines (Blender cloth, Godot) are compared against it,
not the other way round.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

from ..materials.layered_capsule import segment_distance

Vec = Tuple[float, float, float]

GRAVITY: Vec = (0.0, 0.0, -9.81)


@dataclass
class DistanceConstraint:
    i: int
    j: int
    rest: float
    compliance: float
    kind: str = "stretch"          # "stretch" | "bend"
    active: bool = True


@dataclass
class CapsuleCollider:
    """Keeps particles outside a capsule (a, b, radius). ``motion(t)`` → (a, b) makes it kinematic."""

    name: str
    a: Vec
    b: Vec
    radius: float
    friction: float = 0.0
    motion: Optional[Callable[[float], Tuple[Vec, Vec]]] = None
    enabled: bool = True


@dataclass
class ParticleSystem:
    x: List[List[float]]
    inv_mass: List[float]
    constraints: List[DistanceConstraint] = field(default_factory=list)
    colliders: List[CapsuleCollider] = field(default_factory=list)
    contact_offset: float = 0.0      # particle radius (half the cloth thickness)
    damping: float = 0.0             # 1/s
    gravity: Vec = GRAVITY
    time: float = 0.0

    def __post_init__(self):
        self.v = [[0.0, 0.0, 0.0] for _ in self.x]
        self.prev = [list(p) for p in self.x]
        self._contacts: List[Tuple[int, Vec]] = []

    # ------------------------------------------------------------------ stepping
    def step(self, dt: float, substeps: int = 10) -> None:
        h = dt / substeps
        for _ in range(substeps):
            self._substep(h)

    def _substep(self, h: float) -> None:
        x, v, w = self.x, self.v, self.inv_mass
        g = self.gravity
        damp = max(0.0, 1.0 - self.damping * h)
        t_next = self.time + h
        for c in self.colliders:
            if c.motion is not None:
                c.a, c.b = c.motion(t_next)
        for k in range(len(x)):
            self.prev[k][0], self.prev[k][1], self.prev[k][2] = x[k]
            if w[k] == 0.0:
                continue
            vk = v[k]
            vk[0] = vk[0] * damp + g[0] * h
            vk[1] = vk[1] * damp + g[1] * h
            vk[2] = vk[2] * damp + g[2] * h
            x[k][0] += vk[0] * h
            x[k][1] += vk[1] * h
            x[k][2] += vk[2] * h
        h2 = h * h
        for c in self.constraints:
            if c.active:
                self._solve_distance(c, h2)
        self._contacts: List[Tuple[int, Vec]] = []
        for col in self.colliders:
            if col.enabled:
                self._collide(col)
        inv_h = 1.0 / h
        for k in range(len(x)):
            if w[k] == 0.0:
                continue
            v[k][0] = (x[k][0] - self.prev[k][0]) * inv_h
            v[k][1] = (x[k][1] - self.prev[k][1]) * inv_h
            v[k][2] = (x[k][2] - self.prev[k][2]) * inv_h
        for k, n in self._contacts:              # inelastic contact: drop the separating velocity that the
            vn = v[k][0] * n[0] + v[k][1] * n[1] + v[k][2] * n[2]   # projection would otherwise inject
            if vn > 0.0:
                v[k][0] -= vn * n[0]
                v[k][1] -= vn * n[1]
                v[k][2] -= vn * n[2]
        self.time = t_next

    def _solve_distance(self, c: DistanceConstraint, h2: float) -> None:
        wi, wj = self.inv_mass[c.i], self.inv_mass[c.j]
        alpha = c.compliance / h2
        denom = wi + wj + alpha
        if denom == 0.0:
            return
        pi, pj = self.x[c.i], self.x[c.j]
        dx, dy, dz = pi[0] - pj[0], pi[1] - pj[1], pi[2] - pj[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-12:
            return
        dlam = -(length - c.rest) / denom
        nx, ny, nz = dx / length, dy / length, dz / length
        pi[0] += wi * dlam * nx
        pi[1] += wi * dlam * ny
        pi[2] += wi * dlam * nz
        pj[0] -= wj * dlam * nx
        pj[1] -= wj * dlam * ny
        pj[2] -= wj * dlam * nz

    def _collide(self, col: CapsuleCollider) -> None:
        r = col.radius + self.contact_offset
        a, b = col.a, col.b
        for k, p in enumerate(self.x):
            if self.inv_mass[k] == 0.0:
                continue
            d, t = segment_distance((p[0], p[1], p[2]), a, b)
            if d >= r:
                continue
            c = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)
            if d < 1e-12:
                continue
            n = ((p[0] - c[0]) / d, (p[1] - c[1]) / d, (p[2] - c[2]) / d)
            pen = r - d
            self._contacts.append((k, n))
            p[0] += n[0] * pen
            p[1] += n[1] * pen
            p[2] += n[2] * pen
            if col.friction > 0.0:
                q = self.prev[k]
                dx = (p[0] - q[0], p[1] - q[1], p[2] - q[2])
                dn = dx[0] * n[0] + dx[1] * n[1] + dx[2] * n[2]
                tx = (dx[0] - dn * n[0], dx[1] - dn * n[1], dx[2] - dn * n[2])
                tl = math.sqrt(tx[0] * tx[0] + tx[1] * tx[1] + tx[2] * tx[2])
                if tl > 0.0:
                    s = 1.0 if tl < col.friction * pen else col.friction * pen / tl
                    p[0] -= tx[0] * s
                    p[1] -= tx[1] * s
                    p[2] -= tx[2] * s

    # ------------------------------------------------------------------ cutting
    def cut(self, plane_point: Vec, plane_normal: Vec, keep: Callable[[Vec], bool]) -> int:
        """Deactivate constraints that cross the plane at a midpoint where ``keep(mid)`` is False → cut count."""
        n = 0
        for c in self.constraints:
            if not c.active:
                continue
            pi, pj = self.x[c.i], self.x[c.j]
            si = sum((pi[k] - plane_point[k]) * plane_normal[k] for k in range(3))
            sj = sum((pj[k] - plane_point[k]) * plane_normal[k] for k in range(3))
            if si * sj > 0.0:
                continue
            mid = ((pi[0] + pj[0]) / 2, (pi[1] + pj[1]) / 2, (pi[2] + pj[2]) / 2)
            if not keep(mid):
                c.active = False
                n += 1
        return n

    # ------------------------------------------------------------------ diagnostics
    def masses(self) -> List[float]:
        return [0.0 if w == 0.0 else 1.0 / w for w in self.inv_mass]

    def kinetic_energy(self) -> float:
        return sum(0.5 * m * (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) for m, v in zip(self.masses(), self.v))

    def potential_energy(self) -> float:
        g = self.gravity
        return sum(-m * (g[0] * p[0] + g[1] * p[1] + g[2] * p[2]) for m, p in zip(self.masses(), self.x))

    def elastic_energy(self) -> float:
        e = 0.0
        for c in self.constraints:
            if c.active and c.compliance > 0.0:
                e += 0.5 * (math.dist(self.x[c.i], self.x[c.j]) - c.rest) ** 2 / c.compliance
        return e

    def mechanical_energy(self) -> float:
        """Kinetic + gravitational. Use this for drift checks: with near-rigid constraints the elastic term is
        dominated by the one-iteration residual and is not a meaningful stored energy."""
        return self.kinetic_energy() + self.potential_energy()

    def total_energy(self) -> float:
        return self.mechanical_energy() + self.elastic_energy()

    def max_constraint_error(self) -> float:
        return max((abs(math.dist(self.x[c.i], self.x[c.j]) - c.rest) for c in self.constraints if c.active),
                   default=0.0)

    def positions(self, digits: int = 9) -> List[List[float]]:
        return [[round(c, digits) for c in p] for p in self.x]

    def state_hash(self) -> str:
        payload = json.dumps({"x": self.positions(), "active": [c.active for c in self.constraints]},
                             separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------- builders
@dataclass(frozen=True)
class TubeMesh:
    n_around: int
    n_along: int
    faces: Tuple[Tuple[int, int, int, int], ...]   # quads, index = ring * n_around + k


def tube(a: Vec, b: Vec, radius: float, n_around: int, n_along: int, areal_density: float,
         stretch_compliance: float, bend_compliance: float, pin_first_ring: bool = True,
         up_hint: Vec = (1.0, 0.0, 0.0), seed: int = 0) -> Tuple[ParticleSystem, TubeMesh]:
    """Closed cylindrical sleeve from ``a`` (ring 0) to ``b``; ring 0 pinned. Mass from areal density (kg/m²).

    The constraint order is a seeded permutation: a structured Gauss-Seidel sweep over a closed, near-rigid
    lattice ratchets (measured: +4 % mechanical energy in 0.5 s at 20 substeps, +48 % at 80), a fixed shuffle
    does not. Same seed, same order, same result.
    """
    if n_around < 3 or n_along < 2:
        raise ValueError("tube needs n_around >= 3 and n_along >= 2")
    axis = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    length = math.sqrt(sum(c * c for c in axis))
    u = tuple(c / length for c in axis)
    e1 = _normalize(_cross(u, up_hint) if abs(sum(u[i] * up_hint[i] for i in range(3))) < 0.99
                    else _cross(u, (0.0, 1.0, 0.0)))
    e2 = _cross(u, e1)
    x: List[List[float]] = []
    for ring in range(n_along):
        s = ring / (n_along - 1)
        cx, cy, cz = a[0] + axis[0] * s, a[1] + axis[1] * s, a[2] + axis[2] * s
        for k in range(n_around):
            ang = 2.0 * math.pi * k / n_around
            ca, sa = math.cos(ang), math.sin(ang)
            x.append([cx + radius * (ca * e1[0] + sa * e2[0]),
                      cy + radius * (ca * e1[1] + sa * e2[1]),
                      cz + radius * (ca * e1[2] + sa * e2[2])])
    area = 2.0 * math.pi * radius * length
    m = areal_density * area / len(x)
    inv = [0.0 if (pin_first_ring and idx < n_around) else 1.0 / m for idx in range(len(x))]
    sys_ = ParticleSystem(x=x, inv_mass=inv)

    def idx(ring, k):
        return ring * n_around + (k % n_around)

    cons: List[DistanceConstraint] = []
    for ring in range(n_along):
        for k in range(n_around):
            for (r2, k2, kind) in ((ring, k + 1, "stretch"), (ring + 1, k, "stretch"),
                                   (ring + 1, k + 1, "stretch"), (ring, k + 2, "bend"), (ring + 2, k, "bend")):
                if r2 >= n_along:
                    continue
                i, j = idx(ring, k), idx(r2, k2)
                comp = stretch_compliance if kind == "stretch" else bend_compliance
                cons.append(DistanceConstraint(i, j, math.dist(x[i], x[j]), comp, kind))
    random.Random(seed).shuffle(cons)
    sys_.constraints = cons
    faces = tuple((idx(r, k), idx(r, k + 1), idx(r + 1, k + 1), idx(r + 1, k))
                  for r in range(n_along - 1) for k in range(n_around))
    return sys_, TubeMesh(n_around, n_along, faces)


def _cross(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _normalize(v: Sequence[float]) -> Vec:
    n = math.sqrt(sum(c * c for c in v))
    return (v[0] / n, v[1] / n, v[2] / n)
