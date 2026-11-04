"""Widen the canonical hip joint centres (finding A23, variant A of docs/architecture/PELVIS_HIP_CENTERS_PROPOSAL.md).

    python scripts/fix_hip_centres.py                     # dry run
    python scripts/fix_hip_centres.py --apply --report docs/audit/A23_HIP_CENTRES_REPORT.json

The canonical hip joint centres (``FEMUR_L/R.head``) were 133.2 mm apart. The owner approved variant A: only the
femur heads move, to x = ±0.0901 m (spacing 180.2 mm = BodyParts3D ratio 0.674 × inter-ASIS width 267.4 mm,
ESTIMATE; Wu et al. 2002 ISB frame as the geometric contrast; ANSUR II as plausibility control). y and z of the
heads, the knees (``FEMUR_*.tail``) and every other bone stay as they are, so the femur becomes oblique (3.2°).
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
HIP_CENTRE_HALF_SPACING_M = 0.0901    # ESTIMATE (A23): BP3D 0.674 × 267.4 mm / 2, rounded to 0.1 mm


def fix(data: dict) -> tuple[dict, dict]:
    out = json.loads(json.dumps(data))
    B = {b["canonical_name"]: b for b in out["bones"]}
    info = {}
    for side, lateral in (("L", 1.0), ("R", -1.0)):
        head = B[f"FEMUR_{side}"]["head"]
        info[side] = {"x_before": head["x"], "x_after": lateral * HIP_CENTRE_HALF_SPACING_M}
        head["x"] = lateral * HIP_CENTRE_HALF_SPACING_M
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
        "finding": "A23 hip joint centre spacing (133.2 mm canonical vs 180.1 mm BodyParts3D)",
        "variant": "A: FEMUR_L/R.head x only",
        "file": str(a.json.resolve().relative_to(ROOT)).replace("\\", "/"),
        "sha256_lf_before": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
        "sha256_lf_after": hashlib.sha256(new_text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
        "changed_bones": sorted(n for n in after if after[n] != before[n]),
        "parameters": info,
        "provenance": {
            "hip_centre_half_spacing_m": "ESTIMATE — BodyParts3D ratio 0.674 (hip-centre spacing / inter-ASIS, one "
                                         "subject, internal use) × inter-ASIS 267.4 mm; pending HIP_JOINT_CENTRE_SPACING",
            "contrast": "Wu et al. 2002 ISB pelvic frame (geometry only, no numeric value)",
            "plausibility": "ANSUR II men 1.75-1.85 m: bicristal 280.6 ± 16.1 mm, hip breadth 351.2 ± 23.2 mm (skin)",
            "unchanged": "head y/z, knees (FEMUR tail) and every other bone",
        },
        "samples": {n: {"before": before[n]["head"], "after": after[n]["head"]} for n in ("FEMUR_L", "FEMUR_R")},
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
