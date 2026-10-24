"""Quaternion – complete algebraic operations with unit quaternion support.

Contract: CE-Q1 CANONICAL QUATERNION AND MANIFOLD CONTRACT
- Quaternion: general 4D hypercomplex number
- UnitQuaternion: subset with ||q|| = 1 (S³ manifold)
- Double cover: q ~ -q (canonicalized to w ≥ 0)
- Euler angles: boundary only, NOT for internal calculations
"""

import math
from dataclasses import dataclass

from .vector3 import Vector3

# Numerical tolerances (CE-Q1 contract)
# Provenance: DERIVED from FLOAT_COMPARISON in coordinate_system.py
NORM_TOLERANCE = 1e-9  # Unit-norm check; ||q|| below this is degenerate (Decision 22 / D-02)
EQUALITY_TOLERANCE = 1e-9  # Tolerance for quaternion equality


class DegenerateQuaternionError(ValueError):
    """Raised when an operation needs a non-zero quaternion and ||q|| < NORM_TOLERANCE.

    Decision 22 (D-02): degenerate input is an error, never a silent identity.
    """


@dataclass(frozen=True)
class Quaternion:
    """General quaternion (w, x, y, z) representing 4D hypercomplex number.

    This is the general quaternion class. For canonical orientation representation,
    use UnitQuaternion which enforces unit norm and double cover canonicalization.

    Provenance: PROVEN (standard definition)
    """
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def norm(self) -> float:
        """Compute Euclidean norm: ||q|| = sqrt(w² + x² + y² + z²).

        Provenance: PROVEN (standard definition)
        """
        return math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> 'Quaternion':
        """Normalize quaternion to unit norm.

        Raises DegenerateQuaternionError when ||q|| < NORM_TOLERANCE (Decision 22).

        Provenance: PROVEN (standard normalization)
        """
        n = self.norm()
        if n < NORM_TOLERANCE:
            raise DegenerateQuaternionError(f"cannot normalize a degenerate quaternion (||q|| = {n:.3e})")
        return Quaternion(self.w/n, self.x/n, self.y/n, self.z/n)

    def conjugate(self) -> 'Quaternion':
        """Compute conjugate: q* = (w, -x, -y, -z).

        Provenance: PROVEN (standard definition)
        """
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def inverse(self) -> 'Quaternion':
        """Compute inverse: q⁻¹ = q* / ||q||² (so q * q⁻¹ = 1 for any non-zero q; Decision 21).

        Raises DegenerateQuaternionError when ||q|| < NORM_TOLERANCE (Decision 22).

        Provenance: PROVEN (standard definition)
        """
        n = self.norm()
        if n < NORM_TOLERANCE:
            raise DegenerateQuaternionError(f"cannot invert a degenerate quaternion (||q|| = {n:.3e})")
        n2 = n * n
        return Quaternion(self.w / n2, -self.x / n2, -self.y / n2, -self.z / n2)

    def __mul__(self, other: 'Quaternion') -> 'Quaternion':
        """Hamilton product: q₁ * q₂.

        Provenance: PROVEN (standard Hamilton product)
        """
        return Quaternion(
            self.w*other.w - self.x*other.x - self.y*other.y - self.z*other.z,
            self.w*other.x + self.x*other.w + self.y*other.z - self.z*other.y,
            self.w*other.y - self.x*other.z + self.y*other.w + self.z*other.x,
            self.w*other.z + self.x*other.y - self.y*other.x + self.z*other.w
        )

    def dot(self, other: 'Quaternion') -> float:
        """Dot product: q₁ · q₂ = w₁w₂ + x₁x₂ + y₁y₂ + z₁z₂.

        Provenance: PROVEN (standard dot product)
        """
        return self.w*other.w + self.x*other.x + self.y*other.y + self.z*other.z

    def rotate(self, v: Vector3) -> Vector3:
        """Rotate vector v by quaternion: q ⊙ v = q * (0, v) * q⁻¹.

        Raises DegenerateQuaternionError for a degenerate quaternion (Decision 22).

        Provenance: PROVEN (standard quaternion rotation)
        """
        q = self.normalize()
        p = Quaternion(0, v.x, v.y, v.z)
        r = q * p * q.inverse()
        return Vector3(r.x, r.y, r.z)

    def is_finite(self) -> bool:
        """Check if all components are finite (no NaN or Inf).

        Provenance: PROVEN (standard finite check)
        """
        return all(math.isfinite(c) for c in (self.w, self.x, self.y, self.z))

    @staticmethod
    def identity() -> 'Quaternion':
        """Identity quaternion: (1, 0, 0, 0).

        Provenance: PROVEN (standard definition)
        """
        return Quaternion(1, 0, 0, 0)

    @staticmethod
    def zero() -> 'Quaternion':
        """Zero quaternion: (0, 0, 0, 0).

        Provenance: PROVEN (standard definition)
        """
        return Quaternion(0, 0, 0, 0)

    @staticmethod
    def from_axis_angle(axis: Vector3, angle_rad: float) -> 'Quaternion':
        """Create quaternion from axis-angle representation.

        q = (cos(θ/2), sin(θ/2) * axis)

        Provenance: PROVEN (standard axis-angle to quaternion)
        """
        if not axis.is_finite() or not math.isfinite(angle_rad):
            raise ValueError("Axis and angle must be finite")

        half_angle = angle_rad / 2.0
        sin_half = math.sin(half_angle)
        cos_half = math.cos(half_angle)

        axis_normalized = axis.normalize()

        return Quaternion(
            cos_half,
            axis_normalized.x * sin_half,
            axis_normalized.y * sin_half,
            axis_normalized.z * sin_half
        )


@dataclass(frozen=True)
class UnitQuaternion:
    """Unit quaternion: subset of Quaternion with ||q|| = 1 (S³ manifold).

    This is the canonical representation of 3D orientation in Character Engine.
    Enforces unit norm and double cover canonicalization (w ≥ 0).

    Contract: CE-Q1
    - Manifold: S³ (unit quaternions)
    - Double cover: q ~ -q (canonicalized to w ≥ 0)
    - Physical rotation: SO(3) (via q ⊙ v)

    Provenance: PROVEN (CE-Q1 contract)
    """
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self):
        """Enforce unit norm and canonicalize double cover (w ≥ 0)."""
        # Check if components are finite
        if not all(math.isfinite(c) for c in (self.w, self.x, self.y, self.z)):
            raise ValueError(f"UnitQuaternion components must be finite: got ({self.w}, {self.x}, {self.y}, {self.z})")

        # Compute norm
        norm = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)

        # Check degenerate quaternion
        if norm < NORM_TOLERANCE:
            raise DegenerateQuaternionError("Cannot create UnitQuaternion from a degenerate quaternion")

        # Check unit norm tolerance
        if abs(norm - 1.0) > NORM_TOLERANCE:
            raise ValueError(f"UnitQuaternion must have unit norm (||q|| = 1), got ||q|| = {norm:.15f}")

        # Canonicalize double cover: ensure w ≥ 0
        # If w < 0, negate all components (q and -q represent same rotation)
        if self.w < 0:
            object.__setattr__(self, 'w', -self.w)
            object.__setattr__(self, 'x', -self.x)
            object.__setattr__(self, 'y', -self.y)
            object.__setattr__(self, 'z', -self.z)

    def norm(self) -> float:
        """Compute norm (should always be 1.0 within tolerance).

        Provenance: PROVEN (standard definition)
        """
        return math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)

    def conjugate(self) -> 'UnitQuaternion':
        """Compute conjugate: q* = (w, -x, -y, -z).

        For unit quaternions, q⁻¹ = q*.

        Provenance: PROVEN (standard definition)
        """
        return UnitQuaternion(self.w, -self.x, -self.y, -self.z)

    def inverse(self) -> 'UnitQuaternion':
        """Compute inverse: q⁻¹ = q* (for unit quaternions).

        Provenance: PROVEN (standard definition for unit quaternions)
        """
        return self.conjugate()

    def __mul__(self, other: 'UnitQuaternion') -> 'UnitQuaternion':
        """Hamilton product (composition of rotations).

        Result is renormalized to maintain unit norm.

        Provenance: PROVEN (standard Hamilton product)
        """
        result = Quaternion(
            self.w*other.w - self.x*other.x - self.y*other.y - self.z*other.z,
            self.w*other.x + self.x*other.w + self.y*other.z - self.z*other.y,
            self.w*other.y - self.x*other.z + self.y*other.w + self.z*other.x,
            self.w*other.z + self.x*other.y - self.y*other.x + self.z*other.w
        )
        return UnitQuaternion.from_quaternion(result)

    def dot(self, other: 'UnitQuaternion') -> float:
        """Dot product.

        Provenance: PROVEN (standard dot product)
        """
        return self.w*other.w + self.x*other.x + self.y*other.y + self.z*other.z

    def rotate(self, v: Vector3) -> Vector3:
        """Rotate vector v: q ⊙ v = q * (0, v) * q⁻¹.

        Provenance: PROVEN (standard quaternion rotation)
        """
        p = Quaternion(0, v.x, v.y, v.z)
        r = Quaternion(self.w, self.x, self.y, self.z) * p * self.conjugate()
        return Vector3(r.x, r.y, r.z)

    def is_finite(self) -> bool:
        """Check if all components are finite (always true for UnitQuaternion).

        Provenance: PROVEN (standard finite check)
        """
        return True  # Enforced in __post_init__

    def equals(self, other: 'UnitQuaternion', tolerance: float = EQUALITY_TOLERANCE) -> bool:
        """Check equality accounting for double cover (q ≡ -q).

        Provenance: DERIVED (from canonicalization and tolerance)
        """
        # Anti-aliasing: q₁ ≡ q₂ if canonical(q₁) = canonical(q₂)
        # Since both are canonicalized (w ≥ 0), direct comparison is sufficient
        return (abs(self.w - other.w) < tolerance and
                abs(self.x - other.x) < tolerance and
                abs(self.y - other.y) < tolerance and
                abs(self.z - other.z) < tolerance)

    @staticmethod
    def identity() -> 'UnitQuaternion':
        """Identity quaternion: (1, 0, 0, 0).

        Provenance: PROVEN (standard definition)
        """
        return UnitQuaternion(1, 0, 0, 0)

    @staticmethod
    def from_quaternion(q: Quaternion) -> 'UnitQuaternion':
        """Create UnitQuaternion from general Quaternion.

        Normalizes and canonicalizes to w ≥ 0.

        Provenance: DERIVED (from unit enforcement and canonicalization)
        """
        # Check finite
        if not q.is_finite():
            raise ValueError(f"Cannot create UnitQuaternion from non-finite quaternion: ({q.w}, {q.x}, {q.y}, {q.z})")

        # Normalize
        normalized = q.normalize()

        # Canonicalize to w ≥ 0
        if normalized.w < 0:
            normalized = Quaternion(-normalized.w, -normalized.x, -normalized.y, -normalized.z)

        return UnitQuaternion(normalized.w, normalized.x, normalized.y, normalized.z)

    @staticmethod
    def from_axis_angle(axis: Vector3, angle_rad: float) -> 'UnitQuaternion':
        """Create unit quaternion from axis-angle representation.

        q = (cos(θ/2), sin(θ/2) * axis)

        Provenance: PROVEN (standard axis-angle to quaternion)
        """
        if not axis.is_finite() or not math.isfinite(angle_rad):
            raise ValueError("Axis and angle must be finite")

        half_angle = angle_rad / 2.0
        sin_half = math.sin(half_angle)
        cos_half = math.cos(half_angle)

        axis_normalized = axis.normalize()

        return UnitQuaternion(
            cos_half,
            axis_normalized.x * sin_half,
            axis_normalized.y * sin_half,
            axis_normalized.z * sin_half
        )

    @staticmethod
    def from_euler_zyx(roll_deg: float, pitch_deg: float, yaw_deg: float) -> 'UnitQuaternion':
        """Create unit quaternion from Euler angles (ZYX intrinsic, degrees).

        This is a BOUNDARY OPERATION ONLY for external systems that require Euler.
        Euler angles are NOT used for internal calculations.

        Rotation order: Z (yaw), then Y (pitch), then X (roll)

        Provenance: PROVEN (standard Euler to quaternion conversion)
        """
        if not all(math.isfinite(a) for a in (roll_deg, pitch_deg, yaw_deg)):
            raise ValueError("Euler angles must be finite")

        # Convert to radians
        roll = math.radians(roll_deg)
        pitch = math.radians(pitch_deg)
        yaw = math.radians(yaw_deg)

        # Half angles
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        # ZYX intrinsic: q = q_z * q_y * q_x
        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy

        return UnitQuaternion.from_quaternion(Quaternion(w, x, y, z))


def slerp(q1: UnitQuaternion, q2: UnitQuaternion, t: float) -> UnitQuaternion:
    """Spherical linear interpolation on S³.

    Interpolates along the geodesic of S³ (constant angular velocity).

    Formula: slerp(q₁, q₂, t) = (sin((1-t)θ) * q₁ + sin(tθ) * q₂) / sin(θ)
    where θ = arccos(q₁ · q₂)

    Double cover handling: uses shorter path (if q₁ · q₂ < 0, uses -q₂)

    Provenance: PROVEN (Ken Shoemake 1985)
    """
    if not math.isfinite(t):
        raise ValueError("Interpolation parameter t must be finite")

    if t < 0.0 or t > 1.0:
        raise ValueError(f"Interpolation parameter t must be in [0, 1], got {t}")

    # Double cover handling: use shorter path
    dot = q1.dot(q2)
    if dot < 0:
        q2 = UnitQuaternion(-q2.w, -q2.x, -q2.y, -q2.z)
        dot = -dot

    # Clamp dot to [-1, 1] to avoid numerical issues
    dot = max(-1.0, min(1.0, dot))

    # Compute angle between quaternions
    theta = math.acos(dot)

    # Handle near-parallel case (θ ≈ 0)
    if theta < 1e-6:
        # Quaternions are nearly identical, use linear interpolation
        return nlerp(q1, q2, t)

    # Compute interpolation
    sin_theta = math.sin(theta)
    w1 = math.sin((1.0 - t) * theta) / sin_theta
    w2 = math.sin(t * theta) / sin_theta

    result = Quaternion(
        w1 * q1.w + w2 * q2.w,
        w1 * q1.x + w2 * q2.x,
        w1 * q1.y + w2 * q2.y,
        w1 * q1.z + w2 * q2.z
    )

    return UnitQuaternion.from_quaternion(result)


def nlerp(q1: UnitQuaternion, q2: UnitQuaternion, t: float) -> UnitQuaternion:
    """Normalized linear interpolation.

    Interpolates linearly in ℝ⁴, then normalizes to unit quaternion.
    Does NOT follow geodesic (angular velocity not constant), but computationally cheaper.

    Double cover handling: uses shorter path (if q₁ · q₂ < 0, uses -q₂)

    Provenance: PROVEN (Jonathan Blow 2002)
    """
    if not math.isfinite(t):
        raise ValueError("Interpolation parameter t must be finite")

    if t < 0.0 or t > 1.0:
        raise ValueError(f"Interpolation parameter t must be in [0, 1], got {t}")

    # Double cover handling: use shorter path
    dot = q1.dot(q2)
    if dot < 0:
        q2 = UnitQuaternion(-q2.w, -q2.x, -q2.y, -q2.z)

    # Linear interpolation
    result = Quaternion(
        (1.0 - t) * q1.w + t * q2.w,
        (1.0 - t) * q1.x + t * q2.x,
        (1.0 - t) * q1.y + t * q2.y,
        (1.0 - t) * q1.z + t * q2.z
    )

    return UnitQuaternion.from_quaternion(result)


def angular_velocity_to_quaternion_derivative(q: UnitQuaternion, omega_world: Vector3) -> Quaternion:
    """Compute dq/dt from angular velocity ω.

    Contract (Decision 26 / D-06): dq/dt = 0.5 * ω_world * q, where ω_world is the angular
    velocity in the SPATIAL (world / parent) frame, treated as the pure quaternion (0, ω).
    Left multiplication matches q_global = q_parent * q_local; a body-frame ω_body would
    give dq/dt = 0.5 * q * ω_body instead.

    Provenance: PROVEN (standard quaternion kinematics)
    """
    if not q.is_finite():
        raise ValueError("Quaternion must be finite")
    if not omega_world.is_finite():
        raise ValueError("Angular velocity must be finite")

    # Treat ω as pure quaternion (0, ω)
    omega_quat = Quaternion(0, omega_world.x, omega_world.y, omega_world.z)

    # Compute dq/dt = 0.5 * ω * q
    dq_dt = omega_quat * Quaternion(q.w, q.x, q.y, q.z)
    dq_dt = Quaternion(0.5 * dq_dt.w, 0.5 * dq_dt.x, 0.5 * dq_dt.y, 0.5 * dq_dt.z)

    return dq_dt


def integrate_quaternion_angular_velocity(
    q: UnitQuaternion,
    omega_world: Vector3,
    dt: float
) -> UnitQuaternion:
    """Integrate quaternion over time using explicit Euler.

    Contract: q(t + Δt) = normalize(q(t) + Δt * (0.5 * ω_world * q(t))), ω in the spatial
    frame (Decision 26 / D-06).

    Provenance: PROVEN (standard explicit Euler for quaternion integration)
    """
    if not math.isfinite(dt):
        raise ValueError("Timestep dt must be finite")
    if dt < 0:
        raise ValueError(f"Timestep dt must be non-negative, got {dt}")

    # Compute dq/dt
    dq_dt = angular_velocity_to_quaternion_derivative(q, omega_world)

    # Explicit Euler integration
    q_next = Quaternion(
        q.w + dt * dq_dt.w,
        q.x + dt * dq_dt.x,
        q.y + dt * dq_dt.y,
        q.z + dt * dq_dt.z
    )

    # Renormalize to maintain unit norm
    return UnitQuaternion.from_quaternion(q_next)


def geodesic_distance(q1: UnitQuaternion, q2: UnitQuaternion) -> float:
    """Compute geodesic distance on S³.

    Distance = arccos(2(q₁·q₂)² - 1) = 2 * arccos(|q₁·q₂|)

    Provenance: PROVEN (standard geodesic distance on S³)
    """
    # Use absolute dot product to handle double cover
    dot = abs(q1.dot(q2))
    dot = max(-1.0, min(1.0, dot))  # Clamp to [-1, 1]
    return 2.0 * math.acos(dot)
