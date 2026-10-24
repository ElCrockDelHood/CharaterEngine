"""Osteometry: Trotter & Gleser regressions, provenance discipline, derived lengths."""

import json
from pathlib import Path

import pytest

from character_engine.domain.anatomy.osteometry import (
    LONG_BONES,
    LongBoneRegression,
    OsteometricTable,
    bone_length_from_stature,
    load_osteometry,
)
from character_engine.domain.anatomy.osteometry.long_bones import default_osteometry_path
from character_engine.domain.anatomy.reference.source import ProvenanceState

REF = Path(__file__).resolve().parents[2] / "src/character_engine/data/anatomy/references/osteometry.json"


def test_default_path_points_to_bundled_reference():
    assert default_osteometry_path() == REF
    assert REF.exists()


def test_reference_json_declares_sources_and_provenance():
    data = json.loads(REF.read_text(encoding="utf-8"))["osteometric_data"]
    male = data["regressions"]["male_white"]
    assert male["provenance"] == "PROVEN"
    assert male["source_id"] == "TROTTER_1970"
    assert {"FEMUR", "TIBIA", "FIBULA", "HUMERUS", "RADIUS", "ULNA"} <= set(male["bones"])
    for bone, row in male["bones"].items():
        assert {"a", "b", "see_cm"} <= set(row), bone
    assert "TROTTER_1970" in data["sources"]
    female = data["regressions"]["female_white"]
    assert female["provenance"] == "PROVEN"
    assert female["source_id"] == "TROTTER_GLESER_1952"
    for bone, row in female["bones"].items():
        assert row.get("provenance", female["provenance"]) == "PROVEN", bone
        assert row["a"] and row["b"]


def test_female_white_all_long_bones_are_usable():
    table = load_osteometry()
    female = table.regressions["female_white"]
    for bone in LONG_BONES:
        assert female[bone].is_usable, bone
        assert female[bone].provenance == ProvenanceState.PROVEN
    lengths = table.lengths_for_stature(1.65, "female_white")
    assert lengths["FEMUR"] == pytest.approx(0.4490, abs=5e-4)
    assert lengths["TIBIA"] == pytest.approx(0.3568, abs=5e-4)
    assert lengths["HUMERUS"] == pytest.approx(0.3185, abs=5e-4)
    assert lengths["FEMUR"] > lengths["TIBIA"] > lengths["HUMERUS"] > lengths["ULNA"] > lengths["RADIUS"]


def test_female_black_series_is_separate_and_proven():
    table = load_osteometry()
    fb = table.regressions["female_black"]
    assert fb["FEMUR"].is_usable and fb["FEMUR"].a == pytest.approx(2.28)
    # Same stature must not silently reuse the white-female equation.
    w = table.lengths_for_stature(1.65, "female_white")["FEMUR"]
    b = table.lengths_for_stature(1.65, "female_black")["FEMUR"]
    assert abs(w - b) > 0.005


def test_trotter_male_femur_regression_roundtrip():
    """Trotter (1970) white male femur: stature = 2.38 * L + 61.41 (cm)."""
    reg = load_osteometry().regressions["male_white"]["FEMUR"]
    assert reg.a == pytest.approx(2.38) and reg.b == pytest.approx(61.41)
    length = reg.bone_length_cm(180.0)
    assert length == pytest.approx((180.0 - 61.41) / 2.38, rel=1e-6)
    assert reg.stature_cm(length) == pytest.approx(180.0, abs=1e-6)


def test_lengths_for_180_match_documented_derivations():
    lengths = load_osteometry().lengths_for_stature(1.80, "male_white")
    assert lengths["FEMUR"] == pytest.approx(0.4983, abs=5e-4)
    assert lengths["TIBIA"] == pytest.approx(0.4023, abs=5e-4)
    assert lengths["HUMERUS"] == pytest.approx(0.3557, abs=5e-4)
    assert lengths["RADIUS"] == pytest.approx(0.2672, abs=5e-4)
    assert lengths["ULNA"] == pytest.approx(0.2864, abs=5e-4)
    assert lengths["FIBULA"] == pytest.approx(0.4038, abs=5e-4)
    # Anatomical sanity: femur > tibia > humerus > ulna > radius.
    assert lengths["FEMUR"] > lengths["TIBIA"] > lengths["HUMERUS"] > lengths["ULNA"] > lengths["RADIUS"]


def test_lengths_scale_with_stature_monotonically():
    table = load_osteometry()
    short, tall = table.lengths_for_stature(1.60), table.lengths_for_stature(1.90)
    for bone in LONG_BONES:
        assert short[bone] < tall[bone]


def test_bone_length_helper_and_errors():
    assert bone_length_from_stature("FEMUR", 1.80) == pytest.approx(0.4983, abs=5e-4)
    assert bone_length_from_stature("TIBIA", 1.65, population="female_white") == pytest.approx(0.3568, abs=5e-4)
    with pytest.raises(KeyError):
        bone_length_from_stature("SKULL", 1.80)
    with pytest.raises(KeyError):
        bone_length_from_stature("TIBIA", 1.80, population="child_5y")


def test_unusable_regression_refuses_to_compute():
    reg = LongBoneRegression("TIBIA", None, None, None, "", "female_white", ProvenanceState.UNKNOWN)
    assert not reg.is_usable
    with pytest.raises(ValueError):
        reg.bone_length_cm(170.0)


def test_shaft_diameters_are_labelled_estimate():
    table = load_osteometry()
    assert isinstance(table, OsteometricTable)
    assert table.shaft_diameter_provenance == ProvenanceState.ESTIMATE
    assert set(table.shaft_diameters_m) >= set(LONG_BONES)
