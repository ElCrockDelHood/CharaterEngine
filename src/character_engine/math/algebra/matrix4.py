"""Matrix4 – completo para transformaciones."""

from dataclasses import dataclass

from .quaternion import Quaternion
from .vector3 import Vector3


@dataclass(frozen=True)
class Matrix4:
    m11: float = 1.0; m12: float = 0.0; m13: float = 0.0; m14: float = 0.0
    m21: float = 0.0; m22: float = 1.0; m23: float = 0.0; m24: float = 0.0
    m31: float = 0.0; m32: float = 0.0; m33: float = 1.0; m34: float = 0.0
    m41: float = 0.0; m42: float = 0.0; m43: float = 0.0; m44: float = 1.0

    @staticmethod
    def translation(v: Vector3) -> 'Matrix4':
        return Matrix4(m14=v.x, m24=v.y, m34=v.z)

    @staticmethod
    def rotation(q: Quaternion) -> 'Matrix4':
        q = q.normalize()
        return Matrix4(
            m11=1 - 2*(q.y**2 + q.z**2),
            m12=2*(q.x*q.y - q.w*q.z),
            m13=2*(q.x*q.z + q.w*q.y),
            m21=2*(q.x*q.y + q.w*q.z),
            m22=1 - 2*(q.x**2 + q.z**2),
            m23=2*(q.y*q.z - q.w*q.x),
            m31=2*(q.x*q.z - q.w*q.y),
            m32=2*(q.y*q.z + q.w*q.x),
            m33=1 - 2*(q.x**2 + q.y**2)
        )

    @staticmethod
    def scale(v: Vector3) -> 'Matrix4':
        return Matrix4(m11=v.x, m22=v.y, m33=v.z)

    def __matmul__(self, other: 'Matrix4') -> 'Matrix4':
        return Matrix4(
            self.m11*other.m11 + self.m12*other.m21 + self.m13*other.m31 + self.m14*other.m41,
            self.m11*other.m12 + self.m12*other.m22 + self.m13*other.m32 + self.m14*other.m42,
            self.m11*other.m13 + self.m12*other.m23 + self.m13*other.m33 + self.m14*other.m43,
            self.m11*other.m14 + self.m12*other.m24 + self.m13*other.m34 + self.m14*other.m44,
            self.m21*other.m11 + self.m22*other.m21 + self.m23*other.m31 + self.m24*other.m41,
            self.m21*other.m12 + self.m22*other.m22 + self.m23*other.m32 + self.m24*other.m42,
            self.m21*other.m13 + self.m22*other.m23 + self.m23*other.m33 + self.m24*other.m43,
            self.m21*other.m14 + self.m22*other.m24 + self.m23*other.m34 + self.m24*other.m44,
            self.m31*other.m11 + self.m32*other.m21 + self.m33*other.m31 + self.m34*other.m41,
            self.m31*other.m12 + self.m32*other.m22 + self.m33*other.m32 + self.m34*other.m42,
            self.m31*other.m13 + self.m32*other.m23 + self.m33*other.m33 + self.m34*other.m43,
            self.m31*other.m14 + self.m32*other.m24 + self.m33*other.m34 + self.m34*other.m44,
            self.m41*other.m11 + self.m42*other.m21 + self.m43*other.m31 + self.m44*other.m41,
            self.m41*other.m12 + self.m42*other.m22 + self.m43*other.m32 + self.m44*other.m42,
            self.m41*other.m13 + self.m42*other.m23 + self.m43*other.m33 + self.m44*other.m43,
            self.m41*other.m14 + self.m42*other.m24 + self.m43*other.m34 + self.m44*other.m44
        )
