"""Asset manifest validator (F0 of docs/architecture/ASSET_FITTING_PROPOSAL.md, contract PROPOSED).

Synthetic manifests only: no real asset, no download. The canonical node names come from the committed
skeleton (208 nodes, AGENTS.md invariant 4), which this test only reads.
"""

import copy
import hashlib
from pathlib import Path

import pytest

from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.assets import TOLERANCES, validate_manifest, verify_sha256
from character_engine.domain.character.templates import load_canonical_bones

FILE_BYTES = b"synthetic femur bytes"


@pytest.fixture(scope="module")
def nodes():
    bones, containers = load_canonical_bones()
    names = [b["canonical_name"] for b in bones] + [c["canonical_name"] for c in containers]
    assert len(names) == 208
    return names


def _manifest():
    return {
        "asset_id": "femur_synthetic_v1", "file": "FEMUR.glb",
        "sha256": hashlib.sha256(FILE_BYTES).hexdigest(),
        "layer": "bone",
        "parts": [{"mesh": "Femur", "canonical_bone": "FEMUR", "side": "mirror",
                   "anchors": [{"landmark": "femoral_head_centre", "vertex_or_point": [0.0, 0.0, 0.45]},
                               {"landmark": "lateral_epicondyle", "vertex_or_point": [0.04, 0.0, 0.0]},
                               {"landmark": "medial_epicondyle", "vertex_or_point": [-0.04, 0.0, 0.0]}]}],
        "attachments": [{"muscle": "BICEPS_BRACHII", "origin_bone": "SCAPULA", "insertion_bone": "RADIUS"}],
        "source_units": "m", "up": "+Y", "forward": "+Z",
        "licence": "CC BY 4.0", "author": "Synthetic test author", "origin_url": "https://example.org/femur",
        "provenance": "USER_INPUT",
    }


def test_synthetic_example_is_accepted(nodes):
    report = validate_manifest(_manifest(), nodes)
    assert report.ok, report.issues
    assert report.status == "PROPOSED"
    m = report.manifest
    assert m.provenance is ProvenanceState.USER_INPUT and m.unit_scale == 1.0
    assert m.parts[0].target_nodes() == ("FEMUR_L", "FEMUR_R")
    assert verify_sha256(m, FILE_BYTES)
    assert not verify_sha256(m, FILE_BYTES + b"tampered")


@pytest.mark.parametrize("value", ["", "…", "...", "unknown", "TBD", None, 4])
def test_rejects_licence_not_read(nodes, value):
    raw = _manifest()
    raw["licence"] = value
    assert "licence_not_read" in validate_manifest(raw, nodes).codes()


def test_rejects_missing_licence_and_hash(nodes):
    raw = _manifest()
    del raw["licence"], raw["sha256"]
    report = validate_manifest(raw, nodes)
    assert not report.ok and report.manifest is None
    assert {i.path for i in report.issues if i.code == "missing_field"} == {"licence", "sha256"}


@pytest.mark.parametrize("sha", ["", "abc", "Z" * 64, hashlib.sha256(b"x").hexdigest().upper()])
def test_rejects_malformed_hash(nodes, sha):
    raw = _manifest()
    raw["sha256"] = sha
    assert "bad_sha256" in validate_manifest(raw, nodes).codes()


@pytest.mark.parametrize("bone, side, code", [
    ("FEMUR_BONE", "mirror", "unknown_bone"),      # not a canonical node
    ("FEMUR", "midline", "unknown_bone"),          # bilateral bone has no midline node
    ("STERNUM", "L", "unknown_bone"),              # midline bone has no _L node
    ("FEMUR_L", "L", "bone_has_side"),             # side goes in 'side', not in the name
])
def test_rejects_unknown_canonical_bone(nodes, bone, side, code):
    raw = _manifest()
    raw["parts"][0].update(canonical_bone=bone, side=side)
    assert code in validate_manifest(raw, nodes).codes()


@pytest.mark.parametrize("bone, side", [("STERNUM", "midline"), ("FEMUR", "L"), ("FEMUR", "R"),
                                        ("ROOT_SKELETON", "midline")])
def test_accepts_every_valid_side(nodes, bone, side):
    raw = _manifest()
    raw["parts"][0].update(canonical_bone=bone, side=side)
    assert validate_manifest(raw, nodes).ok


@pytest.mark.parametrize("n", [0, 1, 2])
def test_rigid_part_needs_three_anchors(nodes, n):
    raw = _manifest()
    raw["parts"][0]["anchors"] = raw["parts"][0]["anchors"][:n]
    assert "too_few_anchors" in validate_manifest(raw, nodes).codes()


def test_rigid_part_rejects_collinear_anchors(nodes):
    raw = _manifest()
    for k, a in enumerate(raw["parts"][0]["anchors"]):
        a["vertex_or_point"] = [0.0, 0.0, 0.1 * k]
    assert "collinear_anchors" in validate_manifest(raw, nodes).codes()


def test_soft_layer_does_not_need_three_anchors(nodes):
    raw = _manifest()
    raw["layer"] = "skin"
    raw["parts"][0]["anchors"] = []
    assert validate_manifest(raw, nodes).ok


def test_duplicate_or_bad_anchor(nodes):
    raw = _manifest()
    raw["parts"][0]["anchors"][1]["landmark"] = "femoral_head_centre"
    assert "duplicate_anchor" in validate_manifest(raw, nodes).codes()
    raw = _manifest()
    raw["parts"][0]["anchors"][0]["vertex_or_point"] = [0.0, float("nan"), 0.0]
    assert "bad_anchor" in validate_manifest(raw, nodes).codes()


def test_landmark_list_is_optional_until_it_exists(nodes):
    assert validate_manifest(_manifest(), nodes, known_landmarks=None).ok
    report = validate_manifest(_manifest(), nodes, known_landmarks={"femoral_head_centre"})
    assert report.codes().count("unknown_landmark") == 2


def test_muscle_attachments_follow_the_catalogue(nodes):
    raw = _manifest()
    raw["attachments"][0]["insertion_bone"] = "ULNA"
    assert "attachment_mismatch" in validate_manifest(raw, nodes).codes()
    raw["attachments"][0]["muscle"] = "NOT_A_MUSCLE"
    assert "unknown_muscle" in validate_manifest(raw, nodes).codes()
    raw = _manifest()
    raw["layer"], raw["attachments"] = "muscle", []
    assert "missing_attachments" in validate_manifest(raw, nodes).codes()


@pytest.mark.parametrize("key, value, code", [
    ("layer", "cartilage", "bad_layer"), ("source_units", "in", "bad_units"),
    ("up", "Y", "bad_axis"), ("forward", "+Y", "bad_axis"),          # +Y up and +Y forward: not perpendicular
    ("file", "../FEMUR.glb", "bad_file"), ("file", "FEMUR.blend", "bad_file"),
    ("asset_id", "Femur v1", "bad_asset_id"), ("provenance", "MEASURED", "bad_provenance"),
    ("parts", [], "no_parts"), ("origin_url", "…", "origin_not_read"), ("author", "", "author_not_read"),
])
def test_rejects_bad_fields(nodes, key, value, code):
    raw = _manifest()
    raw[key] = value
    assert code in validate_manifest(raw, nodes).codes()


@pytest.mark.parametrize("raw", [None, [], "manifest", 3])
def test_non_object_never_raises(nodes, raw):
    assert validate_manifest(raw, nodes).codes() == ("not_an_object",)


def test_validator_does_not_mutate_input(nodes):
    raw = _manifest()
    before = copy.deepcopy(raw)
    validate_manifest(raw, nodes)
    assert raw == before


def test_tolerances_are_not_approved_values():
    allowed = {ProvenanceState.ESTIMATE, ProvenanceState.UNKNOWN}
    assert all(t.provenance in allowed for t in TOLERANCES.values())
    assert all(t.value is None for t in TOLERANCES.values() if t.provenance is ProvenanceState.UNKNOWN)


def test_manifest_folder_is_outside_the_canonical_fingerprint():
    root = Path(__file__).resolve().parents[2]
    from tests.anatomy.test_contract_fingerprint import ANATOMY_DIR, CONTRACT_FINGERPRINTS
    manifests = root / "assets" / "anatomy" / "manifests"
    assert manifests.is_dir()
    assert ANATOMY_DIR not in manifests.parents
    assert not any("assets" in Path(p).parts for p in CONTRACT_FINGERPRINTS)
