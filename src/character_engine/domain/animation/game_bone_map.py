"""Bone maps onto the CE-GAME-v1 game rig (RIG-GAME-001 step 6).

The game rig uses UE5 Mannequin names, so the industry correspondence Mixamo → UE5 (the one Unreal and most
retargeters use) maps 1:1 without anatomical choices: ``Hips → pelvis``, ``Spine/Spine1/Spine2 →
spine_01/02/03``, ``LeftHandIndex1..3 → index_01..03_l``, ``LeftToeBase → ball_l`` … Quaternius UAL already uses
those names. End bones (``*_End``, ``*4``, ``*_leaf``) and ``root`` stay unmapped.

The maps reuse :class:`~.bone_map.BoneMap` with ``target_rig = "CE-GAME-v1"``: ``source_to_canonical`` then holds
*game* bone names. Source metadata (prefix, axes, unit scale, aliases) is the same as the canonical maps.

:func:`differences_from_canonical` lists the joints where the canonical map lands on a different game bone than
this map. Since the canonical maps were corrected to the same correspondence (fingers 2–5 on the proximal phalanx,
ToeBase on the ball joint — owner, 2026-10-25) only ``Head`` remains, by design: the canonical target CERVICAL_1
has its head at the skull base, the same point as the game ``head`` pivot, but the game rig carries C1 on
``neck_01``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, Mapping, Tuple

from ..rigging.game_rig import GAME_BONES, RIG_ID, canonical_to_game
from .bone_map import _UE_TO_MIXAMO, BONE_MAPS, BoneMap

_GAME_NAMES = frozenset(g.name for g in GAME_BONES)


def _ue_to_game(ue: str) -> str:
    return ue.lower() if ue.lower() in _GAME_NAMES else ""


_MIXAMO_TO_GAME: Dict[str, str] = {mx: _ue_to_game(ue) for ue, mx in _UE_TO_MIXAMO.items() if _ue_to_game(ue)}
_QUATERNIUS_TO_GAME: Dict[str, str] = {ue: _ue_to_game(ue) for ue in _UE_TO_MIXAMO if _ue_to_game(ue)}
_RIGIFY_TO_GAME: Dict[str, str] = {
    "spine": "pelvis", "spine.001": "spine_01", "spine.002": "spine_02", "spine.003": "spine_03",
    "spine.004": "neck_01", "spine.006": "head",
    **{f"{rig}.{S}": f"{game}_{S.lower()}" for S in "LR" for rig, game in (
        ("shoulder", "clavicle"), ("upper_arm", "upperarm"), ("forearm", "lowerarm"), ("hand", "hand"),
        ("thigh", "thigh"), ("shin", "calf"), ("foot", "foot"), ("toe", "ball"))},
}

_TARGETS: Mapping[str, Mapping[str, str]] = {
    "mixamo": _MIXAMO_TO_GAME, "cmu_bvh": _MIXAMO_TO_GAME, "rokoko": _MIXAMO_TO_GAME,
    "quaternius_ual": _QUATERNIUS_TO_GAME, "rigify_def": _RIGIFY_TO_GAME,
}

GAME_BONE_MAPS: Dict[str, BoneMap] = {
    map_id: replace(BONE_MAPS[map_id], source_to_canonical=dict(targets), target_rig=RIG_ID,
                    notes=BONE_MAPS[map_id].notes + " Game-rig targets (UE5 Mannequin names, RIG-GAME-001).")
    for map_id, targets in _TARGETS.items()
}


def get_game_bone_map(map_id: str) -> BoneMap:
    try:
        return GAME_BONE_MAPS[map_id]
    except KeyError as exc:
        raise KeyError(f"unknown game bone map '{map_id}'; known: {sorted(GAME_BONE_MAPS)}") from exc


def differences_from_canonical(map_id: str) -> Dict[str, Tuple[str, str]]:
    """Source joint -> (game bone carrying the canonical target, game-map target) where they differ."""
    carriers = canonical_to_game()
    canon = BONE_MAPS[map_id].source_to_canonical
    out: Dict[str, Tuple[str, str]] = {}
    for src, game in GAME_BONE_MAPS[map_id].source_to_canonical.items():
        via = carriers.get(canon.get(src, ""), "")
        if via != game:
            out[src] = (via, game)
    return out
