"""Put radius and ulna side by side in X (finding A11).

    python scripts/fix_forearm_layout.py                     # dry run
    python scripts/fix_forearm_layout.py --apply --report docs/audit/A11_FOREARM_LAYOUT_REPORT.json

In the anatomical position (palms −Y) the radius is lateral (thumb side) and the ulna medial.
The canonical data split them antero-posteriorly instead (radius at y −0.0333, ulna at +0.0333).
This script keeps each pair's midpoint and the existing half-separation (PLACEHOLDER, no source)
and only moves it from the Y axis to the X axis with the lateral sign of each side (left = +X,
Decision 17). Lengths and z values (elbow / wrist landmarks, Trotter osteometry) are unchanged.
Deterministic and idempotent; refuses the frozen ``_backup`` fixture. Run
``scripts/rebuild_hand_layout.py`` afterwards: the hand is anchored on the radius tail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"


def _r(v: float) -> float:
    v = round(v, 4)
    return 0.0 if v == 0 else v


def fix(data: dict) -> tuple[dict, dict]:
    out = json.loads(json.dumps(data))
    B = {b["canonical_name"]: b for b in out["bones"]}
    info = {}
    for side, lateral in (("L", 1.0), ("R", -1.0)):
        rad, uln = B[f"RADIUS_{side}"], B[f"ULNA_{side}"]
        for end in ("head", "tail"):
            r, u = rad[end], uln[end]
            dx, dy = r["x"] - u["x"], r["y"] - u["y"]
            half = (dx * dx + dy * dy) ** 0.5 / 2
            cx, cy = (r["x"] + u["x"]) / 2, (r["y"] + u["y"]) / 2
            r["x"], r["y"] = _r(cx + lateral * half), _r(cy)
            u["x"], u["y"] = _r(cx - lateral * half), _r(cy)
            info[f"{side}_{end}"] = {"midpoint_xy_m": [_r(cx), _r(cy)], "half_separation_m": _r(half)}
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
    names = ("RADIUS_L", "ULNA_L", "RADIUS_R", "ULNA_R")
    report = {
        "finding": "A11 forearm layout (radius/ulna split in Y instead of X)",
        "file": str(a.json.relative_to(ROOT)).replace("\\", "/"),
        "sha256_before": hashlib.sha256(raw).hexdigest(),
        "sha256_after": hashlib.sha256(new_text.encode("utf-8")).hexdigest(),
        "changed_bones": sorted(n for n in after if after[n] != before[n]),
        "parameters": info,
        "provenance": {
            "midpoints_lengths_z": "unchanged existing data (z = elbow/wrist landmarks, DERIVED)",
            "half_separation": "PLACEHOLDER — pre-existing 0.0333 m, moved from Y to X; pending FOREARM_INTEROSSEOUS_WIDTH",
            "radius_lateral_to_ulna": "PROVEN topology (anatomical position)",
        },
        "samples": {n: {"before": {k: before[n][k] for k in ("head", "tail")},
                        "after": {k: after[n][k] for k in ("head", "tail")}} for n in names},
        "applied": bool(a.apply),
    }
    print(json.dumps({k: v for k, v in report.items() if k != "samples"}, indent=2))
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.apply:
        a.json.write_bytes(new_text.encode("utf-8"))
        print(f"rewritten: {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
