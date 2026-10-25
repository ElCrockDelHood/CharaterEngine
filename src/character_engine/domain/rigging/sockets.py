"""Equipment sockets: named attachment points on canonical bones (CINE-GR-001 step 1).

A socket is a control-layer contract like the rig: it never moves canonical data. Its
placement is ASSUMED (an artistic attachment point, not an anatomical measurement):

* ``along`` — fraction head → tail on the parent bone,
* ``offset_m`` — offset in the canonical frame of the ANATOMICAL position (Z-up, −Y forward,
  left = +X), rotated with the parent bone when the rest pose differs (e.g. T-pose),
* ``direction`` / ``length_m`` — the socket bone's axis (attached items hang along it), also in
  anatomical axes.

Offsets scale with the parent bone length so they follow stature retargeting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Mapping, Sequence, Tuple

from ..anatomy.reference.source import ProvenanceState

Vec = Tuple[float, float, float]


@dataclass(frozen=True)
class EquipmentSocket:
    name: str
    parent_bone: str
    along: float
    offset_m: Vec
    direction: Vec
    length_m: float
    provenance: ProvenanceState = ProvenanceState.ASSUMED
    notes: str = ""


EQUIPMENT_SOCKETS: Tuple[EquipmentSocket, ...] = (
    EquipmentSocket(
        name="SOCKET-sabre_hip.L", parent_bone="COXAL_L", along=1.0,
        offset_m=(0.08, 0.06, 0.0), direction=(0.0, 0.2, -1.0), length_m=0.10,
        notes="Cavalry sabre carried on the left hip (right-hand draw): lateral to the hip joint and "
              "slightly behind the arm plane, hanging down and back. ASSUMED placement."),
    EquipmentSocket(
        name="SOCKET-hand_grip.R", parent_bone="METACARPAL_3_R", along=0.5,
        offset_m=(0.0, -0.02, 0.0), direction=(-1.0, 0.0, 0.0), length_m=0.05,
        notes="Right-hand grip on the palmar side of the third metacarpal (palm faces −Y in the "
              "anatomical position). A held blade runs through the grip channel of the fist, from the "
              "little-finger side to the index side: METACARPAL_5_R -> METACARPAL_2_R = -X in the anatomical "
              "position (Decision 48; previously along the fingers). ASSUMED placement."),
)


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _norm(v: Vec) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _unit(v: Vec) -> Vec:
    n = _norm(v)
    if n == 0:
        raise ValueError("zero-length vector")
    return (v[0] / n, v[1] / n, v[2] / n)


def _rotation_between(a: Vec, b: Vec):
    """Rotation matrix taking unit vector a onto unit vector b (Rodrigues; minimal rotation)."""
    a, b = _unit(a), _unit(b)
    c = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    v = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    if c < -1 + 1e-12:
        raise ValueError("opposite directions: rotation axis undefined")
    k = 1.0 / (1.0 + c)
    vx = ((0, -v[2], v[1]), (v[2], 0, -v[0]), (-v[1], v[0], 0))
    vx2 = tuple(tuple(sum(vx[i][m] * vx[m][j] for m in range(3)) for j in range(3)) for i in range(3))
    return tuple(tuple((1.0 if i == j else 0.0) + vx[i][j] + k * vx2[i][j] for j in range(3)) for i in range(3))


def _apply(m, v: Vec) -> Vec:
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))  # type: ignore[return-value]


def _point(d) -> Vec:
    return (float(d["x"]), float(d["y"]), float(d["z"])) if isinstance(d, Mapping) else tuple(d)  # type: ignore[return-value]


def socket_points(socket: EquipmentSocket, bones: Sequence[dict],
                  reference_bones: Sequence[dict]) -> Tuple[Vec, Vec]:
    """(head, tail) of the socket bone for ``bones`` (any pose / stature).

    ``reference_bones`` is the canonical anatomical-position list the offsets are written in.
    """
    by: Dict[str, dict] = {b["canonical_name"]: b for b in bones}
    ref: Dict[str, dict] = {b["canonical_name"]: b for b in reference_bones}
    p, r = by[socket.parent_bone], ref[socket.parent_bone]
    ph, pt = _point(p["head"]), _point(p["tail"])
    rh, rt = _point(r["head"]), _point(r["tail"])
    rot = _rotation_between(_sub(rt, rh), _sub(pt, ph))
    scale = _norm(_sub(pt, ph)) / _norm(_sub(rt, rh))
    base = tuple(ph[i] + socket.along * (pt[i] - ph[i]) for i in range(3))
    off = _apply(rot, socket.offset_m)
    head = tuple(base[i] + scale * off[i] for i in range(3))
    d = _unit(_apply(rot, socket.direction))
    tail = tuple(head[i] + scale * socket.length_m * d[i] for i in range(3))
    return head, tail  # type: ignore[return-value]


def validate_sockets(sockets: Sequence[EquipmentSocket], canonical_names) -> list:
    """Problems (empty = valid): unknown parents, duplicate names, bad parameters."""
    names = set(canonical_names)
    problems = []
    seen = set()
    for s in sockets:
        if not s.name.startswith("SOCKET-"):
            problems.append(f"{s.name}: socket names start with 'SOCKET-'")
        if s.name in seen:
            problems.append(f"duplicate socket {s.name}")
        seen.add(s.name)
        if s.parent_bone not in names:
            problems.append(f"{s.name}: unknown parent bone {s.parent_bone}")
        if not 0.0 <= s.along <= 1.0:
            problems.append(f"{s.name}: along must be in [0, 1]")
        if s.length_m <= 0 or _norm(s.direction) == 0:
            problems.append(f"{s.name}: length and direction must be non-zero")
    return problems
