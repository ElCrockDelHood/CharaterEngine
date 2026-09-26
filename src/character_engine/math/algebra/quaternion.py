"""Quaternion – completo con operadores."""

from dataclasses import dataclass
import math
from .vector3 import Vector3

@dataclass(frozen=True)
class Quaternion:
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def normalize(self) -> 'Quaternion':
        n = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        if n == 0:
            return Quaternion(1,0,0,0)
        return Quaternion(self.w/n, self.x/n, self.y/n, self.z/n)

    def inverse(self) -> 'Quaternion':
        return Quaternion(self.w, -self.x, -self.y, -self.z).normalize()

    def __mul__(self, other: 'Quaternion') -> 'Quaternion':
        return Quaternion(
            self.w*other.w - self.x*other.x - self.y*other.y - self.z*other.z,
            self.w*other.x + self.x*other.w + self.y*other.z - self.z*other.y,
            self.w*other.y - self.x*other.z + self.y*other.w + self.z*other.x,
            self.w*other.z + self.x*other.y - self.y*other.x + self.z*other.w
        )

    def rotate(self, v: Vector3) -> Vector3:
        q = self.normalize()
        p = Quaternion(0, v.x, v.y, v.z)
        r = q * p * q.inverse()
        return Vector3(r.x, r.y, r.z)

    @staticmethod
    def identity() -> 'Quaternion':
        return Quaternion(1,0,0,0)
