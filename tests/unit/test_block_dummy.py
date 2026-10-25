"""Block dummy (domain/rigging/block_dummy.py): segments over the canonical skeleton, ESTIMATE radii."""

import json
import math
from pathlib import Path

import pytest

from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.rigging import BLOCK_SEGMENTS, ENVELOPE_RADIUS_M, block_placements
from character_engine.domain.rigging.block_dummy import placements_by_name, required_bones

DATA = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"


@pytest.fixture(scope="module")
def points():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    p = lambda d: (d["x"], d["y"], d["z"])  # noqa: E731
    return {b["canonical_name"]: (p(b["head"]), p(b["tail"])) for b in bones}


def _dist(a, b):
    return math.dist(a, b)


def test_segments_cover_body_and_both_sides():
    names = {s.name for s in BLOCK_SEGMENTS}
    assert {"head", "neck", "thorax", "abdomen", "pelvis"} <= names
    for part in ("upper_arm", "forearm", "hand", "thigh", "leg", "foot"):
        assert {f"{part}.L", f"{part}.R"} <= names
    assert len(BLOCK_SEGMENTS) == 17


def test_every_required_bone_exists_in_canonical_skeleton(points):
    assert [b for b in required_bones() if b not in points] == []


def test_capsules_span_their_joints_and_are_estimate(points):
    placements = block_placements(points)
    assert len(placements) == 17
    for p in placements:
        assert p.provenance == ProvenanceState.ESTIMATE
        assert p.radius_m > 0
    head = placements_by_name(placements)["head"]
    # head capsule spans exactly CERVICAL_1 head -> FRONTAL tail (vertex, z 1.80)
    p0, p1 = points["CERVICAL_1"][0], points["FRONTAL"][1]
    assert head.extent_m == pytest.approx(_dist(p0, p1), abs=1e-6)
    assert _dist(head.b, p1) == pytest.approx(head.radius_m, abs=1e-6)
    assert _dist(head.a, p0) == pytest.approx(head.radius_m, abs=1e-6)


def test_left_blocks_are_on_plus_x(points):
    by = placements_by_name(block_placements(points))
    for part in ("upper_arm", "forearm", "hand", "thigh", "leg"):
        assert by[f"{part}.L"].a[0] > 0 > by[f"{part}.R"].a[0]


def test_radius_scales_with_stature(points):
    tall = placements_by_name(block_placements(points, 1.80))
    short = placements_by_name(block_placements(points, 1.62))
    assert short["thorax"].radius_m == pytest.approx(tall["thorax"].radius_m * 0.9, rel=1e-3)
    assert tall["thorax"].radius_m == pytest.approx(ENVELOPE_RADIUS_M[BLOCK_SEGMENTS[2].region])


def test_short_segment_becomes_sphere():
    pts = {b: ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)) for b in required_bones()}
    pts["FRONTAL"] = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.05))
    head = placements_by_name(block_placements(pts))["head"]
    assert head.a == head.b and head.radius_m >= 0.025


def test_missing_bone_is_reported(points):
    broken = dict(points)
    del broken["FEMUR_L"]
    with pytest.raises(KeyError, match="FEMUR_L"):
        block_placements(broken)
    with pytest.raises(ValueError):
        block_placements(points, 0.0)
