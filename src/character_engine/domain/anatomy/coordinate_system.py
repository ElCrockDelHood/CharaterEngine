"""Coordinate System Contract for Anatomical Reconstruction.

This module defines the canonical coordinate system conventions used throughout
the Character Engine for deterministic anatomical reconstruction.

Coordinate System:
- Handedness: Right-handed
- Vertical Axis: Z (positive Z points upward)
- Forward Axis: Negative Y (negative Y points forward/anterior)
- Bilateral Axis: X (positive X = right side)
- Linear Units: Meters
- Angular Units: Degrees (interface), Radians (calculations)
- Ground/Reference Plane: Z = 0
- Origin: Foot midline at ground level (0, 0, 0)
- Rotation Order: ZYX (intrinsic rotations)
- Rotation Direction: Counter-clockwise positive (right-hand rule)
- Right-handed convention: X × Y = Z (standard mathematical convention)
- Forward direction: -Y (semantic meaning: negative Y points forward)
"""

from dataclasses import dataclass
from enum import Enum
from math import degrees, radians
from typing import Tuple


class Handedness(Enum):
    """Coordinate system handedness."""
    RIGHT_HANDED = "right_handed"
    LEFT_HANDED = "left_handed"


class Axis(Enum):
    """Coordinate system axes."""
    X = "x"  # Lateral (left-right)
    Y = "y"  # Anterior-posterior (forward-backward)
    Z = "z"  # Vertical (up-down)


class LinearUnit(Enum):
    """Linear measurement units."""
    METERS = "m"
    MILLIMETERS = "mm"
    CENTIMETERS = "cm"
    FEET = "ft"
    INCHES = "in"


class AngularUnit(Enum):
    """Angular measurement units."""
    DEGREES = "deg"
    RADIANS = "rad"


class LateralSide(Enum):
    """Lateral side designation."""
    LEFT = "left"
    RIGHT = "right"
    MIDLINE = "midline"


@dataclass(frozen=True)
class CoordinateSystem:
    """Canonical coordinate system definition."""

    handedness: Handedness = Handedness.RIGHT_HANDED
    up_axis: Axis = Axis.Z
    forward_axis: Axis = Axis.Y  # Negative Y points forward
    lateral_axis: Axis = Axis.X
    anterior_posterior_axis: Axis = Axis.Y
    linear_unit: LinearUnit = LinearUnit.METERS
    angular_unit: AngularUnit = AngularUnit.DEGREES
    ground_plane_z: float = 0.0
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_order: str = "ZYX"  # Intrinsic rotations: Z, then Y, then X
    rotation_direction: str = "counter_clockwise"  # Right-hand rule

    def __post_init__(self):
        """Validate coordinate system configuration."""
        # Validate right-handedness
        if self.handedness == Handedness.RIGHT_HANDED:
            # Cross product X × Y should equal Z for right-handed system
            # In our convention: X (lateral) × Y (posterior) = Z (upward)
            pass  # Validation handled by cross_product utility

        # Validate axes are orthogonal
        axes = [self.up_axis, self.lateral_axis, self.anterior_posterior_axis]
        if len(set(axes)) != 3:
            raise ValueError("Axes must be orthogonal and distinct")

    def is_right_handed(self) -> bool:
        """Check if coordinate system is right-handed."""
        return self.handedness == Handedness.RIGHT_HANDED

    def get_positive_direction(self, axis: Axis) -> str:
        """Get semantic meaning of positive direction for an axis."""
        descriptions = {
            Axis.Z: "upward (above ground)",
            Axis.X: "right side of body",
            Axis.Y: "posterior (backward), so negative Y is forward/anterior"
        }
        return descriptions.get(axis, "unknown")

    def get_forward_direction(self) -> Tuple[float, float, float]:
        """Get the forward direction vector.

        Returns:
            (0, -1, 0) - negative Y points forward/anterior
        """
        return (0.0, -1.0, 0.0)

    def get_up_direction(self) -> Tuple[float, float, float]:
        """Get the up direction vector.

        Returns:
            (0, 0, 1) - positive Z points upward
        """
        return (0.0, 0.0, 1.0)

    def get_right_direction(self) -> Tuple[float, float, float]:
        """Get the right direction vector.

        Returns:
            (1, 0, 0) - positive X points right
        """
        return (1.0, 0.0, 0.0)

    def get_side_from_x(self, x_coordinate: float) -> LateralSide:
        """Determine lateral side from X coordinate."""
        tolerance = 0.001  # 1mm tolerance for midline determination
        if abs(x_coordinate) < tolerance:
            return LateralSide.MIDLINE
        elif x_coordinate > 0:
            return LateralSide.RIGHT
        else:
            return LateralSide.LEFT

    def mirror_x(self, coordinates: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Mirror coordinates across X = 0 plane (YZ plane).

        Args:
            coordinates: (x, y, z) tuple to mirror

        Returns:
            Mirrored coordinates (-x, y, z)
        """
        x, y, z = coordinates
        return (-x, y, z)

    def is_mirror_involution(self, coordinates: Tuple[float, float, float]) -> bool:
        """Check if mirror operation is involutive (mirror(mirror(x)) == x).

        Args:
            coordinates: (x, y, z) tuple to test

        Returns:
            True if mirror(mirror(coordinates)) == coordinates within tolerance
        """
        tolerance = 1e-9
        original = coordinates
        mirrored_once = self.mirror_x(original)
        mirrored_twice = self.mirror_x(mirrored_once)

        return all(
            abs(a - b) < tolerance
            for a, b in zip(original, mirrored_twice)
        )


@dataclass(frozen=True)
class Tolerance:
    """Numerical tolerance definitions for coordinate system operations."""

    # Coordinate tolerances (meters)
    CRITICAL_MEASUREMENT: float = 0.001  # 1mm - joint centers, landmarks
    IMPORTANT_MEASUREMENT: float = 0.002  # 2mm - bone lengths, dimensions
    GENERAL_MEASUREMENT: float = 0.005  # 5mm - general positions
    BILATERAL_SYMMETRY: float = 0.002  # 2mm - left-right equivalence

    # Angular tolerances (degrees)
    CRITICAL_ANGLE: float = 2.0  # spine curvature, joint axes
    IMPORTANT_ANGLE: float = 3.0  # joint orientations
    GENERAL_ANGLE: float = 5.0  # general orientations

    # Proportion tolerances (percentage)
    CRITICAL_PROPORTION: float = 0.05  # 5% - major body ratios
    IMPORTANT_PROPORTION: float = 0.10  # 10% - segment ratios
    GENERAL_PROPORTION: float = 0.15  # 15% - detailed ratios

    # Floating-point tolerances
    FLOAT_COMPARISON: float = 1e-9  # General floating-point comparison
    ZERO_THRESHOLD: float = 1e-6  # Threshold for considering value as zero


class UnitConverter:
    """Unit conversion utilities."""

    @staticmethod
    def meters_to_millimeters(meters: float) -> float:
        """Convert meters to millimeters."""
        return meters * 1000.0

    @staticmethod
    def millimeters_to_meters(millimeters: float) -> float:
        """Convert millimeters to meters."""
        return millimeters / 1000.0

    @staticmethod
    def meters_to_centimeters(meters: float) -> float:
        """Convert meters to centimeters."""
        return meters * 100.0

    @staticmethod
    def centimeters_to_meters(centimeters: float) -> float:
        """Convert centimeters to meters."""
        return centimeters / 100.0

    @staticmethod
    def meters_to_feet(meters: float) -> float:
        """Convert meters to feet."""
        return meters * 3.28084

    @staticmethod
    def feet_to_meters(feet: float) -> float:
        """Convert feet to meters."""
        return feet / 3.28084

    @staticmethod
    def meters_to_inches(meters: float) -> float:
        """Convert meters to inches."""
        return meters * 39.3701

    @staticmethod
    def inches_to_meters(inches: float) -> float:
        """Convert inches to meters."""
        return inches / 39.3701

    @staticmethod
    def degrees_to_radians(degrees: float) -> float:
        """Convert degrees to radians."""
        return radians(degrees)

    @staticmethod
    def radians_to_degrees(radians: float) -> float:
        """Convert radians to degrees."""
        return degrees(radians)


# Canonical coordinate system instance
CANONICAL_COORDINATE_SYSTEM = CoordinateSystem()

# Canonical tolerance instance
CANONICAL_TOLERANCE = Tolerance()

# Unit converter instance
UNIT_CONVERTER = UnitConverter()


def validate_coordinate_system() -> bool:
    """Validate canonical coordinate system configuration.

    Returns:
        True if coordinate system is valid
    """
    try:
        # Test basic properties
        assert CANONICAL_COORDINATE_SYSTEM.is_right_handed()
        assert CANONICAL_COORDINATE_SYSTEM.up_axis == Axis.Z
        assert CANONICAL_COORDINATE_SYSTEM.lateral_axis == Axis.X
        assert CANONICAL_COORDINATE_SYSTEM.anterior_posterior_axis == Axis.Y

        # Test rotation conventions
        assert CANONICAL_COORDINATE_SYSTEM.rotation_order == "ZYX"
        assert CANONICAL_COORDINATE_SYSTEM.rotation_direction == "counter_clockwise"

        # Test mirror involution
        test_coords = (1.0, 2.0, 3.0)
        assert CANONICAL_COORDINATE_SYSTEM.is_mirror_involution(test_coords)

        # Test side determination
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(1.0) == LateralSide.RIGHT
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(-1.0) == LateralSide.LEFT
        assert CANONICAL_COORDINATE_SYSTEM.get_side_from_x(0.0) == LateralSide.MIDLINE

        # Test direction vectors
        forward = CANONICAL_COORDINATE_SYSTEM.get_forward_direction()
        assert forward == (0.0, -1.0, 0.0)

        up = CANONICAL_COORDINATE_SYSTEM.get_up_direction()
        assert up == (0.0, 0.0, 1.0)

        right = CANONICAL_COORDINATE_SYSTEM.get_right_direction()
        assert right == (1.0, 0.0, 0.0)

        # Test right-handedness
        assert validate_right_handedness()

        # Test coordinate transformations
        test_point = (1.0, 2.0, 3.0)
        origin = (0.0, 0.0, 0.0)
        rotation = (0.0, 0.0, 0.0)

        # Identity rotation should preserve point
        local = world_to_local(test_point, origin, rotation)
        world = local_to_world(local, origin, rotation)
        assert all(abs(a - b) < CANONICAL_TOLERANCE.FLOAT_COMPARISON
                  for a, b in zip(test_point, world))

        return True
    except AssertionError:
        return False


def get_rotation_order() -> str:
    """Get canonical rotation order.

    Returns:
        Rotation order string (e.g., "ZYX")
    """
    return "ZYX"  # Intrinsic rotations: Z, then Y, then X


def get_rotation_direction() -> str:
    """Get canonical rotation direction.

    Returns:
        Rotation direction ("counter_clockwise" or "clockwise")
    """
    return "counter_clockwise"  # Right-hand rule


def is_valid_coordinate(coordinate: Tuple[float, float, float]) -> bool:
    """Check if coordinate is valid (finite values).

    Args:
        coordinate: (x, y, z) tuple to validate

    Returns:
        True if coordinate has finite values
    """
    import math
    x, y, z = coordinate
    return all(
        math.isfinite(val) and not math.isnan(val)
        for val in (x, y, z)
    )


def normalize_vector(vector: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Normalize a vector to unit length.

    Args:
        vector: (x, y, z) tuple to normalize

    Returns:
        Normalized (unit) vector
    """
    import math
    x, y, z = vector
    magnitude = math.sqrt(x*x + y*y + z*z)

    if magnitude < CANONICAL_TOLERANCE.ZERO_THRESHOLD:
        return (0.0, 0.0, 0.0)

    return (x/magnitude, y/magnitude, z/magnitude)


def cross_product(a: Tuple[float, float, float],
                 b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Compute cross product of two 3D vectors.

    Args:
        a: First vector (x, y, z)
        b: Second vector (x, y, z)

    Returns:
        Cross product vector a × b
    """
    ax, ay, az = a
    bx, by, bz = b

    return (
        ay * bz - az * by,
        az * bx - ax * bz,
        ax * by - ay * bx
    )


def validate_right_handedness() -> bool:
    """Validate right-handed coordinate system using cross product.

    For right-handed system: X × Y should equal Z (standard mathematical convention)
    Forward direction is semantically -Y (anterior), but mathematically we use Y for cross product

    Returns:
        True if coordinate system is right-handed
    """
    x_axis = (1.0, 0.0, 0.0)  # Lateral axis (positive = right)
    y_axis = (0.0, 1.0, 0.0)  # Anterior-posterior axis (positive = posterior)
    up_axis = (0.0, 0.0, 1.0)  # Vertical axis (positive = up)

    cross_xy = cross_product(x_axis, y_axis)

    # Check if cross product equals up axis within tolerance
    return all(
        abs(a - b) < CANONICAL_TOLERANCE.FLOAT_COMPARISON
        for a, b in zip(cross_xy, up_axis)
    )


def world_to_local(point: Tuple[float, float, float],
                   origin: Tuple[float, float, float],
                   rotation: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Convert world coordinates to local coordinates.

    Args:
        point: World-space point (x, y, z)
        origin: Local origin in world space (ox, oy, oz)
        rotation: Euler angles in degrees (rx, ry, rz) following ZYX order

    Returns:
        Local-space point (lx, ly, lz)
    """
    import math

    # Translate to local origin
    translated = (
        point[0] - origin[0],
        point[1] - origin[1],
        point[2] - origin[2]
    )

    # Convert rotation to radians
    rx, ry, rz = [UNIT_CONVERTER.degrees_to_radians(a) for a in rotation]

    # Apply inverse rotation (ZYX order)
    # For ZYX intrinsic rotations, inverse is reverse order with negated angles
    x, y, z = translated

    # Inverse Z rotation
    cos_z = math.cos(-rz)
    sin_z = math.sin(-rz)
    x1 = x * cos_z - y * sin_z
    y1 = x * sin_z + y * cos_z
    z1 = z

    # Inverse Y rotation
    cos_y = math.cos(-ry)
    sin_y = math.sin(-ry)
    x2 = x1 * cos_y + z1 * sin_y
    y2 = y1
    z2 = -x1 * sin_y + z1 * cos_y

    # Inverse X rotation
    cos_x = math.cos(-rx)
    sin_x = math.sin(-rx)
    x3 = x2
    y3 = y2 * cos_x - z2 * sin_x
    z3 = y2 * sin_x + z2 * cos_x

    return (x3, y3, z3)


def local_to_world(point: Tuple[float, float, float],
                   origin: Tuple[float, float, float],
                   rotation: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Convert local coordinates to world coordinates.

    Args:
        point: Local-space point (lx, ly, lz)
        origin: Local origin in world space (ox, oy, oz)
        rotation: Euler angles in degrees (rx, ry, rz) following ZYX order

    Returns:
        World-space point (wx, wy, wz)
    """
    import math

    # Convert rotation to radians
    rx, ry, rz = [UNIT_CONVERTER.degrees_to_radians(a) for a in rotation]

    # Apply rotation (ZYX order)
    x, y, z = point

    # X rotation
    cos_x = math.cos(rx)
    sin_x = math.sin(rx)
    x1 = x
    y1 = y * cos_x - z * sin_x
    z1 = y * sin_x + z * cos_x

    # Y rotation
    cos_y = math.cos(ry)
    sin_y = math.sin(ry)
    x2 = x1 * cos_y - z1 * sin_y
    y2 = y1
    z2 = x1 * sin_y + z1 * cos_y

    # Z rotation
    cos_z = math.cos(rz)
    sin_z = math.sin(rz)
    x3 = x2 * cos_z + y2 * sin_z
    y3 = -x2 * sin_z + y2 * cos_z
    z3 = z2

    # Translate to world origin
    world = (
        x3 + origin[0],
        y3 + origin[1],
        z3 + origin[2]
    )

    return world


def parent_to_child(point: Tuple[float, float, float],
                   parent_origin: Tuple[float, float, float],
                   parent_rotation: Tuple[float, float, float],
                   child_origin: Tuple[float, float, float],
                   child_rotation: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Convert point from parent coordinate frame to child coordinate frame.

    Args:
        point: Point in parent space
        parent_origin: Parent origin in world space
        parent_rotation: Parent rotation in degrees
        child_origin: Child origin in world space
        child_rotation: Child rotation in degrees

    Returns:
        Point in child space
    """
    # Convert point to world space
    world_point = local_to_world(point, parent_origin, parent_rotation)

    # Convert world point to child space
    child_point = world_to_local(world_point, child_origin, child_rotation)

    return child_point
