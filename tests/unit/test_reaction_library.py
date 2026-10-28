"""Reaction library (domain/gameplay/reaction_library.py): ASSUMED rule, hashing, schema of the Godot JSON."""

import copy
import json
from pathlib import Path

import pytest

from character_engine.domain.gameplay.reaction_library import (
    REACTION_CLIPS,
    SCHEMA_VERSION,
    entry_sha256,
    reaction_for,
    summary,
    validate_library,
)

GODOT_JSON = (Path(__file__).resolve().parents[2] / "runtime" / "godot" / "addons" / "character_engine" / "data"
              / "reaction_library_d1.json")


@pytest.mark.parametrize("region, severity, lethality, incap, clip", [
    ("forearm", 2, 0.009, False, "Hit_Chest"),
    ("head", 2, 0.1, False, "Hit_Head"),
    ("neck", 3, 0.2, False, "Hit_Head"),
    ("thorax", 4, 0.3, False, "Hit_Knockback"),
    ("thigh", 2, 0.05, True, "Hit_Knockback"),
    ("thorax", 5, 0.4, False, "Death01"),
    ("abdomen", 3, 0.6, False, "Death01"),
])
def test_reaction_rule(region, severity, lethality, incap, clip):
    assert reaction_for(region, severity, lethality, incap)[0] == clip
    assert clip in REACTION_CLIPS.values()


def _entry(contact=True):
    e = {"id": "x", "attack_clip": "Sword_Attack", "defender_stance": "Sword_Idle", "distance_m": 1.2,
         "distance_provenance": "ESTIMATE", "frames": [0, 1], "signed_distance_m": [0.5, -0.01],
         "min_distance_m": -0.01, "energy_j": None, "energy_basis": "UNKNOWN", "seed": None,
         "provenance": "estimate", "first_contact": None, "wound": None, "reaction": None}
    if contact:
        e["first_contact"] = {"frame": 1, "segment": "forearm.L", "bone": "RADIUS_L", "penetration_m": 0.01,
                              "entry_point": [0, 0, 1]}
        e["wound"] = {"type": "incision", "bone": "RADIUS_L", "region": "forearm", "depth_m": 0.01,
                      "width_m": 0.035, "layers_breached": ["skin"], "severity": 2, "lethality": 0.01,
                      "bleeding_rate": 0.2, "fracture": False, "incapacitating": False, "provenance": "estimate"}
        clip, rule = reaction_for("forearm", 2, 0.01, False)
        e["reaction"] = {"clip": clip, "rule": rule, "provenance": "ASSUMED"}
    else:
        e["signed_distance_m"], e["min_distance_m"] = [0.5, 0.3], 0.3
    e["sha256"] = entry_sha256(e)
    return e


def _doc(*entries):
    return {"schema_version": SCHEMA_VERSION, "sources": [{"file": "a.glb", "sha256": "0" * 64, "licence": "CC0"}],
            "entries": list(entries)}


def test_valid_document_and_summary():
    doc = _doc(_entry(True), {**_entry(False), "id": "y"} | {"sha256": entry_sha256({**_entry(False), "id": "y"})})
    assert validate_library(doc) == []
    assert summary(doc) == {"entries": 2, "contacts": 1, "reactions": {"Hit_Chest": 1}}


def test_tampering_is_detected():
    e = _entry(True)
    bad = copy.deepcopy(e)
    bad["wound"]["severity"] = 5                     # reaction no longer follows the rule, hash broken
    problems = validate_library(_doc(bad))
    assert any("sha256" in p for p in problems) and any("rule" in p for p in problems)


def test_hash_is_stable_and_ignores_its_own_field():
    e = _entry(True)
    assert entry_sha256(e) == entry_sha256(json.loads(json.dumps(e))) == e["sha256"]


@pytest.mark.skipif(not GODOT_JSON.exists(), reason="reaction library not generated yet")
def test_committed_godot_library_is_valid():
    data = json.loads(GODOT_JSON.read_text(encoding="utf-8"))
    assert validate_library(data) == []
    assert summary(data)["entries"] > 0
