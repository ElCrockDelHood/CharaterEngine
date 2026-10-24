"""Convergence of the quaternion integrator (R10 §4.3–4.4, criterion corrected by Decision 38).

Explicit Euler + renormalisation (``integrate_quaternion_angular_velocity``):

* Case 1, fixed axis: each step is an exact rotation about the right axis by 2·atan(ω·dt/2) instead
  of ω·dt, an O(dt³) local error, so the global error is SECOND order (measured ratio 3.99–4.00).
  R10's "|r − 2| < 0.1" assumed first order; the corrected criterion is "order ≥ 1".
* Case 2, variable axis: the method is first order (measured ratio 2.00): |r − 2| < 0.1.
"""

import math

import pytest

from character_engine.math.algebra.quaternion import (
    UnitQuaternion,
    geodesic_distance,
    integrate_quaternion_angular_velocity,
)
from character_engine.math.algebra.vector3 import Vector3

DTS = (0.1, 0.05, 0.025, 0.0125)


def _integrate(omega_of_t, dt, t_end=1.0):
    q, t = UnitQuaternion.identity(), 0.0
    for _ in range(round(t_end / dt)):
        q = integrate_quaternion_angular_velocity(q, omega_of_t(t), dt)
        t += dt
    return q


def _ratios(errors):
    return [errors[i] / errors[i + 1] for i in range(len(errors) - 1)]


def test_convergence_fixed_axis_is_at_least_first_order():
    omega = Vector3(0.0, 0.0, math.pi / 2)
    reference = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi / 2)
    errors, norm_errors = [], []
    for dt in DTS:
        q = _integrate(lambda t: omega, dt)
        errors.append(geodesic_distance(q, reference))
        norm_errors.append(abs(q.norm() - 1.0))
    orders = [math.log2(r) for r in _ratios(errors)]
    assert all(o >= 1.0 for o in orders), orders              # corrected R10 criterion
    assert all(o == pytest.approx(2.0, abs=0.1) for o in orders), orders   # observed (documents F-1)
    assert max(norm_errors) < 1e-12
    assert errors[0] == pytest.approx(3.2179e-3, rel=1e-3)   # measured tolerance at dt = 0.1 (Decision 38)


def test_convergence_variable_axis_is_first_order():
    def omega(t):
        return Vector3(math.sin(t), math.cos(t), 0.5)
    reference = _integrate(omega, 1e-5)
    errors = [geodesic_distance(_integrate(omega, dt), reference) for dt in DTS]
    for r in _ratios(errors):
        assert abs(r - 2.0) < 0.1, r
    assert errors[0] == pytest.approx(4.351e-2, rel=1e-2)     # measured tolerance at dt = 0.1 (Decision 38)
