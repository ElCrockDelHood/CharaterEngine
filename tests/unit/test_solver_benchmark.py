"""Experiment 0 (scripts/solver_benchmark.py): result schema, run plan and a Blender 3.6 smoke run."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import solver_benchmark as sb  # noqa: E402
from engine_tests import find_blender  # noqa: E402

OK = {"case": "rigid", "size": 10, "frames": 3, "seed": 7, "status": "ok", "provenance": "ESTIMATE",
      "conditions": {"gravity_m_s2": -9.81}, "sim_s_per_frame": 0.01, "replay_s_per_frame": 0.001,
      "render_s": 0.5, "ram_peak_mb": 200.0}


def test_valid_ok_result_has_no_problems():
    assert sb.validate_result(OK) == []


@pytest.mark.parametrize("patch, expected", [
    ({"status": "done"}, "bad status"),
    ({"provenance": "PROVEN"}, "provenance must be ESTIMATE"),
    ({"case": "smoke"}, "unknown case"),
    ({"sim_s_per_frame": -1.0}, "negative sim_s_per_frame"),
])
def test_invalid_results_are_reported(patch, expected):
    assert any(expected in p for p in sb.validate_result({**OK, **patch}))


def test_exceeded_result_needs_no_measurements():
    r = {"case": "fluid", "size": 64, "frames": 48, "seed": 7, "status": "exceeded", "provenance": "ESTIMATE"}
    assert sb.validate_result(r) == []


def test_plan_runs_light_levels_first_and_heavy_last():
    p = sb.plan([0, 1, 2], list(sb.CASES))
    assert [lv for _, _, lv in p] == sorted(lv for _, _, lv in p)
    assert p[-1] == ("fluid", 64, 2)
    assert len(p) == 3 * len(sb.CASES)


@pytest.mark.skipif(find_blender() is None, reason="Blender not installed")
def test_smoke_run_in_blender(tmp_path):
    code = sb.main(["--smoke", "--quiet", "--out-dir", str(tmp_path / "out"), "--render-dir", str(tmp_path / "png")])
    assert code == 0
    summary = json.loads(next((tmp_path / "out").glob("*_solver_benchmark.json")).read_text(encoding="utf-8"))
    assert {r["case"] for r in summary["results"]} == set(sb.CASES)
    for r in summary["results"]:
        assert r["status"] == "ok", r
        assert sb.validate_result(r) == []
        assert r["render_sha256"] and Path(r["render_png"]).exists()
