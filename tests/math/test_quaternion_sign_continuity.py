"""Sign-continuity branch of ``integrate_quaternion_angular_velocity`` (CE-Q4 review F-3, Decision 28).

For a pure ω the Euler update is orthogonal to q, so q_next·q = 1 exactly in real arithmetic and the
branch never fires in normal use. It only fires when floating-point cancellation swamps q, e.g. with an
absurd step: then the renormalised state lands in the opposite hemisphere and the branch flips it back.
"""

from character_engine.math.algebra.quaternion import (
    Quaternion,
    UnitQuaternion,
    angular_velocity_to_quaternion_derivative,
    integrate_quaternion_angular_velocity,
)
from character_engine.math.algebra.vector3 import Vector3


def _raw_step(q, omega, dt):
    """The integrator without the sign-continuity branch."""
    dq = angular_velocity_to_quaternion_derivative(q, omega)
    return UnitQuaternion.from_quaternion(
        Quaternion(q.w + dt * dq.w, q.x + dt * dq.x, q.y + dt * dq.y, q.z + dt * dq.z))


def _components(q):
    return (q.w, q.x, q.y, q.z)


def test_branch_flips_a_state_that_crossed_to_the_other_hemisphere():
    q = UnitQuaternion(0.5, 0.5, 0.5, 0.5)
    omega, dt = Vector3(0.3, -0.7, 0.2), 1e19          # cancellation regime, found by search
    raw = _raw_step(q, omega, dt)
    assert raw.dot(q) < 0                              # without the branch the sign would jump
    stepped = integrate_quaternion_angular_velocity(q, omega, dt)
    assert stepped.dot(q) > 0
    assert _components(stepped) == tuple(-c for c in _components(raw))   # same rotation, other sign


def test_branch_is_inactive_for_ordinary_steps():
    q = UnitQuaternion(0.5, 0.5, 0.5, 0.5)
    omega = Vector3(0.3, -0.7, 0.2)
    for dt in (1e-3, 1e-1, 10.0):
        raw = _raw_step(q, omega, dt)
        assert raw.dot(q) > 0
        assert _components(integrate_quaternion_angular_velocity(q, omega, dt)) == _components(raw)
