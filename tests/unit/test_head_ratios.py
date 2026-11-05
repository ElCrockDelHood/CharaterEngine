"""Decision 75 (A31): head width and depth ratios from ANSUR II (DERIVED), registered source, idempotent script."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "src" / "character_engine" / "data" / "anatomy" / "references"


def _ratio(key):
    def walk(o):
        if isinstance(o, dict):
            if key in o:
                return o[key]
            for v in o.values():
                r = walk(v)
                if r is not None:
                    return r
        return None
    return walk(json.loads((REF / "anthropometry.json").read_text(encoding="utf-8")))


@pytest.mark.parametrize("key,value,lo,hi,mm", [("head_width_ratio", 0.0862, 0.0809, 0.092, 155.2),
                                                ("head_depth_ratio", 0.1121, 0.1059, 0.1183, 201.8)])
def test_ratios_come_from_ansur_ii(key, value, lo, hi, mm):
    r = _ratio(key)
    assert r["value"] == value and r["range"] == [lo, hi]
    assert r["provenance"] == "DERIVED" and r["source_id"] == "ANSUR_II_2012" and "n = 1814" in r["notes"]
    assert r["value"] * 1800 == pytest.approx(mm, abs=0.1)


def test_source_is_registered_with_its_population():
    reg = json.loads((REF / "source_registry.json").read_text(encoding="utf-8"))
    text = json.dumps(reg)
    assert '"id": "ANSUR_II_2012"' in text and "not the civilian population" in text


def test_script_is_idempotent():
    spec = importlib.util.spec_from_file_location("fix_head_ratios", ROOT / "scripts" / "fix_head_ratios.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    a = (REF / "anthropometry.json").read_bytes().decode("utf-8")
    r = (REF / "source_registry.json").read_bytes().decode("utf-8")
    assert m.fix_anthropometry(a) == a and m.fix_registry(r) == r
