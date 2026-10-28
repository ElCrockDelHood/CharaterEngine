"""Reaction library (domain/gameplay/reaction_library.py): ASSUMED rules, parry geometry, hashing, Godot JSON schema."""

import copy
import json
import math
from pathlib import Path

import pytest

from character_engine.domain.gameplay.reaction_library import (
    PARRY_CONTACT_M,
    REACTION_CLIPS,
    SCHEMA_VERSION,
    attacker_reaction_for,
    entry_sha256,
    first_event,
    parry_reaction_for,
    reaction_for,
    segment_distance,
    summary,
    validate_library,
)

GODOT_JSON = (Path(__file__).resolve().parents[2] / "runtime" / "godot" / "addons" / "character_engine" / "data"
              / "reaction_library_d1.json")


@pytest.mark.parametrize("region, severity, lethality, incap, clip, rule", [
    ("forearm", 2, 0.009, False, "Hit_Chest", "body_stagger"),
    ("thorax", 3, 0.1, True, "Hit_Chest", "body_stagger"),        # schema 4: incapacitating torso no longer falls
    ("head", 4, 0.2, True, "Hit_Head", "head_or_neck"),
    ("neck", 3, 0.2, False, "Hit_Head", "head_or_neck"),
    ("thigh", 3, 0.05, True, "Hit_Knockback", "leg_incapacitated_fall"),
    ("thigh", 2, 0.05, False, "Hit_Chest", "body_stagger"),
    ("abdomen", 4, 0.3, False, "Hit_Knockback", "severe"),
    ("thorax", 5, 0.4, False, "Death01", "lethal"),
    ("head", 3, 0.6, False, "Death01", "lethal"),
])
def test_reaction_rule(region, severity, lethality, incap, clip, rule):
    assert reaction_for(region, severity, lethality, incap) == (clip, rule)
    assert clip in REACTION_CLIPS.values()


def test_attacker_rules():
    assert attacker_reaction_for("Sword_Block", "thorax") == ("Sword_Regular_A_Rec", "landed_hit_recovery")
    assert parry_reaction_for("Sword_Block") == ("Hit_Chest", "parried_recoil")


def test_segment_distance():
    d, mid = segment_distance((0, 0, 0), (1, 0, 0), (0.5, 1, 0), (0.5, -1, 0))   # crossing segments
    assert d == pytest.approx(0.0) and mid == pytest.approx((0.5, 0.0, 0.0))
    d, _ = segment_distance((0, 0, 0), (1, 0, 0), (0, 0, 0.3), (1, 0, 0.3))      # parallel, 0.3 apart
    assert d == pytest.approx(0.3)
    d, _ = segment_distance((0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0))          # collinear, end gap
    assert d == pytest.approx(1.0)
    d, _ = segment_distance((0, 0, 0), (0, 0, 0), (0, 1, 0), (0, 1, 0))          # two points
    assert d == pytest.approx(1.0)
    d, _ = segment_distance((0, 0, 0), (1, 1, 0), (1, 0, 1), (0, 1, 1))
    assert d == pytest.approx(1.0) and math.isfinite(d)


def test_first_event_order():
    assert first_event([0, 1, 2], [0.5, -0.01, 0.2], [1.0, 1.0, 0.0]) == ("body_hit", 1)
    assert first_event([0, 1, 2], [0.5, 0.3, -0.1], [1.0, 0.02, 1.0]) == ("parry", 1)
    assert first_event([0, 1], [0.5, -0.01], [1.0, PARRY_CONTACT_M]) == ("parry", 1)      # tie: blade met first
    assert first_event([0, 1], [0.5, 0.4], [1.0, 0.9]) == ("none", None)


def _base(eid="x"):
    return {"id": eid, "attack_clip": "Sword_Attack", "defender_stance": "Sword_Idle", "distance_m": 1.2,
            "distance_provenance": "ESTIMATE", "frames": [0, 1], "signed_distance_m": [0.5, 0.3],
            "blade_distance_m": [1.0, 0.8], "min_distance_m": 0.3, "event": "none", "first_contact": None,
            "first_parry": None, "wound": None, "reaction": None, "reaction_playback": None, "parry_playback": None,
            "energy_j": None, "energy_basis": "UNKNOWN", "seed": None, "provenance": "estimate"}


def _hit(eid="hit"):
    e = _base(eid)
    e.update(signed_distance_m=[0.5, -0.01], min_distance_m=-0.01, event="body_hit")
    e["first_contact"] = {"frame": 1, "segment": "forearm.L", "bone": "RADIUS_L", "penetration_m": 0.01,
                          "entry_point": [0, 0, 1]}
    e["wound"] = {"type": "incision", "bone": "RADIUS_L", "region": "forearm", "depth_m": 0.01, "width_m": 0.035,
                  "layers_breached": ["skin"], "severity": 2, "lethality": 0.01, "bleeding_rate": 0.2,
                  "fracture": False, "incapacitating": False, "provenance": "estimate"}
    clip, rule = reaction_for("forearm", 2, 0.01, False)
    e["reaction"] = {"clip": clip, "rule": rule, "provenance": "ASSUMED"}
    e["reaction_playback"] = {"start_frame": 1, "clip": clip, "blend_in_frames": 4, "frames": [1, 2, 3],
                              "signed_distance_m": [-0.01, 0.02, 0.2], "separated_at_frame": 2,
                              "max_penetration_after_m": 0.0, "penetrating_at_end": False,
                              "wound_bone_consistent_ratio": 1.0, "provenance": "ASSUMED",
                              "attacker_reaction": {"clip": "Sword_Regular_A_Rec", "rule": "landed_hit_recovery",
                                                    "starts_frame": 2, "blend_in_frames": 4,
                                                    "provenance": "ASSUMED"}}
    e["sha256"] = entry_sha256(e)
    return e


def _parry(eid="parry", reached=False):
    e = _base(eid)
    e.update(blade_distance_m=[1.0, 0.02], event="parry")
    e["first_parry"] = {"frame": 1, "blade_distance_m": 0.02, "point": [0, -0.5, 1.2]}
    e["parry_playback"] = {"start_frame": 1, "attacker_clip": "Hit_Chest", "rule": "parried_recoil",
                           "blend_in_frames": 4, "frames": [1, 2], "signed_distance_m": [0.3, -0.01 if reached else 0.4],
                           "body_reached_after_parry": reached, "provenance": "ASSUMED"}
    e["sha256"] = entry_sha256(e)
    return e


def _none(eid="none"):
    e = _base(eid)
    e["sha256"] = entry_sha256(e)
    return e


def _doc(*entries):
    return {"schema_version": SCHEMA_VERSION, "sources": [{"file": "a.glb", "sha256": "0" * 64, "licence": "CC0"}],
            "entries": list(entries)}


def test_valid_document_and_summary():
    doc = _doc(_hit(), _parry(), _parry("p2", reached=True), _none())
    assert validate_library(doc) == []
    assert summary(doc) == {"entries": 4, "body_hits": 1, "parries": 2, "reactions": {"Hit_Chest": 1},
                            "parries_reaching_body_after": 1}


@pytest.mark.parametrize("mutate, message", [
    (lambda e: e["wound"].__setitem__("severity", 5), "rule"),
    (lambda e: e["reaction_playback"].__setitem__("start_frame", 0), "first contact"),
    (lambda e: e["reaction_playback"]["attacker_reaction"].__setitem__("starts_frame", 1), "frame after contact"),
    (lambda e: e["reaction_playback"].__setitem__("blend_in_frames", -1), "blend_in_frames"),
    (lambda e: e.__setitem__("event", "parry"), "does not match"),
])
def test_body_hit_tampering_is_detected(mutate, message):
    e = _hit()
    mutate(e)
    e["sha256"] = entry_sha256(e)
    assert any(message in p for p in validate_library(_doc(e)))


def test_parry_rules():
    e = _parry()
    e["wound"] = {"type": "incision"}
    e["sha256"] = entry_sha256(e)
    assert any("no wound" in p for p in validate_library(_doc(e)))
    e2 = _parry()
    e2["parry_playback"]["body_reached_after_parry"] = True
    e2["sha256"] = entry_sha256(e2)
    assert any("inconsistent" in p for p in validate_library(_doc(e2)))


def test_hash_detects_changes_and_ignores_its_own_field():
    e = _hit()
    assert entry_sha256(e) == entry_sha256(json.loads(json.dumps(e))) == e["sha256"]
    bad = copy.deepcopy(e)
    bad["distance_m"] = 1.3
    assert any("sha256" in p for p in validate_library(_doc(bad)))


@pytest.mark.skipif(not GODOT_JSON.exists(), reason="reaction library not generated yet")
def test_committed_godot_library_is_valid():
    data = json.loads(GODOT_JSON.read_text(encoding="utf-8"))
    assert validate_library(data) == []
    assert summary(data)["entries"] > 0
