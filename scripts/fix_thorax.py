"""Thorax: sternum and ribs (Decision 73, variant A of docs/architecture/THORAX_PROPOSAL.md).

    python scripts/fix_thorax.py                     # dry run
    python scripts/fix_thorax.py --apply --report docs/audit/A28_THORAX_REPORT.json

``STERNUM``: the head (incisura jugularis) stays, so the sternoclavicular joint, clavicle, scapula and shoulders of A24
are untouched; the tail goes to the xiphoid tip (BodyParts3D offset ×1.0468, midline). Each rib runs from its
costovertebral end to its free / costochondral end, placed relative to the mid-point of its own thoracic vertebra with
BodyParts3D offsets (×1.0468; one subject, ESTIMATE). A straight segment is only the chord of a curved rib. Head = most
medial vertex of the posterior 40 %; tail = most anterior vertex; rib 12 (floating, its most anterior vertex is not its
tip) = the vertex farthest from the head, a rule that agrees with the general one within 3 mm on ribs 10 and 11.
Deterministic and idempotent; refuses the frozen ``_backup`` fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

XIPHOID_FROM_IJ = (0.0, -0.0715, -0.1688)     # m, y and z; BodyParts3D × 1.0468, ESTIMATE; x = midline
# rib -> (head, tail), m, relative to the vertebra mid-point; x lateral (left side), y +posterior, z up; ESTIMATE
RIBS = {
    1: ((0.0168, -0.0058, -0.0033), (0.0587, -0.0617, -0.0522)),
    2: ((0.0161, -0.0025, 0.0024), (0.0497, -0.1063, -0.0747)),
    3: ((0.0131, 0.0015, 0.0065), (0.0515, -0.1302, -0.0818)),
    4: ((0.0144, -0.0029, 0.0062), (0.0605, -0.1518, -0.0898)),
    5: ((0.0215, 0.0063, 0.0004), (0.0825, -0.1634, -0.1033)),
    6: ((0.0144, 0.0015, 0.0055), (0.0942, -0.1631, -0.1071)),
    7: ((0.0196, 0.0102, 0.0163), (0.112, -0.1499, -0.1086)),
    8: ((0.0213, 0.0138, 0.0098), (0.1224, -0.1246, -0.1093)),
    9: ((0.027, 0.0174, 0.002), (0.1267, -0.093, -0.1112)),
    10: ((0.0297, 0.0222, -0.0006), (0.1255, -0.0695, -0.1075)),
    11: ((0.0244, 0.0231, 0.0018), (0.1097, -0.0382, -0.1025)),
    12: ((0.0324, 0.0269, -0.0103), (0.0893, 0.0099, -0.0729)),   # tail: farthest vertex from the head
}


def _r(v: float) -> float:
    v = round(v, 4)
    return 0.0 if v == 0 else v


def fix(data: dict) -> tuple[dict, dict]:
    out = json.loads(json.dumps(data))
    B = {b["canonical_name"]: b for b in out["bones"]}
    st = B["STERNUM"]
    st["tail"] = {"x": 0.0, "y": _r(st["head"]["y"] + XIPHOID_FROM_IJ[1]), "z": _r(st["head"]["z"] + XIPHOID_FROM_IJ[2])}
    info = {"STERNUM_tail": st["tail"]}
    for i, (head, tail) in RIBS.items():
        t = B[f"THORACIC_{i}"]
        cy, cz = (t["head"]["y"] + t["tail"]["y"]) / 2, (t["head"]["z"] + t["tail"]["z"]) / 2
        for side, sign in (("L", 1.0), ("R", -1.0)):
            rib = B[f"RIB_{i:02d}_{side}"]
            for end, o in (("head", head), ("tail", tail)):
                rib[end] = {"x": _r(sign * o[0]), "y": _r(cy + o[1]), "z": _r(cz + o[2])}
        info[f"RIB_{i:02d}_L"] = {"head": B[f"RIB_{i:02d}_L"]["head"], "tail": B[f"RIB_{i:02d}_L"]["tail"]}
    return out, info


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
    new, info = fix(data)
    new_text = json.dumps(new, indent=2, ensure_ascii=False).replace("\n", newline) + text[len(body):]
    before = {b["canonical_name"]: b for b in data["bones"]}
    after = {b["canonical_name"]: b for b in new["bones"]}
    report = {
        "finding": "A28 thorax: sternum 47 mm stub, ribs short horizontal stubs detached from the spine",
        "variant": "A: sternum tail and all ribs; sternum head, clavicle, scapula and shoulders kept",
        "sha256_lf_before": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
        "sha256_lf_after": hashlib.sha256(new_text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
        "changed_bones": sorted(n for n in after if after[n] != before[n]),
        "parameters": info,
        "provenance": {"sternum_ribs": "ESTIMATE — BodyParts3D (one subject, internal use) × 1.0468; ribs relative to their own vertebra",
                       "shape": "straight chords of curved bones; the visible curve belongs to the mesh / proxy"},
        "applied": bool(a.apply),
    }
    print(json.dumps({k: v for k, v in report.items() if k != "parameters"}, indent=2))
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.apply:
        a.json.write_bytes(new_text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
