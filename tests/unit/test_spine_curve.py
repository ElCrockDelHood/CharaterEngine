"""Decision 71 (A26): the canonical spine follows the BodyParts3D sagittal curves (ESTIMATE); z and x unchanged."""

import importlib.util
import json
from pathlib import Path

import pytest

from character_engine.domain.character.templates import default_canonical_json

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206_backup.json"
VERT = [f"CERVICAL_{i}" for i in range(1, 8)] + [f"THORACIC_{i}" for i in range(1, 13)] + [f"LUMBAR_{i}" for i in range(1, 6)]


def _mod():
    spec = importlib.util.spec_from_file_location("fix_spine_curve", ROOT / "scripts" / "fix_spine_curve.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def data():
    return json.loads(default_canonical_json().read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def B(data):
    return {b["canonical_name"]: b for b in data["bones"]}


def _mid_y(b):
    return (b["head"]["y"] + b["tail"]["y"]) / 2


def test_curves_have_the_right_signs(B):
    assert min(_mid_y(B[f"CERVICAL_{i}"]) for i in range(3, 8)) < -0.004          # cervical lordosis (anterior)
    assert max(_mid_y(B[f"THORACIC_{i}"]) for i in range(1, 13)) > 0.025          # thoracic kyphosis (posterior)
    assert min(_mid_y(B[f"LUMBAR_{i}"]) for i in range(1, 6)) < -0.025            # lumbar lordosis (anterior)


def test_x_z_and_neighbours_unchanged(B):
    for n in VERT:
        assert B[n]["head"]["x"] == 0.0 and B[n]["tail"]["x"] == 0.0
    assert (B["CERVICAL_1"]["head"]["z"], B["LUMBAR_5"]["tail"]["z"]) == pytest.approx((1.5516, 1.1808))
    for n in ("SACRUM", "COCCYX"):
        assert B[n]["head"]["y"] == 0.0 and B[n]["tail"]["y"] == 0.0
    assert B["STERNUM"]["head"] == {"x": 0.0, "y": -0.0666, "z": 1.4868}


def test_chain_is_continuous_at_each_disc(B):
    for a, b in zip(VERT, VERT[1:]):
        assert B[a]["tail"]["y"] == pytest.approx(B[b]["head"]["y"], abs=1e-4)


def test_fix_is_idempotent_and_refuses_the_backup(data):
    m = _mod()
    again, _ = m.fix(data)
    assert again == data
    assert m.main(["--json", str(BACKUP)]) == 2
