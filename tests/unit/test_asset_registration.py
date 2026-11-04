"""Landmark registration (F1 of docs/architecture/ASSET_FITTING_PROPOSAL.md) on synthetic data only."""

import math
import random

import pytest

from character_engine.domain.assets.registration import (
    MIN_SPREAD_RATIO,
    RegistrationError,
    determinant,
    fit_sphere,
    register,
    spread_ratio,
)


def _rot(axis, angle):
    n = math.sqrt(sum(c * c for c in axis))
    x, y, z = (c / n for c in axis)
    c, s, C = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return ((c + x * x * C, x * y * C - z * s, x * z * C + y * s),
            (y * x * C + z * s, c + y * y * C, y * z * C - x * s),
            (z * x * C - y * s, z * y * C + x * s, c + z * z * C))


def _apply(r, s, t, p):
    return tuple(s * sum(r[i][j] * p[j] for j in range(3)) + t[i] for i in range(3))


ANCHORS_3 = [(0.0, 0.0, 0.45), (0.04, 0.0, 0.0), (-0.04, 0.0, 0.0)]          # head, lateral, medial (femur-like)
ANCHORS_5 = ANCHORS_3 + [(0.0, -0.02, 0.02), (0.05, 0.01, 0.40)]


@pytest.mark.parametrize("anchors", [ANCHORS_3, ANCHORS_5])
@pytest.mark.parametrize("axis, angle, s, t", [
    ((0, 0, 1), 0.0, 1.0, (0, 0, 0)),
    ((1, 2, 3), 1.1, 0.83, (0.1, -0.2, 0.9)),
    ((0, 1, 0), math.pi - 1e-3, 1.27, (-1.0, 0.5, 0.0)),
    ((-2, 0.5, 1), 2.9, 0.001, (5.0, 5.0, 5.0)),               # mm -> m style scale
])
def test_recovers_known_similarity_transform(anchors, axis, angle, s, t):
    r = _rot(axis, angle)
    target = [_apply(r, s, t, p) for p in anchors]
    reg = register(anchors, target)
    assert reg.scale == pytest.approx(s, rel=1e-9)
    for i in range(3):
        assert reg.translation[i] == pytest.approx(t[i], abs=1e-6)
        for j in range(3):
            assert reg.rotation[i][j] == pytest.approx(r[i][j], abs=1e-6)
    assert determinant(reg.rotation) == pytest.approx(1.0, abs=1e-9)
    assert reg.rms < 1e-6 and max(reg.residuals) < 1e-6
    for p, q in zip(anchors, target):
        assert reg.apply(p) == pytest.approx(q, abs=1e-6)


def test_rigid_mode_keeps_unit_scale_and_reports_residuals():
    r = _rot((0, 0, 1), 0.4)
    target = [_apply(r, 2.0, (0, 0, 0), p) for p in ANCHORS_5]
    reg = register(ANCHORS_5, target, with_scale=False)
    assert reg.scale == 1.0 and reg.rms > 0.01          # cannot absorb the factor 2


def test_noisy_anchors_give_finite_rms():
    rng = random.Random(7)
    r = _rot((1, 1, 0), 0.7)
    target = [tuple(c + rng.gauss(0, 1e-3) for c in _apply(r, 1.0, (0.1, 0, 0), p)) for p in ANCHORS_5]
    reg = register(ANCHORS_5, target)
    assert 1e-5 < reg.rms < 5e-3 and len(reg.residuals) == 5


def test_reflection_is_rejected_with_non_coplanar_anchors():
    mirrored = [(-x, y, z) for x, y, z in ANCHORS_5]
    r = _rot((0, 1, 1), 0.3)
    target = [_apply(r, 1.0, (0, 0, 0), p) for p in mirrored]
    with pytest.raises(RegistrationError, match="reflection"):
        register(ANCHORS_5, target)


def test_three_anchors_cannot_see_chirality():
    reg = register(ANCHORS_3, [(-x, y, z) for x, y, z in ANCHORS_3])
    assert not reg.chirality_checked and reg.rms < 1e-9 and determinant(reg.rotation) == pytest.approx(1.0)
    assert register(ANCHORS_5, ANCHORS_5).chirality_checked


@pytest.mark.parametrize("anchors", [
    [(0, 0, 0), (0, 0, 1), (0, 0, 2)],
    [(0, 0, 0), (0, 0, 1), (MIN_SPREAD_RATIO * 0.1, 0, 0.5)],
    [(0, 0, 0), (0, 0, 0), (0, 0, 0)],
])
def test_nearly_collinear_anchors_are_rejected(anchors):
    with pytest.raises(RegistrationError, match="collinear"):
        register(anchors, ANCHORS_3)


def test_input_errors():
    with pytest.raises(RegistrationError):
        register(ANCHORS_3[:2], ANCHORS_3[:2])
    with pytest.raises(RegistrationError):
        register(ANCHORS_3, ANCHORS_5)
    with pytest.raises(RegistrationError):
        register([(0, 0, float("nan"))] + ANCHORS_3[1:], ANCHORS_3)


def test_spread_ratio_bounds():
    assert spread_ratio([(0, 0, 0), (1, 0, 0), (2, 0, 0)])[0] == pytest.approx(0.0, abs=1e-9)
    tetra = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    assert spread_ratio(tetra) == pytest.approx((1.0, 1.0))


def test_sphere_fit_recovers_centre_and_radius():
    rng = random.Random(3)
    c, r = (0.1, -0.05, 0.9), 0.023
    pts = []
    for _ in range(200):
        u, v = rng.uniform(-1, 1), rng.uniform(0, 2 * math.pi)
        w = math.sqrt(1 - u * u)
        pts.append((c[0] + r * w * math.cos(v), c[1] + r * w * math.sin(v), c[2] + r * u))
    centre, radius, rms = fit_sphere(pts)
    assert centre == pytest.approx(c, abs=1e-9) and radius == pytest.approx(r, abs=1e-9) and rms < 1e-9
    with pytest.raises(RegistrationError):
        fit_sphere(pts[:3])
