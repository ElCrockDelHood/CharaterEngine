"""Coordinate System Tests.

Tests for the canonical coordinate system contract defined in coordinate_system.py.
"""

import pytest
import math
from character_engine.domain.anatomy.coordinate_system import (
    CoordinateSystem,
    Handedness,
    Axis,
    LinearUnit,
    AngularUnit,
    LateralSide,
    Tolerance,
    UnitConverter,
    CANONICAL_COORDINATE_SYSTEM,
    CANONICAL_TOLERANCE,
    UNIT_CONVERTER,
    validate_coordinate_system,
    get_rotation_order,
    get_rotation_direction,
    is_valid_coordinate,
    normalize_vector,
    cross_product,
    validate_right_handedness
)


class TestCoordinateSystem:
    """Test coordinate system configuration."""
    
    def test_canonical_system_is_right_handed(self):
        """Test canonical coordinate system is right-handed."""
        assert CANONICAL_COORDINATE_SYSTEM.is_right_handed()
    
    def test_canonical_system_axes(self):
        """Test canonical coordinate system has correct axes."""
        assert CANONICAL_COORDINATE_SYSTEM.up_axis == Axis.Z
        assert CANONICAL_COORDINATE_SYSTEM.lateral_axis == Axis.X
        assert CANONICAL_COORDINATE_SYSTEM.anterior_posterior_axis == Axis.Y
    
    def test_canonical_system_units(self):
        """Test canonical coordinate system has correct units."""
        assert CANONICAL_COORDINATE_SYSTEM.linear_unit == LinearUnit.METERS
        assert CANONICAL_COORDINATE_SYSTEM.angular_unit == AngularUnit.DEGREES
    
    def test_canonical_system_origin(self):
        """Test canonical coordinate system origin."""
        assert CANONICAL_COORDINATE_SYSTEM.origin == (0.0, 0.0, 0.0)
        assert CANONICAL_COORDINATE_SYSTEM.ground_plane_z == 0.0
    
    def test_positive_direction_descriptions(self):
        """Test positive direction descriptions are defined."""
        assert "upward" in CANONICAL_COORDINATE_SYSTEM.get_positive_direction(Axis.Z)
        assert "right" in CANONICAL_COORDINATE_SYSTEM.get_positive_direction(Axis.X)
        assert "posterior" in CANONICAL_COORDINATE_SYSTEM.get_positive_direction(Axis.Y)
    
    def test_side_determination(self):
        """Test lateral side determination from X coordinate."""
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(1.0) == LateralSide.RIGHT
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(-1.0) == LateralSide.LEFT
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(0.0) == LateralSide.MIDLINE
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(0.0005) == LateralSide.MIDLINE
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(-0.0005) == LateralSide.MIDLINE
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(0.0015) == LateralSide.RIGHT
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(-0.0015) == LateralSide.LEFT


class TestMirrorOperation:
    """Test mirror operation across X = 0 plane."""
    
    def test_mirror_x(self):
        """Test basic mirror operation."""
        coords = (1.0, 2.0, 3.0)
        mirrored = CANONICAL_COORDINATE_SYSTEM.mirror_x(coords)
        assert mirrored == (-1.0, 2.0, 3.0)
    
    def test_mirror_involution(self):
        """Test mirror operation is involutive (mirror(mirror(x)) == x)."""
        test_coords = [
            (1.0, 2.0, 3.0),
            (-1.0, -2.0, -3.0),
            (0.0, 0.0, 0.0),
            (100.0, -50.0, 25.0)
        ]
        
        for coords in test_coords:
            assert CANONICAL_COORDINATE_SYSTEM.is_mirror_involution(coords)
    
    def test_mirror_preserves_y_z(self):
        """Test mirror preserves Y and Z coordinates."""
        coords = (1.0, 2.0, 3.0)
        mirrored = CANONICAL_COORDINATE_SYSTEM.mirror_x(coords)
        
        assert mirrored[1] == coords[1]  # Y preserved
        assert mirrored[2] == coords[2]  # Z preserved
        assert mirrored[0] == -coords[0]  # X inverted
    
    def test_mirror_midline(self):
        """Test mirror of midline coordinate."""
        coords = (0.0, 1.0, 2.0)
        mirrored = CANONICAL_COORDINATE_SYSTEM.mirror_x(coords)
        assert mirrored == coords  # Midline unchanged


class TestTolerance:
    """Test tolerance definitions."""
    
    def test_coordinate_tolerances(self):
        """Test coordinate tolerances are appropriately scaled."""
        assert CANONICAL_TOLERANCE.CRITICAL_MEASUREMENT == 0.001  # 1mm
        assert CANONICAL_TOLERANCE.IMPORTANT_MEASUREMENT == 0.002  # 2mm
        assert CANONICAL_TOLERANCE.GENERAL_MEASUREMENT == 0.005  # 5mm
        assert CANONICAL_TOLERANCE.BILATERAL_SYMMETRY == 0.002  # 2mm
    
    def test_angular_tolerances(self):
        """Test angular tolerances are appropriately scaled."""
        assert CANONICAL_TOLERANCE.CRITICAL_ANGLE == 2.0
        assert CANONICAL_TOLERANCE.IMPORTANT_ANGLE == 3.0
        assert CANONICAL_TOLERANCE.GENERAL_ANGLE == 5.0
    
    def test_proportion_tolerances(self):
        """Test proportion tolerances are appropriately scaled."""
        assert CANONICAL_TOLERANCE.CRITICAL_PROPORTION == 0.05  # 5%
        assert CANONICAL_TOLERANCE.IMPORTANT_PROPORTION == 0.10  # 10%
        assert CANONICAL_TOLERANCE.GENERAL_PROPORTION == 0.15  # 15%
    
    def test_floating_point_tolerances(self):
        """Test floating-point tolerances."""
        assert CANONICAL_TOLERANCE.FLOAT_COMPARISON == 1e-9
        assert CANONICAL_TOLERANCE.ZERO_THRESHOLD == 1e-6


class TestUnitConverter:
    """Test unit conversion utilities."""
    
    def test_meters_to_millimeters(self):
        """Test meters to millimeters conversion."""
        assert UNIT_CONVERTER.meters_to_millimeters(1.0) == 1000.0
        assert UNIT_CONVERTER.meters_to_millimeters(0.5) == 500.0
        assert UNIT_CONVERTER.meters_to_millimeters(0.001) == 1.0
    
    def test_millimeters_to_meters(self):
        """Test millimeters to meters conversion."""
        assert UNIT_CONVERTER.millimeters_to_meters(1000.0) == 1.0
        assert UNIT_CONVERTER.millimeters_to_meters(500.0) == 0.5
        assert UNIT_CONVERTER.millimeters_to_meters(1.0) == 0.001
    
    def test_meters_to_centimeters(self):
        """Test meters to centimeters conversion."""
        assert UNIT_CONVERTER.meters_to_centimeters(1.0) == 100.0
        assert UNIT_CONVERTER.meters_to_centimeters(0.5) == 50.0
    
    def test_centimeters_to_meters(self):
        """Test centimeters to meters conversion."""
        assert UNIT_CONVERTER.centimeters_to_meters(100.0) == 1.0
        assert UNIT_CONVERTER.centimeters_to_meters(50.0) == 0.5
    
    def test_degrees_to_radians(self):
        """Test degrees to radians conversion."""
        assert abs(UNIT_CONVERTER.degrees_to_radians(180.0) - math.pi) < 1e-9
        assert abs(UNIT_CONVERTER.degrees_to_radians(90.0) - math.pi/2) < 1e-9
        assert abs(UNIT_CONVERTER.degrees_to_radians(0.0) - 0.0) < 1e-9
    
    def test_radians_to_degrees(self):
        """Test radians to degrees conversion."""
        assert abs(UNIT_CONVERTER.radians_to_degrees(math.pi) - 180.0) < 1e-6
        assert abs(UNIT_CONVERTER.radians_to_degrees(math.pi/2) - 90.0) < 1e-6
        assert abs(UNIT_CONVERTER.radians_to_degrees(0.0) - 0.0) < 1e-6


class TestValidationFunctions:
    """Test coordinate system validation functions."""
    
    def test_validate_coordinate_system(self):
        """Test coordinate system validation."""
        assert validate_coordinate_system() is True
    
    def test_validate_right_handedness(self):
        """Test right-handedness validation."""
        # Standard right-handed check: X × Y should equal Z
        assert validate_right_handedness() is True
    
    def test_rotation_order(self):
        """Test rotation order definition."""
        assert get_rotation_order() == "ZYX"
    
    def test_rotation_direction(self):
        """Test rotation direction definition."""
        assert get_rotation_direction() == "counter_clockwise"
    
    def test_is_valid_coordinate(self):
        """Test coordinate validity checking."""
        # Valid coordinates
        assert is_valid_coordinate((1.0, 2.0, 3.0))
        assert is_valid_coordinate((0.0, 0.0, 0.0))
        assert is_valid_coordinate((-1.0, -2.0, -3.0))
        
        # Invalid coordinates (NaN)
        assert not is_valid_coordinate((float('nan'), 2.0, 3.0))
        assert not is_valid_coordinate((1.0, float('nan'), 3.0))
        assert not is_valid_coordinate((1.0, 2.0, float('nan')))
        
        # Invalid coordinates (infinity)
        assert not is_valid_coordinate((float('inf'), 2.0, 3.0))
        assert not is_valid_coordinate((1.0, float('inf'), 3.0))
        assert not is_valid_coordinate((1.0, 2.0, float('inf')))


class TestVectorOperations:
    """Test vector mathematical operations."""
    
    def test_normalize_vector(self):
        """Test vector normalization."""
        # Unit vector
        assert normalize_vector((1.0, 0.0, 0.0)) == (1.0, 0.0, 0.0)
        
        # Non-unit vector
        normalized = normalize_vector((2.0, 0.0, 0.0))
        assert normalized == (1.0, 0.0, 0.0)
        
        # Diagonal vector
        normalized = normalize_vector((1.0, 1.0, 1.0))
        magnitude = math.sqrt(3.0)
        expected = (1.0/magnitude, 1.0/magnitude, 1.0/magnitude)
        for a, b in zip(normalized, expected):
            assert abs(a - b) < 1e-9
    
    def test_normalize_zero_vector(self):
        """Test zero vector normalization."""
        result = normalize_vector((0.0, 0.0, 0.0))
        assert result == (0.0, 0.0, 0.0)
    
    def test_cross_product(self):
        """Test cross product calculation."""
        # X × Y = Z
        x_axis = (1.0, 0.0, 0.0)
        y_axis = (0.0, 1.0, 0.0)
        z_axis = (0.0, 0.0, 1.0)
        
        result = cross_product(x_axis, y_axis)
        for a, b in zip(result, z_axis):
            assert abs(a - b) < 1e-9
        
        # Y × Z = X
        result = cross_product(y_axis, z_axis)
        for a, b in zip(result, x_axis):
            assert abs(a - b) < 1e-9
        
        # Z × X = Y
        result = cross_product(z_axis, x_axis)
        for a, b in zip(result, y_axis):
            assert abs(a - b) < 1e-9
    
    def test_cross_product_anticommutative(self):
        """Test cross product anticommutativity (a × b = -(b × a))."""
        a = (1.0, 2.0, 3.0)
        b = (4.0, 5.0, 6.0)
        
        ab = cross_product(a, b)
        ba = cross_product(b, a)
        
        for a_val, b_val in zip(ab, ba):
            assert abs(a_val + b_val) < 1e-9


class TestCoordinateSystemIntegration:
    """Integration tests for coordinate system."""
    
    def test_bilateral_symmetry_tolerance(self):
        """Test bilateral symmetry tolerance is appropriate."""
        # Left and right coordinates should be within tolerance
        left_coords = (-0.1, 1.0, 2.0)
        right_coords = (0.1, 1.0, 2.0)
        
        # Mirror left to right
        mirrored = CANONICAL_COORDINATE_SYSTEM.mirror_x(left_coords)
        
        # Check within bilateral symmetry tolerance
        for a, b in zip(mirrored, right_coords):
            assert abs(a - b) <= CANONICAL_TOLERANCE.BILATERAL_SYMMETRY
    
    def test_origin_semantics(self):
        """Test origin semantics are consistent."""
        # Origin should be at foot midline ground level
        origin = CANONICAL_COORDINATE_SYSTEM.origin
        assert origin == (0.0, 0.0, 0.0)
        assert origin[2] == CANONICAL_COORDINATE_SYSTEM.ground_plane_z
    
    def test_world_space_semantics(self):
        """Test world-space semantics."""
        # All coordinates should be in world-space (no local transforms)
        # This is a design constraint - test ensures we maintain this
        test_coords = (1.0, 2.0, 3.0)
        
        # Mirror operation should work on world coordinates
        mirrored = CANONICAL_COORDINATE_SYSTEM.mirror_x(test_coords)
        assert mirrored is not None
        assert len(mirrored) == 3


class TestCoordinateSystemConstraints:
    """Test coordinate system constraints and invariants."""
    
    def test_invalid_axes_combination(self):
        """Test that invalid axis combinations are rejected."""
        with pytest.raises(ValueError):
            # All axes being the same should fail
            CoordinateSystem(
                up_axis=Axis.X,
                lateral_axis=Axis.X,
                anterior_posterior_axis=Axis.X
            )
    
    def test_coordinate_system_immutability(self):
        """Test coordinate system is immutable (frozen dataclass)."""
        # This test ensures we can't accidentally modify the canonical system
        with pytest.raises(Exception):  # FrozenInstanceError
            CANONICAL_COORDINATE_SYSTEM.up_axis = Axis.Y
    
    def test_tolerance_immutability(self):
        """Test tolerance definitions are immutable (frozen dataclass)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            CANONICAL_TOLERANCE.CRITICAL_MEASUREMENT = 0.002


class TestCoordinateSystemCompatibility:
    """Test compatibility with existing repository conventions."""
    
    def test_z_up_compatibility(self):
        """Test Z-up convention matches existing data."""
        # Current data uses Z-up (feet at Z=0)
        assert CANONICAL_COORDINATE_SYSTEM.up_axis == Axis.Z
        assert CANONICAL_COORDINATE_SYSTEM.ground_plane_z == 0.0
    
    def test_meter_units_compatibility(self):
        """Test meter units match existing data."""
        # Current data uses meters
        assert CANONICAL_COORDINATE_SYSTEM.linear_unit == LinearUnit.METERS
    
    def test_right_handed_compatibility(self):
        """Test right-handedness matches existing convention."""
        # Current system is right-handed
        assert CANONICAL_COORDINATE_SYSTEM.is_right_handed()
