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

Pure Python, no engine code. The JSON written from it is read by Godot (plain JSON, no engine types).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping, Tuple

from ..trauma import Severity

SCHEMA_VERSION = 1

REACTION_CLIPS: Mapping[str, str] = {
    "death": "Death01", "knockback": "Hit_Knockback", "head": "Hit_Head", "body": "Hit_Chest",
}
HEAD_REGIONS = ("head", "neck")

ENTRY_KEYS = ("id", "attack_clip", "defender_stance", "distance_m", "distance_provenance", "frames",
              "signed_distance_m", "min_distance_m", "first_contact", "wound", "reaction", "energy_j",
              "energy_basis", "seed", "provenance", "sha256")
CONTACT_KEYS = ("frame", "segment", "bone", "penetration_m", "entry_point")
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
            if e["wound"] is not None or e["reaction"] is not None:
                problems.append(f"{eid}: wound/reaction without contact")
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
    return {"entries": len(entries), "contacts": len(contacts), "reactions": per_clip}
