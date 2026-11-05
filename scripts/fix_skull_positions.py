"""Skull bones at their BodyParts3D positions (Decision 74, variant A of docs/architecture/SKULL_PROPOSAL.md).

    python scripts/fix_skull_positions.py                     # dry run
    python scripts/fix_skull_positions.py --apply --report docs/audit/A30_SKULL_REPORT.json

Each skull bone keeps its segment length and direction and moves to its BodyParts3D centroid (stature map x1.0468, y
relative to the C1 body; one subject, ESTIMATE); pairs are mirror-averaged, midline bones get x = 0. ``FRONTAL`` keeps
its tail at z = 1.80 m (the vertex, stature contract), so it becomes longer. ``MANDIBLE`` is NOT moved: its head is the
chin (0.87 H, PROVEN) and the game jaw pivot, a separate step. Ear ossicles are absent from BodyParts3D and stay.
The table holds final positions, so the script is deterministic and idempotent; refuses the ``_backup`` fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

# bone -> (head, tail), m; ESTIMATE
POSITIONS = {
    "FRONTAL": ((0.0, -0.0607, 1.7024), (0.0, -0.0607, 1.8)),
    "PARIETAL_L": ((0.0257, 0.0293, 1.7327), (0.0257, 0.0293, 1.7662)),
    "PARIETAL_R": ((-0.0257, 0.0293, 1.7327), (-0.0257, 0.0293, 1.7662)),
    "TEMPORAL_L": ((0.0513, -0.0056, 1.6315), (0.0513, -0.0056, 1.6983)),
    "TEMPORAL_R": ((-0.0513, -0.0056, 1.6315), (-0.0513, -0.0056, 1.6983)),
    "OCCIPITAL": ((0.0, 0.058, 1.6471), (0.0, 0.058, 1.7139)),
    "SPHENOID": ((0.0, -0.0402, 1.6519), (0.0, -0.0402, 1.6854)),
    "ETHMOID": ((0.0, -0.067, 1.6489), (0.0, -0.067, 1.6823)),
    "MAXILLA_L": ((0.0188, -0.0812, 1.6178), (0.0188, -0.0812, 1.6512)),
    "MAXILLA_R": ((-0.0188, -0.0812, 1.6178), (-0.0188, -0.0812, 1.6512)),
    "ZYGOMATIC_L": ((0.0481, -0.0683, 1.641), (0.0481, -0.0683, 1.6745)),
    "ZYGOMATIC_R": ((-0.0481, -0.0683, 1.641), (-0.0481, -0.0683, 1.6745)),
    "NASAL_L": ((0.0028, -0.1051, 1.6612), (0.0028, -0.1051, 1.6814)),
    "NASAL_R": ((-0.0028, -0.1051, 1.6612), (-0.0028, -0.1051, 1.6814)),
    "LACRIMAL_L": ((0.0121, -0.083, 1.6584), (0.0121, -0.083, 1.6718)),
    "LACRIMAL_R": ((-0.0121, -0.083, 1.6584), (-0.0121, -0.083, 1.6718)),
    "PALATINE_L": ((0.014, -0.0539, 1.633), (0.014, -0.0539, 1.6531)),
    "PALATINE_R": ((-0.014, -0.0539, 1.633), (-0.014, -0.0539, 1.6531)),
    "INFERIOR_NASAL_CONCHA_L": ((0.0118, -0.0778, 1.635), (0.0118, -0.0778, 1.6484)),
    "INFERIOR_NASAL_CONCHA_R": ((-0.0118, -0.0778, 1.635), (-0.0118, -0.0778, 1.6484)),
    "VOMER": ((0.0, -0.0581, 1.6305), (0.0, -0.0581, 1.664)),
    "HYOID": ((0.0, -0.0372, 1.5801), (0.0, -0.0372, 1.583)),
}


def fix(data: dict) -> tuple[dict, list]:
    out = json.loads(json.dumps(data))
    changed = []
    for b in out["bones"]:
        target = POSITIONS.get(b["canonical_name"])
        if target is None:
            continue
        head = dict(zip("xyz", target[0]))
        tail = dict(zip("xyz", target[1]))
        if b["head"] != head or b["tail"] != tail:
            changed.append(b["canonical_name"])
        b["head"], b["tail"] = head, tail
    return out, changed


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
    report = {
        "finding": "A30 skull bones at schematic positions (A22 median 50 mm)",
        "variant": "A without MANDIBLE; vertex kept at 1.80 m",
        "sha256_lf_before": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
        "sha256_lf_after": hashlib.sha256(new_text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
        "changed_bones": changed,
        "provenance": "ESTIMATE: BodyParts3D centroids (one subject, internal use), stature map, y relative to the C1 body",
        "applied": bool(a.apply),
    }
    print(json.dumps(report, indent=2))
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.apply:
        a.json.write_bytes(new_text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
