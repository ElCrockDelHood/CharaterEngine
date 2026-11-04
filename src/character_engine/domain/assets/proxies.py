"""Script-generated PROXY geometry for anatomy with no real mesh yet (A25).

BodyParts3D (A18, A22, IS-A tree) has no latissimus dorsi, rectus abdominis, tibialis anterior, peroneus group,
major joint ligaments, coccyx or ear ossicles. Until a sourced mesh exists, each of them is a simple shape placed on
the canonical skeleton:

* **muscle** — a spindle between origin and insertion taken from the ``MUSCLES`` catalogue (bone + fraction,
  radius, tendon fraction: all ESTIMATE in the catalogue);
* **ligament** — a thin band between two attachment points: a canonical bone point plus an offset. The knee
  half-width (41.7 mm) is the BodyParts3D epicondylar width scaled to the canonical frame (A20, ESTIMATE). Every
  other offset and every radius is **PLACEHOLDER**;
* **bone** — an ellipsoid on the bone's own canonical segment (coccyx, malleus, incus, stapes); the radius is a
  PLACEHOLDER fraction of the segment length.

Pure Python, deterministic (fixed tessellation and number formatting): the same skeleton gives the same bytes.
Nothing here changes the canonical data or the rig; the shapes only *read* the canonical points. Every piece gets an
asset manifest (``domain/assets/manifest.py``, contract PROPOSED, Decision 61).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..tissue.muscles import MUSCLES

Vec = Tuple[float, float, float]
Joints = Mapping[str, Tuple[Vec, Vec]]

KNEE_HALF_WIDTH_M = 0.0417          # ESTIMATE: BP3D femoral epicondylar width 80.6 mm × 1.0358 / 2 (A20)
LIGAMENT_RADIUS_M = 0.004           # PLACEHOLDER
BROAD_LIGAMENT_RADIUS_M = 0.006     # PLACEHOLDER (collateral / deltoid bands)
BONE_RADIUS_FRACTION = 0.35         # PLACEHOLDER: ellipsoid radius = fraction × segment length
RINGS, SEGMENTS = 12, 12
LICENCE = "Character Engine project-generated proxy (no third-party geometry)"
AUTHOR = "Character Engine, scripts/build_anatomy_proxies.py"
ORIGIN = "scripts/build_anatomy_proxies.py (domain/assets/proxies.py)"


@dataclass(frozen=True)
class Point:
    """Canonical point: ``t`` along a bone segment (0 head, 1 tail) plus an offset in anatomical axes.

    The offset's x is *lateral* (mirrored per side), y is posterior (+Y), z is up."""
    bone: str                 # base name (side suffix added by the builder unless axial)
    t: float
    offset: Vec = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class ProxySpec:
    asset_id: str             # without side
    name: str
    layer: str                # "muscle" | "ligament" | "bone"
    origin: Point
    insertion: Point
    radius_m: float
    provenance: str           # ProvenanceState name of the geometry
    note: str
    muscle: Optional[str] = None       # MUSCLES base name for muscles
    tendon_fraction: float = 0.0
    bilateral: bool = True


_AXIAL = {"STERNUM", "SACRUM", "COCCYX", "OCCIPITAL", "MANDIBLE", "HYOID"}


def _muscle(base: str, name: str, note: str) -> ProxySpec:
    m = MUSCLES[f"{base}_L"]
    strip = lambda b: b[:-2] if b.endswith(("_L", "_R")) else b   # noqa: E731
    return ProxySpec(f"proxy_{base.lower()}", name, "muscle", Point(strip(m.origin_bone), m.origin_t),
                     Point(strip(m.insertion_bone), m.insertion_t), m.radius_m, "ESTIMATE",
                     f"MUSCLES catalogue attachments and radius (ESTIMATE); {note}", base, m.tendon_fraction)


W = KNEE_HALF_WIDTH_M
SPECS: Tuple[ProxySpec, ...] = (
    _muscle("LATISSIMUS_DORSI", "Latissimus dorsi", "absent from BodyParts3D IS-A"),
    _muscle("RECTUS_ABDOMINIS", "Rectus abdominis", "absent from BodyParts3D IS-A"),
    _muscle("TIBIALIS_ANTERIOR", "Tibialis anterior", "absent from BodyParts3D IS-A"),
    _muscle("PERONEUS_GROUP", "Peroneus (fibularis) group", "absent from BodyParts3D IS-A"),
    ProxySpec("proxy_knee_acl", "Anterior cruciate ligament", "ligament", Point("FEMUR", 1.0, (0.010, 0.015, 0.0)),
              Point("TIBIA", 0.0, (0.0, -0.015, 0.0)), LIGAMENT_RADIUS_M, "PLACEHOLDER",
              "lateral femoral condyle (posterior) -> anterior intercondylar area; offsets PLACEHOLDER"),
    ProxySpec("proxy_knee_pcl", "Posterior cruciate ligament", "ligament", Point("FEMUR", 1.0, (-0.010, -0.010, 0.0)),
              Point("TIBIA", 0.0, (0.0, 0.020, -0.010)), LIGAMENT_RADIUS_M, "PLACEHOLDER",
              "medial femoral condyle -> posterior intercondylar area; offsets PLACEHOLDER"),
    ProxySpec("proxy_knee_mcl", "Medial collateral ligament", "ligament", Point("FEMUR", 1.0, (-W, 0.0, 0.010)),
              Point("TIBIA", 0.0, (-0.035, 0.0, -0.060)), BROAD_LIGAMENT_RADIUS_M, "PLACEHOLDER",
              "medial epicondyle (half-width ESTIMATE, A20) -> medial tibia; tibial offset PLACEHOLDER"),
    ProxySpec("proxy_knee_lcl", "Lateral collateral ligament", "ligament", Point("FEMUR", 1.0, (W, 0.0, 0.010)),
              Point("FIBULA", 0.0), BROAD_LIGAMENT_RADIUS_M, "PLACEHOLDER",
              "lateral epicondyle (half-width ESTIMATE, A20) -> fibular head (canonical, A21 PLACEHOLDER)"),
    ProxySpec("proxy_ankle_atfl", "Anterior talofibular ligament", "ligament", Point("FIBULA", 1.0, (0.0, -0.010, 0.0)),
              Point("TALUS", 0.0, (0.015, -0.020, 0.0)), LIGAMENT_RADIUS_M, "PLACEHOLDER",
              "lateral malleolus -> talar neck; offsets PLACEHOLDER"),
    ProxySpec("proxy_ankle_deltoid", "Deltoid ligament (medial collateral of the ankle)", "ligament",
              Point("TIBIA", 1.0, (-0.020, 0.0, 0.0)), Point("TALUS", 0.0, (-0.020, 0.0, -0.020)),
              BROAD_LIGAMENT_RADIUS_M, "PLACEHOLDER", "medial malleolus -> medial talus; offsets PLACEHOLDER"),
    ProxySpec("proxy_shoulder_coracoclavicular", "Coracoclavicular ligament", "ligament", Point("CLAVICLE", 0.8),
              Point("SCAPULA", 0.1, (0.0, -0.030, -0.020)), LIGAMENT_RADIUS_M, "PLACEHOLDER",
              "lateral clavicle -> coracoid process (offset from the A24 scapula segment PLACEHOLDER)"),
    ProxySpec("proxy_shoulder_coracoacromial", "Coracoacromial ligament", "ligament",
              Point("SCAPULA", 0.1, (0.0, -0.030, -0.020)), Point("SCAPULA", 0.0), LIGAMENT_RADIUS_M, "PLACEHOLDER",
              "coracoid process -> acromion (scapula head, A24); coracoid offset PLACEHOLDER"),
    ProxySpec("proxy_shoulder_glenohumeral", "Glenohumeral ligaments (capsule band)", "ligament",
              Point("SCAPULA", 0.12), Point("HUMERUS", 0.0), BROAD_LIGAMENT_RADIUS_M, "PLACEHOLDER",
              "glenoid rim -> humeral head (A24 joint centre); radius PLACEHOLDER"),
    ProxySpec("proxy_coccyx", "Coccyx", "bone", Point("COCCYX", 0.0), Point("COCCYX", 1.0), 0.0, "PLACEHOLDER",
              "absent from BodyParts3D; ellipsoid on the canonical segment", bilateral=False),
    ProxySpec("proxy_malleus", "Malleus", "bone", Point("MALLEUS", 0.0), Point("MALLEUS", 1.0), 0.0, "PLACEHOLDER",
              "absent from BodyParts3D; ellipsoid on the canonical segment"),
    ProxySpec("proxy_incus", "Incus", "bone", Point("INCUS", 0.0), Point("INCUS", 1.0), 0.0, "PLACEHOLDER",
              "absent from BodyParts3D; ellipsoid on the canonical segment"),
    ProxySpec("proxy_stapes", "Stapes", "bone", Point("STAPES", 0.0), Point("STAPES", 1.0), 0.0, "PLACEHOLDER",
              "absent from BodyParts3D; ellipsoid on the canonical segment"),
)


# ------------------------------------------------------------------------------------------------ vectors

def _add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])          # noqa: E704
def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])          # noqa: E704
def _mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)                    # noqa: E704
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]          # noqa: E704


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a))
    if n == 0.0:
        raise ValueError("degenerate segment")
    return _mul(a, 1.0 / n)


def bone_name(base: str, side: Optional[str]) -> str:
    return base if (side is None or base in _AXIAL) else f"{base}_{side}"


def resolve(p: Point, joints: Joints, side: Optional[str]) -> Vec:
    head, tail = joints[bone_name(p.bone, side)]
    base = _add(head, _mul(_sub(tail, head), p.t))
    lateral = -1.0 if side == "R" else 1.0
    return _add(base, (lateral * p.offset[0], p.offset[1], p.offset[2]))


def _frame(a: Vec, b: Vec) -> Tuple[Vec, Vec, Vec]:
    axis = _unit(_sub(b, a))
    ref = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = _unit(_cross(axis, ref))
    return axis, u, _cross(axis, u)


def tube(a: Vec, b: Vec, radius_at, rings: int = RINGS, segments: int = SEGMENTS):
    """Closed tube from a to b; ``radius_at(s)`` for s in [0, 1]. Returns (vertices, triangles)."""
    axis, u, v = _frame(a, b)
    length = math.dist(a, b)
    verts: List[Vec] = [a]
    for i in range(1, rings):
        s = i / rings
        c = _add(a, _mul(axis, s * length))
        r = radius_at(s)
        for j in range(segments):
            ang = 2.0 * math.pi * j / segments
            verts.append(_add(c, _add(_mul(u, r * math.cos(ang)), _mul(v, r * math.sin(ang)))))
    verts.append(b)
    faces: List[Tuple[int, int, int]] = []
    last = len(verts) - 1
    for j in range(segments):                                     # start cap
        faces.append((0, 1 + (j + 1) % segments, 1 + j))
    for i in range(rings - 2):
        r0, r1 = 1 + i * segments, 1 + (i + 1) * segments
        for j in range(segments):
            j1 = (j + 1) % segments
            faces.append((r0 + j, r0 + j1, r1 + j1))
            faces.append((r0 + j, r1 + j1, r1 + j))
    base = 1 + (rings - 2) * segments
    for j in range(segments):                                     # end cap
        faces.append((base + j, base + (j + 1) % segments, last))
    return verts, faces


def shape_for(spec: ProxySpec, a: Vec, b: Vec):
    length = math.dist(a, b)
    if spec.layer == "muscle":
        tf = spec.tendon_fraction
        def r(s):                                                  # noqa: E306
            if s < tf or s > 1.0 - tf:
                return spec.radius_m * 0.25                        # tendon part: 0.25 × radius, PLACEHOLDER
            x = (s - tf) / max(1e-9, 1.0 - 2.0 * tf)
            return spec.radius_m * max(0.25, math.sin(math.pi * x))
        return tube(a, b, r)
    if spec.layer == "ligament":
        return tube(a, b, lambda s: spec.radius_m)
    rad = BONE_RADIUS_FRACTION * length
    return tube(a, b, lambda s: rad * math.sin(math.pi * s))


def to_obj(name: str, verts: Sequence[Vec], faces: Sequence[Tuple[int, int, int]], header: Sequence[str]) -> bytes:
    lines = [f"# {h}" for h in header] + [f"o {name}"]
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in verts]
    lines += [f"f {i + 1} {j + 1} {k + 1}" for i, j, k in faces]
    return ("\n".join(lines) + "\n").encode("utf-8")


def build(joints: Joints) -> Dict[str, bytes]:
    """All proxy files: ``<asset_id>.obj`` and ``<asset_id>.manifest.json`` (bytes, deterministic)."""
    files: Dict[str, bytes] = {}
    index = []
    for spec in SPECS:
        for side in (("L", "R") if spec.bilateral else (None,)):
            aid = spec.asset_id + (f"_{side.lower()}" if side else "")
            a, b = resolve(spec.origin, joints, side), resolve(spec.insertion, joints, side)
            verts, faces = shape_for(spec, a, b)
            header = [f"{spec.name} ({side or 'midline'}) PROXY, layer {spec.layer}, provenance {spec.provenance}",
                      spec.note, LICENCE, "units m, Z-up, -Y forward, left = +X (canonical frame)"]
            obj = to_obj(aid, verts, faces, header)
            files[f"{aid}.obj"] = obj
            axis, u, _ = _frame(a, b)
            mid = _mul(_add(a, b), 0.5)
            r = max(spec.radius_m, BONE_RADIUS_FRACTION * math.dist(a, b) if spec.layer == "bone" else 0.0)
            anchors = [{"landmark": f"{aid}_origin", "vertex_or_point": list(a)},
                       {"landmark": f"{aid}_insertion", "vertex_or_point": list(b)},
                       {"landmark": f"{aid}_equator", "vertex_or_point": list(_add(mid, _mul(u, r)))}]
            part_side = side if side else "midline"
            part_bone = spec.origin.bone
            if side and part_bone in _AXIAL:          # bilateral muscle on a midline bone: anchor on the sided end
                part_bone = spec.insertion.bone
            manifest = {
                "asset_id": aid, "file": f"{aid}.obj", "sha256": hashlib.sha256(obj).hexdigest(),
                "layer": spec.layer,
                "parts": [{"mesh": aid, "canonical_bone": part_bone, "side": part_side,
                           "anchors": [{**x, "vertex_or_point": [round(c, 6) for c in x["vertex_or_point"]]}
                                       for x in anchors]}],
                "attachments": ([{"muscle": spec.muscle, "origin_bone": spec.origin.bone,
                                  "insertion_bone": spec.insertion.bone}] if spec.muscle else []),
                "source_units": "m", "up": "+Z", "forward": "-Y",
                "licence": LICENCE, "author": AUTHOR, "origin_url": ORIGIN, "provenance": spec.provenance,
                "note": spec.note,
            }
            files[f"{aid}.manifest.json"] = (json.dumps(manifest, indent=1) + "\n").encode("utf-8")
            index.append({"asset_id": aid, "name": spec.name, "layer": spec.layer, "side": part_side,
                          "provenance": spec.provenance, "vertices": len(verts), "triangles": len(faces),
                          "length_m": round(math.dist(a, b), 6)})
    files["INDEX.json"] = (json.dumps({"status": "PROXY geometry (A25); replace with sourced meshes when available",
                                       "pieces": index}, indent=1) + "\n").encode("utf-8")
    return files
