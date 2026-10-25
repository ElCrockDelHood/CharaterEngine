"""Tissue layers, muscle catalogue and wound assessment."""

import json
from pathlib import Path

import pytest

from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.tissue import (
    BODY_REGIONS,
    MUSCLES,
    BodyRegion,
    TissueLayer,
    muscles_attached_to,
    region_of_bone,
    tissue_profile,
)
from character_engine.domain.trauma import (
    LETHALITY_BY_REGION,
    REFERENCE_BLUNT_ENERGY_J,
    Severity,
    Wound,
    WoundType,
    assess_wound,
    blunt_impact_to_wound,
)

CANON = Path(__file__).resolve().parents[2] / "src/character_engine/data/anatomy/human_adult_206.json"


@pytest.fixture(scope="module")
def bone_names():
    return {b["canonical_name"] for b in json.loads(CANON.read_text(encoding="utf-8"))["bones"]}


# ------------------------------------------------------------------ layers ---------------

def test_every_region_has_profile_with_estimate_provenance():
    for region in BODY_REGIONS:
        p = tissue_profile(region)
        assert p.provenance == ProvenanceState.ESTIMATE
        assert p.layers()[0] == TissueLayer.SKIN
        assert p.total_depth_m() > 0
        for layer in p.layers():
            lo, hi = p.thickness_range_m[layer]
            assert lo <= p.thickness_m[layer] <= hi


def test_layer_order_and_cavities():
    thorax = tissue_profile(BodyRegion.THORAX)
    assert thorax.has_cavity and thorax.layers()[-1] == TissueLayer.VISCERA
    assert not tissue_profile(BodyRegion.THIGH).has_cavity
    assert thorax.depth_to_layer(TissueLayer.SKIN) == 0.0
    assert thorax.depth_to_layer(TissueLayer.BONE) > thorax.depth_to_layer(TissueLayer.MUSCLE)
    assert thorax.layer_at_depth(0.0005) == TissueLayer.SKIN
    assert thorax.layer_at_depth(10.0) == TissueLayer.VISCERA
    with pytest.raises(KeyError):
        tissue_profile(BodyRegion.THIGH).depth_to_layer(TissueLayer.VISCERA)


def test_every_canonical_bone_maps_to_a_region(bone_names):
    for name in bone_names | {"ROOT_SKELETON", "CRANIUM"}:
        assert isinstance(region_of_bone(name), BodyRegion), name
    assert region_of_bone("FRONTAL") == BodyRegion.HEAD
    assert region_of_bone("RIB_08_L") == BodyRegion.THORAX
    assert region_of_bone("TOE_PHALANX_DISTAL_1_R") == BodyRegion.FOOT
    assert region_of_bone("PHALANX_DISTAL_1_R") == BodyRegion.HAND
    with pytest.raises(KeyError):
        region_of_bone("WING")


# ------------------------------------------------------------------ muscles --------------

def test_muscle_attachments_reference_real_bones(bone_names):
    assert len(MUSCLES) >= 40
    for m in MUSCLES.values():
        assert m.origin_bone in bone_names, m.name
        assert m.insertion_bone in bone_names, m.name
        assert 0.0 <= m.origin_t <= 1.0 and 0.0 <= m.insertion_t <= 1.0
        assert m.radius_m > 0 and 0.0 <= m.tendon_fraction < 1.0
        assert m.attachment_provenance == ProvenanceState.PROVEN
        assert m.geometry_provenance == ProvenanceState.ESTIMATE


def test_muscles_are_bilateral_and_queryable():
    names = set(MUSCLES)
    lefts = {n for n in names if n.endswith("_L")}
    assert lefts and all(n[:-2] + "_R" in names for n in lefts)
    assert any(m.name.startswith("QUADRICEPS") for m in muscles_attached_to("PATELLA_L"))
    assert not muscles_attached_to("STAPES_L")


# ------------------------------------------------------------------ wounds ---------------

def test_blade_contact_maps_to_estimate_incision_without_energy():
    from character_engine.domain.trauma import WoundType, assess_wound, blade_contact_to_wound
    w = blade_contact_to_wound("RADIUS_L", 0.008, 0.035, entry_point=(0.2, -0.1, 1.2))
    assert w.wound_type == WoundType.INCISION and w.energy_j is None
    assert w.depth_m == 0.008 and w.width_m == 0.035
    assert w.provenance == ProvenanceState.ESTIMATE
    a1, a2 = assess_wound(w), assess_wound(w)
    assert a1 == a2                                   # deterministic (same input -> same assessment)
    assert a1.region.value == "forearm"
    with pytest.raises(ValueError):
        blade_contact_to_wound("RADIUS_L", 0.0, 0.035)


def test_wound_validation():
    with pytest.raises(ValueError):
        Wound("STERNUM", WoundType.STAB, depth_m=-0.01)


def test_severity_increases_with_depth():
    sev = [assess_wound(Wound("FEMUR_L", WoundType.STAB, depth_m=d)).severity.value for d in (0.001, 0.02, 0.06, 0.12)]
    assert sev == sorted(sev) and sev[0] < sev[-1]


def test_abrasion_is_minor_and_skin_only():
    a = assess_wound(Wound("RADIUS_L", WoundType.ABRASION, depth_m=0.0005))
    assert a.layers_breached == (TissueLayer.SKIN,)
    assert a.severity == Severity.MINOR and not a.incapacitating and a.lethality < 0.05


def test_deep_thoracic_stab_is_lethal_risk():
    a = assess_wound(Wound("STERNUM", WoundType.STAB, depth_m=0.12, width_m=0.02))
    assert a.deepest_layer == TissueLayer.VISCERA
    assert a.severity.value >= 5 and a.is_lethal
    assert "cavity_penetration" in a.tags and "haemorrhage" in a.tags


def test_region_lethality_ordering():
    assert LETHALITY_BY_REGION[BodyRegion.HEAD] > LETHALITY_BY_REGION[BodyRegion.THIGH] > LETHALITY_BY_REGION[BodyRegion.HAND]
    head = assess_wound(Wound("FRONTAL", WoundType.GUNSHOT, depth_m=0.08, energy_j=800))
    hand = assess_wound(Wound("METACARPAL_3_L", WoundType.GUNSHOT, depth_m=0.03, energy_j=800))
    assert head.lethality > hand.lethality
    assert head.is_lethal and not hand.is_lethal


def test_amputation_and_burn_rules():
    amp = assess_wound(Wound("HUMERUS_L", WoundType.AMPUTATION, depth_m=0.10, width_m=0.09))
    assert amp.fracture and amp.incapacitating and amp.lethality >= 0.4
    burn = assess_wound(Wound("TIBIA_L", WoundType.BURN, depth_m=0.004))
    assert burn.bleeding_rate == 0.0


def test_blunt_energy_scale():
    light = assess_wound(blunt_impact_to_wound("STERNUM", energy_j=60.0))
    heavy = assess_wound(blunt_impact_to_wound("STERNUM", energy_j=REFERENCE_BLUNT_ENERGY_J * 1.1))
    assert light.severity == Severity.MINOR and not light.fracture
    assert heavy.fracture and heavy.incapacitating
    assert TissueLayer.SKIN not in light.layers_breached  # skin intact under blunt trauma
    assert blunt_impact_to_wound("STERNUM", impulse=0.5).depth_m < blunt_impact_to_wound("STERNUM", impulse=1.0).depth_m
    with pytest.raises(ValueError):
        blunt_impact_to_wound("STERNUM")


def test_assessment_is_labelled_estimate():
    a = assess_wound(Wound("TIBIA_L", WoundType.LACERATION, depth_m=0.01))
    assert a.provenance == ProvenanceState.ESTIMATE
    assert a.wound.provenance == ProvenanceState.USER_INPUT
