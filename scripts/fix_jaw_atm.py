"""Jaw pivot at the temporomandibular joint (Decision 78, variant A of docs/architecture/JAW_ATM_PROPOSAL.md).

    python scripts/fix_jaw_atm.py                     # dry run
    python scripts/fix_jaw_atm.py --apply --report docs/audit/A32_JAW_ATM_REPORT.json

``MANDIBLE`` head moves from the chin to the midline point of the condylar axis, and its tail becomes the chin, whose height
stays at 0.87 H (PROVEN, Drillis & Contini 1966). Both y values and the joint height are ESTIMATE: BodyParts3D ``FJ3289``, one
subject, x1.0468, frame offset calibrated on the skull bones of A30. No node, parent or game bone changes. The table
holds final positions, so the script is deterministic and idempotent; refuses the ``_backup`` fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "src" / "character_engine" / "data" / "anatomy" / "references"
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
REGISTRY = REFERENCES / "source_registry.json"

HEAD = {"x": 0.0, "y": -0.0168, "z": 1.6539}
TAIL = {"x": 0.0, "y": -0.0914, "z": 1.566}

_OLD_NOTE = "MANDIBLE head stays at the chin (0.87 H, DRILLIS_CONTINI_1966); its TMJ pivot is pending."
_NEW_NOTE = "MANDIBLE: see TMJ_AXIS."
_ANCHOR = '      "SKULL_BONE_POSITIONS:'
_TMJ_NOTE = (
    '      "TMJ_AXIS: MANDIBLE head at the midline point of the condylar axis, tail at the chin. ESTIMATE - Decision 78 / A32 '
    "from BodyParts3D FJ3289 (one subject, x 1.0468, frame offset calibrated on the A30 skull bones). The chin height stays at "
    '0.87 H (PROVEN, DRILLIS_CONTINI_1966); its y is ESTIMATE. A population source for the joint position is pending.",\n'
)


def fix(data: dict) -> tuple[dict, bool]:
    out = json.loads(json.dumps(data))
    bone = next(b for b in out["bones"] if b["canonical_name"] == "MANDIBLE")
    changed = bone["head"] != HEAD or bone["tail"] != TAIL
    bone["head"], bone["tail"] = dict(HEAD), dict(TAIL)
    return out, changed


def fix_registry(text: str) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    t = text.replace("\r\n", "\n")
    if '"TMJ_AXIS:' in t:
        return t.replace("\n", newline)
    if t.count(_OLD_NOTE) != 1 or t.count(_ANCHOR) != 1:
        raise SystemExit("registry anchor not found")
    t = t.replace(_OLD_NOTE, _NEW_NOTE).replace(_ANCHOR, _TMJ_NOTE + _ANCHOR)
    json.loads(t)
    return t.replace("\n", newline)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path, default=CANONICAL)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", type=Path, default=None)
    a = ap.parse_args(argv)
    if a.json.name.endswith("_backup.json"):
        print("refusing to touch the frozen backup fixture")
        return 2
    raw = a.json.read_bytes()
    text = raw.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    data = json.loads(text)
    body = json.dumps(data, indent=2, ensure_ascii=False).replace("\n", newline)
    if not text.startswith(body):
        print("formatting is not reproducible; aborting")
        return 3
    new, changed = fix(data)
    new_text = json.dumps(new, indent=2, ensure_ascii=False).replace("\n", newline) + text[len(body):]
    registry_raw = REGISTRY.read_bytes()
    registry_new = fix_registry(registry_raw.decode("utf-8"))
    report = {
        "finding": "A32 jaw pivot at the chin; the jaw must rotate at the temporomandibular joint",
        "variant": "A: head at the TMJ axis midpoint, tail at the chin",
        "mandible": {"head": HEAD, "tail": TAIL},
        "sha256_lf_before": _sha(raw),
        "sha256_lf_after": _sha(new_text.encode("utf-8")),
        "registry_sha256_lf_before": _sha(registry_raw),
        "registry_sha256_lf_after": _sha(registry_new.encode("utf-8")),
        "changed": changed,
        "provenance": {
            "head": "ESTIMATE: BodyParts3D FJ3289, condylar heads, one subject, x1.0468, frame offset calibrated on the A30 skull bones",
            "tail_z": "PROVEN: chin 0.87 H, DRILLIS_CONTINI_1966",
            "tail_y": "ESTIMATE: BodyParts3D FJ3289 menton, same map",
        },
        "applied": bool(a.apply),
    }
    print(json.dumps(report, indent=2))
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if a.apply:
        a.json.write_bytes(new_text.encode("utf-8"))
        REGISTRY.write_bytes(registry_new.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
