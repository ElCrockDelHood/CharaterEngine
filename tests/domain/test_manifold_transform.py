"""Tests for GlobalTransform and LocalJointTransform.

Contract: CE-Q1 CANONICAL QUATERNION AND MANIFOLD CONTRACT
Contract: CE-Q3 GLOBAL AND LOCAL MANIFOLD TRANSFORM SYSTEM

Tests validate manifold properties, hierarchical composition, and frame transformations.
"""

import math

import pytest

from character_engine.domain.anatomy.osteology.transform import (
    BonePivot,
    GlobalTransform,
    LocalJointTransform,
    Transform,
)
from character_engine.math.algebra.quaternion import Quaternion, UnitQuaternion
from character_engine.math.algebra.vector3 import Vector3


class TestGlobalTransform:
    """Tests for GlobalTransform (p ∈ ℝ³, q ∈ S³)."""

    def test_identity(self):
        """Test identity global transform."""
        t = GlobalTransform.identity()
        assert t.position == Vector3.zero()
        assert t.orientation == UnitQuaternion.identity()

    def test_position_finite_validation(self):
        """Test that position must be finite."""
        with pytest.raises(ValueError):
            GlobalTransform(Vector3(float('nan'), 0, 0))

        with pytest.raises(ValueError):
            GlobalTransform(Vector3(float('inf'), 0, 0))

    def test_compose_identity(self):
        """Test composition with identity."""
        t = GlobalTransform(Vector3(1, 2, 3), UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4))
        identity = GlobalTransform.identity()

        result = t.compose(LocalJointTransform.identity())
        assert result.position == pytest.approx(t.position, abs=1e-9)
        assert result.orientation.equals(t.orientation)

    def test_compose_local_offset(self):
        """Test composition with local position offset."""
        global_t = GlobalTransform(Vector3(1, 0, 0), UnitQuaternion.identity())
        local_t = LocalJointTransform(Vector3(1, 0, 0), UnitQuaternion.identity())

        result = global_t.compose(local_t)
        # Should be (1+1, 0, 0) = (2, 0, 0)
        assert result.position.x == pytest.approx(2.0, abs=1e-9)
        assert result.position.y == pytest.approx(0.0, abs=1e-9)
        assert result.position.z == pytest.approx(0.0, abs=1e-9)

    def test_compose_local_rotation(self):
        """Test composition with local rotation."""
        global_t = GlobalTransform(Vector3.zero(), UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4))
        local_t = LocalJointTransform(Vector3(1, 0, 0), UnitQuaternion.identity())

        result = global_t.compose(local_t)
        # Local position (1, 0, 0) rotated by 45° about Z should be (cos45°, sin45°, 0)
        expected_x = math.cos(math.pi/4)
        expected_y = math.sin(math.pi/4)
        assert result.position.x == pytest.approx(expected_x, abs=1e-9)
        assert result.position.y == pytest.approx(expected_y, abs=1e-9)
        assert result.position.z == pytest.approx(0.0, abs=1e-9)

    def test_compose_orientation(self):
        """Test orientation composition: q_global = q_parent * q_local."""
        q_parent = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        q_local = UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/4)

        global_t = GlobalTransform(Vector3.zero(), q_parent)
        local_t = LocalJointTransform(Vector3.zero(), q_local)

        result = global_t.compose(local_t)
        expected = q_parent * q_local
        assert result.orientation.equals(expected)

    def test_inverse_identity(self):
        """Test inverse of identity is identity."""
        t = GlobalTransform.identity()
        inv = t.inverse()
        assert inv.position == Vector3.zero()
        assert inv.orientation.equals(UnitQuaternion.identity())

    def test_inverse_composition(self):
        """Test that T * T⁻¹ = identity."""
        t = GlobalTransform(
            Vector3(1, 2, 3),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )
        inv = t.inverse()

        # Compose T with T⁻¹ (should be identity)
        # Note: We need to compose in the right order
        # Global is already in world frame, so T⁻¹ * T should give identity
        result = inv.compose(LocalJointTransform(t.position, t.orientation))

        assert result.position == pytest.approx(Vector3.zero(), abs=1e-9)
        assert result.orientation.equals(UnitQuaternion.identity())

    def test_round_trip_global_local(self):
        """Test round-trip: global → local → global."""
        global_t = GlobalTransform(
            Vector3(1, 2, 3),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )
        parent_t = GlobalTransform(
            Vector3(10, 20, 30),
            UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/4)
        )

        # Compute local: p_local = q_parent⁻¹ ⊙ (p_global - p_parent), q_local = q_parent⁻¹ * q_global
        pos_diff = global_t.position - parent_t.position
        local_pos = parent_t.orientation.inverse().rotate(pos_diff)
        local_orient = parent_t.orientation.inverse() * global_t.orientation
        local = LocalJointTransform(local_pos, local_orient)

        # Compose back: global' = parent * local
        global_prime = parent_t.compose(local)

        assert global_prime.position.x == pytest.approx(global_t.position.x, abs=1e-6)
        assert global_prime.position.y == pytest.approx(global_t.position.y, abs=1e-6)
        assert global_prime.position.z == pytest.approx(global_t.position.z, abs=1e-6)
        assert global_prime.orientation.equals(global_t.orientation)

    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        t = GlobalTransform(
            Vector3(1, 2, 3),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )

        data = t.to_dict()
        t2 = GlobalTransform.from_dict(data)

        assert t2.position == pytest.approx(t.position, abs=1e-9)
        assert t2.orientation.equals(t.orientation)


class TestLocalJointTransform:
    """Tests for LocalJointTransform (p_local ∈ ℝ³, q_local ∈ S³)."""

    def test_identity(self):
        """Test identity local transform."""
        t = LocalJointTransform.identity()
        assert t.position == Vector3.zero()
        assert t.orientation == UnitQuaternion.identity()

    def test_position_finite_validation(self):
        """Test that position must be finite."""
        with pytest.raises(ValueError):
            LocalJointTransform(Vector3(float('nan'), 0, 0))

        with pytest.raises(ValueError):
            LocalJointTransform(Vector3(float('inf'), 0, 0))

    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        t = LocalJointTransform(
            Vector3(1, 2, 3),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )

        data = t.to_dict()
        t2 = LocalJointTransform.from_dict(data)

        assert t2.position == pytest.approx(t.position, abs=1e-9)
        assert t2.orientation.equals(t.orientation)

    def test_to_dict_serialises_canonical_orientation(self):
        """Decision 28: arithmetic keeps the sign, serialisation writes the w ≥ 0 form."""
        q = UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi / 6)
        neg = UnitQuaternion(-q.w, -q.x, -q.y, -q.z)
        for cls in (LocalJointTransform, GlobalTransform):
            a, b = cls(Vector3(1, 2, 3), q).to_dict(), cls(Vector3(1, 2, 3), neg).to_dict()
            assert a == b and a["orientation"]["w"] > 0


class TestHierarchicalComposition:
    """Tests for hierarchical parent-child composition."""

    def test_two_level_chain(self):
        """Test two-level chain: root → joint."""
        root = GlobalTransform(
            Vector3(0, 0, 0),
            UnitQuaternion.identity()
        )
        joint_local = LocalJointTransform(
            Vector3(1, 0, 0),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        )

        joint_global = root.compose(joint_local)

        # Position should be (1, 0, 0) (no rotation in root)
        assert joint_global.position == pytest.approx(Vector3(1, 0, 0), abs=1e-9)
        # Orientation should be the local rotation
        assert joint_global.orientation.equals(joint_local.orientation)

    def test_three_level_chain(self):
        """Test three-level chain: root → joint1 → joint2."""
        root = GlobalTransform(
            Vector3(0, 0, 0),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )
        joint1_local = LocalJointTransform(
            Vector3(1, 0, 0),
            UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/6)
        )
        joint2_local = LocalJointTransform(
            Vector3(0, 1, 0),
            UnitQuaternion.from_axis_angle(Vector3(1, 0, 0), math.pi/6)
        )

        # Compute joint1 global
        joint1_global = root.compose(joint1_local)

        # Compute joint2 global
        joint2_global = joint1_global.compose(joint2_local)

        # Verify orientation composition
        expected_orientation = root.orientation * joint1_local.orientation * joint2_local.orientation
        assert joint2_global.orientation.equals(expected_orientation)

    def test_long_chain_consistency(self):
        """Test long chain for consistency."""
        transforms = []
        current = GlobalTransform.identity()

        # Create 10-level chain
        for i in range(10):
            local = LocalJointTransform(
                Vector3(0.1 * i, 0, 0),
                UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0.1 * i)
            )
            current = current.compose(local)
            transforms.append(current)

        # Verify each transform is valid
        for t in transforms:
            assert t.position.is_finite()
            assert t.orientation.norm() == pytest.approx(1.0, abs=1e-9)

    def test_propagation_without_scale(self):
        """Test that composition works without scale (pure rotation + translation)."""
        parent = GlobalTransform(
            Vector3(1, 2, 3),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        )
        child_local = LocalJointTransform(
            Vector3(4, 5, 6),
            UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/3)
        )

        child_global = parent.compose(child_local)

        # Verify unit norm is preserved
        assert child_global.orientation.norm() == pytest.approx(1.0, abs=1e-9)

    def test_combined_rotations(self):
        """Test combined rotations from multiple levels."""
        root = GlobalTransform(
            Vector3.zero(),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/2)
        )
        joint_local = LocalJointTransform(
            Vector3.zero(),
            UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/2)
        )

        joint_global = root.compose(joint_local)

        # Should be 90° about Z followed by 90° about Y
        # Test by rotating a vector
        v = Vector3(1, 0, 0)
        v_rotated = joint_global.orientation.rotate(v)

        # Verify the result is a unit vector
        assert v_rotated.length() == pytest.approx(1.0, abs=1e-9)


class TestFrameTransformations:
    """Tests for explicit frame transformations."""

    def test_local_to_global_single(self):
        """Test local → global transformation for single joint."""
        parent_global = GlobalTransform(
            Vector3(0, 0, 0),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        )
        local = LocalJointTransform(
            Vector3(1, 0, 0),
            UnitQuaternion.identity()
        )

        global_t = parent_global.compose(local)

        # Local position should be rotated by parent orientation
        expected_x = math.cos(math.pi/4)
        expected_y = math.sin(math.pi/4)
        assert global_t.position.x == pytest.approx(expected_x, abs=1e-9)
        assert global_t.position.y == pytest.approx(expected_y, abs=1e-9)

    def test_global_to_local_single(self):
        """Test global → local transformation for single joint."""
        parent_global = GlobalTransform(
            Vector3(0, 0, 0),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        )
        global_joint = GlobalTransform(
            Vector3(math.cos(math.pi/4), math.sin(math.pi/4), 0),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/4)
        )

        # Compute local: p_local = q_parent⁻¹ ⊙ (p_global - p_parent), q_local = q_parent⁻¹ * q_global
        pos_diff = global_joint.position - parent_global.position
        local_pos = parent_global.orientation.inverse().rotate(pos_diff)
        local_orient = parent_global.orientation.inverse() * global_joint.orientation
        local = LocalJointTransform(local_pos, local_orient)

        # Local position should be (1, 0, 0)
        assert local.position == pytest.approx(Vector3(1, 0, 0), abs=1e-9)
        # Local orientation should be identity (same rotation as parent, so cancels out)
        assert local.orientation.equals(UnitQuaternion.identity())

    def test_frame_explicitness(self):
        """Test that frame transformations are explicit."""
        # Create a chain where each joint has a different local frame
        root = GlobalTransform.identity()

        joint1_local = LocalJointTransform(
            Vector3(1, 0, 0),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )
        joint1_global = root.compose(joint1_local)

        joint2_local = LocalJointTransform(
            Vector3(0, 1, 0),
            UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/6)
        )
        joint2_global = joint1_global.compose(joint2_local)

        # Verify that local transforms are preserved independently
        assert joint1_local.position == pytest.approx(Vector3(1, 0, 0), abs=1e-9)
        assert joint2_local.position == pytest.approx(Vector3(0, 1, 0), abs=1e-9)


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_composition_determinism(self):
        """Test that composition is deterministic."""
        parent = GlobalTransform(
            Vector3(1, 2, 3),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )
        local = LocalJointTransform(
            Vector3(4, 5, 6),
            UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/4)
        )

        results = []
        for _ in range(10):
            result = parent.compose(local)
            results.append(result)

        # All results should be identical
        for r in results[1:]:
            assert r.position == pytest.approx(results[0].position, abs=1e-9)
            assert r.orientation.equals(results[0].orientation)

    def test_inverse_determinism(self):
        """Test that inverse is deterministic."""
        t = GlobalTransform(
            Vector3(1, 2, 3),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )

        results = []
        for _ in range(10):
            inv = t.inverse()
            results.append(inv)

        # All results should be identical
        for r in results[1:]:
            assert r.position == pytest.approx(results[0].position, abs=1e-9)
            assert r.orientation.equals(results[0].orientation)


class TestNumericalProperties:
    """Tests for numerical properties and error propagation."""

    def test_normalization_preservation(self):
        """Test that unit norm is preserved through composition."""
        parent = GlobalTransform(
            Vector3(1, 2, 3),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )
        local = LocalJointTransform(
            Vector3(4, 5, 6),
            UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/4)
        )

        global_t = parent.compose(local)

        # Orientation should still be unit
        assert global_t.orientation.norm() == pytest.approx(1.0, abs=1e-9)

    def test_no_scale_deformation(self):
        """Test that no scale deformation occurs (no scale in manifold transforms)."""
        parent = GlobalTransform(
            Vector3(1, 2, 3),
            UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), math.pi/6)
        )
        local = LocalJointTransform(
            Vector3(4, 5, 6),
            UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), math.pi/4)
        )

        global_t = parent.compose(local)

        # Rotations preserve vector length
        v = Vector3(1, 0, 0)
        v_rotated = global_t.orientation.rotate(v)
        assert v_rotated.length() == pytest.approx(v.length(), abs=1e-9)

    def test_error_propagation_small_chain(self):
        """Test error propagation in small chain."""
        transforms = []
        current = GlobalTransform.identity()

        # Create chain with small rotations
        for _ in range(5):
            local = LocalJointTransform(
                Vector3(0.01, 0, 0),
                UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0.01)
            )
            current = current.compose(local)
            transforms.append(current)

        # Verify no numerical blow-up
        for t in transforms:
            assert t.position.is_finite()
            assert t.orientation.norm() == pytest.approx(1.0, abs=1e-9)


class TestBackwardCompatibility:
    """Tests for backward compatibility with legacy Transform."""

    def test_transform_still_works(self):
        """Test that legacy Transform class still works."""

        t = Transform(
            Vector3(1, 2, 3),
            Quaternion(1, 0, 0, 0),
            Vector3(1, 1, 1)
        )

        assert t.position == Vector3(1, 2, 3)
        assert t.scale == Vector3(1, 1, 1)

    def test_bone_pivot_still_works(self):
        """Test that legacy BonePivot class still works."""

        pivot = BonePivot(
            Vector3(1, 2, 3),
            Quaternion(1, 0, 0, 0)
        )

        assert pivot.local_position == Vector3(1, 2, 3)
