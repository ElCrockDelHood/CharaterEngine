"""Transform (TRS, uniform scale) is exact against 4×4 matrices (Decisions 23–25 / D-03..D-05)."""

import math
import random

import pytest

from character_engine.domain.anatomy.osteology.transform import NonUniformScaleError, Transform
from character_engine.math.algebra.matrix4 import Matrix4
from character_engine.math.algebra.quaternion import Quaternion
from character_engine.math.algebra.vector3 import Vector3

_FIELDS = [f"m{r}{c}" for r in range(1, 5) for c in range(1, 5)]


def _close(a: Matrix4, b: Matrix4, tol: float = 1e-9) -> bool:
    return all(abs(getattr(a, f) - getattr(b, f)) <= tol for f in _FIELDS)


def _random_trs(rng: random.Random, unit_rotation: bool = True) -> Transform:
    axis = Vector3(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))
    rot = Quaternion.from_axis_angle(axis, rng.uniform(-math.pi, math.pi))
    if not unit_rotation:   # non-unit rotation quaternion: still a pure rotation once normalised
        k = rng.uniform(0.5, 3.0)
        rot = Quaternion(rot.w * k, rot.x * k, rot.y * k, rot.z * k)
    s = rng.uniform(0.2, 5.0)
    pos = Vector3(rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(-3, 3))
    return Transform(pos, rot, Vector3(s, s, s))


@pytest.fixture
def rng():
    return random.Random(20261024)


def test_inverse_is_exact(rng):
    for unit in (True, False):
        for _ in range(50):
            t = _random_trs(rng, unit)
            assert _close(t.to_matrix() @ t.inverse().to_matrix(), Matrix4())
            assert _close(t.inverse().to_matrix() @ t.to_matrix(), Matrix4())


def test_compose_equals_matrix_product(rng):
    for unit in (True, False):
        for _ in range(50):
            a, b = _random_trs(rng, unit), _random_trs(rng, unit)
            assert _close(a.compose(b).to_matrix(), a.to_matrix() @ b.to_matrix())


def test_compose_is_associative(rng):
    for _ in range(50):
        a, b, c = _random_trs(rng), _random_trs(rng), _random_trs(rng)
        assert _close(a.compose(b).compose(c).to_matrix(), a.compose(b.compose(c)).to_matrix())


def test_compose_with_inverse_is_identity(rng):
    """R21 TI-007: with the old inverse this only held for p = 0 or s = (1,1,1)."""
    for _ in range(50):
        t = _random_trs(rng)
        assert _close(t.compose(t.inverse()).to_matrix(), Matrix4())
        assert _close(t.inverse().compose(t).to_matrix(), Matrix4())


def test_old_inverse_counterexample_now_exact():
    t = Transform(Vector3(1, 2, 3), Quaternion.from_axis_angle(Vector3(0, 0, 1), 0.7), Vector3(2, 2, 2))
    inv = t.inverse()
    assert inv.scale == Vector3(0.5, 0.5, 0.5)
    assert _close(t.to_matrix() @ inv.to_matrix(), Matrix4())


def test_non_uniform_scale_is_rejected_by_algebra():
    t = Transform(Vector3(1, 0, 0), Quaternion.identity(), Vector3(1, 2, 3))
    assert not t.is_uniform_scale()
    with pytest.raises(NonUniformScaleError):
        t.inverse()
    with pytest.raises(NonUniformScaleError):
        t.compose(Transform())
    with pytest.raises(NonUniformScaleError):
        Transform().compose(t)
    assert isinstance(NonUniformScaleError("x"), ValueError)
    # data with non-uniform scale can still be stored and converted to a matrix
    assert t.to_matrix().m22 == pytest.approx(2.0)
