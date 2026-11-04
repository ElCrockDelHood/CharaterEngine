"""Finding A23, variant A (Decision 67): hip joint centres 180.2 mm apart (ESTIMATE), knees and the rest unchanged."""

import importlib.util
import json
import math
from pathlib import Path

import pytest

from character_engine.domain.character.templates import default_canonical_json

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206_backup.json"


def _fix_module():
    spec = importlib.util.spec_from_file_location("fix_hip_centres", ROOT / "scripts" / "fix_hip_centres.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def data():
    return json.loads(default_canonical_json().read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def B(data):
    return {b["canonical_name"]: b for b in data["bones"]}


def _p(b, end):
    return (b[end]["x"], b[end]["y"], b[end]["z"])


def test_hip_centre_spacing_and_mirror(B):
    l, r = _p(B["FEMUR_L"], "head"), _p(B["FEMUR_R"], "head")
    assert l == pytest.approx((0.0901, 0.0, 0.954)) and r == pytest.approx((-0.0901, 0.0, 0.954))
    assert math.dist(l, r) == pytest.approx(0.1802, abs=1e-9)


@pytest.mark.parametrize("side,sign", [("L", 1), ("R", -1)])
def test_knees_unchanged_and_femur_oblique(B, side, sign):
    f = B[f"FEMUR_{side}"]
    assert _p(f, "tail") == pytest.approx((sign * 0.0666, 0.0, 0.5362))
    assert sign * (f["head"]["x"] - f["tail"]["x"]) > 0                  # hip lateral to the knee
    tilt = math.degrees(math.atan2(abs(f["head"]["x"] - f["tail"]["x"]), f["head"]["z"] - f["tail"]["z"]))
    assert tilt == pytest.approx(3.22, abs=0.01)
    assert math.dist(_p(f, "head"), _p(f, "tail")) == pytest.approx(0.41846, abs=1e-5)


def test_fix_is_idempotent_and_changes_only_the_femur_heads(data):
    mod = _fix_module()
    again, _ = mod.fix(data)
    assert again == data
    pre = json.loads(json.dumps(data))
    for b in pre["bones"]:
        if b["canonical_name"] in ("FEMUR_L", "FEMUR_R"):
            b["head"]["x"] = 0.0666 if b["canonical_name"].endswith("_L") else -0.0666
    fixed, _ = mod.fix(pre)
    changed = {a["canonical_name"] for a, b in zip(pre["bones"], fixed["bones"]) if a != b}
    assert changed == {"FEMUR_L", "FEMUR_R"} and fixed == data


def test_fix_refuses_the_frozen_backup():
    assert _fix_module().main(["--json", str(BACKUP)]) == 2
