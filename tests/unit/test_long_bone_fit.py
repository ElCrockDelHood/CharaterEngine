"""Long-bone anchor rules and derived targets (F2, A20) on synthetic meshes only."""

import math

import pytest

from character_engine.domain.assets.long_bone_fit import (
    RULES,
    axial_extent,
    canonical_lateral,
    derive_targets,
    end_point,
    extract_anchors,
)
from character_engine.domain.assets.registration import register, spread_ratio


def _bone(length=0.40, head_r=0.022, width=0.08, n=24):
    """Synthetic left long bone, Z-up: shaft points, a spherical head (proximal, medial = -X) and a wide distal end."""
    pts = []
    for k in range(n + 1):
        z = 0.05 + length * k / n
        for j in range(n):
            a = 2 * math.pi * j / n
            pts.append((0.012 * math.cos(a), 0.012 * math.sin(a), z))
    c = (-0.03, 0.0, 0.05 + length)
    for i in range(1, n):
        th = math.pi * i / n
        for j in range(n):
            ph = 2 * math.pi * j / n
            pts.append((c[0] + head_r * math.sin(th) * math.cos(ph), c[1] + head_r * math.sin(th) * math.sin(ph),
                        c[2] + head_r * math.cos(th)))
    for j in range(n):
        a = 2 * math.pi * j / n
        pts.append((width / 2 * math.cos(a), 0.02 * math.sin(a), 0.03))
    return pts, c


def test_every_rule_has_three_or_more_unique_anchor_names():
    for bone, rule in RULES.items():
        names = rule.anchor_names()
        assert len(names) >= 3 and len(set(names)) == len(names), bone
        assert all(n == n.lower() and " " not in n for n in names)


def test_femur_rule_is_the_a19_rule():
    f = RULES["FEMUR"]
    head = f.proximal.joint
    assert (head.kind, head.end, head.fraction, head.half) == ("sphere", "proximal", 0.12, "medial")
    lat, med = f.distal.pair
    assert (lat.kind, lat.fraction, lat.direction, med.direction) == ("extreme", 0.10, (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0))
    assert f.anchor_names() == ("femoral_head_centre", "femoral_lateral_epicondyle", "femoral_medial_epicondyle")


def test_sphere_anchor_recovers_the_head_centre():
    pts, c = _bone()
    anchors, info = extract_anchors(RULES["FEMUR"], pts, "L")
    assert anchors["femoral_head_centre"] == pytest.approx(c, abs=1e-9)
    assert info["femoral_head_centre"]["radius_mm"] == pytest.approx(22.0, abs=1e-6)
    assert anchors["femoral_lateral_epicondyle"][0] == pytest.approx(0.04)
    assert anchors["femoral_medial_epicondyle"][0] == pytest.approx(-0.04)


@pytest.mark.parametrize("bone", list(RULES))
def test_right_side_is_the_exact_mirror_of_the_left(bone):
    pts, _ = _bone()
    left, _ = extract_anchors(RULES[bone], pts, "L")
    right, _ = extract_anchors(RULES[bone], [(-x, y, z) for x, y, z in pts], "R")
    for name, p in left.items():
        assert right[name] == pytest.approx((-p[0], p[1], p[2]), abs=1e-12)


def test_canonical_lateral_is_perpendicular_and_signed():
    head, tail = (0.0666, 0.0, 0.954), (0.0666, 0.0, 0.5362)
    assert canonical_lateral(head, tail, "L") == pytest.approx((1.0, 0.0, 0.0))
    assert canonical_lateral(head, tail, "R") == pytest.approx((-1.0, 0.0, 0.0))
    oblique = canonical_lateral((0.0, 0.0, 1.0), (0.1, 0.0, 0.0), "L")
    axis = (-0.1, 0.0, 1.0)
    assert sum(a * b for a, b in zip(oblique, axis)) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("bone", list(RULES))
def test_targets_keep_head_and_tail_and_register(bone):
    rule = RULES[bone]
    pts, _ = _bone()
    anchors, _ = extract_anchors(rule, pts, "L")
    head, tail = (0.0666, 0.0, 0.954), (0.0666, 0.0, 0.5362)
    targets, prov = derive_targets(rule, anchors, head, tail, "L")
    assert set(targets) == set(rule.anchor_names()) == set(prov)
    mid = lambda e: end_point(e, targets)   # noqa: E731
    assert mid(rule.proximal) == pytest.approx(head, abs=1e-12)
    assert mid(rule.distal) == pytest.approx(tail, abs=1e-12)
    names = rule.anchor_names()
    if spread_ratio([anchors[n] for n in names])[0] > 1e-3:
        reg = register([anchors[n] for n in names], [targets[n] for n in names])
        assert reg.scale > 0 and math.isfinite(reg.rms)


def test_axial_extent_along_the_canonical_axis():
    pts = [(0.0, 0.0, 0.1), (0.05, 0.02, 0.6), (0.0, 0.0, 0.3)]
    assert axial_extent(pts, (0.0, 0.0, 1.0), (0.0, 0.0, 0.0)) == pytest.approx(0.5)
