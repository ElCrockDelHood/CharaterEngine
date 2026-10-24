"""The Godot runtime consumes a JSON table generated from the Python gameplay domain."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from character_engine.domain.gameplay import (
    SHENMUE_MOVES,
    default_hitboxes,
    gameplay_runtime_table,
    run_scenario,
)
from character_engine.domain.gameplay.runtime_table import SCHEMA, _scenario_scripts

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data" / "gameplay_shenmue.json"


@pytest.fixture(scope="module")
def table():
    return gameplay_runtime_table()


def test_table_covers_every_move_and_hitbox_bone(table):
    assert table["schema"] == SCHEMA
    assert set(table["moves"]) == set(SHENMUE_MOVES)
    bones = set(default_hitboxes())
    for mid, entry in table["moves"].items():
        mv = SHENMUE_MOVES[mid]
        assert entry["startup"] + entry["active"] + entry["recovery"] == mv.total_frames
        assert set(entry["impacts"]) == bones
        for imp in entry["impacts"].values():
            assert 1 <= imp["severity"] <= 6
            assert imp["health_cost"] > 0
            assert imp["provenance"] == "estimate"


def test_reference_scenarios_are_deterministic(table):
    for sc in table["reference_scenarios"]:
        again = run_scenario(next(s for s in _scenario_scripts() if s["scenario_id"] == sc["spec"]["scenario_id"]))
        assert again == sc["expected"]


def test_reference_scenarios_encode_shenmue_rules(table):
    by_id = {sc["spec"]["scenario_id"]: sc["expected"] for sc in table["reference_scenarios"]}
    jab = by_id["jab_lands"]["hits"]
    assert jab and jab[0]["frame"] == SHENMUE_MOVES["jab"].startup + 1 and jab[0]["bone_hit"] == "MANDIBLE"
    assert by_id["guard_blocks_jab"]["hits"][0]["blocked"] is True
    assert by_id["guard_blocks_jab"]["fighters"]["opponent"]["health"] == 100.0
    throw = by_id["throw_beats_guard"]["hits"][0]
    assert throw["move_id"] == "shoulder_throw" and throw["blocked"] is False and throw["knockdown"] is True
    assert by_id["elbow_command"]["hits"][0]["move_id"] == "elbow_assault"   # F F P beats P
    assert by_id["whiff_out_of_reach"]["hits"] == []
    assert any(e["kind"] == "whiff" for e in by_id["whiff_out_of_reach"]["events"])
    assert by_id["autoplay_180"]["fighters"]["opponent"]["health"] < 100.0


def test_committed_json_is_in_sync_with_domain(table):
    assert TABLE.exists(), "run scripts/export_gameplay_data.py"
    committed = json.loads(TABLE.read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(table))   # normalise tuples/enums the same way json does
