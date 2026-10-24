"""Rig definition: IK/FK chains, spline chains and control bones over the canonical skeleton.

Engine-neutral description consumed by the Blender addon (builds constraints), the
Godot runtime (``SkeletonIK3D`` / ``SkeletonModifier3D`` set-up) and UPBGE (bge
components). Layers follow the Rigify convention:

* ``DEF-``  deform bones = the 206 canonical bones (never renamed)
* ``MCH-``  mechanism bones (IK targets, poles, FK/IK blend intermediates)
* ``CTRL-`` animator-facing controls (widgets)

Nothing here is anatomical data; it is a control contract, so no provenance tags apply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class IKChain:
    chain_id: str
    bones: Tuple[str, ...]          # canonical bones root → tip (2 or 3 for limb IK)
    target_bone: str                # canonical bone whose head is the IK effector
    pole_offset_m: Tuple[float, float, float]  # pole position relative to mid-joint (canonical axes)
    fk_ik_property: str             # name of the 0..1 switch exposed to animators
    stretch: bool = False
    foot_roll: bool = False         # adds heel/ball pivot mechanism (legs)


@dataclass(frozen=True)
class SplineChain:
    chain_id: str
    bones: Tuple[str, ...]          # ordered canonical bones driven by a spline / bendy chain
    controls: int = 3               # number of CTRL bones along the spline


@dataclass(frozen=True)
class ControlBone:
    name: str                       # e.g. CTRL-hand_ik.L
    drives: Tuple[str, ...]         # canonical bones or MCH bones it drives
    widget: str = "cube"
    layer: str = "CTRL"


@dataclass(frozen=True)
class RigDefinition:
    rig_id: str
    ik_chains: Tuple[IKChain, ...]
    spline_chains: Tuple[SplineChain, ...]
    controls: Tuple[ControlBone, ...]
    root_control: str = "CTRL-root"
    properties: Dict[str, float] = field(default_factory=dict)  # default switch values

    def all_referenced_bones(self) -> List[str]:
        out: List[str] = []
        for c in self.ik_chains:
            out.extend(c.bones)
            out.append(c.target_bone)
        for s in self.spline_chains:
            out.extend(s.bones)
        return out


def _limb_chains() -> List[IKChain]:
    chains: List[IKChain] = []
    for side, sx in (("L", 1.0), ("R", -1.0)):   # left = +X (Decision 17)
        chains.append(IKChain(
            chain_id=f"arm_{side}", bones=(f"HUMERUS_{side}", f"RADIUS_{side}"), target_bone=f"CAPITATE_{side}",
            pole_offset_m=(0.0, 0.40, 0.0),      # elbow pole behind (+Y is backwards in canonical frame)
            fk_ik_property=f"arm_ik_{side}", stretch=False))
        chains.append(IKChain(
            chain_id=f"leg_{side}", bones=(f"FEMUR_{side}", f"TIBIA_{side}"), target_bone=f"TALUS_{side}",
            pole_offset_m=(0.0, -0.50, 0.0),     # knee pole in front (-Y forward)
            fk_ik_property=f"leg_ik_{side}", stretch=False, foot_roll=True))
        chains.append(IKChain(
            chain_id=f"clavicle_{side}", bones=(f"CLAVICLE_{side}",), target_bone=f"HUMERUS_{side}",
            pole_offset_m=(sx * 0.0, 0.0, 0.0), fk_ik_property=f"clavicle_follow_{side}"))
    return chains


def _spline_chains() -> List[SplineChain]:
    spine = tuple(f"LUMBAR_{i}" for i in range(5, 0, -1)) + tuple(f"THORACIC_{i}" for i in range(12, 0, -1))
    neck = tuple(f"CERVICAL_{i}" for i in range(7, 0, -1))
    out = [SplineChain("spine", spine, controls=4), SplineChain("neck", neck, controls=2)]
    for side in ("L", "R"):
        for finger in range(1, 6):
            bones = [f"METACARPAL_{finger}_{side}", f"PHALANX_PROXIMAL_{finger}_{side}"]
            if finger != 1:
                bones.append(f"PHALANX_INTERMEDIATE_{finger}_{side}")
            bones.append(f"PHALANX_DISTAL_{finger}_{side}")
            out.append(SplineChain(f"finger_{finger}_{side}", tuple(bones), controls=1))
        toes = []
        for toe in range(1, 6):
            toes.append(f"TOE_PHALANX_PROXIMAL_{toe}_{side}")
            toes.append(f"TOE_PHALANX_DISTAL_{toe}_{side}")
        out.append(SplineChain(f"toes_{side}", tuple(toes), controls=1))
    return out


def _controls() -> List[ControlBone]:
    ctrls = [
        ControlBone("CTRL-root", ("ROOT_SKELETON",), widget="circle"),
        ControlBone("CTRL-torso", ("SACRUM", "COXAL_L", "COXAL_R"), widget="cube"),
        ControlBone("CTRL-chest", tuple(f"THORACIC_{i}" for i in range(1, 13)) + ("STERNUM",), widget="circle"),
        ControlBone("CTRL-head", ("CRANIUM", "CERVICAL_1"), widget="circle"),
        ControlBone("CTRL-jaw", ("MANDIBLE",), widget="cube"),
        ControlBone("CTRL-breath", tuple(f"RIB_{i:02d}_{s}" for i in range(1, 11) for s in "LR") + ("STERNUM",),
                    widget="sphere"),
    ]
    for side in ("L", "R"):
        ctrls += [
            ControlBone(f"CTRL-hand_ik.{side}", (f"MCH-ik_target_arm_{side}",), widget="cube"),
            ControlBone(f"CTRL-elbow_pole.{side}", (f"MCH-pole_arm_{side}",), widget="sphere"),
            ControlBone(f"CTRL-foot_ik.{side}", (f"MCH-ik_target_leg_{side}",), widget="cube"),
            ControlBone(f"CTRL-knee_pole.{side}", (f"MCH-pole_leg_{side}",), widget="sphere"),
            ControlBone(f"CTRL-foot_roll.{side}", (f"MCH-heel_{side}", f"MCH-ball_{side}"), widget="circle"),
            ControlBone(f"CTRL-upper_arm_fk.{side}", (f"HUMERUS_{side}",), widget="circle"),
            ControlBone(f"CTRL-forearm_fk.{side}", (f"RADIUS_{side}", f"ULNA_{side}"), widget="circle"),
            ControlBone(f"CTRL-hand_fk.{side}", (f"CAPITATE_{side}",), widget="circle"),
            ControlBone(f"CTRL-thigh_fk.{side}", (f"FEMUR_{side}",), widget="circle"),
            ControlBone(f"CTRL-shin_fk.{side}", (f"TIBIA_{side}", f"FIBULA_{side}"), widget="circle"),
            ControlBone(f"CTRL-foot_fk.{side}", (f"TALUS_{side}", f"CALCANEUS_{side}"), widget="circle"),
            ControlBone(f"CTRL-shoulder.{side}", (f"CLAVICLE_{side}", f"SCAPULA_{side}"), widget="cube"),
        ]
    return ctrls


HUMANOID_RIG = RigDefinition(
    rig_id="humanoid_ce_v1",
    ik_chains=tuple(_limb_chains()),
    spline_chains=tuple(_spline_chains()),
    controls=tuple(_controls()),
    properties={"arm_ik_L": 1.0, "arm_ik_R": 1.0, "leg_ik_L": 1.0, "leg_ik_R": 1.0,
                "clavicle_follow_L": 0.5, "clavicle_follow_R": 0.5, "breath_amplitude": 0.0},
)


def validate_rig_against_bones(rig: RigDefinition, canonical_names: Iterable[str]) -> List[str]:
    """Return a list of problems (empty = valid): unknown bones, duplicate chain ids."""
    names = set(canonical_names) | {"ROOT_SKELETON", "CRANIUM"}
    problems: List[str] = []
    for b in rig.all_referenced_bones():
        if b not in names:
            problems.append(f"unknown bone '{b}'")
    ids = [c.chain_id for c in rig.ik_chains] + [s.chain_id for s in rig.spline_chains]
    dupes = {i for i in ids if ids.count(i) > 1}
    problems += [f"duplicate chain id '{d}'" for d in sorted(dupes)]
    for c in rig.controls:
        for d in c.drives:
            if not d.startswith("MCH-") and d not in names:
                problems.append(f"control '{c.name}' drives unknown bone '{d}'")
    return problems
