"""Decision 78 (A32): the jaw pivots at the TMJ, the chin stays at 0.87 H, and the node contract does not change."""

import importlib.util
import json
import math
from pathlib import Path

import pytest

from character_engine.domain.character.templates import default_canonical_json
from character_engine.domain.rigging import GAME_BONES
from character_engine.domain.rigging.face import JAW_OPEN_MAX_DEG, jaw_rotation
from character_engine.export.gltf_game import game_skeleton_points

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "src" / "character_engine" / "data" / "anatomy" / "references" / "source_registry.json"
BACKUP = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206_backup.json"


def _mod():
    spec = importlib.util.spec_from_file_location("fix_jaw_atm", ROOT / "scripts" / "fix_jaw_atm.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def data():
    return json.loads(default_canonical_json().read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def mandible(data):
    return next(b for b in data["bones"] if b["canonical_name"] == "MANDIBLE")


def test_head_is_the_tmj_and_tail_the_chin(mandible):
    assert mandible["head"] == {"x": 0.0, "y": -0.0168, "z": 1.6539}
    assert mandible["tail"] == {"x": 0.0, "y": -0.0914, "z": 1.566}
    assert mandible["tail"]["z"] == pytest.approx(0.87 * 1.80)         # PROVEN chin height kept
    assert mandible["tail"]["y"] < mandible["head"]["y"] and mandible["tail"]["z"] < mandible["head"]["z"]


def test_node_contract_does_not_change(data, mandible):
    names = [b["canonical_name"] for b in data["bones"]] + [c["canonical_name"] for c in data.get("containers", [])]
    assert len(set(names)) == 208 and mandible["parent"] == "CRANIUM"
    assert len(GAME_BONES) == 66
    jaw = next(g for g in GAME_BONES if g.name == "jaw")
    assert jaw.parent == "head" and jaw.covers == ("MANDIBLE",)


def test_opening_moves_the_chin_down_and_back_about_the_tmj():
    points = game_skeleton_points(pose="tpose")
    head, tail = points["jaw"]
    v = [tail[i] - head[i] for i in range(3)]
    w, x, y, z = jaw_rotation(points, 1.0)
    u = (x, y, z)
    cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    cross2 = (u[1] * cross[2] - u[2] * cross[1], u[2] * cross[0] - u[0] * cross[2], u[0] * cross[1] - u[1] * cross[0])
    moved = [v[i] + 2 * (w * cross[i] + cross2[i]) for i in range(3)]
    travel = math.dist(v, moved)
    assert moved[2] < v[2]
    assert travel == pytest.approx(2 * math.hypot(*v) * math.sin(math.radians(JAW_OPEN_MAX_DEG) / 2), abs=1e-9)
    assert 0.045 < travel < 0.055                                      # the chin really moves, about 50 mm at 25 degrees


def test_opening_limit_stays_25_degrees():
    assert JAW_OPEN_MAX_DEG == 25.0


def test_script_is_idempotent_and_refuses_the_backup():
    m = _mod()
    original = json.loads(default_canonical_json().read_text(encoding="utf-8"))
    out, changed = m.fix(original)
    assert out == original and not changed
    text = REGISTRY.read_bytes().decode("utf-8")
    assert m.fix_registry(text) == text and '"TMJ_AXIS:' in text
    assert m.main(["--json", str(BACKUP)]) == 2
