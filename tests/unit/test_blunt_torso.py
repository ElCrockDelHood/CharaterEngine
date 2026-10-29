"""Material sample 2: hollow layered capsule, plateau blunt model and the thorax strike."""

import json
import math
from pathlib import Path

import pytest

from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.materials import MaterialKind, OuterLayer, layered_capsule
from character_engine.domain.physics import CapsuleCollider, ParticleSystem
from character_engine.domain.physics.blunt import (
    Impactor,
    blunt_through,
    blunt_wound,
    legacy_blunt_depth_m,
)
from character_engine.domain.physics.torso_strike import (
    SampleConfig,
    build_layers,
    run_variant,
    thorax_placement,
)
from character_engine.domain.tissue import BodyRegion, TissueLayer, tissue_profile

DATA = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

SMALL = SampleConfig(coat_n_around=16, coat_n_along=6, settle_frames=12, strike_frames=24)


@pytest.fixture(scope="module")
def points():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    p = lambda d: (d["x"], d["y"], d["z"])  # noqa: E731
    return {b["canonical_name"]: (p(b["head"]), p(b["tail"])) for b in bones}


@pytest.fixture(scope="module")
def capsules(points):
    cfg = SampleConfig()
    pl = thorax_placement(points)
    return build_layers(pl, cfg, False), build_layers(pl, cfg, True)


@pytest.fixture(scope="module")
def runs(points):
    return {vest: run_variant(points, vest, SMALL) for vest in (False, True)}


# ------------------------------------------------------------------ hollow capsule -------

def test_hollow_layers_wall_then_cavity(capsules):
    bare, vested = capsules
    assert [s.name for s in bare.shells] == ["viscera", "bone", "tendon", "muscle", "fat", "skin", "coat_gap", "coat"]
    assert [s.name for s in vested.shells] == ["viscera", "bone", "tendon", "muscle", "fat", "skin", "vest_gap",
                                                "vest", "coat_gap", "coat"]
    for inner, outer in zip(bare.shells, bare.shells[1:]):
        assert outer.r_inner == pytest.approx(inner.r_outer, abs=1e-12)
    assert bare.shell("viscera").r_inner == 0.0 and bare.shell("viscera").material == MaterialKind.VISCERA
    assert bare.shell("skin").r_outer == pytest.approx(0.13)
    rib = tissue_profile(BodyRegion.THORAX).thickness_m[TissueLayer.BONE]
    assert bare.shell("bone").thickness == pytest.approx(rib, abs=1e-9)          # full rib thickness, not half
    assert bare.soft_scale == 1.0
    prof = bare.profile
    assert prof.thickness_m[TissueLayer.VISCERA] == pytest.approx(bare.shell("viscera").r_outer, abs=1e-6)
    assert prof.total_depth_m() == pytest.approx(0.13, abs=1e-5)                 # skin surface → axis


def test_hollow_wall_is_scaled_when_it_leaves_no_cavity(points):
    pl = thorax_placement(points)
    thin = type(pl)(pl.name, pl.region, pl.weight_bone, pl.a, pl.b, 0.05, pl.provenance)
    lc = layered_capsule(thin, [])
    assert lc.soft_scale < 1.0
    assert lc.shell("viscera").r_outer > 0.0


def test_forearm_still_uses_the_solid_fit(points):
    from character_engine.domain.physics.forearm_strike import build_layers as forearm_layers
    from character_engine.domain.physics.forearm_strike import forearm_placement
    lc = forearm_layers(forearm_placement(points), __import__(
        "character_engine.domain.physics.forearm_strike", fromlist=["SampleConfig"]).SampleConfig(), False)
    assert lc.shells[0].name == "bone" and lc.shells[0].r_inner == 0.0


# ------------------------------------------------------------------ blunt model ----------

def test_energy_is_conserved(capsules):
    for lc in capsules:
        for v in (1.0, 3.0, 5.0, 7.0, 9.0, 12.0):
            r = blunt_through(lc, Impactor(1.2, v, 0.03))
            assert sum(row.absorbed_j for row in r.absorbed) + r.stored_j + r.residual_j == pytest.approx(
                r.energy_in_j, abs=1e-4)


def test_depth_grows_with_energy(capsules):
    for lc in capsules:
        depths = [blunt_through(lc, Impactor(1.2, v, 0.03)).affected_depth_m for v in (0.5, 2, 4, 6, 8, 10, 14)]
        assert depths == sorted(depths) and depths[0] >= 0.0


def test_vest_protects_at_equal_energy_and_raises_the_fracture_threshold(capsules):
    bare, vested = capsules
    for v in (2.0, 5.0, 6.0, 8.0, 9.0):
        a = blunt_through(bare, Impactor(1.2, v, 0.03))
        b = blunt_through(vested, Impactor(1.2, v, 0.03))
        assert b.affected_depth_m <= a.affected_depth_m

    def threshold(lc):
        return next(v / 10 for v in range(10, 200) if blunt_through(lc, Impactor(1.2, v / 10, 0.03)).fractured)

    assert threshold(vested) > threshold(bare)


def test_rib_shell_is_all_or_nothing(capsules):
    bare, _ = capsules
    held = blunt_through(bare, Impactor(1.2, 6.0, 0.03))
    assert held.stopped_in == "bone" and not held.fractured and held.stored_j > 0
    assert held.affected_depth_m == pytest.approx(bare.profile.depth_to_layer(TissueLayer.BONE), abs=1e-6)
    broke = blunt_through(bare, Impactor(1.2, 8.0, 0.03))
    assert broke.fractured and broke.affected_depth_m > held.affected_depth_m


def test_air_gap_is_free_and_steel_is_rejected(capsules, points):
    bare, _ = capsules
    r = blunt_through(bare, Impactor(1.2, 0.5, 0.03))
    gap = next(row for row in r.absorbed if row.shell == "coat_gap")
    assert gap.absorbed_j == 0.0 and gap.compression_m == pytest.approx(0.008)
    steel = layered_capsule(thorax_placement(points), [OuterLayer("plate", MaterialKind.ARMOR_STEEL, 0.0015, 0.002)])
    with pytest.raises(ValueError, match="crush parameters"):
        blunt_through(steel, Impactor(1.2, 5.0, 0.03))


def test_wound_goes_through_the_unchanged_trauma_entry(capsules):
    bare, _ = capsules
    imp = Impactor(1.2, 9.0, 0.03)
    w = blunt_wound("THORACIC_6", imp, blunt_through(bare, imp))
    assert w.wound_type.value == "blunt" and w.provenance == ProvenanceState.ESTIMATE
    assert w.width_m == pytest.approx(0.06) and w.energy_j == pytest.approx(48.6, abs=1e-3)
    assert legacy_blunt_depth_m(bare, 48.6) < w.depth_m          # the 400 J constant barely reaches the fat layer


# ------------------------------------------------------------------ XPBD skip ------------

def test_skip_collider_lets_an_indenter_push_cloth_in_locally():
    def drop(with_skip):
        s = ParticleSystem(x=[[0.0, 0.0, 0.05]], inv_mass=[1.0], gravity=(0.0, 0.0, 0.0))
        pusher = CapsuleCollider("pusher", (0.0, 0.0, 0.07), (0.0, 0.0, 0.2), 0.02)
        body = CapsuleCollider("body", (-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.1,
                               skip=pusher if with_skip else None, skip_margin=0.01)
        s.colliders = [pusher, body]
        s.step(1 / 60, 10)
        return s.x[0]
    free = drop(True)
    assert math.hypot(free[1], free[2]) < 0.1 - 1e-6      # pushed inside the body radius by the pusher
    blocked = drop(False)
    assert math.hypot(blocked[1], blocked[2]) >= 0.1 - 1e-9


# ------------------------------------------------------------------ sample ---------------

def test_sample_is_reproducible(points, runs):
    again = run_variant(points, False, SMALL)
    assert again["sha256"] == runs[False]["sha256"] and again["hash"] == runs[False]["hash"]


def test_vest_changes_the_outcome(runs):
    bare, vested = runs[False], runs[True]
    assert bare["blunt"]["fractured"] and not vested["blunt"]["fractured"]
    assert bare["wound"]["deepest_layer"] == "viscera" and vested["wound"]["deepest_layer"] != "viscera"
    assert vested["wound"]["severity"] < bare["wound"]["severity"]
    for r in runs.values():
        assert r["wound_legacy_mapping"]["severity"] <= r["wound"]["severity"]
        assert r["wound_legacy_mapping"]["basis"].startswith("E / REFERENCE_BLUNT_ENERGY_J")


def test_sample_physics_and_report(runs):
    for r in runs.values():
        assert r["coat"]["max_body_penetration_m"] <= 0.001
        assert r["energy"]["settle_max_j"] <= r["energy"]["settle_start_j"] * 1.01
        assert r["provenance"] == "estimate" and "sphere" in r["geometry_note"]
        assert r["frames"][-1]["phase"] == "strike" and "impactor" in r["frames"][-1] and "coat" in r["frames"][-1]
        assert len(r["sweep"]) == len(SMALL.sweep_speeds_m_s)
        energies = [row["energy_j"] for row in r["sweep"]]
        assert energies == sorted(energies)
    json.dumps(runs[True])
