"""Decision 73 (A28): sternum and ribs from BodyParts3D (ESTIMATE); sternum head, clavicle and shoulders unchanged."""

import importlib.util
import json
import math
from pathlib import Path

import pytest

from character_engine.domain.character.templates import default_canonical_json

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206_backup.json"


def _mod():
    spec = importlib.util.spec_from_file_location("fix_thorax", ROOT / "scripts" / "fix_thorax.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def data():
    return json.loads(default_canonical_json().read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def B(data):
    return {b["canonical_name"]: b for b in data["bones"]}


def _p(b, end):
    return (b[end]["x"], b[end]["y"], b[end]["z"])


def test_sternum_runs_from_the_jugular_notch_to_the_xiphoid(B):
    st = B["STERNUM"]
    assert _p(st, "head") == pytest.approx((0.0, -0.0666, 1.4868))           # unchanged: SC joint of A24 stays put
    assert _p(st, "tail") == pytest.approx((0.0, -0.1381, 1.318))
    assert math.dist(_p(st, "head"), _p(st, "tail")) == pytest.approx(0.1833, abs=1e-3)
    assert st["parent"] == "THORACIC_1"


def test_clavicle_still_sits_at_the_sternum_top(B):
    for side in "LR":
        assert math.dist(_p(B[f"CLAVICLE_{side}"], "head"), _p(B["STERNUM"], "head")) < 0.03
        assert B[f"CLAVICLE_{side}"]["parent"] == "STERNUM"


@pytest.mark.parametrize("i", range(1, 13))
def test_ribs_start_at_their_vertebra_and_mirror(B, i):
    l, r, t = B[f"RIB_{i:02d}_L"], B[f"RIB_{i:02d}_R"], B[f"THORACIC_{i}"]
    assert l["parent"] == f"THORACIC_{i}"
    mid = tuple((a + b) / 2 for a, b in zip(_p(t, "head"), _p(t, "tail")))
    assert math.dist(_p(l, "head"), mid) < 0.05                                 # costovertebral end at the vertebra
    assert l["tail"]["x"] > 0 and l["tail"]["z"] < l["head"]["z"]              # lateral and descending
    assert l["tail"]["y"] < l["head"]["y"]                                     # runs forward
    for end in ("head", "tail"):
        a, b = _p(l, end), _p(r, end)
        assert b == pytest.approx((-a[0], a[1], a[2]), abs=1e-9)


def test_chords_follow_the_real_pattern(B):
    chord = {i: math.dist(_p(B[f"RIB_{i:02d}_L"], "head"), _p(B[f"RIB_{i:02d}_L"], "tail")) for i in range(1, 13)}
    assert max(chord, key=chord.get) == 7 and chord[7] == pytest.approx(0.2231, abs=1e-3)
    assert chord[1] < chord[3] < chord[7] and chord[12] < chord[11] < chord[9]
    assert chord[12] == pytest.approx(0.0862, abs=1e-3)                        # floating rib, own rule


def test_fix_is_idempotent_and_refuses_the_backup(data):
    m = _mod()
    again, _ = m.fix(data)
    assert again == data
    assert m.main(["--json", str(BACKUP)]) == 2
