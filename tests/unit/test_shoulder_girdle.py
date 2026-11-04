"""Finding A24, variant A (Decision 68): shoulder joint centres 406.8 mm apart, clavicle SC -> AC, scapula AC -> AI.

Positions only; the hierarchy (CLAVICLE parent ROOT_SKELETON) is unchanged here (topology is a separate step).
"""

import importlib.util
import json
import math
from pathlib import Path

import pytest

from character_engine.domain.anatomy.pose.tpose import apply_tpose
from character_engine.domain.character.templates import default_canonical_json

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206_backup.json"


def _fix_module():
    spec = importlib.util.spec_from_file_location("fix_shoulder_girdle", ROOT / "scripts" / "fix_shoulder_girdle.py")
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


def test_shoulder_joint_spacing(B):
    assert math.dist(_p(B["HUMERUS_L"], "head"), _p(B["HUMERUS_R"], "head")) == pytest.approx(0.4068, abs=1e-9)


@pytest.mark.parametrize("side,sign", [("L", 1), ("R", -1)])
def test_girdle_layout(B, side, sign):
    hum, cla, sca, st = B[f"HUMERUS_{side}"], B[f"CLAVICLE_{side}"], B[f"SCAPULA_{side}"], B["STERNUM"]
    assert _p(hum, "tail") == pytest.approx((sign * 0.2331, 0.0, 1.1566))          # elbow unchanged
    assert (hum["head"]["y"], hum["head"]["z"]) == pytest.approx((0.0, 1.4724))       # shoulder height unchanged
    sc, ac = _p(cla, "head"), _p(cla, "tail")
    assert sign * sc[0] < 0.03 and math.dist(sc, _p(st, "head")) < 0.03            # SC beside the sternum top
    assert sign * ac[0] > sign * sc[0] and ac[1] > sc[1]                            # AC lateral and posterior
    assert _p(sca, "head") == pytest.approx(ac)                                     # scapula starts at the AC joint
    assert _p(sca, "tail")[2] < _p(sca, "head")[2] and _p(sca, "tail")[1] > 0       # inferior angle low, posterior
    assert cla["parent"] == "ROOT_SKELETON" and sca["parent"] == f"CLAVICLE_{side}"  # hierarchy unchanged


def test_left_right_mirror(B):
    for n in ("HUMERUS", "CLAVICLE", "SCAPULA"):
        for end in ("head", "tail"):
            l, r = _p(B[f"{n}_L"], end), _p(B[f"{n}_R"], end)
            assert r == pytest.approx((-l[0], l[1], l[2]), abs=1e-9)


def test_tpose_still_puts_the_oblique_humerus_horizontal(data):
    out = {b["canonical_name"]: b for b in apply_tpose(data["bones"])}
    for side, sign in (("L", 1), ("R", -1)):
        h = out[f"HUMERUS_{side}"]
        assert h["tail"]["z"] == pytest.approx(h["head"]["z"], abs=1e-6)
        assert sign * (h["tail"]["x"] - h["head"]["x"]) > 0.3


def test_fix_is_idempotent_and_refuses_the_backup(data):
    mod = _fix_module()
    again, _ = mod.fix(data)
    assert again == data
    assert mod.main(["--json", str(BACKUP)]) == 2
