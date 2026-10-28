"""Material sample 1: left forearm with a wool sleeve and an optional steel bracer, struck by a sabre edge.

Pipeline (all pure Python, deterministic):

1. ``forearm.L`` block-dummy capsule from the canonical skeleton → layered capsule (bone, tendon, muscle, fat, skin)
   plus sleeve (wool) and, in the armoured variant, a steel bracer over the middle of the forearm.
2. XPBD sleeve settles under gravity on the skin capsule (frames at 60 fps).
3. Strike in slow motion: the blade edge moves from the front (−Y, canonical forward) towards the arm axis. The
   stopping depth comes from :func:`cut_through` (energy spent on cut area); the edge decelerates uniformly from
   first contact to that depth. While the edge is inside the sleeve, sleeve constraints in front of it are cut.
4. The depth below the skin becomes a wound through the existing trauma entry points (no new trauma logic):
   ``blade_contact_to_wound`` when skin was cut, ``blunt_impact_to_wound`` with the residual energy (upper bound)
   when the bracer stopped the blade. Both are assessed against the fitted tissue profile.

Every non-canonical input is listed in :class:`SampleConfig` with its provenance.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..materials.catalog import MaterialKind, material, material_table
from ..materials.layered_capsule import LayeredCapsule, OuterLayer, layered_capsule
from ..rigging.block_dummy import block_placements, placements_by_name
from ..trauma import assess_wound, blade_contact_to_wound, blunt_impact_to_wound
from .cut import Blade, CutResult, cut_through
from .xpbd import CapsuleCollider, ParticleSystem, TubeMesh, tube

Vec = Tuple[float, float, float]

SEGMENT = "forearm.L"
BONE_HIT = "RADIUS_L"          # weight bone of the forearm block (block_dummy.py)


@dataclass(frozen=True)
class SampleConfig:
    stature_m: float = 1.80
    # sleeve (ESTIMATE: heavy wool broadcloth, loose uniform fit)
    sleeve_thickness_m: float = 0.002
    sleeve_gap_m: float = 0.006
    sleeve_n_around: int = 32
    sleeve_n_along: int = 16
    # bracer (ESTIMATE: historical plate bracers are ~1-2 mm)
    bracer_thickness_m: float = 0.0015
    bracer_gap_m: float = 0.002
    bracer_z_range: Tuple[float, float] = (0.15, 0.85)
    # blade (mass PLACEHOLDER = placeholder sabre; speed ESTIMATE)
    blade_effective_mass_kg: float = 0.6
    blade_speed_m_s: float = 10.0
    blade_width_m: float = 0.028
    blade_edge_radius_m: float = 0.002
    strike_t_axial: float = 0.5
    blade_start_gap_m: float = 0.06
    # time
    fps: int = 60
    settle_frames: int = 40
    strike_frames: int = 40
    slow_motion: float = 20.0          # strike frames cover 1/(fps*slow_motion) s each
    substeps: int = 20                 # max sleeve constraint error ~0.1 mm at 32x16
    seed: int = 0                      # seeds the XPBD constraint order (the only use of randomness)
    provenance: Mapping[str, str] = field(default_factory=lambda: {
        "stature_m": "USER_INPUT", "sleeve_*": "ESTIMATE", "bracer_*": "ESTIMATE",
        "blade_effective_mass_kg": "PLACEHOLDER", "blade_speed_m_s": "ESTIMATE", "blade_width_m": "PLACEHOLDER",
        "time": "ASSUMED (presentation)"})


def forearm_placement(points: Mapping[str, Tuple[Vec, Vec]], stature_m: float = 1.80):
    return placements_by_name(block_placements(points, stature_m))[SEGMENT]


def build_layers(placement, cfg: SampleConfig, armored: bool) -> LayeredCapsule:
    outer = [OuterLayer("sleeve", MaterialKind.CLOTH_WOOL, cfg.sleeve_thickness_m, cfg.sleeve_gap_m)]
    if armored:
        outer.append(OuterLayer("bracer", MaterialKind.ARMOR_STEEL, cfg.bracer_thickness_m, cfg.bracer_gap_m,
                                cfg.bracer_z_range))
    return layered_capsule(placement, outer)


def _lerp(a: Vec, b: Vec, t: float) -> Vec:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _unit(v: Vec) -> Vec:
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / n, v[1] / n, v[2] / n)


def build_sleeve(lc: LayeredCapsule, cfg: SampleConfig) -> Tuple[ParticleSystem, TubeMesh]:
    p = lc.placement
    u = _unit(_sub(p.b, p.a))
    top = (p.a[0] - u[0] * p.radius_m, p.a[1] - u[1] * p.radius_m, p.a[2] - u[2] * p.radius_m)
    wool = material(MaterialKind.CLOTH_WOOL).mechanical
    sleeve = lc.shell("sleeve")
    r_mid = (sleeve.r_inner + sleeve.r_outer) / 2.0
    system, mesh = tube(top, p.b, r_mid, cfg.sleeve_n_around, cfg.sleeve_n_along, wool.areal_density.value,
                        wool.stretch_compliance.value, wool.bend_compliance.value, seed=cfg.seed)
    system.contact_offset = cfg.sleeve_thickness_m / 2.0
    system.damping = wool.damping.value
    return system, mesh


def run_variant(points: Mapping[str, Tuple[Vec, Vec]], armored: bool,
                cfg: SampleConfig = SampleConfig(), keep_frames: bool = True) -> Dict:
    placement = forearm_placement(points, cfg.stature_m)
    lc = build_layers(placement, cfg, armored)
    blade = Blade(cfg.blade_effective_mass_kg, cfg.blade_speed_m_s, cfg.blade_width_m)
    cut: CutResult = cut_through(lc, blade, cfg.strike_t_axial)
    system, mesh = build_sleeve(lc, cfg)

    a, b = placement.a, placement.b
    centre = _lerp(a, b, cfg.strike_t_axial)
    strike_dir = (0.0, 1.0, 0.0)                    # from the front (−Y) towards +Y
    edge_dir = (1.0, 0.0, 0.0)
    half_edge = 0.12
    r_out = max(s.r_outer for s in lc.shells
                if s.z_range is None or s.z_range[0] <= cfg.strike_t_axial <= s.z_range[1])
    contact_h = r_out                                # edge distance to the axis at first contact
    stop_h = r_out - cut.penetration_m
    start_h = r_out + cfg.blade_start_gap_m
    v0 = blade.speed_m_s
    t_contact = (start_h - contact_h) / v0
    s_cut = contact_h - stop_h
    decel = v0 * v0 / (2.0 * s_cut) if s_cut > 0 else math.inf
    t_stop = t_contact + (2.0 * s_cut / v0 if s_cut > 0 else 0.0)

    def edge_h(t: float) -> float:
        if t <= t_contact:
            return start_h - v0 * t
        if t >= t_stop:
            return stop_h
        tc = t - t_contact
        return contact_h - (v0 * tc - 0.5 * decel * tc * tc)

    def blade_ends(h: float) -> Tuple[Vec, Vec]:
        c = (centre[0] - strike_dir[0] * h, centre[1] - strike_dir[1] * h, centre[2] - strike_dir[2] * h)
        return ((c[0] - edge_dir[0] * half_edge, c[1], c[2]), (c[0] + edge_dir[0] * half_edge, c[1], c[2]))

    wool_mu = material(MaterialKind.CLOTH_WOOL).mechanical.friction.value
    skin = CapsuleCollider("skin", a, b, placement.radius_m, friction=wool_mu)
    strike_t0 = [0.0]
    blade_col = CapsuleCollider("blade", *blade_ends(start_h), cfg.blade_edge_radius_m, friction=0.0,
                                motion=lambda t: blade_ends(edge_h(t - strike_t0[0])), enabled=False)
    system.colliders = [blade_col, skin]

    sleeve_shell = lc.shell("sleeve")
    frames: List[Dict] = []
    energy: List[float] = []
    max_pen = 0.0
    cuts = 0

    def record(frame: int, phase: str, h: Optional[float]):
        nonlocal max_pen
        for k, p in enumerate(system.x):
            if system.inv_mass[k] == 0.0:
                continue
            pen = lc.skin_radius + system.contact_offset - lc.axial((p[0], p[1], p[2]))[0]
            max_pen = max(max_pen, pen)
        entry = {"frame": frame, "phase": phase, "time_s": round(system.time, 6)}
        if h is not None:
            entry["blade"] = [list(map(lambda c: round(c, 6), e)) for e in blade_ends(h)]
            entry["edge_to_axis_m"] = round(h, 6)
        if keep_frames:
            entry["sleeve"] = system.positions(6)
        frames.append(entry)

    record(0, "settle", None)
    energy.append(system.mechanical_energy())
    frame = 0
    for _ in range(cfg.settle_frames):
        system.step(1.0 / cfg.fps, cfg.substeps)
        frame += 1
        energy.append(system.mechanical_energy())
        record(frame, "settle", None)
    settle_hash = system.state_hash()
    max_err = system.max_constraint_error()

    strike_t0[0] = system.time
    blade_col.enabled = True
    dt = 1.0 / (cfg.fps * cfg.slow_motion)
    plane_n = _unit(_sub(b, a))
    for _ in range(cfg.strike_frames):
        system.step(dt, cfg.substeps)
        frame += 1
        h = edge_h(system.time - strike_t0[0])
        if h < sleeve_shell.r_outer:                  # edge inside / past the sleeve: cut in front of it
            cuts += system.cut(centre, plane_n, keep=lambda m, h=h, cy=centre[1]: (m[1] - cy) > -h)
        record(frame, "strike", h)

    if cut.skin_depth_m > 0.0:
        wound = blade_contact_to_wound(BONE_HIT, cut.skin_depth_m, cfg.blade_width_m,
                                       entry_point=tuple(round(c, 6) for c in _lerp(a, b, cfg.strike_t_axial)),
                                       direction=strike_dir)
    elif cut.residual_energy_j > 0.0:
        wound = blunt_impact_to_wound(BONE_HIT, energy_j=cut.residual_energy_j, contact_radius_m=0.02)
    else:
        wound = None
    assessment = assess_wound(wound, lc.profile) if wound else None

    result = {
        "sample": "material_sample_1_forearm_strike",
        "variant": "armored" if armored else "unarmored",
        "config": {k: v for k, v in asdict(cfg).items()},
        "placement": {"segment": SEGMENT, "a": list(a), "b": list(b), "radius_m": placement.radius_m,
                      "provenance": placement.provenance.value},
        "shells": [{"name": s.name, "material": s.material.value, "r_inner_m": round(s.r_inner, 6),
                    "r_outer_m": round(s.r_outer, 6), "z_range": s.z_range, "provenance": s.provenance.value}
                   for s in lc.shells],
        "soft_scale": lc.soft_scale,
        "blade": {"kinetic_energy_j": round(blade.kinetic_energy_j, 6), "mass": blade.mass_provenance.value,
                  "speed": blade.speed_provenance.value},
        "cut": {**asdict(cut), "stopped_material": cut.stopped_material.value if cut.stopped_material else None,
                "provenance": cut.provenance.value},
        "wound": None if assessment is None else {
            "bone": wound.bone_hit, "type": wound.wound_type.value, "depth_m": wound.depth_m,
            "width_m": wound.width_m, "energy_j": wound.energy_j,
            "region": assessment.region.value,
            "layers_breached": [layer.value for layer in assessment.layers_breached],
            "deepest_layer": assessment.deepest_layer.value, "severity": assessment.severity.value,
            "lethality": assessment.lethality, "bleeding_rate": assessment.bleeding_rate,
            "fracture": assessment.fracture, "incapacitating": assessment.incapacitating,
            "provenance": assessment.provenance.value},
        "sleeve": {"n_particles": len(system.x), "n_constraints": len(system.constraints),
                   "constraints_cut": cuts, "faces": [list(f) for f in mesh.faces],
                   "max_skin_penetration_m": round(max_pen, 6)},
        "energy": {"basis": "kinetic + gravitational, settle phase (sleeve only, no blade)",
                   "settle_start_j": round(energy[0], 9), "settle_end_j": round(energy[-1], 9),
                   "settle_max_j": round(max(energy), 9), "max_constraint_error_m": round(max_err, 6)},
        "hash": {"settle_state": settle_hash, "final_state": system.state_hash()},
        "frames": frames,
        "materials": material_table(),
        "provenance": ProvenanceState.ESTIMATE.value,
        "determinism": "plain-float XPBD; constraint order is a permutation seeded by config.seed",
    }
    result["sha256"] = result_hash(result)
    return result


def result_hash(result: Dict) -> str:
    stable = {k: v for k, v in result.items() if k not in ("sha256", "timing")}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
