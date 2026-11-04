"""Region-by-region skeleton comparison (F2, A22) on synthetic data and the canonical bone list."""

import math

import pytest

from character_engine.domain.assets.skeleton_regions import (
    GLOBAL_ANCHORS,
    REGIONS,
    all_region_bones,
    anchor_targets,
    bone_metrics,
    end_centroid,
    pelvis_dimensions,
    pelvis_landmarks,
    point_segment_distance,
    region_summary,
)
from character_engine.domain.character.templates import load_canonical_bones


def test_regions_cover_the_206_canonical_bones_once():
    bones, _ = load_canonical_bones()
    names = [b["canonical_name"] for b in bones]
    covered = all_region_bones()
    assert len(covered) == len(set(covered)) == 206
    assert set(covered) == set(names)
    assert set(REGIONS) == {"pelvis", "spine", "thorax", "shoulder_girdle", "arm", "hand", "leg", "foot", "skull"}


def test_global_anchors_are_the_measured_limb_joints():
    bones, _ = load_canonical_bones()
    joints = {b["canonical_name"]: (tuple(b["head"].values()), tuple(b["tail"].values())) for b in bones}
    targets = anchor_targets(joints)
    assert len(GLOBAL_ANCHORS) == len(targets) == 8
    assert targets[0] == joints["FEMUR_L"][0] and targets[1] == joints["FEMUR_L"][1]


def test_point_segment_distance():
    assert point_segment_distance((0, 1, 0), (0, 0, 0), (0, 0, 1)) == pytest.approx(1.0)
    assert point_segment_distance((0, 0, 3), (0, 0, 0), (0, 0, 1)) == pytest.approx(2.0)


def _rod(head, tail, n=50, r=0.005):
    pts = []
    for i in range(n + 1):
        t = i / n
        c = tuple(h + (b - h) * t for h, b in zip(head, tail))
        for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
            pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2]))
    return pts


def test_bone_metrics_zero_for_a_mesh_on_its_segment():
    head, tail = (0.1, 0.0, 1.0), (0.1, 0.0, 0.6)
    m = bone_metrics(_rod(head, tail), head, tail)
    assert m["centroid_to_segment_mm"] == pytest.approx(0.0, abs=1e-9)
    assert m["extent_over_length"] == pytest.approx(1.0)
    assert m["axis_angle_deg"] == pytest.approx(0.0, abs=1e-6)
    assert m["head_error_mm"] < 25 and m["tail_error_mm"] < 25        # end slices are 10 % of 400 mm


def test_bone_metrics_see_a_shift():
    head, tail = (0.1, 0.0, 1.0), (0.1, 0.0, 0.6)
    shifted = [(x, y - 0.0333, z) for x, y, z in _rod(head, tail)]
    m = bone_metrics(shifted, head, tail)
    assert m["centroid_to_segment_mm"] == pytest.approx(33.3, abs=1e-6)
    assert m["centroid_minus_midpoint_mm"][1] == pytest.approx(-33.3, abs=1e-6)


def test_end_centroid_uses_at_least_three_points():
    pts = [(0, 0, 0), (0, 0, 1), (0, 0, 2), (0, 0, 3)]
    assert end_centroid(pts, (0, 0, 1), "head", 0.0) == pytest.approx((0, 0, 1))
    assert end_centroid(pts, (0, 0, 1), "tail", 0.0) == pytest.approx((0, 0, 2))


def test_region_summary_removes_the_common_shift():
    metrics = {b: {"centroid_to_segment_mm": 50.0, "centroid_minus_midpoint_mm": [0.0, 50.0, 0.0],
                   "head_error_mm": 50.0, "tail_error_mm": 50.0, "extent_over_length": 1.0, "axis_angle_deg": 0.0}
               for b in ("A", "B")}
    s = region_summary(metrics, ("A", "B", "C"))
    assert s["missing"] == ["C"] and s["fitted"] == 2
    assert s["mean_centroid_shift_mm"] == pytest.approx([0.0, 50.0, 0.0])
    assert s["centroid_to_midpoint_after_region_shift_mm"]["max"] == pytest.approx(0.0)


def test_pelvis_landmarks_on_a_synthetic_pair():
    def coxal(sign):
        # anterior spine at -Y top, posterior at +Y top, medial pubis at the bottom towards x = 0
        return [(sign * 0.12, -0.10, 1.00), (sign * 0.10, 0.05, 1.00), (sign * 0.02, -0.06, 0.80),
                (sign * 0.10, 0.0, 0.90), (sign * 0.13, 0.0, 0.85)]
    lm = pelvis_landmarks(coxal(1.0), coxal(-1.0))
    assert lm["asis_L"] == (0.12, -0.10, 1.00) and lm["psis_R"] == (-0.10, 0.05, 1.00)
    assert lm["pubic_symphysis"] == pytest.approx((0.0, -0.06, 0.80))
    d = pelvis_dimensions(lm, (0.09, -0.02, 0.88), (-0.09, -0.02, 0.88))
    assert d["inter_asis_width_mm"] == pytest.approx(240.0)
    assert d["inter_hip_centre_width_mm"] == pytest.approx(180.0)
    assert d["pelvic_depth_asis_psis_mm"] == pytest.approx(150.0)
