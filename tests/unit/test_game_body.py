"""Block body on the CE-GAME-v1 game rig (Souls arena visuals): placements and the committed Blender export."""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.rigging import GAME_BONES
from character_engine.domain.rigging.game_body import GAME_BODY_SEGMENTS, body_spec, game_body_placements
from character_engine.export.gltf_game import game_skeleton_points

ROOT = Path(__file__).resolve().parents[2]
BODY = ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data" / "human_game_v1_body.glb"
GAME_NAMES = {g.name for g in GAME_BONES}


def _glb(path: Path):
    data = path.read_bytes()
    n = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + n]), data[20 + n + 8:]


def test_one_capsule_per_segment_on_game_bones_above_the_ground():
    caps = game_body_placements(game_skeleton_points(pose="tpose"))
    assert len(caps) == len(GAME_BODY_SEGMENTS) == 56
    assert {c.weight_bone for c in caps} <= GAME_NAMES and len({c.weight_bone for c in caps}) == 56
    assert min(min(c.a[2], c.b[2]) - c.radius_m for c in caps) >= -1e-9
    assert {c.provenance for c in caps} <= {ProvenanceState.ESTIMATE, ProvenanceState.ASSUMED}
    assert all(c.radius_m > 0 for c in caps)


def test_body_scales_with_stature():
    pts = game_skeleton_points(pose="tpose")
    big = {c.weight_bone: c.radius_m for c in game_body_placements(pts, 1.80)}
    small = {c.weight_bone: c.radius_m for c in game_body_placements(pts, 1.62)}
    assert small["spine_03"] < big["spine_03"]


def test_committed_blender_body_is_in_sync_skinned_and_clean():
    assert BODY.exists(), "run scripts/bake_game_body.py (Blender 3.6)"
    doc, binary = _glb(BODY)
    sha = hashlib.sha256(json.dumps(body_spec(game_skeleton_points(pose="tpose")), sort_keys=True).encode()).hexdigest()
    stamped = [n["extras"]["ce_body_spec_sha256"] for n in doc["nodes"] if "ce_body_spec_sha256" in n.get("extras", {})]
    assert stamped == [sha], "human_game_v1_body.glb is stale: re-run scripts/bake_game_body.py"
    assert len(doc["skins"]) == 1 and len(doc["skins"][0]["joints"]) == 66
    assert {doc["nodes"][j]["name"] for j in doc["skins"][0]["joints"]} == GAME_NAMES
    assert len(doc["meshes"]) == 1 and not doc.get("animations")
    prim = doc["meshes"][0]["primitives"][0]
    assert "JOINTS_1" not in prim["attributes"] and not prim.get("targets")      # <= 4 influences, no shape keys
    acc = doc["accessors"][prim["attributes"]["POSITION"]]
    view = doc["bufferViews"][acc["bufferView"]]
    off = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    xyz = struct.unpack_from(f"<{acc['count'] * 3}f", binary, off)
    assert acc["count"] > 1000 and all(math.isfinite(v) for v in xyz)
    assert min(xyz[1::3]) >= -1e-4                                               # glTF Y-up: nothing below ground
