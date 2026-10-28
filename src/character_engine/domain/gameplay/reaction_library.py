"""Reaction library (Deliverable 1): attack clip x defender stance x spacing -> contact -> wound -> reaction.

Each entry of the library is produced offline (Blender mock-up, ``runtime/blender/ce_reaction_library.py``):
the attacker's PLACEHOLDER sabre is tested frame by frame against the defender's collision capsules and against
the defender's own sabre. The **first event** decides the entry:

* ``body_hit`` — the blade enters a capsule first: the contact becomes a wound through the domain wound model
  (layer 1, deterministic, the same code the Godot gameplay table is generated from) and the wound selects a
  reaction clip (``reaction_for``);
* ``parry`` — the two blades touch first (blade centre lines closer than ``PARRY_CONTACT_M``): no wound, the
  attacker plays the recoil clip (``parry_reaction_for``) and the scan checks whether the body is reached later;
* ``none`` — neither happens.

The reaction rules are **ASSUMED**: they stand in for the baked L2/L3 manifestations of Decisions 44-45 until
offline simulation produces them, and they can only use the clips of the CC0 animation libraries (Quaternius
UAL1/UAL2), which have no dedicated "blocked hit", "fall" or "stagger" clips. Defender reaction (schema 4):

* lethal (lethality >= 0.5 or severity >= CRITICAL) -> ``Death01``
* head or neck -> ``Hit_Head``
* incapacitating wound of the leg (thigh, leg, foot) -> ``Hit_Knockback`` (loses support: falls)
* severity >= SEVERE elsewhere -> ``Hit_Knockback``
* anything else -> ``Hit_Chest`` (stagger)

History: schema 2 added ``reaction_playback`` (the defender plays the reaction from the first contact), schema 3
the NLA blend-in and ``attacker_reaction`` (recovery clip after a landed hit), schema 4 the parry detection
(``event``, ``blade_distance_m``, ``first_parry``, ``parry_playback``) and the reaction rule above (schema 3:
any incapacitating wound -> knockback).

Pure Python, no engine code. The JSON written from it is read by Godot (plain JSON, no engine types).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..trauma import Severity

SCHEMA_VERSION = 4   # 2: reaction_playback; 3: blend-in, attacker_reaction; 4: parry, reaction rule by region

REACTION_CLIPS: Mapping[str, str] = {
    "death": "Death01", "knockback": "Hit_Knockback", "head": "Hit_Head", "body": "Hit_Chest",
}
HEAD_REGIONS = ("head", "neck")
LEG_REGIONS = ("thigh", "leg", "foot")

#: Attacker after a landed body hit: recovery clip of the sword library (ASSUMED stand-in for an impact recoil).
ATTACKER_RECOVERY_CLIP = "Sword_Regular_A_Rec"
#: Attacker after a parry: torso-recoil clip (ASSUMED; the CC0 libraries have no "blocked hit" clip).
ATTACKER_PARRIED_CLIP = "Hit_Chest"
#: Blade-on-blade contact when the blade centre lines come this close (= PLACEHOLDER blade width), ASSUMED.
PARRY_CONTACT_M = 0.035

EVENTS = ("body_hit", "parry", "none")
ENTRY_KEYS = ("id", "attack_clip", "defender_stance", "distance_m", "distance_provenance", "frames",
              "signed_distance_m", "blade_distance_m", "min_distance_m", "event", "first_contact", "first_parry",
              "wound", "reaction", "reaction_playback", "parry_playback", "energy_j", "energy_basis", "seed",
              "provenance", "sha256")
CONTACT_KEYS = ("frame", "segment", "bone", "penetration_m", "entry_point")
PARRY_KEYS = ("frame", "blade_distance_m", "point")
PLAYBACK_KEYS = ("start_frame", "clip", "blend_in_frames", "frames", "signed_distance_m", "separated_at_frame",
                 "max_penetration_after_m", "penetrating_at_end", "wound_bone_consistent_ratio", "provenance",
                 "attacker_reaction")
PARRY_PLAYBACK_KEYS = ("start_frame", "attacker_clip", "rule", "blend_in_frames", "frames", "signed_distance_m",
                       "body_reached_after_parry", "provenance")
ATTACKER_REACTION_KEYS = ("clip", "rule", "starts_frame", "blend_in_frames", "provenance")
WOUND_KEYS = ("type", "bone", "region", "depth_m", "width_m", "layers_breached", "severity", "lethality",
              "bleeding_rate", "fracture", "incapacitating", "provenance")

Vec = Sequence[float]


def reaction_for(region: str, severity: int, lethality: float, incapacitating: bool) -> Tuple[str, str]:
    """(reaction clip, rule name) for a wound assessment — ASSUMED rule, see module docstring."""
    if lethality >= 0.5 or severity >= Severity.CRITICAL.value:
        return REACTION_CLIPS["death"], "lethal"
    if region in HEAD_REGIONS:
        return REACTION_CLIPS["head"], "head_or_neck"
    if incapacitating and region in LEG_REGIONS:
        return REACTION_CLIPS["knockback"], "leg_incapacitated_fall"
    if severity >= Severity.SEVERE.value:
        return REACTION_CLIPS["knockback"], "severe"
    return REACTION_CLIPS["body"], "body_stagger"


def attacker_reaction_for(defender_stance: str, wound_region: str) -> Tuple[str, str]:
    """(clip, rule) for the attacker after a landed body hit — ASSUMED: always the sword recovery clip."""
    return ATTACKER_RECOVERY_CLIP, "landed_hit_recovery"


def parry_reaction_for(defender_stance: str) -> Tuple[str, str]:
    """(clip, rule) for the attacker whose blade was met by the defender's — ASSUMED recoil."""
    return ATTACKER_PARRIED_CLIP, "parried_recoil"


def segment_distance(p0: Vec, p1: Vec, q0: Vec, q1: Vec) -> Tuple[float, Tuple[float, float, float]]:
    """Closest distance between segments p0-p1 and q0-q1, and the midpoint of the closest pair (pure geometry)."""
    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def clamp(x):
        return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

    d1, d2, r = sub(p1, p0), sub(q1, q0), sub(p0, q0)
    a, e, f = dot(d1, d1), dot(d2, d2), dot(d2, r)
    if a <= 1e-12 and e <= 1e-12:
        s = t = 0.0
    elif a <= 1e-12:
        s, t = 0.0, clamp(f / e)
    else:
        c = dot(d1, r)
        if e <= 1e-12:
            s, t = clamp(-c / a), 0.0
        else:
            b = dot(d1, d2)
            den = a * e - b * b
            s = clamp((b * f - c * e) / den) if den > 1e-12 else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                s, t = clamp(-c / a), 0.0
            elif t > 1.0:
                s, t = clamp((b - c) / a), 1.0
    cp = (p0[0] + d1[0] * s, p0[1] + d1[1] * s, p0[2] + d1[2] * s)
    cq = (q0[0] + d2[0] * t, q0[1] + d2[1] * t, q0[2] + d2[2] * t)
    diff = sub(cp, cq)
    mid = ((cp[0] + cq[0]) / 2, (cp[1] + cq[1]) / 2, (cp[2] + cq[2]) / 2)
    return dot(diff, diff) ** 0.5, mid


def first_event(frames: Sequence[int], signed: Sequence[float], blade: Sequence[float]) -> Tuple[str, Optional[int]]:
    """('body_hit' | 'parry' | 'none', frame): whichever happens first; a tie counts as a parry (blade met first)."""
    for fr, s, b in zip(frames, signed, blade):
        if b <= PARRY_CONTACT_M:
            return "parry", fr
        if s <= 0.0:
            return "body_hit", fr
    return "none", None


def entry_sha256(entry: Mapping[str, Any]) -> str:
    """SHA-256 of the entry's canonical JSON (sorted keys), excluding its own ``sha256`` field."""
    body = {k: v for k, v in entry.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _check_body_hit(e: Mapping[str, Any], eid: str) -> List[str]:
    problems: List[str] = []
    c, w, r = e["first_contact"], e["wound"], e["reaction"]
    if not c or [k for k in CONTACT_KEYS if k not in c] or c["penetration_m"] <= 0:
        return [f"{eid}: bad first_contact"]
    if not w or [k for k in WOUND_KEYS if k not in w]:
        problems.append(f"{eid}: bad wound")
    elif r is None or r.get("clip") not in REACTION_CLIPS.values():
        problems.append(f"{eid}: bad reaction")
    elif (r["clip"], r["rule"]) != reaction_for(w["region"], w["severity"], w["lethality"], w["incapacitating"]):
        problems.append(f"{eid}: reaction does not follow the rule")
    p = e["reaction_playback"]
    if not p or [k for k in PLAYBACK_KEYS if k not in p]:
        return problems + [f"{eid}: bad reaction_playback"]
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
    if e["first_parry"] is not None or e["parry_playback"] is not None:
        problems.append(f"{eid}: a body hit carries no parry")
    return problems


def _check_parry(e: Mapping[str, Any], eid: str) -> List[str]:
    problems: List[str] = []
    fp, pp = e["first_parry"], e["parry_playback"]
    if not fp or [k for k in PARRY_KEYS if k not in fp] or fp["blade_distance_m"] > PARRY_CONTACT_M:
        return [f"{eid}: bad first_parry"]
    if any(e[k] is not None for k in ("first_contact", "wound", "reaction", "reaction_playback")):
        problems.append(f"{eid}: a parry carries no wound or reaction")
    if not pp or [k for k in PARRY_PLAYBACK_KEYS if k not in pp]:
        return problems + [f"{eid}: bad parry_playback"]
    if pp["start_frame"] != fp["frame"]:
        problems.append(f"{eid}: parry playback must start at the parry")
    if (pp["attacker_clip"], pp["rule"]) != parry_reaction_for(e["defender_stance"]):
        problems.append(f"{eid}: parry reaction does not follow the rule")
    if len(pp["frames"]) != len(pp["signed_distance_m"]) or not pp["frames"]:
        problems.append(f"{eid}: one parry-playback distance per frame")
    if pp["body_reached_after_parry"] != any(s <= 0.0 for s in pp["signed_distance_m"][1:]):
        problems.append(f"{eid}: body_reached_after_parry inconsistent")
    return problems


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
        if not len(e["signed_distance_m"]) == len(e["blade_distance_m"]) == len(e["frames"]):
            problems.append(f"{eid}: one signed and one blade distance per frame")
        event, frame = first_event(e["frames"], e["signed_distance_m"], e["blade_distance_m"])
        if e["event"] not in EVENTS or e["event"] != event:
            problems.append(f"{eid}: event {e['event']} does not match the scan ({event})")
        elif event == "body_hit":
            problems += _check_body_hit(e, eid)
            if e["first_contact"] and e["first_contact"]["frame"] != frame:
                problems.append(f"{eid}: first_contact frame is not the first body contact")
        elif event == "parry":
            problems += _check_parry(e, eid)
            if e["first_parry"] and e["first_parry"]["frame"] != frame:
                problems.append(f"{eid}: first_parry frame is not the first blade contact")
        elif any(e[k] is not None for k in ("first_contact", "first_parry", "wound", "reaction",
                                            "reaction_playback", "parry_playback")):
            problems.append(f"{eid}: no event but contact data present")
        if e["provenance"] != "estimate":
            problems.append(f"{eid}: provenance must be estimate")
        if e["sha256"] != entry_sha256(e):
            problems.append(f"{eid}: sha256 mismatch")
    return problems


def summary(data: Mapping[str, Any]) -> Dict[str, Any]:
    """Counts used by reports: entries, events, reactions per clip, parries that still reached the body."""
    entries = data.get("entries", [])
    hits = [e for e in entries if e.get("event") == "body_hit"]
    parries = [e for e in entries if e.get("event") == "parry"]
    per_clip: Dict[str, int] = {}
    for e in hits:
        per_clip[e["reaction"]["clip"]] = per_clip.get(e["reaction"]["clip"], 0) + 1
    return {"entries": len(entries), "body_hits": len(hits), "parries": len(parries), "reactions": per_clip,
            "parries_reaching_body_after": sum(1 for e in parries if e["parry_playback"]["body_reached_after_parry"])}
