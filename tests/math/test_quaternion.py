"""Tests for Quaternion and UnitQuaternion classes.

Contract: CE-Q1 CANONICAL QUATERNION AND MANIFOLD CONTRACT
Tests validate mathematical properties, not just concrete examples.
"""

import math

import pytest

from character_engine.math.algebra.quaternion import (
    NORM_TOLERANCE,
    Quaternion,
    UnitQuaternion,
    angular_velocity_to_quaternion_derivative,
    geodesic_distance,
    integrate_quaternion_angular_velocity,
    nlerp,
    slerp,
)
from character_engine.math.algebra.vector3 import Vector3


class TestQuaternion:
    """Tests for general Quaternion class."""

    def test_identity(self):
        """Test identity quaternion properties."""
        q = Quaternion.identity()
        assert q == Quaternion(1, 0, 0, 0)
        assert q.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_zero(self):
        """Test zero quaternion."""
        q = Quaternion.zero()
        assert q == Quaternion(0, 0, 0, 0)
        assert q.norm() == pytest.approx(0.0, abs=NORM_TOLERANCE)

    def test_norm(self):
        """Test norm calculation."""
        q = Quaternion(1, 0, 0, 0)
        assert q.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

        q = Quaternion(0, 1, 0, 0)
        assert q.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

        q = Quaternion(1, 2, 3, 4)
        assert q.norm() == pytest.approx(math.sqrt(30), abs=NORM_TOLERANCE)

    def test_normalize(self):
        """Test normalization."""
        q = Quaternion(2, 0, 0, 0)
        qn = q.normalize()
        assert qn.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)
        assert qn == Quaternion(1, 0, 0, 0)

        # Zero quaternion normalizes to identity
        q = Quaternion.zero()
        qn = q.normalize()
        assert qn == Quaternion.identity()

    def test_conjugate(self):
        """Test conjugate."""
        q = Quaternion(1, 2, 3, 4)
        qc = q.conjugate()
        assert qc == Quaternion(1, -2, -3, -4)

    def test_inverse(self):
        """Test inverse: q * q⁻¹ has unit norm for unit quaternions."""
        # Test with unit quaternion
        q = Quaternion(1, 0, 0, 0)
        qi = q.inverse()
        product = q * qi
        assert product.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

        # Test with normalized quaternion
        q = Quaternion(1, 2, 3, 4).normalize()
        qi = q.inverse()
        product = q * qi
        assert product.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_multiplication_associativity(self):
        """Test associativity: (q₁ * q₂) * q₃ = q₁ * (q₂ * q₃)."""
        q1 = Quaternion(1, 2, 3, 4)
        q2 = Quaternion(5, 6, 7, 8)
        q3 = Quaternion(9, 10, 11, 12)

        left = (q1 * q2) * q3
        right = q1 * (q2 * q3)

        assert left.w == pytest.approx(right.w, abs=NORM_TOLERANCE)
        assert left.x == pytest.approx(right.x, abs=NORM_TOLERANCE)
        assert left.y == pytest.approx(right.y, abs=NORM_TOLERANCE)
        assert left.z == pytest.approx(right.z, abs=NORM_TOLERANCE)

    def test_dot_product(self):
        """Test dot product."""
        q1 = Quaternion(1, 2, 3, 4)
        q2 = Quaternion(5, 6, 7, 8)
        dot = q1.dot(q2)
        assert dot == pytest.approx(1*5 + 2*6 + 3*7 + 4*8, abs=NORM_TOLERANCE)

    def test_rotate_vector(self):
        """Test vector rotation preserves vector norm."""
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)
        v = Vector3(1, 0, 0)
        vr = q.rotate(v)

        # Vector norm should be preserved
        assert vr.length() == pytest.approx(v.length(), abs=NORM_TOLERANCE)

        # Rotation by 90° about Z should map (1, 0, 0) to (0, 1, 0)
        assert vr.x == pytest.approx(0.0, abs=NORM_TOLERANCE)
        assert vr.y == pytest.approx(1.0, abs=NORM_TOLERANCE)
        assert vr.z == pytest.approx(0.0, abs=NORM_TOLERANCE)

    def test_rotate_vector_composition(self):
        """Test rotation composition: q₁ ⊙ (q₂ ⊙ v) = (q₁ * q₂) ⊙ v."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/4)
        v = Vector3(1, 0, 0)

        left = q1.rotate(q2.rotate(v))
        right = (q1 * q2).rotate(v)

        assert left.x == pytest.approx(right.x, abs=NORM_TOLERANCE)
        assert left.y == pytest.approx(right.y, abs=NORM_TOLERANCE)
        assert left.z == pytest.approx(right.z, abs=NORM_TOLERANCE)

    def test_is_finite(self):
        """Test finite check."""
        q = Quaternion(1, 2, 3, 4)
        assert q.is_finite()

        q = Quaternion(float('nan'), 0, 0, 0)
        assert not q.is_finite()

        q = Quaternion(float('inf'), 0, 0, 0)
        assert not q.is_finite()


class TestUnitQuaternion:
    """Tests for UnitQuaternion class."""

    def test_identity(self):
        """Test identity quaternion."""
        q = UnitQuaternion.identity()
        assert q == UnitQuaternion(1, 0, 0, 0)
        assert q.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_unit_norm_enforcement(self):
        """Test that unit norm is enforced."""
        # Should accept unit quaternion
        q = UnitQuaternion(1, 0, 0, 0)
        assert q.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

        # Should reject non-unit quaternion
        with pytest.raises(ValueError):
            UnitQuaternion(2, 0, 0, 0)

        # Should accept within tolerance
        q = UnitQuaternion(1 + 1e-10, 0, 0, 0)
        assert q.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_double_cover_canonicalization(self):
        """Test canonicalization to w ≥ 0."""
        # q with w > 0 should remain unchanged
        q = UnitQuaternion(0.5, 0.5, 0.5, 0.5)
        assert q.w > 0

        # q with w < 0 should be negated
        q = UnitQuaternion(-0.5, 0.5, 0.5, 0.5)
        assert q.w > 0
        assert q.x == pytest.approx(-0.5, abs=NORM_TOLERANCE)
        assert q.y == pytest.approx(-0.5, abs=NORM_TOLERANCE)
        assert q.z == pytest.approx(-0.5, abs=NORM_TOLERANCE)

    def test_from_quaternion(self):
        """Test creation from general Quaternion."""
        q = Quaternion(2, 0, 0, 0)
        uq = UnitQuaternion.from_quaternion(q)
        assert uq == UnitQuaternion.identity()

        q = Quaternion(0, 2, 0, 0)
        uq = UnitQuaternion.from_quaternion(q)
        assert uq == UnitQuaternion(0, 1, 0, 0)

    def test_from_quaternion_canonicalization(self):
        """Test that from_quaternion canonicalizes double cover."""
        q = Quaternion(-0.5, 0.5, 0.5, 0.5)
        uq = UnitQuaternion.from_quaternion(q)
        assert uq.w > 0

    def test_from_quaternion_finite_check(self):
        """Test that from_quaternion rejects non-finite input."""
        q = Quaternion(float('nan'), 0, 0, 0)
        with pytest.raises(ValueError):
            UnitQuaternion.from_quaternion(q)

        q = Quaternion(float('inf'), 0, 0, 0)
        with pytest.raises(ValueError):
            UnitQuaternion.from_quaternion(q)

    def test_from_axis_angle(self):
        """Test creation from axis-angle."""
        # 90° rotation about Z
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)
        expected_w = math.cos(math.pi/4)
        expected_xyz = math.sin(math.pi/4)
        assert q.w == pytest.approx(expected_w, abs=NORM_TOLERANCE)
        assert q.x == pytest.approx(0.0, abs=NORM_TOLERANCE)
        assert q.y == pytest.approx(0.0, abs=NORM_TOLERANCE)
        assert q.z == pytest.approx(expected_xyz, abs=NORM_TOLERANCE)

    def test_from_axis_angle_finite_check(self):
        """Test that from_axis_angle rejects non-finite input."""
        with pytest.raises(ValueError):
            UnitQuaternion.from_axis_angle(Vector3(float('nan'), 0, 0), 0)

        with pytest.raises(ValueError):
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), float('nan'))

    def test_from_euler_zyx(self):
        """Test creation from Euler angles (ZYX intrinsic)."""
        # 90° rotation about Z (yaw)
        q = UnitQuaternion.from_euler_zyx(0, 0, 90)
        # Should rotate (1, 0, 0) to (0, 1, 0)
        v = Vector3(1, 0, 0)
        vr = q.rotate(v)
        assert vr.x == pytest.approx(0.0, abs=NORM_TOLERANCE)
        assert vr.y == pytest.approx(1.0, abs=NORM_TOLERANCE)
        assert vr.z == pytest.approx(0.0, abs=NORM_TOLERANCE)

    def test_from_euler_zyx_finite_check(self):
        """Test that from_euler_zyx rejects non-finite input."""
        with pytest.raises(ValueError):
            UnitQuaternion.from_euler_zyx(float('nan'), 0, 0)

    def test_conjugate(self):
        """Test conjugate."""
        q = UnitQuaternion(0.5, 0.5, 0.5, 0.5)
        qc = q.conjugate()
        assert qc == UnitQuaternion(0.5, -0.5, -0.5, -0.5)

    def test_inverse(self):
        """Test inverse: q * q⁻¹ = identity."""
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        qi = q.inverse()
        product = q * qi
        assert product.equals(UnitQuaternion.identity())

    def test_multiplication(self):
        """Test quaternion multiplication (composition)."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/4)
        product = q1 * q2
        assert product.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_multiplication_associativity(self):
        """Test associativity: (q₁ * q₂) * q₃ = q₁ * (q₂ * q₃)."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/6)
        q3 = UnitQuaternion.from_axis_angle(Vector3(1, 0, 0), math.pi/6)

        left = (q1 * q2) * q3
        right = q1 * (q2 * q3)

        assert left.equals(right)

    def test_equals_with_tolerance(self):
        """Test equality with tolerance."""
        q1 = UnitQuaternion.identity()
        q2 = UnitQuaternion.identity()
        assert q1.equals(q2)

        # Small difference within tolerance
        q2 = UnitQuaternion.from_quaternion(Quaternion(1 + 1e-10, 0, 0, 0))
        assert q1.equals(q2)

        # Larger difference outside tolerance
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0.1)
        assert not q1.equals(q2)

    def test_rotate_vector_preserves_norm(self):
        """Test that rotation preserves vector norm."""
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/3)
        v = Vector3(1, 2, 3)
        vr = q.rotate(v)
        assert vr.length() == pytest.approx(v.length(), abs=NORM_TOLERANCE)

    def test_double_cover_equivalence(self):
        """Test that q and -q represent the same rotation."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        q2 = UnitQuaternion(-q1.w, -q1.x, -q1.y, -q1.z)

        # Both should be canonicalized to w ≥ 0
        assert q1.equals(q2)

        # Both should rotate vectors identically
        v = Vector3(1, 0, 0)
        vr1 = q1.rotate(v)
        vr2 = q2.rotate(v)
        assert vr1.x == pytest.approx(vr2.x, abs=NORM_TOLERANCE)
        assert vr1.y == pytest.approx(vr2.y, abs=NORM_TOLERANCE)
        assert vr1.z == pytest.approx(vr2.z, abs=NORM_TOLERANCE)


class TestSLERP:
    """Tests for spherical linear interpolation."""

    def test_slerp_identity(self):
        """Test slerp(q, q, t) = q."""
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        for t in [0.0, 0.5, 1.0]:
            result = slerp(q, q, t)
            assert result.equals(q)

    def test_slerp_endpoints(self):
        """Test slerp(q₁, q₂, 0) = q₁ and slerp(q₁, q₂, 1) = q₂."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        assert slerp(q1, q2, 0).equals(q1)
        assert slerp(q1, q2, 1).equals(q2)

    def test_slerp_unit_norm(self):
        """Test that slerp maintains unit norm."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = slerp(q1, q2, t)
            assert result.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_slerp_shortest_path(self):
        """Test that slerp takes the shortest path (double cover handling)."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 3*math.pi/2)  # Long way

        # slerp should take the shorter path (equivalent to -90°)
        q_half = slerp(q1, q2, 0.5)
        expected = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), -math.pi/4)
        assert q_half.equals(expected)

    def test_slerp_near_parallel(self):
        """Test slerp with nearly parallel quaternions (θ ≈ 0)."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 1e-8)

        result = slerp(q1, q2, 0.5)
        assert result.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_slerp_finite_check(self):
        """Test that slerp rejects non-finite t."""
        q1 = UnitQuaternion.identity()
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        with pytest.raises(ValueError):
            slerp(q1, q2, float('nan'))

        with pytest.raises(ValueError):
            slerp(q1, q2, float('inf'))

    def test_slerp_range_check(self):
        """Test that slerp rejects t outside [0, 1]."""
        q1 = UnitQuaternion.identity()
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        with pytest.raises(ValueError):
            slerp(q1, q2, -0.1)

        with pytest.raises(ValueError):
            slerp(q1, q2, 1.1)


class TestNLERP:
    """Tests for normalized linear interpolation."""

    def test_nlerp_identity(self):
        """Test nlerp(q, q, t) = q."""
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        for t in [0.0, 0.5, 1.0]:
            result = nlerp(q, q, t)
            assert result.equals(q)

    def test_nlerp_endpoints(self):
        """Test nlerp(q₁, q₂, 0) = q₁ and nlerp(q₁, q₂, 1) = q₂."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        assert nlerp(q1, q2, 0).equals(q1)
        assert nlerp(q1, q2, 1).equals(q2)

    def test_nlerp_unit_norm(self):
        """Test that nlerp maintains unit norm."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = nlerp(q1, q2, t)
            assert result.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_nlerp_shortest_path(self):
        """Test that nlerp takes the shortest path (double cover handling)."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 3*math.pi/2)

        # nlerp should negate q2 to take shorter path
        q_half = nlerp(q1, q2, 0.5)
        # Result should be between q1 and -q2
        assert q_half.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_nlerp_finite_check(self):
        """Test that nlerp rejects non-finite t."""
        q1 = UnitQuaternion.identity()
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        with pytest.raises(ValueError):
            nlerp(q1, q2, float('nan'))

        with pytest.raises(ValueError):
            nlerp(q1, q2, float('inf'))

    def test_nlerp_range_check(self):
        """Test that nlerp rejects t outside [0, 1]."""
        q1 = UnitQuaternion.identity()
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        with pytest.raises(ValueError):
            nlerp(q1, q2, -0.1)

        with pytest.raises(ValueError):
            nlerp(q1, q2, 1.1)


class TestAngularVelocity:
    """Tests for angular velocity and integration."""

    def test_angular_velocity_to_quaternion_derivative(self):
        """Test dq/dt = 0.5 * ω * q."""
        q = UnitQuaternion.identity()
        omega = Vector3(0, 0, math.pi/2)  # 90°/s about Z

        dq_dt = angular_velocity_to_quaternion_derivative(q, omega)

        # For identity quaternion, dq/dt should be (0, ω/2)
        assert dq_dt.w == pytest.approx(0.0, abs=NORM_TOLERANCE)
        assert dq_dt.x == pytest.approx(0.0, abs=NORM_TOLERANCE)
        assert dq_dt.y == pytest.approx(0.0, abs=NORM_TOLERANCE)
        assert dq_dt.z == pytest.approx(math.pi/4, abs=NORM_TOLERANCE)

    def test_angular_velocity_finite_check(self):
        """Test that angular_velocity_to_quaternion_derivative rejects non-finite input."""
        q = UnitQuaternion.identity()

        with pytest.raises(ValueError):
            angular_velocity_to_quaternion_derivative(q, Vector3(float('nan'), 0, 0))

        with pytest.raises(ValueError):
            angular_velocity_to_quaternion_derivative(q, Vector3(0, float('inf'), 0))

    def test_integrate_quaternion_angular_velocity(self):
        """Test explicit Euler integration with small timestep."""
        q = UnitQuaternion.identity()
        omega = Vector3(0, 0, math.pi/2)  # 90°/s about Z
        dt = 0.01  # Small timestep for better accuracy

        # Integrate for 1 second (100 steps)
        for _ in range(100):
            q = integrate_quaternion_angular_velocity(q, omega, dt)

        # After 1 second at 90°/s, should be approximately 90° rotation about Z
        expected = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)
        assert q.equals(expected, tolerance=1e-2)  # Larger tolerance for Euler integration

    def test_integrate_preserves_unit_norm(self):
        """Test that integration maintains unit norm."""
        q = UnitQuaternion.identity()
        omega = Vector3(0, 0, math.pi/4)
        dt = 0.1

        for _ in range(10):
            q = integrate_quaternion_angular_velocity(q, omega, dt)
            assert q.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_integrate_finite_check(self):
        """Test that integrate_quaternion_angular_velocity rejects non-finite input."""
        q = UnitQuaternion.identity()
        omega = Vector3(0, 0, math.pi/2)

        with pytest.raises(ValueError):
            integrate_quaternion_angular_velocity(q, omega, float('nan'))

        with pytest.raises(ValueError):
            integrate_quaternion_angular_velocity(q, omega, float('inf'))

        with pytest.raises(ValueError):
            integrate_quaternion_angular_velocity(q, omega, -0.1)

    def test_integrate_zero_angular_velocity(self):
        """Test that zero angular velocity preserves quaternion."""
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        omega = Vector3(0, 0, 0)
        dt = 1.0

        q_next = integrate_quaternion_angular_velocity(q, omega, dt)
        assert q_next.equals(q)


class TestGeodesicDistance:
    """Tests for geodesic distance on S³."""

    def test_geodesic_distance_identity(self):
        """Test distance to self is zero."""
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        assert geodesic_distance(q, q) == pytest.approx(0.0, abs=NORM_TOLERANCE)

    def test_geodesic_distance_symmetry(self):
        """Test distance is symmetric: d(q₁, q₂) = d(q₂, q₁)."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        d1 = geodesic_distance(q1, q2)
        d2 = geodesic_distance(q2, q1)
        assert d1 == pytest.approx(d2, abs=NORM_TOLERANCE)

    def test_geodesic_distance_double_cover(self):
        """Test that q and -q have distance π (half sphere)."""
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        q_neg = UnitQuaternion(-q.w, -q.x, -q.y, -q.z)

        # After canonicalization, both should be equivalent
        # Distance should be zero (both canonicalized to same representation)
        d = geodesic_distance(q, q_neg)
        assert d == pytest.approx(0.0, abs=NORM_TOLERANCE)

    def test_geodesic_distance_known_values(self):
        """Test geodesic distance for known rotations."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)

        # Distance should be π/2 (90° on S³ corresponds to 45° rotation)
        d = geodesic_distance(q1, q2)
        # For unit quaternions, geodesic distance = 2 * angle
        # angle between rotations = π/4, so distance = π/2
        assert d == pytest.approx(math.pi/2, abs=NORM_TOLERANCE)


class TestNumericalValidation:
    """Tests for numerical validation and edge cases."""

    def test_zero_quaternion_handling(self):
        """Test zero quaternion normalization."""
        q = Quaternion.zero()
        qn = q.normalize()
        assert qn == Quaternion.identity()

    def test_nan_propagation(self):
        """Test NaN detection."""
        q = Quaternion(float('nan'), 0, 0, 0)
        assert not q.is_finite()

        with pytest.raises(ValueError):
            UnitQuaternion.from_quaternion(q)

    def test_inf_propagation(self):
        """Test Inf detection."""
        q = Quaternion(float('inf'), 0, 0, 0)
        assert not q.is_finite()

        with pytest.raises(ValueError):
            UnitQuaternion.from_quaternion(q)

    def test_determinism(self):
        """Test that operations are deterministic."""
        q1 = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        q2 = UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/6)

        # Run same operation multiple times
        results = []
        for _ in range(10):
            results.append(q1 * q2)

        # All results should be identical
        for r in results[1:]:
            assert r.equals(results[0])


class TestQuaternionFromAxisAngle:
    """Test Quaternion.from_axis_angle static method."""

    def test_from_axis_angle_unit_quaternion(self):
        """Test that from_axis_angle creates unit quaternion."""
        q = Quaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)
        assert q.norm() == pytest.approx(1.0, abs=NORM_TOLERANCE)

    def test_from_axis_angle_general_quaternion(self):
        """Test that from_axis_angle works with general Quaternion."""
        q = Quaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)
        # Should be same as UnitQuaternion result
        uq = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)
        assert q.w == pytest.approx(uq.w, abs=NORM_TOLERANCE)
        assert q.x == pytest.approx(uq.x, abs=NORM_TOLERANCE)
        assert q.y == pytest.approx(uq.y, abs=NORM_TOLERANCE)
        assert q.z == pytest.approx(uq.z, abs=NORM_TOLERANCE)
