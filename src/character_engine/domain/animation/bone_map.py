"""Bone maps: external mocap skeleton names → canonical bone names.

The canonical skeleton is anatomical (206 bones); mocap rigs are *control* rigs of
15–65 joints. A ``BoneMap`` therefore maps each source joint to the canonical bone
whose **head** best matches the joint centre. Chains of unmapped canonical bones
(individual vertebrae, carpals, tarsals) are driven by spline/IK in the rig, not by mocap.

Formats covered: Mixamo (FBX, ``mixamorig:`` prefix), CMU BVH (``Hips``/``LeftUpLeg``
naming as in the cgspeed conversion), Rokoko/SmartSuit (Mixamo-like), and the
Blender/UPBGE "Rigify DEF-" prefix for round-tripping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional


@dataclass(frozen=True)
class BoneMap:
    map_id: str
    label: str
    source_to_canonical: Mapping[str, str]
    prefix: str = ""
    root_joint: str = "Hips"
    forward_axis: str = "+Z"        # mocap forward axis in its native file
    up_axis: str = "+Y"
    scale_to_m: float = 1.0          # multiply source units to metres
    notes: str = ""
    aliases: Mapping[str, str] = field(default_factory=dict)  # alternate source spellings

    def canonical(self, source_joint: str) -> Optional[str]:
        name = source_joint
        if self.prefix and name.startswith(self.prefix):
            name = name[len(self.prefix):]
        name = self.aliases.get(name, name)
        return self.source_to_canonical.get(name)

    def coverage(self) -> int:
        return len(set(self.source_to_canonical.values()))


# Humanoid "standard" joint set (Mixamo naming) → canonical bone (joint centre = bone head).
_MIXAMO: Dict[str, str] = {
    "Hips": "SACRUM",
    "Spine": "LUMBAR_5",
    "Spine1": "LUMBAR_1",
    "Spine2": "THORACIC_8",
    "Neck": "CERVICAL_7",
    "Head": "CERVICAL_1",
    "HeadTop_End": "PARIETAL_L",
    "LeftShoulder": "CLAVICLE_L",
    "LeftArm": "HUMERUS_L",
    "LeftForeArm": "RADIUS_L",
    "LeftHand": "CAPITATE_L",
    "LeftHandThumb1": "METACARPAL_1_L",
    "LeftHandThumb2": "PHALANX_PROXIMAL_1_L",
    "LeftHandThumb3": "PHALANX_DISTAL_1_L",
    "LeftHandIndex1": "METACARPAL_2_L",
    "LeftHandIndex2": "PHALANX_PROXIMAL_2_L",
    "LeftHandIndex3": "PHALANX_INTERMEDIATE_2_L",
    "LeftHandIndex4": "PHALANX_DISTAL_2_L",
    "LeftHandMiddle1": "METACARPAL_3_L",
    "LeftHandMiddle2": "PHALANX_PROXIMAL_3_L",
    "LeftHandMiddle3": "PHALANX_INTERMEDIATE_3_L",
    "LeftHandMiddle4": "PHALANX_DISTAL_3_L",
    "LeftHandRing1": "METACARPAL_4_L",
    "LeftHandRing2": "PHALANX_PROXIMAL_4_L",
    "LeftHandRing3": "PHALANX_INTERMEDIATE_4_L",
    "LeftHandRing4": "PHALANX_DISTAL_4_L",
    "LeftHandPinky1": "METACARPAL_5_L",
    "LeftHandPinky2": "PHALANX_PROXIMAL_5_L",
    "LeftHandPinky3": "PHALANX_INTERMEDIATE_5_L",
    "LeftHandPinky4": "PHALANX_DISTAL_5_L",
    "LeftUpLeg": "FEMUR_L",
    "LeftLeg": "TIBIA_L",
    "LeftFoot": "TALUS_L",
    "LeftToeBase": "METATARSAL_3_L",
    "LeftToe_End": "TOE_PHALANX_DISTAL_3_L",
}
for _k, _v in list(_MIXAMO.items()):
    if _k.startswith("Left"):
        _MIXAMO["Right" + _k[4:]] = _v[:-2] + "_R"

_CMU_ALIASES = {
    "LowerBack": "Spine", "Spine1": "Spine2", "Neck1": "Head",
    "LHipJoint": "Hips", "RHipJoint": "Hips",
    "LeftFingerBase": "LeftHandMiddle1", "RightFingerBase": "RightHandMiddle1",
    "LeftHandIndex1": "LeftHandIndex1", "LThumb": "LeftHandThumb1", "RThumb": "RightHandThumb1",
}

BONE_MAPS: Dict[str, BoneMap] = {
    "mixamo": BoneMap(
        map_id="mixamo", label="Mixamo / Adobe (FBX)", source_to_canonical=_MIXAMO, prefix="mixamorig:",
        forward_axis="+Z", up_axis="+Y", scale_to_m=0.01,
        notes="Mixamo exports in centimetres, Y-up, +Z forward. 65 joints; fingers fully covered."),
    "cmu_bvh": BoneMap(
        map_id="cmu_bvh", label="CMU Motion Capture (BVH, cgspeed conversion)", source_to_canonical=_MIXAMO,
        aliases=_CMU_ALIASES, forward_axis="+Z", up_axis="+Y", scale_to_m=0.056444,
        notes="cgspeed BVH files use Mixamo-like names with a few differences (LowerBack, Neck1, *HipJoint). "
              "Unit scale 0.056444 (CMU asf units → m, as documented by cgspeed); fingers mostly absent."),
    "rokoko": BoneMap(
        map_id="rokoko", label="Rokoko Studio (Mixamo naming)", source_to_canonical=_MIXAMO,
        forward_axis="+Z", up_axis="+Y", scale_to_m=1.0,
        notes="Rokoko can export with Mixamo naming in metres."),
    "rigify_def": BoneMap(
        map_id="rigify_def", label="Rigify DEF- layer (round-trip)",
        source_to_canonical={
            "spine": "SACRUM", "spine.001": "LUMBAR_3", "spine.002": "THORACIC_10", "spine.003": "THORACIC_4",
            "spine.004": "CERVICAL_7", "spine.005": "CERVICAL_3", "spine.006": "CERVICAL_1",
            "shoulder.L": "CLAVICLE_L", "upper_arm.L": "HUMERUS_L", "forearm.L": "RADIUS_L", "hand.L": "CAPITATE_L",
            "thigh.L": "FEMUR_L", "shin.L": "TIBIA_L", "foot.L": "TALUS_L", "toe.L": "METATARSAL_3_L",
            "shoulder.R": "CLAVICLE_R", "upper_arm.R": "HUMERUS_R", "forearm.R": "RADIUS_R", "hand.R": "CAPITATE_R",
            "thigh.R": "FEMUR_R", "shin.R": "TIBIA_R", "foot.R": "TALUS_R", "toe.R": "METATARSAL_3_R",
        },
        prefix="DEF-", forward_axis="-Y", up_axis="+Z", scale_to_m=1.0,
        notes="Blender native axes; used to drive the canonical DEF layer from a Rigify control rig."),
}


def get_bone_map(map_id: str) -> BoneMap:
    try:
        return BONE_MAPS[map_id]
    except KeyError as exc:
        raise KeyError(f"unknown bone map '{map_id}'; known: {sorted(BONE_MAPS)}") from exc


def invert(bone_map: BoneMap) -> Dict[str, str]:
    """canonical → first source joint (for export back to a mocap-style rig)."""
    out: Dict[str, str] = {}
    for src, canon in bone_map.source_to_canonical.items():
        out.setdefault(canon, bone_map.prefix + src)
    return out
