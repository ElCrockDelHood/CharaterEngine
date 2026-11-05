"""Bone fragments of a fractured blunt blow: how many, how big, how fast, where to (A33). Additive and opt-in.

``strike_model.py`` decides *whether* a rigid shell breaks; this module describes *how it comes apart*, so a renderer
or a runtime can draw shards instead of a bent surface. Nothing here feeds back into wounds, ``strike_model.py`` or any
earlier result. Schema ``ce-fracture/1`` (``FractureEvent.to_dict``) is the contract with the Blender and Godot threads.

Model (every constant below is ESTIMATE or ASSUMED, with its range):

* **Pattern by region**: skull ``spiderweb`` (many shards radiating from the impact), thorax ``transverse_ribs`` (few
  long pieces across the body, driven inward), long bones ``butterfly`` (one wedge plus large pieces along the bone),
  the rest ``small_pieces``.
* **Mobilised mass**: ``bone density (catalog) × patch area × shell thickness × MOBILE_FRACTION``, patch radius =
  ``PATCH_FACTOR`` × the striker's contact radius, and no wider than the struck half of the bone (π × its outer radius;
  on a thin bone the patch is a band across it). The masses of the fragments add up to exactly this.
* **Excess energy**: tissue energy left after the fracture criterion. Where an energy criterion exists (skull) it is
  ``E_diss − mid criterion``; elsewhere ``E_diss − F_mid² / 2k``, the energy already spent when the linear-spring force
  reached the midpoint of the region's force range.
* **Count**: ``n = clamp(round(a · (E_excess / E_REF) ** b), N_MIN, cap)``, ``a`` and ``cap`` per pattern, ``cap`` ≤ ``N_MAX``
  (24, the budget of a GeForce 740M + i3). Fragmentation theory (Mott, Grady) gives the *form* of a power law in energy;
  no published number from it, and no measured bone fragment size or speed, was used.
* **Sizes**: Weibull-distributed weights with the pattern's shape, rescaled so the masses sum to the mobilised mass.
* **Speeds**: ``FRAGMENT_KE_FRACTION`` of the excess energy becomes fragment kinetic energy, shared in proportion to
  mass × a random factor; no fragment moves faster than ``MAX_SPEED_RATIO`` × the blow's speed (elastic limit), so the
  kinetic energy reported can be lower than the share. Inner fragments (under the contact patch) leave in a cone around
  the inward normal: the input of a secondary-injury model. Outer ones scatter radially, with an inward bias.

Local frame of positions and velocities: ``x`` lateral, ``y`` along the segment axis, ``z`` inward along the strike.
Not modelled: spalling outward, crack propagation in time, fragment collisions, drag in tissue, bone anisotropy.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

from ..materials.catalog import MaterialKind, material
from ..tissue import BodyRegion
from .body_strike import LayeredBody
from .strike_model import REGION_RESPONSE, StrikeOutcome, Striker, strike_blunt

Vec = Tuple[float, float, float]
SCHEMA = "ce-fracture/1"

PATCH_FACTOR = 2.0               # ASSUMED, 1.5–3: fractured patch radius / contact radius
MOBILE_FRACTION = 0.6            # ASSUMED, 0.4–0.9: share of the patch that detaches
E_REF_J = 50.0                   # ASSUMED: excess energy at which n = a
COUNT_EXPONENT = 0.6             # ASSUMED, 0.4–0.8: power law form only (Mott / Grady frame, no number from them)
N_MIN, N_MAX = 3, 24             # N_MAX: hardware budget (GeForce 740M + i3)
FRAGMENT_KE_FRACTION = 0.10      # ASSUMED, 0.05–0.15
MAX_SPEED_RATIO = 2.0            # DERIVED: a light body struck elastically by a heavy one leaves at up to 2 v
INNER_CONE_DEG = 20.0            # ASSUMED, 10–35: half angle around the inward normal
SPIN_RATIO = (0.2, 1.0)          # ASSUMED: angular speed = ratio × speed / size


@dataclass(frozen=True)
class Pattern:
    name: str
    count_a: float               # n at E_REF_J, ASSUMED
    cap: int                     # most fragments of this pattern, ASSUMED, <= N_MAX
    weibull_shape: float         # lower = more unequal sizes, ASSUMED, 0.8–3
    aspect: float                # length / width of a fragment, ASSUMED
    outer_inward_bias: float     # inward share of an outer fragment's direction, ASSUMED, 0–1


SPIDERWEB = Pattern("spiderweb", 10.0, N_MAX, 1.6, 1.8, 0.3)
TRANSVERSE_RIBS = Pattern("transverse_ribs", 4.0, 8, 2.0, 3.0, 0.8)      # ribs bend inward
BUTTERFLY = Pattern("butterfly", 3.0, 6, 1.0, 2.0, 0.4)                  # one wedge, 2–3 large pieces, a few chips
SMALL_PIECES = Pattern("small_pieces", 6.0, 12, 1.4, 1.2, 0.5)
REGION_PATTERN: Mapping[BodyRegion, Pattern] = {
    BodyRegion.HEAD: SPIDERWEB, BodyRegion.THORAX: TRANSVERSE_RIBS,
    BodyRegion.UPPER_ARM: BUTTERFLY, BodyRegion.FOREARM: BUTTERFLY, BodyRegion.THIGH: BUTTERFLY, BodyRegion.LEG: BUTTERFLY,
    BodyRegion.NECK: SMALL_PIECES, BodyRegion.ABDOMEN: SMALL_PIECES, BodyRegion.PELVIS: SMALL_PIECES,
    BodyRegion.HAND: SMALL_PIECES, BodyRegion.FOOT: SMALL_PIECES,
}


@dataclass(frozen=True)
class Fragment:
    id: int
    kind: str                    # wedge | piece
    inner: bool                  # starts under the contact patch
    size_m: float                # lateral size of the plate-like piece
    aspect: float
    mass_kg: float
    position_m: Vec              # offset from the impact point, local frame
    velocity_m_s: Vec            # local frame
    angular_speed_rad_s: float
    spin_axis: Vec               # unit, local frame


@dataclass(frozen=True)
class FractureEvent:
    segment: str
    region: str
    bone: str
    fractured: bool
    pattern: str
    seed: int
    impact_point_m: Vec
    frame_x: Vec                 # lateral, world
    frame_y: Vec                 # along the segment, world
    frame_z: Vec                 # inward normal, world
    patch_radius_m: float
    shell_thickness_m: float
    patch_mass_kg: float         # sum of the fragment masses
    excess_energy_j: float
    fragment_kinetic_j: float
    fragments: Tuple[Fragment, ...]
    provenance: str = "ASSUMED"

    def to_dict(self) -> Dict[str, object]:
        """JSON-ready, with a fixed key order (schema ``ce-fracture/1``)."""
        return {
            "schema": SCHEMA, "segment": self.segment, "region": self.region, "bone": self.bone,
            "fractured": self.fractured, "pattern": self.pattern, "seed": self.seed,
            "impact_point_m": list(self.impact_point_m),
            "frame": {"x": list(self.frame_x), "y": list(self.frame_y), "z": list(self.frame_z)},
            "patch_radius_m": self.patch_radius_m, "shell_thickness_m": self.shell_thickness_m,
            "patch_mass_kg": self.patch_mass_kg, "excess_energy_j": self.excess_energy_j,
            "fragment_kinetic_j": self.fragment_kinetic_j, "provenance": self.provenance,
            "fragments": [{"id": f.id, "kind": f.kind, "inner": f.inner, "size_m": f.size_m, "aspect": f.aspect,
                           "mass_kg": f.mass_kg, "position_m": list(f.position_m),
                           "velocity_m_s": list(f.velocity_m_s), "angular_speed_rad_s": f.angular_speed_rad_s,
                           "spin_axis": list(f.spin_axis)} for f in self.fragments],
        }

    @staticmethod
    def from_dict(d: Mapping[str, object]) -> FractureEvent:
        if d["schema"] != SCHEMA:
            raise ValueError(f"unknown schema {d['schema']!r}")
        fr = d["frame"]
        return FractureEvent(
            d["segment"], d["region"], d["bone"], d["fractured"], d["pattern"], d["seed"], tuple(d["impact_point_m"]),
            tuple(fr["x"]), tuple(fr["y"]), tuple(fr["z"]), d["patch_radius_m"], d["shell_thickness_m"],
            d["patch_mass_kg"], d["excess_energy_j"], d["fragment_kinetic_j"],
            tuple(Fragment(f["id"], f["kind"], f["inner"], f["size_m"], f["aspect"], f["mass_kg"], tuple(f["position_m"]),
                           tuple(f["velocity_m_s"]), f["angular_speed_rad_s"], tuple(f["spin_axis"]))
                  for f in d["fragments"]),
            d["provenance"])


def fragment_count(pattern: Pattern, excess_energy_j: float) -> int:
    n = round(pattern.count_a * (max(0.0, excess_energy_j) / E_REF_J) ** COUNT_EXPONENT)
    return max(N_MIN, min(pattern.cap, n))


def excess_energy_j(outcome: StrikeOutcome) -> float:
    """Tissue energy beyond the fracture criterion; 0 when the shell held."""
    if not outcome.fractured:
        return 0.0
    resp = REGION_RESPONSE[BodyRegion(outcome.region)]
    if resp.fracture_energy_j is not None:
        spent = 0.5 * (resp.fracture_energy_j[0] + resp.fracture_energy_j[1])
    else:
        spent = resp.fracture_force_n[1] ** 2 / (2.0 * resp.stiffness_n_per_m)
    return max(0.0, outcome.dissipated_j - spent)


def default_seed(outcome: StrikeOutcome) -> int:
    key = f"{outcome.segment}|{outcome.striker_energy_j}|{outcome.reduced_mass_kg}|{outcome.peak_force_n}"
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:12], 16)   # 48 bits: exact in JSON parsers that read doubles


def _unit(v: Vec) -> Vec:
    n = math.sqrt(sum(c * c for c in v))
    return (v[0] / n, v[1] / n, v[2] / n)


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _frame(inward: Vec, axis: Vec) -> Tuple[Vec, Vec, Vec]:
    z = _unit(inward)
    if abs(sum(a * b for a, b in zip(axis, z))) > 0.999 * math.sqrt(sum(a * a for a in axis)):
        axis = (1.0, 0.0, 0.0) if abs(z[0]) < 0.9 else (0.0, 1.0, 0.0)
    x = _unit(_cross(axis, z))
    return x, _cross(z, x), z


def _angle(pattern: Pattern, i: int, n: int, rng: random.Random) -> float:
    if pattern is TRANSVERSE_RIBS:                  # across the body: left and right of the impact
        return (0.0 if i % 2 == 0 else math.pi) + rng.uniform(-0.3, 0.3)
    if pattern is BUTTERFLY:                        # along the bone: above and below the impact
        return (0.5 * math.pi if i % 2 == 0 else 1.5 * math.pi) + rng.uniform(-0.4, 0.4)
    return 2.0 * math.pi * i / n + rng.uniform(-0.25, 0.25) * 2.0 * math.pi / n


def fracture_event(outcome: StrikeOutcome, bone: str, impact_point: Vec, inward_normal: Vec, contact_radius_m: float,
                   shell_thickness_m: float, bone_depth_m: float = 0.0, speed_m_s: Optional[float] = None,
                   axis: Vec = (0.0, 0.0, 1.0), seed: Optional[int] = None,
                   shell_outer_radius_m: Optional[float] = None) -> FractureEvent:
    """Fragments of one blow. ``bone_depth_m``: skin to bone along the normal; ``speed_m_s``: of the blow (speed cap);
    ``shell_outer_radius_m``: limits the patch width to the struck half of the bone."""
    seed = default_seed(outcome) if seed is None else seed
    region = BodyRegion(outcome.region)
    pattern = REGION_PATTERN[region]
    fx, fy, fz = _frame(inward_normal, axis)
    patch_r = PATCH_FACTOR * contact_radius_m
    base = {"segment": outcome.segment, "region": outcome.region, "bone": bone, "pattern": pattern.name, "seed": seed,
            "impact_point_m": tuple(round(c, 6) for c in impact_point), "frame_x": fx, "frame_y": fy, "frame_z": fz,
            "patch_radius_m": round(patch_r, 6), "shell_thickness_m": round(shell_thickness_m, 6)}
    if not outcome.fractured:
        return FractureEvent(fractured=False, patch_mass_kg=0.0, excess_energy_j=0.0, fragment_kinetic_j=0.0,
                             fragments=(), **base)
    rho = material(MaterialKind.BONE).mechanical.density.value
    half_width = patch_r if shell_outer_radius_m is None else min(patch_r, 0.5 * math.pi * shell_outer_radius_m)
    # circle when the bone is wide enough; else the part of that circle inside a band of half width ``half_width``
    w = half_width / patch_r
    area = patch_r ** 2 * (2.0 * math.asin(w) + 2.0 * w * math.sqrt(1.0 - w * w))
    patch_mass = rho * area * shell_thickness_m * MOBILE_FRACTION
    excess = excess_energy_j(outcome)
    n = fragment_count(pattern, excess)
    rng = random.Random(seed)

    weights = sorted(((-math.log(1.0 - rng.random())) ** (1.0 / pattern.weibull_shape) + 1e-6 for _ in range(n)),
                     reverse=True)
    total = sum(weights)
    masses = [patch_mass * w / total for w in weights]
    masses[-1] = patch_mass - sum(masses[:-1])      # the sum is exact

    shares = [m * rng.uniform(0.5, 1.5) for m in masses]
    budget = FRAGMENT_KE_FRACTION * excess
    v_cap = MAX_SPEED_RATIO * (speed_m_s if speed_m_s is not None else math.inf)
    frags: List[Fragment] = []
    kinetic = 0.0
    for i, m in enumerate(masses):
        speed = min(math.sqrt(2.0 * budget * shares[i] / sum(shares) / m), v_cap)
        kinetic += 0.5 * m * speed * speed
        r = patch_r * math.sqrt((i + 0.5) / n)      # largest first, nearest the impact
        theta = _angle(pattern, i, n, rng)
        radial = (math.cos(theta), math.sin(theta))
        inner = r <= contact_radius_m
        if inner:                                   # cone around the inward normal
            tilt = math.radians(INNER_CONE_DEG) * math.sqrt(rng.random())
            spread = rng.uniform(0.0, 2.0 * math.pi)
            direction = (math.sin(tilt) * math.cos(spread), math.sin(tilt) * math.sin(spread), math.cos(tilt))
        else:                                       # radial scatter, biased inward
            b = pattern.outer_inward_bias
            direction = _unit((radial[0] * (1.0 - b), radial[1] * (1.0 - b), b))
        size = math.sqrt(m / (rho * shell_thickness_m))
        spin = rng.uniform(*SPIN_RATIO) * speed / size
        axis_v = _unit((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1) + 1e-9))
        depth = bone_depth_m + rng.uniform(0.0, shell_thickness_m)
        frags.append(Fragment(
            id=i, kind="wedge" if pattern is BUTTERFLY and i == 0 else "piece", inner=inner, size_m=round(size, 6),
            aspect=pattern.aspect, mass_kg=m,
            position_m=(round(max(-half_width, min(half_width, r * radial[0])), 6), round(r * radial[1], 6), round(depth, 6)),
            velocity_m_s=tuple(round(speed * c, 6) for c in direction), angular_speed_rad_s=round(spin, 3),
            spin_axis=tuple(round(c, 6) for c in axis_v)))
    return FractureEvent(fractured=True, patch_mass_kg=patch_mass, excess_energy_j=round(excess, 6),
                         fragment_kinetic_j=round(kinetic, 6), fragments=tuple(frags), **base)


def strike_fracture(body: LayeredBody, segment: str, striker: Striker, from_dir: Vec = (0.0, -1.0, 0.0),
                    t_axial: float = 0.5, seed: Optional[int] = None) -> Tuple[StrikeOutcome, FractureEvent]:
    """Central blunt strike (``strike_model.strike_blunt``) and its fragments, for the block body."""
    outcome = strike_blunt(body, segment, striker, t_axial=t_axial)
    lc = body.capsules[segment]
    a, b = lc.placement.a, lc.placement.b
    centre = tuple(a[i] + (b[i] - a[i]) * t_axial for i in range(3))
    u = _unit(from_dir)
    r_skin = next(s.r_outer for s in lc.shells if s.material is MaterialKind.SKIN)
    bone_shell = next(s for s in lc.shells if s.material is MaterialKind.BONE)
    impact = tuple(centre[i] + u[i] * r_skin for i in range(3))
    axis = tuple(b[i] - a[i] for i in range(3))
    if sum(c * c for c in axis) < 1e-12:            # point segment (neck, abdomen, pelvis): the body's vertical
        axis = (0.0, 0.0, 1.0)
    return outcome, fracture_event(
        outcome, lc.placement.weight_bone, impact, (-u[0], -u[1], -u[2]), striker.contact_radius_m, bone_shell.thickness,
        bone_depth_m=r_skin - bone_shell.r_outer, speed_m_s=striker.speed_m_s, axis=axis, seed=seed,
        shell_outer_radius_m=bone_shell.r_outer)
