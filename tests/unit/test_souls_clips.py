"""Souls-like placeholder clips (STYLE-SOULS-001 step 4): spec, frame lengths, and the committed Blender bake."""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import pytest

from character_engine.domain.animation.souls_clips import (
    DIRECTIONS,
    PROBE_BONES,
    SOULS_CLIPS,
    STANCE,
    clip_for,
    clip_reference,
)
from character_engine.domain.gameplay.souls import SOULS_MOVES, SOULS_TUNING
from character_engine.domain.rigging import GAME_BONES
from character_engine.export.gltf_game import game_skeleton_points

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data"
GAME_NAMES = {g.name for g in GAME_BONES}


def _glb_json(path: Path) -> dict:
    data = path.read_bytes()
    n = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + n])


def test_clip_set_and_lengths_follow_the_python_frame_data():
    assert set(SOULS_CLIPS) == {"idle", "walk", "guard", "light_1", "light_2", "light_3", "heavy", "dodge", "hit",
                                "stagger", "windup"}
    light, heavy = SOULS_MOVES["staff_light"], SOULS_MOVES["staff_heavy"]
    for i in (1, 2, 3):
        assert SOULS_CLIPS[f"light_{i}"].frames == light.startup + light.active + light.recovery
    assert SOULS_CLIPS["heavy"].frames == heavy.startup + heavy.active + heavy.recovery
    assert SOULS_CLIPS["dodge"].frames == SOULS_TUNING["dodge_frames"]
    assert SOULS_CLIPS["stagger"].frames == SOULS_TUNING["stagger_frames"]
    assert SOULS_CLIPS["hit"].frames == light.hitstun
    assert SOULS_CLIPS["windup"].frames == SOULS_TUNING["telegraph_frames"]
    for c in SOULS_CLIPS.values():
        frames = [f for f, _ in c.keys]
        assert frames == sorted(frames) and frames[0] == 0 and frames[-1] == c.frames, c.clip_id
        for _, pose in c.keys:
            assert set(pose) <= GAME_NAMES and all(d in DIRECTIONS for d, _ in pose.values())
    assert set(STANCE) <= GAME_NAMES


def test_strike_key_lands_on_the_first_active_frame():
    light = SOULS_MOVES["staff_light"]
    strike_frames = [f for f, pose in SOULS_CLIPS["light_1"].keys if pose.get("upperarm_r", ("", 0))[0] == "forward"]
    assert strike_frames[0] == light.startup + 1


def test_state_to_clip_mapping():
    assert clip_for("startup", "staff_light", 2) == "light_2"
    assert clip_for("recovery", "staff_heavy", 0) == "heavy"
    assert clip_for("dodge") == "dodge" and clip_for("hitstun") == "hit" and clip_for("stagger") == "stagger"
    assert clip_for("guard") == "guard" and clip_for("walk") == "walk" and clip_for("idle") == "idle"
    assert clip_for("telegraph") == "windup"


def test_light_strike_points_the_arm_forward():
    ref = clip_reference(game_skeleton_points(pose="tpose"))
    key = next(k for k in ref["clips"]["light_1"]["keys"] if k["frame"] == SOULS_MOVES["staff_light"].startup + 1)
    assert key["directions"]["upperarm_r"][1] < -0.9                  # -Y forward
    for k in ref["clips"]["idle"]["keys"]:
        for b in PROBE_BONES:
            assert math.hypot(*k["directions"][b]) == pytest.approx(1.0)


def test_committed_json_is_in_sync():
    text = json.dumps(clip_reference(game_skeleton_points(pose="tpose")), indent=2, sort_keys=True) + "\n"
    assert (DATA / "souls_clips.json").read_text(encoding="utf-8") == text, "run scripts/export_souls_clips.py"


def test_committed_blender_bake_matches_the_spec_and_has_game_bones_only():
    glb = DATA / "souls_clips.glb"
    assert glb.exists(), "run scripts/bake_souls_clips.py (Blender 3.6)"
    doc = _glb_json(glb)
    sha = hashlib.sha256((DATA / "souls_clips.json").read_bytes()).hexdigest()
    shas = [n["extras"]["ce_clips_spec_sha256"] for n in doc["nodes"] if "ce_clips_spec_sha256" in n.get("extras", {})]
    assert shas == [sha], "souls_clips.glb is stale: re-bake with scripts/bake_souls_clips.py"
    assert len(doc["skins"]) == 1 and len(doc["skins"][0]["joints"]) == 66
    assert not any(p.get("targets") for m in doc.get("meshes", []) for p in m["primitives"])   # no shape keys
    acc = doc["accessors"]
    names = {a["name"]: a for a in doc["animations"]}
    assert set(names) == set(SOULS_CLIPS)
    for cid, anim in names.items():
        assert {doc["nodes"][c["target"]["node"]]["name"] for c in anim["channels"]} <= GAME_NAMES
        t_end = max(acc[s["input"]]["max"][0] for s in anim["samplers"])
        assert t_end * 60 == pytest.approx(SOULS_CLIPS[cid].frames, abs=1e-3), cid
