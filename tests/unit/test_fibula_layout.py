"""Finding A21: in the anatomical position the fibula is lateral to the tibia (Decision 65).

Left = +X (Decision 33), so FIBULA_L has the larger x and FIBULA_R the smaller (more negative) x; the fibula sits
beside the tibia in X, not in front of it in Y. The offset (0.0333 m) is the pre-existing PLACEHOLDER moved from −Y
to X (pending FIBULA_INTEROSSEOUS_OFFSET); z values and length are unchanged, the tibia is untouched.
"""

import importlib.util
import json
import math
from pathlib import Path

import pytest

from character_engine.domain.character.templates import default_canonical_json

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206_backup.json"


def _fix_module():
    spec = importlib.util.spec_from_file_location("fix_fibula_layout", ROOT / "scripts" / "fix_fibula_layout.py")
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


@pytest.mark.parametrize("side,lateral", [("L", 1), ("R", -1)])
def test_fibula_is_lateral_to_tibia(B, side, lateral):
    for end in ("head", "tail"):
        f, t = B[f"FIBULA_{side}"][end], B[f"TIBIA_{side}"][end]
        assert lateral * (f["x"] - t["x"]) == pytest.approx(0.0333, abs=1e-6), f"{side} {end}: fibula must be lateral"
        assert f["y"] == pytest.approx(t["y"], abs=1e-9), f"{side} {end}: no antero-posterior offset without a source"


def test_left_and_right_fibula_mirror_exactly(B):
    for end in ("head", "tail"):
        l, r = _p(B["FIBULA_L"], end), _p(B["FIBULA_R"], end)
        assert (r[0], r[1], r[2]) == pytest.approx((-l[0], l[1], l[2]), abs=1e-9)


@pytest.mark.parametrize("side", ["L", "R"])
def test_fibula_length_and_heights_kept(B, side):
    f = B[f"FIBULA_{side}"]
    assert (f["head"]["z"], f["tail"]["z"]) == pytest.approx((0.487, 0.0702), abs=1e-9)
    assert math.dist(_p(f, "head"), _p(f, "tail")) == pytest.approx(0.4168, abs=1e-9)
    assert f["parent"] == f"FEMUR_{side}"
    t = B[f"TIBIA_{side}"]
    assert _p(t, "head") == pytest.approx((0.0666 if side == "L" else -0.0666, 0.0, 0.487))
    assert _p(t, "tail") == pytest.approx((0.0666 if side == "L" else -0.0666, 0.0, 0.0702))


def test_fix_changes_only_the_fibulae_and_is_idempotent(data):
    mod = _fix_module()
    before = json.loads(BACKUP.read_text(encoding="utf-8"))
    current = {b["canonical_name"]: b for b in data["bones"]}
    again, _ = mod.fix(data)
    assert again == data                                         # idempotent on the committed state
    # applied to the pre-A21 layout it changes FIBULA_L/R only (the backup is pre-retarget, so build that state)
    pre = json.loads(json.dumps(data))
    for b in pre["bones"]:
        if b["canonical_name"] in ("FIBULA_L", "FIBULA_R"):
            tib = current[b["canonical_name"].replace("FIBULA", "TIBIA")]
            for end in ("head", "tail"):
                b[end]["x"], b[end]["y"] = tib[end]["x"], -0.0333
    fixed, _ = mod.fix(pre)
    changed = {b["canonical_name"] for b, a in zip(pre["bones"], fixed["bones"]) if a != b}
    assert changed == {"FIBULA_L", "FIBULA_R"} and fixed == data
    assert before["bones"]                                         # backup readable, untouched by the fix


def test_fix_refuses_the_frozen_backup():
    assert _fix_module().main(["--json", str(BACKUP)]) == 2


def test_skeleton_contract_unchanged(data, B):
    assert len(data["bones"]) == 206 and len(data["bones"]) + len(data["containers"]) == 208
    assert not [n for n in B if B[n]["parent"] in ("FIBULA_L", "FIBULA_R")]     # nothing hangs from the fibula
