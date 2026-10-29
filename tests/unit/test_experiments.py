"""Experiment library (domain/gameplay/experiments.py): grid, bracketing, bisection, record hashing and validation."""

import json
from pathlib import Path

import pytest

from character_engine.domain.gameplay.experiments import (
    EXPERIMENT_SCHEMA_VERSION,
    bisect_threshold,
    bracket,
    grid,
    interpolate_zero,
    record_sha256,
    threshold_from,
    validate_experiments,
)

GODOT_JSON = (Path(__file__).resolve().parents[2] / "runtime" / "godot" / "addons" / "character_engine" / "data"
              / "experiments_d1.json")


def _pt(d, m):
    return {"distance_m": d, "min_signed_distance_m": m, "contact": m <= 0.0, "first_contact_frame": 20 if m <= 0
            else None, "bone": "STERNUM" if m <= 0 else None, "min_frame": 20}


def test_grid():
    g = grid(0.7, 1.1, 10)
    assert len(g) == 10 and g[0] == 0.7 and g[-1] == 1.1
    assert all(b > a for a, b in zip(g, g[1:]))
    with pytest.raises(ValueError):
        grid(1.0, 1.0, 10)


def test_bracket_and_interpolation():
    pts = [_pt(0.7, -0.2), _pt(0.8, -0.1), _pt(0.9, -0.01), _pt(1.0, 0.09)]
    assert bracket(pts) == (0.9, 1.0, True)
    assert bracket([_pt(0.7, 0.1)]) == (None, 0.7, True)
    assert bracket([_pt(0.7, 0.1), _pt(0.8, -0.1), _pt(0.9, 0.2)]) == (0.8, 0.9, False)   # hole below contact
    assert interpolate_zero(0.9, -0.01, 1.0, 0.09) == pytest.approx(0.91)
    assert interpolate_zero(0.9, 0.01, 1.0, 0.09) is None


def test_bisection_converges_on_a_known_threshold():
    steps = bisect_threshold(lambda d: d <= 0.9123, 0.9, 1.0, 0.001)
    assert all(abs(b[0] - a[0]) <= 0.05 for a, b in zip(steps, steps[1:]))
    pts = [_pt(0.9, -0.01), _pt(1.0, 0.09)]
    sp = [_pt(d, -0.001 if c else 0.001) for d, c in steps]
    t = threshold_from(pts, sp)
    assert t["contact_up_to_m"] <= 0.9123 < t["no_contact_from_m"]
    assert t["width_m"] <= 0.001


def _record():
    pts = [_pt(0.7, -0.2), _pt(0.8, -0.1), _pt(0.9, -0.01), _pt(1.0, 0.09)]
    steps = [_pt(0.95, 0.04)]
    r = {"id": "exp001", "title": "t", "question": "q", "conditions": {"sources": [{"file": "a.glb"}]},
         "grid": pts, "bisection": {"tolerance_m": 0.05, "steps": steps},
         "threshold": dict(threshold_from(pts, steps), interpolated_m=0.91), "provenance": "estimate",
         "limitations": []}
    r["sha256"] = record_sha256(r)
    return r


def test_valid_record_and_tampering():
    doc = {"schema_version": EXPERIMENT_SCHEMA_VERSION, "experiments": [_record()]}
    assert validate_experiments(doc) == []
    bad = _record()
    bad["grid"][2]["contact"] = False
    bad["sha256"] = record_sha256(bad)
    assert any("inconsistent" in p for p in validate_experiments({"schema_version": 1, "experiments": [bad]}))
    bad = _record()
    bad["threshold"]["contact_up_to_m"] = 0.95
    bad["sha256"] = record_sha256(bad)
    assert any("does not follow" in p for p in validate_experiments({"schema_version": 1, "experiments": [bad]}))
    bad = _record()
    bad["question"] = "changed"
    assert any("sha256" in p for p in validate_experiments({"schema_version": 1, "experiments": [bad]}))


@pytest.mark.skipif(not GODOT_JSON.exists(), reason="experiments not generated yet")
def test_committed_experiments_are_valid():
    data = json.loads(GODOT_JSON.read_text(encoding="utf-8"))
    assert validate_experiments(data) == []
