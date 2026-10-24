"""Vector3 – matemáticas puras."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> 'Vector3':
        return Vector3(-self.x, -self.y, -self.z)

    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> 'Vector3':
        l = self.length()
        return Vector3(self.x/l, self.y/l, self.z/l) if l > 0 else Vector3(0,0,0)

    def distance_to(self, other: 'Vector3') -> float:
        return (self - other).length()

    def dot(self, other: 'Vector3') -> float:
        return self.x*other.x + self.y*other.y + self.z*other.z

    def cross(self, other: 'Vector3') -> 'Vector3':
        return Vector3(
            self.y*other.z - self.z*other.y,
            self.z*other.x - self.x*other.z,
            self.x*other.y - self.y*other.x
        )

    @staticmethod
    def zero() -> 'Vector3':
        return Vector3(0, 0, 0)

    def is_finite(self) -> bool:
        """Check if all components are finite (no NaN or Inf).

        Provenance: PROVEN (standard finite check)
        """
        return all(math.isfinite(c) for c in (self.x, self.y, self.z))
