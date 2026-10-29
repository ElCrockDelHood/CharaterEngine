"""Material sample 2: thorax with ribs and cavity, wool coat and an optional padded vest, hit by a blunt strike.

Same pipeline as sample 1 (``forearm_strike.py``), with a blunt model instead of a cut model:

1. Thorax layered capsule (hollow: skin, fat, muscle, tendon, rib shell, cavity) + coat (wool) and, in the vested
   variant, a padded vest under the coat.
2. XPBD coat settles under gravity; a kinematic impactor (end-on, contact radius ``impactor_radius_m``) travels
   in slow motion and indents the coat; the body collider ignores the cloth near the impactor so it can be pushed in.
3. The energy path comes from :func:`blunt_through` (plateau crush + rib fracture energy). The stopping depth of the
   impactor is the total displacement of that model (garment gaps + crushed layers).
4. The affected depth becomes ``Wound(BLUNT)`` and goes through the unchanged ``assess_wound``. The same strike is
   also assessed with the legacy mapping (``blunt_impact_to_wound``: E / 400 J · depth to bone) for comparison, and
   an energy sweep shows where each variant starts to fracture ribs.

Geometry limit (block dummy): the thorax block is a sphere at chest height (its spine segment, T12 tail to T1 head,
is 0.146 m long, shorter than two radii). The sample therefore stacks the layers on a cylinder along that segment;
it shows layer behaviour, not chest shape. Every non-canonical input is listed in :class:`SampleConfig`.
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
from ..rigging.block_dummy import BlockPlacement, block_placements, placements_by_name
from ..trauma import Wound, WoundType, assess_wound
from .blunt import BluntResult, Impactor, blunt_through, blunt_wound, legacy_blunt_depth_m
from .xpbd import CapsuleCollider, ParticleSystem, TubeMesh, tube

Vec = Tuple[float, float, float]

SEGMENT = "thorax"
BONE_HIT = "THORACIC_6"          # weight bone of the thorax block (block_dummy.py)
SPINE_ENDS = (("THORACIC_12", 1), ("THORACIC_1", 0))      # (bone, 0 = head / 1 = tail)


@dataclass(frozen=True)
class SampleConfig:
    stature_m: float = 1.80
    # coat (ESTIMATE: heavy wool, loose)
    coat_thickness_m: float = 0.003
    coat_gap_m: float = 0.008
    coat_n_around: int = 36
    coat_n_along: int = 12
    # vest (ESTIMATE: 20 mm quilted gambeson-type)
    vest_thickness_m: float = 0.02
    vest_gap_m: float = 0.004
    # impactor (mass PLACEHOLDER, speed ESTIMATE, end-on contact patch ESTIMATE)
    impactor_mass_kg: float = 1.2
    impactor_speed_m_s: float = 9.0
    impactor_radius_m: float = 0.03
    impactor_length_m: float = 0.25
    strike_t_axial: float = 0.5
    start_gap_m: float = 0.08
    sweep_speeds_m_s: Tuple[float, ...] = (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 14.0)
    # time
    fps: int = 60
    settle_frames: int = 40
    strike_frames: int = 44
    slow_motion: float = 20.0
    substeps: int = 20
    seed: int = 0                      # seeds the XPBD constraint order (the only use of randomness)
    provenance: Mapping[str, str] = field(default_factory=lambda: {
        "stature_m": "USER_INPUT", "coat_*": "ESTIMATE", "vest_*": "ESTIMATE",
        "impactor_mass_kg": "PLACEHOLDER", "impactor_speed_m_s": "ESTIMATE", "impactor_radius_m": "ESTIMATE",
        "time": "ASSUMED (presentation)"})


def thorax_placement(points: Mapping[str, Tuple[Vec, Vec]], stature_m: float = 1.80) -> BlockPlacement:
    """Block-dummy thorax radius, with the axis taken along the T12–T1 spine segment (see module docstring)."""
    base = placements_by_name(block_placements(points, stature_m))[SEGMENT]
    p0 = points[SPINE_ENDS[0][0]][SPINE_ENDS[0][1]]
    p1 = points[SPINE_ENDS[1][0]][SPINE_ENDS[1][1]]
    return BlockPlacement(base.name, base.region, base.weight_bone, p0, p1, base.radius_m, base.provenance)


def build_layers(placement: BlockPlacement, cfg: SampleConfig, vest: bool) -> LayeredCapsule:
    outer: List[OuterLayer] = []
    if vest:
        outer.append(OuterLayer("vest", MaterialKind.PADDED_CLOTH, cfg.vest_thickness_m, cfg.vest_gap_m))
    outer.append(OuterLayer("coat", MaterialKind.CLOTH_WOOL, cfg.coat_thickness_m, cfg.coat_gap_m))
    return layered_capsule(placement, outer)


def _lerp(a: Vec, b: Vec, t: float) -> Vec:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _impactor(cfg: SampleConfig, speed: Optional[float] = None) -> Impactor:
    return Impactor(cfg.impactor_mass_kg, cfg.impactor_speed_m_s if speed is None else speed,
                    cfg.impactor_radius_m)


def _assess(lc: LayeredCapsule, wound: Wound) -> Dict:
    a = assess_wound(wound, lc.profile)
    return {"depth_m": wound.depth_m, "width_m": wound.width_m, "energy_j": wound.energy_j,
            "layers_breached": [layer.value for layer in a.layers_breached], "deepest_layer": a.deepest_layer.value,
            "severity": a.severity.value, "lethality": a.lethality, "bleeding_rate": a.bleeding_rate,
            "fracture": a.fracture, "incapacitating": a.incapacitating, "tags": list(a.tags),
            "provenance": a.provenance.value}


def energy_sweep(lc: LayeredCapsule, cfg: SampleConfig) -> List[Dict]:
    rows = []
    for v in cfg.sweep_speeds_m_s:
        imp = _impactor(cfg, v)
        res = blunt_through(lc, imp, cfg.strike_t_axial)
        w = _assess(lc, blunt_wound(BONE_HIT, imp, res))
        legacy = _assess(lc, Wound(BONE_HIT, WoundType.BLUNT, legacy_blunt_depth_m(lc, res.energy_in_j),
                                   round(2 * cfg.impactor_radius_m, 4), res.energy_in_j))
        rows.append({"speed_m_s": v, "energy_j": res.energy_in_j, "stopped_in": res.stopped_in,
                     "affected_depth_mm": round(res.affected_depth_m * 1000, 1), "ribs_fractured": res.fractured,
                     "deepest_layer": w["deepest_layer"], "severity": w["severity"],
                     "legacy_deepest_layer": legacy["deepest_layer"], "legacy_severity": legacy["severity"]})
    return rows


def build_coat(lc: LayeredCapsule, cfg: SampleConfig) -> Tuple[ParticleSystem, TubeMesh]:
    p = lc.placement
    coat = lc.shell("coat")
    wool = material(MaterialKind.CLOTH_WOOL).mechanical
    r_mid = (coat.r_inner + coat.r_outer) / 2.0
    system, mesh = tube(p.b, p.a, r_mid, cfg.coat_n_around, cfg.coat_n_along, wool.areal_density.value,
                        wool.stretch_compliance.value, wool.bend_compliance.value, seed=cfg.seed)
    system.contact_offset = cfg.coat_thickness_m / 2.0
    system.damping = wool.damping.value
    return system, mesh


def run_variant(points: Mapping[str, Tuple[Vec, Vec]], vest: bool, cfg: SampleConfig = SampleConfig(),
                keep_frames: bool = True) -> Dict:
    placement = thorax_placement(points, cfg.stature_m)
    lc = build_layers(placement, cfg, vest)
    imp = _impactor(cfg)
    blunt: BluntResult = blunt_through(lc, imp, cfg.strike_t_axial)
    system, mesh = build_coat(lc, cfg)

    a, b = placement.a, placement.b
    centre = _lerp(a, b, cfg.strike_t_axial)
    # the impactor travels from the front (−Y) towards +Y
    rb = cfg.impactor_radius_m
    r_out = lc.outer_radius
    contact_h = r_out + rb                           # tip-sphere centre distance to the axis at first contact
    stop_h = contact_h - blunt.displacement_m
    start_h = contact_h + cfg.start_gap_m
    v0 = imp.speed_m_s
    t_contact = cfg.start_gap_m / v0
    disp = blunt.displacement_m
    decel = v0 * v0 / (2.0 * disp) if disp > 0 else math.inf
    t_stop = t_contact + (2.0 * disp / v0 if disp > 0 else 0.0)

    def tip_h(t: float) -> float:
        if t <= t_contact:
            return start_h - v0 * t
        if t >= t_stop:
            return stop_h
        tc = t - t_contact
        return contact_h - (v0 * tc - 0.5 * decel * tc * tc)

    def impactor_ends(h: float) -> Tuple[Vec, Vec]:
        tip = (centre[0], centre[1] - h, centre[2])
        return tip, (tip[0], tip[1] - cfg.impactor_length_m, tip[2])

    body_r = lc.shell("coat_gap").r_inner
    wool_mu = material(MaterialKind.CLOTH_WOOL).mechanical.friction.value
    strike_t0 = [0.0]
    bat = CapsuleCollider("impactor", *impactor_ends(start_h), rb, friction=0.0,
                          motion=lambda t: impactor_ends(tip_h(t - strike_t0[0])), enabled=False)
    body = CapsuleCollider("body", a, b, body_r, friction=wool_mu, skip=bat, skip_margin=0.04)
    system.colliders = [bat, body]

    frames: List[Dict] = []
    energy: List[float] = []
    max_pen = 0.0

    def record(frame: int, phase: str, h: Optional[float]):
        nonlocal max_pen
        for k, q in enumerate(system.x):
            if system.inv_mass[k] == 0.0:
                continue
            if phase == "settle":                    # penetration of the resting coat into the body collider
                d = body.radius + system.contact_offset - _axial_distance(q, a, b)
                max_pen = max(max_pen, d)
        entry = {"frame": frame, "phase": phase, "time_s": round(system.time, 6)}
        if h is not None:
            entry["impactor"] = [[round(c, 6) for c in e] for e in impactor_ends(h)]
            entry["tip_to_axis_m"] = round(h, 6)
        if keep_frames:
            entry["coat"] = system.positions(6)
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
    bat.enabled = True
    dt = 1.0 / (cfg.fps * cfg.slow_motion)
    for _ in range(cfg.strike_frames):
        system.step(dt, cfg.substeps)
        frame += 1
        record(frame, "strike", tip_h(system.time - strike_t0[0]))

    wound = blunt_wound(BONE_HIT, imp, blunt)
    legacy = Wound(BONE_HIT, WoundType.BLUNT, legacy_blunt_depth_m(lc, blunt.energy_in_j),
                   round(2 * rb, 4), blunt.energy_in_j)
    result = {
        "sample": "material_sample_2_thorax_blunt",
        "variant": "vested" if vest else "unvested",
        "config": {k: v for k, v in asdict(cfg).items()},
        "geometry_note": "thorax block is a sphere; layers are stacked on a cylinder along the T12-T1 spine segment",
        "placement": {"segment": SEGMENT, "a": list(a), "b": list(b), "radius_m": placement.radius_m,
                      "provenance": placement.provenance.value},
        "shells": [{"name": s.name, "material": s.material.value, "r_inner_m": round(s.r_inner, 6),
                    "r_outer_m": round(s.r_outer, 6), "z_range": s.z_range, "provenance": s.provenance.value}
                   for s in lc.shells],
        "wall_scale": lc.soft_scale,
        "impactor": {"kinetic_energy_j": blunt.energy_in_j, "mass": imp.mass_provenance.value,
                     "speed": imp.speed_provenance.value, "contact_area_m2": round(imp.contact_area_m2, 6)},
        "blunt": {**{k: v for k, v in asdict(blunt).items() if k not in ("absorbed", "provenance")},
                  "absorbed": [asdict(r) for r in blunt.absorbed], "provenance": blunt.provenance.value},
        "wound": _assess(lc, wound),
        "wound_legacy_mapping": {**_assess(lc, legacy), "basis": "E / REFERENCE_BLUNT_ENERGY_J * depth to bone"},
        "sweep": energy_sweep(lc, cfg),
        "coat": {"n_particles": len(system.x), "n_constraints": len(system.constraints),
                 "faces": [list(f) for f in mesh.faces], "max_body_penetration_m": round(max_pen, 6)},
        "energy": {"basis": "kinetic + gravitational, settle phase (coat only, no impactor)",
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


def _axial_distance(p, a: Vec, b: Vec) -> float:
    from ..materials.layered_capsule import segment_distance
    return segment_distance((p[0], p[1], p[2]), a, b)[0]


def result_hash(result: Dict) -> str:
    stable = {k: v for k, v in result.items() if k not in ("sha256", "timing")}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
