"""Decision 74 (A30): skull bones at BodyParts3D positions (ESTIMATE); vertex and mandible unchanged."""

import importlib.util
import json
from pathlib import Path

import pytest

from character_engine.domain.character.templates import default_canonical_json

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206_backup.json"


def _mod():
    spec = importlib.util.spec_from_file_location("fix_skull_positions", ROOT / "scripts" / "fix_skull_positions.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def data():
    return json.loads(default_canonical_json().read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def B(data):
    return {b["canonical_name"]: b for b in data["bones"]}


def _mid(b, k):
    return (b["head"][k] + b["tail"][k]) / 2


def test_vertex_and_mandible_unchanged(B):
    assert B["FRONTAL"]["tail"]["z"] == pytest.approx(1.80)
    assert B["MANDIBLE"]["head"] == {"x": 0.0, "y": 0.0, "z": 1.566}          # chin, 0.87 H (PROVEN), jaw pivot
    assert B["MANDIBLE"]["tail"] == {"x": 0.0, "y": 0.0, "z": 1.5994}


def test_midline_and_mirror(B):
    for n in ("FRONTAL", "OCCIPITAL", "SPHENOID", "ETHMOID", "VOMER", "HYOID"):
        assert B[n]["head"]["x"] == 0.0 and B[n]["tail"]["x"] == 0.0, n
    for base in ("PARIETAL", "TEMPORAL", "MAXILLA", "ZYGOMATIC", "NASAL", "LACRIMAL", "PALATINE", "INFERIOR_NASAL_CONCHA"):
        for end in ("head", "tail"):
            l, r = B[f"{base}_L"][end], B[f"{base}_R"][end]
            assert (r["x"], r["y"], r["z"]) == pytest.approx((-l["x"], l["y"], l["z"]), abs=1e-3), base


def test_anatomical_order(B):
    assert _mid(B["NASAL_L"], "z") < _mid(B["FRONTAL"], "z")                  # the nose is below the forehead
    assert _mid(B["MAXILLA_L"], "z") < _mid(B["NASAL_L"], "z")                # the upper jaw is below the nose
    assert _mid(B["FRONTAL"], "y") < _mid(B["OCCIPITAL"], "y")                # the forehead is in front of the occiput
    assert B["CERVICAL_1"]["head"]["z"] > B["HYOID"]["head"]["z"]             # the hyoid sits below the skull base


def test_fix_is_idempotent_and_refuses_the_backup(data):
    m = _mod()
    again, changed = m.fix(data)
    assert again == data and changed == []
    assert m.main(["--json", str(BACKUP)]) == 2
