"""Reaction library (Deliverable 1): attack clip x defender stance x spacing -> contact -> wound -> reaction.

Each entry of the library is produced offline (Blender mock-up, ``runtime/blender/ce_reaction_library.py``):
the attacker's PLACEHOLDER sabre is tested frame by frame against the defender's collision capsules; the
first frame with penetration becomes a wound through the domain wound model (layer 1, deterministic, the same
code the Godot gameplay table is generated from), and the wound selects a reaction clip.

The reaction rule is **ASSUMED**: it stands in for the baked L2/L3 manifestations of Decisions 44-45 until
offline simulation produces them. It maps the assessment to one of the reaction clips available in the
CC0 animation libraries (Quaternius UAL1/UAL2):

* lethal (lethality >= 0.5 or severity >= CRITICAL) -> ``Death01``
* incapacitating or severity >= SEVERE -> ``Hit_Knockback``
* head or neck -> ``Hit_Head``
* anything else -> ``Hit_Chest``

Schema 2 adds ``reaction_playback``: from the first-contact frame the defender plays the reaction clip (no blend,
``blend_in_frames`` 0, ASSUMED) and the scan continues, recording the signed distance after contact, the frame the
blade leaves the body, the deepest penetration after contact, and how often the wound point carried by the
wounded bone still has that bone as its nearest canonical bone.

Schema 3 blends the reaction in over ``blend_in_frames`` (ASSUMED) and adds ``attacker_reaction``: after a landed
body hit the attacker switches to the sword recovery clip (``attacker_reaction_for``, ASSUMED) from the frame after
contact, with the same blend.

Pure Python, no engine code. The JSON written from it is read by Godot (plain JSON, no engine types).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping, Tuple

from ..trauma import Severity

SCHEMA_VERSION = 3   # 2: reaction_playback; 3: blend-in and attacker_reaction

REACTION_CLIPS: Mapping[str, str] = {
    "death": "Death01", "knockback": "Hit_Knockback", "head": "Hit_Head", "body": "Hit_Chest",
}
HEAD_REGIONS = ("head", "neck")

#: Attacker after a landed body hit: recovery clip of the sword library (ASSUMED stand-in for an impact recoil).
ATTACKER_RECOVERY_CLIP = "Sword_Regular_A_Rec"

ENTRY_KEYS = ("id", "attack_clip", "defender_stance", "distance_m", "distance_provenance", "frames",
              "signed_distance_m", "min_distance_m", "first_contact", "wound", "reaction", "reaction_playback", "energy_j",
              "energy_basis", "seed", "provenance", "sha256")
CONTACT_KEYS = ("frame", "segment", "bone", "penetration_m", "entry_point")
PLAYBACK_KEYS = ("start_frame", "clip", "blend_in_frames", "frames", "signed_distance_m", "separated_at_frame",
                 "max_penetration_after_m", "penetrating_at_end", "wound_bone_consistent_ratio", "provenance",
                 "attacker_reaction")
ATTACKER_REACTION_KEYS = ("clip", "rule", "starts_frame", "blend_in_frames", "provenance")
WOUND_KEYS = ("type", "bone", "region", "depth_m", "width_m", "layers_breached", "severity", "lethality",
              "bleeding_rate", "fracture", "incapacitating", "provenance")


def reaction_for(region: str, severity: int, lethality: float, incapacitating: bool) -> Tuple[str, str]:
    """(reaction clip, rule name) for a wound assessment — ASSUMED rule, see module docstring."""
    if lethality >= 0.5 or severity >= Severity.CRITICAL.value:
        return REACTION_CLIPS["death"], "lethal"
    if incapacitating or severity >= Severity.SEVERE.value:
        return REACTION_CLIPS["knockback"], "incapacitating_or_severe"
    if region in HEAD_REGIONS:
        return REACTION_CLIPS["head"], "head_or_neck"
    return REACTION_CLIPS["body"], "body"


def attacker_reaction_for(defender_stance: str, wound_region: str) -> Tuple[str, str]:
    """(clip, rule) for the attacker after a landed body hit — ASSUMED: always the sword recovery clip.

    Blade-on-blade contact (a parry) is not modelled, so every contact here is a hit on the body, whatever the
    defender's stance; a "blocked" attacker reaction would need that detection first.
    """
    return ATTACKER_RECOVERY_CLIP, "landed_hit_recovery"


def entry_sha256(entry: Mapping[str, Any]) -> str:
    """SHA-256 of the entry's canonical JSON (sorted keys), excluding its own ``sha256`` field."""
    body = {k: v for k, v in entry.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_library(data: Mapping[str, Any]) -> List[str]:
    """Problems found in a reaction library document (empty list = valid)."""
    problems: List[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION}")
    sources = data.get("sources")
    if not sources or not all({"file", "sha256", "licence"} <= set(s) for s in sources):
        problems.append("sources must list file, sha256 and licence")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        return problems + ["entries must be a non-empty list"]
    ids = set()
    for e in entries:
        eid = e.get("id", "?")
        missing = [k for k in ENTRY_KEYS if k not in e]
        if missing:
            problems.append(f"{eid}: missing {missing}")
            continue
        if eid in ids:
            problems.append(f"duplicate id {eid}")
        ids.add(eid)
        if len(e["signed_distance_m"]) != len(e["frames"]):
            problems.append(f"{eid}: one signed distance per frame")
        if e["first_contact"] is None:
            if e["wound"] is not None or e["reaction"] is not None or e["reaction_playback"] is not None:
                problems.append(f"{eid}: wound/reaction/playback without contact")
            if e["min_distance_m"] <= 0:
                problems.append(f"{eid}: penetration recorded but no first_contact")
        else:
            c, w, r = e["first_contact"], e["wound"], e["reaction"]
            if [k for k in CONTACT_KEYS if k not in c] or c["penetration_m"] <= 0:
                problems.append(f"{eid}: bad first_contact")
            if not w or [k for k in WOUND_KEYS if k not in w]:
                problems.append(f"{eid}: bad wound")
            elif r is None or r.get("clip") not in REACTION_CLIPS.values():
                problems.append(f"{eid}: bad reaction")
            elif (r["clip"], r["rule"]) != reaction_for(w["region"], w["severity"], w["lethality"],
                                                        w["incapacitating"]):
                problems.append(f"{eid}: reaction does not follow the rule")
            p = e["reaction_playback"]
            if not p or [k for k in PLAYBACK_KEYS if k not in p]:
                problems.append(f"{eid}: bad reaction_playback")
            else:
                if p["start_frame"] != c["frame"] or (r and p["clip"] != r["clip"]):
                    problems.append(f"{eid}: playback must start at the first contact with the reaction clip")
                if len(p["frames"]) != len(p["signed_distance_m"]) or not p["frames"]:
                    problems.append(f"{eid}: one playback distance per frame")
                if not 0.0 <= p["wound_bone_consistent_ratio"] <= 1.0:
                    problems.append(f"{eid}: wound_bone_consistent_ratio out of [0, 1]")
                if not isinstance(p["blend_in_frames"], int) or p["blend_in_frames"] < 0:
                    problems.append(f"{eid}: blend_in_frames must be a non-negative integer")
                ar = p["attacker_reaction"]
                if ar is not None:
                    if [k for k in ATTACKER_REACTION_KEYS if k not in ar]:
                        problems.append(f"{eid}: bad attacker_reaction")
                    elif (ar["clip"], ar["rule"]) != attacker_reaction_for(e["defender_stance"], (w or {}).get("region", "")):
                        problems.append(f"{eid}: attacker reaction does not follow the rule")
                    elif ar["starts_frame"] != c["frame"] + 1:
                        problems.append(f"{eid}: attacker reaction must start the frame after contact")
        if e["provenance"] != "estimate":
            problems.append(f"{eid}: provenance must be estimate")
        if e["sha256"] != entry_sha256(e):
            problems.append(f"{eid}: sha256 mismatch")
    return problems


def summary(data: Mapping[str, Any]) -> Dict[str, Any]:
    """Counts used by reports: entries, contacts, reactions per clip."""
    entries = data.get("entries", [])
    contacts = [e for e in entries if e.get("first_contact")]
    per_clip: Dict[str, int] = {}
    for e in contacts:
        per_clip[e["reaction"]["clip"]] = per_clip.get(e["reaction"]["clip"], 0) + 1
    separated = sum(1 for e in contacts if (e.get("reaction_playback") or {}).get("separated_at_frame") is not None)
    return {"entries": len(entries), "contacts": len(contacts), "reactions": per_clip,
            "separated_after_reaction": separated}
