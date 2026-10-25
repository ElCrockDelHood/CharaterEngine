"""CE-GAME-v1: the 66-bone game skeleton derived from the canonical 206 (RIG-GAME-001 step 1, Decision 51).

Two levels: the canonical skeleton (L0, 208 nodes) stays the anatomical truth and is never renamed; the game
skeleton (L1) is what runtimes, animation clips and mocap use. Bone names follow the UE5 Mannequin convention.

Every L1 bone is placed from canonical joint points, so it follows any pose or stature retarget of the
canonical bones:

* :class:`Joint` — the head or tail of a canonical bone (DERIVED),
* :class:`Lerp` — a fraction between two anchors; DERIVED for midpoints of paired joints (hip centre),
  ASSUMED for rig placements (twist bones at a fraction of the segment, the orbit centre),
* :class:`Offset` — an anchor plus an offset in anatomical axes, rotated with a reference canonical bone
  (ASSUMED; only the eye aim uses it).

``covers`` partitions the 208 canonical nodes among the game bones: each canonical bone rides on exactly one
game bone. Runtimes use it to keep anatomical meaning (a hitbox on ``RIB_08_L`` rides on ``spine_03`` and still
reports ``RIB_08_L`` to trauma) and Blender uses it to drive the hidden canonical layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

from ..anatomy.reference.source import ProvenanceState
from .sockets import _apply, _point, _rotation_between, _sub

Vec = Tuple[float, float, float]
D, A = ProvenanceState.DERIVED, ProvenanceState.ASSUMED

RIG_ID = "CE-GAME-v1"
CONTAINERS = ("ROOT_SKELETON", "CRANIUM")


@dataclass(frozen=True)
class Joint:
    bone: str
    end: str = "head"            # "head" | "tail"


@dataclass(frozen=True)
class Lerp:
    a: Anchor
    b: Anchor
    t: float
    provenance: ProvenanceState = A


@dataclass(frozen=True)
class Offset:
    base: Anchor
    offset_m: Vec                # anatomical axes (Z-up, -Y forward, left = +X)
    reference_bone: str          # canonical bone whose rotation carries the offset
    provenance: ProvenanceState = A


@dataclass(frozen=True)
class Origin:
    """Canonical origin (foot midline on the ground)."""


Anchor = Union[Joint, Lerp, Offset, Origin]


@dataclass(frozen=True)
class GameBone:
    name: str
    parent: Optional[str]
    head: Anchor
    tail: Anchor
    covers: Tuple[str, ...] = ()
    group: str = ""

    @property
    def provenance(self) -> ProvenanceState:
        return A if A in (_anchor_provenance(self.head), _anchor_provenance(self.tail)) else D


def _anchor_provenance(a: Anchor) -> ProvenanceState:
    if isinstance(a, (Joint, Origin)):
        return D
    if isinstance(a, Lerp):
        inner = {_anchor_provenance(a.a), _anchor_provenance(a.b), a.provenance}
        return A if A in inner else D
    return A


def _j(bone: str, end: str = "head") -> Joint:
    return Joint(bone, end)


def _side_bones(s: str) -> List[GameBone]:
    lo = s.lower()
    elbow, wrist = _j(f"HUMERUS_{s}", "tail"), _j(f"CAPITATE_{s}")
    knee, ankle = _j(f"FEMUR_{s}", "tail"), _j(f"TALUS_{s}")
    ball = _j(f"TOE_PHALANX_PROXIMAL_2_{s}")
    carpals = tuple(f"{c}_{s}" for c in ("SCAPHOID", "LUNATE", "TRIQUETRUM", "PISIFORM", "TRAPEZIUM", "TRAPEZOID",
                                        "CAPITATE", "HAMATE"))
    tarsals = tuple(f"{c}_{s}" for c in ("TALUS", "CALCANEUS", "NAVICULAR", "CUBOID", "CUNEIFORM_MEDIAL",
                                        "CUNEIFORM_INTERMEDIATE", "CUNEIFORM_LATERAL"))
    toes = tuple(f"TOE_PHALANX_{p}_{t}_{s}" for t in range(1, 6)
                 for p in (("PROXIMAL", "DISTAL") if t == 1 else ("PROXIMAL", "INTERMEDIATE", "DISTAL")))
    out = [
        GameBone(f"clavicle_{lo}", "spine_03", _j(f"CLAVICLE_{s}"), _j(f"HUMERUS_{s}"),
                 (f"CLAVICLE_{s}", f"SCAPULA_{s}"), "arm"),
        GameBone(f"upperarm_{lo}", f"clavicle_{lo}", _j(f"HUMERUS_{s}"), elbow, (f"HUMERUS_{s}",), "arm"),
        GameBone(f"upperarm_twist_01_{lo}", f"upperarm_{lo}", Lerp(_j(f"HUMERUS_{s}"), elbow, 0.5), elbow, (), "arm"),
        GameBone(f"lowerarm_{lo}", f"upperarm_{lo}", elbow, wrist, (f"RADIUS_{s}", f"ULNA_{s}"), "arm"),
        GameBone(f"lowerarm_twist_01_{lo}", f"lowerarm_{lo}", Lerp(elbow, wrist, 0.75), wrist, (), "arm"),
        GameBone(f"hand_{lo}", f"lowerarm_{lo}", wrist, _j(f"METACARPAL_3_{s}", "tail"),
                 carpals + (f"METACARPAL_2_{s}", f"METACARPAL_3_{s}"), "arm"),
        GameBone(f"thumb_01_{lo}", f"hand_{lo}", _j(f"METACARPAL_1_{s}"), _j(f"METACARPAL_1_{s}", "tail"),
                 (f"METACARPAL_1_{s}",), "hand"),
        GameBone(f"thumb_02_{lo}", f"thumb_01_{lo}", _j(f"PHALANX_PROXIMAL_1_{s}"),
                 _j(f"PHALANX_PROXIMAL_1_{s}", "tail"), (f"PHALANX_PROXIMAL_1_{s}",), "hand"),
        GameBone(f"thumb_03_{lo}", f"thumb_02_{lo}", _j(f"PHALANX_DISTAL_1_{s}"),
                 _j(f"PHALANX_DISTAL_1_{s}", "tail"), (f"PHALANX_DISTAL_1_{s}",), "hand"),
        GameBone(f"ring_metacarpal_{lo}", f"hand_{lo}", _j(f"METACARPAL_4_{s}"), _j(f"METACARPAL_4_{s}", "tail"),
                 (f"METACARPAL_4_{s}",), "hand"),
        GameBone(f"pinky_metacarpal_{lo}", f"hand_{lo}", _j(f"METACARPAL_5_{s}"), _j(f"METACARPAL_5_{s}", "tail"),
                 (f"METACARPAL_5_{s}",), "hand"),
    ]
    for finger, digit, base in (("index", 2, "hand"), ("middle", 3, "hand"), ("ring", 4, "ring_metacarpal"),
                                ("pinky", 5, "pinky_metacarpal")):
        parent = f"{base}_{lo}"
        for i, phalanx in enumerate(("PROXIMAL", "INTERMEDIATE", "DISTAL"), start=1):
            bone = f"PHALANX_{phalanx}_{digit}_{s}"
            out.append(GameBone(f"{finger}_0{i}_{lo}", parent, _j(bone), _j(bone, "tail"), (bone,), "hand"))
            parent = f"{finger}_0{i}_{lo}"
    out += [
        GameBone(f"thigh_{lo}", "pelvis", _j(f"FEMUR_{s}"), knee, (f"FEMUR_{s}",), "leg"),
        GameBone(f"thigh_twist_01_{lo}", f"thigh_{lo}", Lerp(_j(f"FEMUR_{s}"), knee, 0.5), knee, (), "leg"),
        GameBone(f"calf_{lo}", f"thigh_{lo}", knee, ankle, (f"TIBIA_{s}", f"FIBULA_{s}", f"PATELLA_{s}"), "leg"),
        GameBone(f"foot_{lo}", f"calf_{lo}", ankle, ball,
                 tarsals + tuple(f"METATARSAL_{m}_{s}" for m in range(1, 6)), "leg"),
        GameBone(f"ball_{lo}", f"foot_{lo}", ball, _j(f"TOE_PHALANX_DISTAL_2_{s}", "tail"), toes, "leg"),
    ]
    # Orbit centre between the medial wall (lacrimal) and the lateral rim (zygomatic); no canonical eyeball.
    eye = Lerp(_j(f"LACRIMAL_{s}"), _j(f"ZYGOMATIC_{s}", "tail"), 0.5, A)
    out.append(GameBone(f"eye_{lo}", "head", eye, Offset(eye, (0.0, -0.025, 0.0), "FRONTAL"), (), "face"))
    return out


_SKULL = ("FRONTAL", "PARIETAL_L", "PARIETAL_R", "TEMPORAL_L", "TEMPORAL_R", "OCCIPITAL", "SPHENOID", "ETHMOID",
          "MAXILLA_L", "MAXILLA_R", "ZYGOMATIC_L", "ZYGOMATIC_R", "NASAL_L", "NASAL_R", "LACRIMAL_L", "LACRIMAL_R",
          "PALATINE_L", "PALATINE_R", "INFERIOR_NASAL_CONCHA_L", "INFERIOR_NASAL_CONCHA_R", "VOMER",
          "MALLEUS_L", "MALLEUS_R", "INCUS_L", "INCUS_R", "STAPES_L", "STAPES_R")


def _game_bones() -> Tuple[GameBone, ...]:
    hip = Lerp(_j("FEMUR_L"), _j("FEMUR_R"), 0.5, D)          # midpoint of the femoral heads
    # Vertebra heads are their superior end: a spine segment pivots at the inferior end (tail) of its lowest
    # vertebra and ends where the next segment starts.
    s1, s2, s3 = _j("LUMBAR_5", "tail"), _j("LUMBAR_2", "tail"), _j("THORACIC_9", "tail")
    neck, skull_base = _j("CERVICAL_7", "tail"), _j("CERVICAL_1")
    lumbar = lambda *ns: tuple(f"LUMBAR_{n}" for n in ns)          # noqa: E731
    thoracic = lambda *ns: tuple(f"THORACIC_{n}" for n in ns)      # noqa: E731
    ribs = tuple(f"RIB_{i:02d}_{s}" for s in "LR" for i in range(1, 13))
    core = [
        GameBone("root", None, Origin(), hip, ("ROOT_SKELETON",), "core"),
        GameBone("pelvis", "root", hip, s1, ("SACRUM", "COCCYX", "COXAL_L", "COXAL_R"), "core"),
        GameBone("spine_01", "pelvis", s1, s2, lumbar(5, 4, 3), "core"),
        GameBone("spine_02", "spine_01", s2, s3, lumbar(2, 1) + thoracic(12, 11, 10), "core"),
        GameBone("spine_03", "spine_02", s3, neck, thoracic(*range(9, 0, -1)) + ribs + ("STERNUM",), "core"),
        GameBone("neck_01", "spine_03", neck, skull_base, tuple(f"CERVICAL_{n}" for n in range(7, 0, -1)) + ("HYOID",),
                 "core"),
        GameBone("head", "neck_01", skull_base, _j("FRONTAL", "tail"), ("CRANIUM",) + _SKULL, "core"),
        GameBone("jaw", "head", _j("MANDIBLE"), _j("MANDIBLE", "tail"), ("MANDIBLE",), "face"),
    ]
    return tuple(core + _side_bones("L") + _side_bones("R"))


GAME_BONES: Tuple[GameBone, ...] = _game_bones()


def canonical_to_game() -> Dict[str, str]:
    """Canonical node name -> game bone carrying it (all 208 nodes)."""
    return {c: b.name for b in GAME_BONES for c in b.covers}


def _resolve(a: Anchor, by: Mapping[str, dict], ref: Mapping[str, dict]) -> Vec:
    if isinstance(a, Origin):
        return (0.0, 0.0, 0.0)
    if isinstance(a, Joint):
        return _point(by[a.bone][a.end])
    if isinstance(a, Lerp):
        p, q = _resolve(a.a, by, ref), _resolve(a.b, by, ref)
        return (p[0] + a.t * (q[0] - p[0]), p[1] + a.t * (q[1] - p[1]), p[2] + a.t * (q[2] - p[2]))
    base = _resolve(a.base, by, ref)
    b, r = by[a.reference_bone], ref[a.reference_bone]
    rot = _rotation_between(_sub(_point(r["tail"]), _point(r["head"])), _sub(_point(b["tail"]), _point(b["head"])))
    off = _apply(rot, a.offset_m)
    return (base[0] + off[0], base[1] + off[1], base[2] + off[2])


def game_bone_points(bones: Sequence[dict], reference_bones: Optional[Sequence[dict]] = None) -> Dict[str, Tuple[Vec, Vec]]:
    """(head, tail) of every game bone for canonical ``bones`` in any pose / stature.

    ``reference_bones`` is the anatomical-position list :class:`Offset` values are written in (default: ``bones``).
    """
    by = {b["canonical_name"]: b for b in bones}
    ref = {b["canonical_name"]: b for b in (reference_bones or bones)}
    return {g.name: (_resolve(g.head, by, ref), _resolve(g.tail, by, ref)) for g in GAME_BONES}


def validate_game_rig(canonical_names: Sequence[str], game_bones: Sequence[GameBone] = GAME_BONES) -> List[str]:
    """Problems (empty = valid): hierarchy, unknown canonical bones, incomplete or overlapping coverage."""
    problems: List[str] = []
    names = [g.name for g in game_bones]
    seen = set()
    roots = [g for g in game_bones if g.parent is None]
    if len(roots) != 1:
        problems.append(f"expected one root, found {len(roots)}")
    for g in game_bones:
        if g.name in seen:
            problems.append(f"duplicate game bone {g.name}")
        if g.parent is not None and g.parent not in seen:
            problems.append(f"{g.name}: parent {g.parent} missing or not declared before it")
        seen.add(g.name)
    known = set(canonical_names)
    for g in game_bones:
        for a in (g.head, g.tail):
            for bone in _anchor_bones(a):
                if bone not in known:
                    problems.append(f"{g.name}: anchor on unknown canonical bone {bone}")
    covered: Dict[str, str] = {}
    for g in game_bones:
        for c in g.covers:
            if c in covered:
                problems.append(f"{c} covered by both {covered[c]} and {g.name}")
            covered[c] = g.name
    for c in sorted(known | set(CONTAINERS)):
        if c not in covered:
            problems.append(f"canonical node {c} not covered by any game bone")
    for c in covered:
        if c not in known and c not in CONTAINERS:
            problems.append(f"covers unknown canonical bone {c}")
    if len(names) != len(set(names)):
        problems.append("duplicate names")
    return problems


def _anchor_bones(a: Anchor) -> List[str]:
    if isinstance(a, Joint):
        return [a.bone]
    if isinstance(a, Lerp):
        return _anchor_bones(a.a) + _anchor_bones(a.b)
    if isinstance(a, Offset):
        return _anchor_bones(a.base) + [a.reference_bone]
    return []


def _game_control_rig():
    from .rig_definition import IKChain, RigDefinition

    chains = []
    for side in ("L", "R"):
        s = side.lower()
        chains.append(IKChain(f"arm_{side}", (f"upperarm_{s}", f"lowerarm_{s}"), f"hand_{s}",
                              pole_offset_m=(0.0, 0.40, 0.0), fk_ik_property=f"arm_ik_{side}"))
        chains.append(IKChain(f"leg_{side}", (f"thigh_{s}", f"calf_{s}"), f"foot_{s}",
                              pole_offset_m=(0.0, -0.50, 0.0), fk_ik_property=f"leg_ik_{side}", foot_roll=True))
    return RigDefinition(rig_id="ce_game_v1_controls", ik_chains=tuple(chains), spline_chains=(), controls=(),
                         properties={f"{limb}_ik_{s}": 1.0 for limb in ("arm", "leg") for s in "LR"})


#: IK/FK control layer over the game skeleton (same contract and pole offsets as ``HUMANOID_RIG``).
GAME_CONTROL_RIG = _game_control_rig()
