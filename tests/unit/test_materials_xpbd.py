"""Material sample 1: material catalogue, layered capsule, XPBD solver, cut model and the forearm strike."""

import json
import math
from pathlib import Path

import pytest

from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.materials import (
    MATERIALS,
    MaterialKind,
    OuterLayer,
    Quantity,
    layered_capsule,
    material,
    material_table,
)
from character_engine.domain.physics import (
    Blade,
    CapsuleCollider,
    DistanceConstraint,
    ParticleSystem,
    cut_through,
)
from character_engine.domain.physics.forearm_strike import (
    SampleConfig,
    build_layers,
    forearm_placement,
    run_variant,
)
from character_engine.domain.physics.xpbd import tube
from character_engine.domain.tissue import BodyRegion, TissueLayer, tissue_profile

DATA = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

SMALL = SampleConfig(sleeve_n_around=12, sleeve_n_along=6, settle_frames=12, strike_frames=24)


@pytest.fixture(scope="module")
def points():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    p = lambda d: (d["x"], d["y"], d["z"])  # noqa: E731
    return {b["canonical_name"]: (p(b["head"]), p(b["tail"])) for b in bones}


@pytest.fixture(scope="module")
def runs(points):
    return {armored: run_variant(points, armored, SMALL) for armored in (False, True)}


# ------------------------------------------------------------------ catalogue ------------

def test_no_material_value_is_proven_and_every_value_has_a_range():
    for m in MATERIALS.values():
        for name in m.mechanical.__dataclass_fields__:
            q = getattr(m.mechanical, name)
            if q is None:
                continue
            assert isinstance(q, Quantity)
            assert q.provenance not in (ProvenanceState.PROVEN, ProvenanceState.DERIVED), (m.name, name)
            assert q.low <= q.value <= q.high


def test_tuning_constants_are_assumed_not_estimates():
    assert material(MaterialKind.ARMOR_STEEL).mechanical.cut_energy.provenance == ProvenanceState.ASSUMED
    assert material(MaterialKind.BONE).mechanical.cut_energy.provenance == ProvenanceState.ASSUMED
    wool = material(MaterialKind.CLOTH_WOOL).mechanical
    assert wool.stretch_compliance.provenance == wool.bend_compliance.provenance == ProvenanceState.ASSUMED


def test_quantity_outside_range_is_rejected():
    with pytest.raises(ValueError):
        Quantity(2.0, 0.0, 1.0, "m", ProvenanceState.ESTIMATE)


def test_optical_uses_openpbr_names_and_table_is_json():
    for kind, m in MATERIALS.items():
        if kind is MaterialKind.AIR:
            assert m.optical is None
            continue
        assert m.optical.provenance == ProvenanceState.ASSUMED
        assert all(0.0 <= c <= 1.0 for c in m.optical.base_color)
    assert material(MaterialKind.ARMOR_STEEL).optical.base_metalness == 1.0
    assert material(MaterialKind.CLOTH_WOOL).optical.fuzz_weight > 0
    table = json.loads(json.dumps(material_table()))
    assert {row["kind"] for row in table} == {k.value for k in MaterialKind}


# ------------------------------------------------------------------ layered capsule ------

def test_layers_fill_the_envelope_inside_out(points):
    lc = build_layers(forearm_placement(points), SampleConfig(), armored=True)
    names = [s.name for s in lc.shells]
    assert names == ["bone", "tendon", "muscle", "fat", "skin", "sleeve_gap", "sleeve", "bracer_gap", "bracer"]
    for inner, outer in zip(lc.shells, lc.shells[1:]):
        assert outer.r_inner == pytest.approx(inner.r_outer, abs=1e-12)
    assert lc.shell("skin").r_outer == pytest.approx(0.04)                     # envelope radius at 1.80 m
    bone_t = tissue_profile(BodyRegion.FOREARM).thickness_m[TissueLayer.BONE]
    assert lc.shell("bone").r_outer == pytest.approx(bone_t / 2)
    assert 0 < lc.soft_scale < 1
    assert lc.shell("bracer").z_range == SampleConfig().bracer_z_range
    # fitted profile adds up to the envelope (half bone thickness + soft layers)
    prof = lc.profile
    soft = sum(prof.thickness_m[layer] for layer in (TissueLayer.SKIN, TissueLayer.FAT, TissueLayer.MUSCLE,
                                                       TissueLayer.TENDON))
    assert soft + prof.thickness_m[TissueLayer.BONE] / 2 == pytest.approx(0.04, abs=1e-5)


def test_material_at_point(points):
    lc = build_layers(forearm_placement(points), SampleConfig(), armored=True)
    a, b = lc.placement.a, lc.placement.b
    mid = tuple((a[i] + b[i]) / 2 for i in range(3))
    at = lambda r: lc.material_at((mid[0] + r, mid[1], mid[2]))  # noqa: E731
    assert at(0.001) == MaterialKind.BONE
    assert at(0.039) == MaterialKind.SKIN
    assert at(0.047) == MaterialKind.CLOTH_WOOL
    assert at(0.051) == MaterialKind.ARMOR_STEEL
    assert at(0.2) is None
    near_elbow = (a[0] + 0.051, a[1], a[2])                                     # t = 0: outside the bracer range
    assert lc.material_at(near_elbow) is None


# ------------------------------------------------------------------ cut model ------------

def test_cut_depth_grows_with_energy_and_armour_stops_the_reference_strike(points):
    pl = forearm_placement(points)
    bare = layered_capsule(pl, [OuterLayer("sleeve", MaterialKind.CLOTH_WOOL, 0.002, 0.006)])
    depths = [cut_through(bare, Blade(0.6, v, 0.028)).penetration_m for v in (2.0, 5.0, 10.0)]
    assert depths == sorted(depths) and depths[0] > 0
    assert cut_through(bare, Blade(0.6, 0.0, 0.028)).penetration_m == 0.0
    ref = cut_through(bare, Blade(0.6, 10.0, 0.028))
    assert ref.skin_depth_m > 0 and ref.stopped_in == "bone" and not ref.transected
    armored = build_layers(pl, SampleConfig(), armored=True)
    stop = cut_through(armored, Blade(0.6, 10.0, 0.028))
    assert stop.stopped_in == "bracer" and stop.skin_depth_m == 0.0
    assert stop.residual_energy_j == pytest.approx(30.0)
    assert "bracer" not in stop.shells_cut


# ------------------------------------------------------------------ XPBD -----------------

def test_free_fall_matches_gravity():
    s = ParticleSystem(x=[[0.0, 0.0, 10.0]], inv_mass=[1.0])
    for _ in range(60):
        s.step(1.0 / 60.0, 20)
    assert s.x[0][2] == pytest.approx(10.0 - 0.5 * 9.81, rel=2e-3)
    assert s.v[0][2] == pytest.approx(-9.81, rel=1e-9)


def test_pinned_particle_and_rigid_distance():
    s = ParticleSystem(x=[[0.0, 0.0, 1.0], [0.0, 0.0, 0.5]], inv_mass=[0.0, 1.0],
                       constraints=[DistanceConstraint(0, 1, 0.5, 0.0)])
    for _ in range(120):
        s.step(1.0 / 60.0, 20)
    assert s.x[0] == [0.0, 0.0, 1.0]
    assert math.dist(s.x[0], s.x[1]) == pytest.approx(0.5, abs=1e-6)


def test_capsule_keeps_particles_out():
    s = ParticleSystem(x=[[0.0, 0.0, 0.5]], inv_mass=[1.0], contact_offset=0.001)
    s.colliders = [CapsuleCollider("floor_bar", (-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.1)]
    for _ in range(120):
        s.step(1.0 / 60.0, 10)
    assert math.hypot(s.x[0][1], s.x[0][2]) >= 0.101 - 1e-9
    assert s.x[0][2] > 0


def test_tube_is_deterministic_and_does_not_gain_energy():
    def run():
        s, mesh = tube((0, 0, 1.0), (0, 0, 0.8), 0.05, 12, 6, 0.35, 1e-6, 5e-3)
        s.colliders = [CapsuleCollider("arm", (0, 0, 1.0), (0, 0, 0.8), 0.04, 0.4)]
        s.contact_offset, s.damping = 0.001, 0.5
        e0 = s.mechanical_energy()
        energies = []
        for _ in range(30):
            s.step(1.0 / 60.0, 20)
            energies.append(s.mechanical_energy())
        return s, mesh, e0, energies

    s1, mesh, e0, energies = run()
    s2, *_ = run()
    assert s1.state_hash() == s2.state_hash()
    assert len(mesh.faces) == 12 * 5
    assert max(energies) <= e0 * 1.01                     # ≤ 1 % numerical drift
    assert all(w == 0.0 for w in s1.inv_mass[:12])          # first ring pinned


def test_cut_deactivates_crossing_constraints():
    s, _ = tube((0, 0, 1.0), (0, 0, 0.8), 0.05, 12, 6, 0.35, 1e-6, 5e-3)
    n = s.cut((0, 0, 0.9), (0, 0, 1.0), keep=lambda m: m[1] > 0.0)
    assert n > 0
    assert all(c.active or (s.x[c.i][1] + s.x[c.j][1]) / 2 <= 0 for c in s.constraints)


# ------------------------------------------------------------------ sample ---------------

def test_sample_is_reproducible(points, runs):
    again = run_variant(points, False, SMALL)
    assert again["sha256"] == runs[False]["sha256"]
    assert again["hash"] == runs[False]["hash"]


def test_armour_changes_the_layer_reached(runs):
    bare, armored = runs[False], runs[True]
    assert bare["wound"]["type"] == "incision"
    assert armored["wound"]["type"] == "blunt"
    order = [layer.value for layer in TissueLayer]
    assert order.index(armored["wound"]["deepest_layer"]) < order.index(bare["wound"]["deepest_layer"])
    assert armored["wound"]["severity"] < bare["wound"]["severity"]
    assert bare["sleeve"]["constraints_cut"] > 0 and armored["sleeve"]["constraints_cut"] == 0


def test_sample_physics_criteria(runs):
    for r in runs.values():
        assert r["sleeve"]["max_skin_penetration_m"] <= 0.001
        assert r["energy"]["settle_max_j"] <= r["energy"]["settle_start_j"] * 1.01
        assert r["placement"]["segment"] == "forearm.L" and r["placement"]["radius_m"] == pytest.approx(0.04)
        assert r["provenance"] == "estimate"
        assert r["frames"][-1]["phase"] == "strike" and "sleeve" in r["frames"][-1]
    json.dumps(runs[False])                                  # report is JSON-ready
