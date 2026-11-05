"""Decision 72 (A27): vertebral heights from BodyParts3D (ESTIMATE); stature, hips and shoulders unchanged."""

import importlib.util
import json
from pathlib import Path

import pytest

from character_engine.domain.character.templates import default_canonical_json

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206_backup.json"
SPINE = ([f"CERVICAL_{i}" for i in range(1, 8)] + [f"THORACIC_{i}" for i in range(1, 13)]
         + [f"LUMBAR_{i}" for i in range(1, 6)] + ["SACRUM", "COCCYX"])


def _mod():
    spec = importlib.util.spec_from_file_location("fix_spine_heights", ROOT / "scripts" / "fix_spine_heights.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def data():
    return json.loads(default_canonical_json().read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def B(data):
    return {b["canonical_name"]: b for b in data["bones"]}


def test_chain_is_contiguous_and_descends(B):
    for a, b in zip(SPINE, SPINE[1:]):
        assert B[a]["tail"]["z"] == pytest.approx(B[b]["head"]["z"], abs=1e-9), (a, b)
    for n in SPINE:
        assert B[n]["head"]["z"] > B[n]["tail"]["z"], n


def test_regions_have_real_proportions(B):
    span = lambda a, b: B[a]["head"]["z"] - B[b]["tail"]["z"]   # noqa: E731
    assert span("CERVICAL_1", "CERVICAL_7") == pytest.approx(0.1121, abs=1e-4)      # was 0.0302
    assert span("THORACIC_1", "THORACIC_12") == pytest.approx(0.3063, abs=1e-4)     # was 0.1462
    assert B["LUMBAR_4"]["head"]["z"] == pytest.approx(1.1232)                     # ANSUR II iliocristale 1.091 m near L4


def test_stature_hips_shoulders_unchanged(B):
    assert B["FRONTAL"]["tail"]["z"] == pytest.approx(1.80)
    assert B["FEMUR_L"]["head"]["z"] == pytest.approx(0.954)
    assert B["HUMERUS_L"]["head"]["z"] == pytest.approx(1.4724)
    assert B["STERNUM"]["head"]["z"] == pytest.approx(1.4868)


def test_head_pivot_stays_under_the_occipital(B):
    assert B["CERVICAL_1"]["head"]["z"] < B["OCCIPITAL"]["head"]["z"]


def test_fix_is_idempotent_and_refuses_the_backup(data):
    m = _mod()
    again, _ = m.fix(data)
    assert again == data
    assert m.main(["--json", str(BACKUP)]) == 2
