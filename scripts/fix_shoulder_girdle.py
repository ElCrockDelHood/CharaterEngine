"""Shoulder girdle positions (finding A24, variant A of docs/architecture/SHOULDER_GIRDLE_PROPOSAL.md).

    python scripts/fix_shoulder_girdle.py                     # dry run
    python scripts/fix_shoulder_girdle.py --apply --report docs/audit/A24_SHOULDER_GIRDLE_REPORT.json

Moves only HUMERUS_L/R.head x (gleno-humeral spacing 406.8 mm = ANSUR II biacromial 421.1 mm × BodyParts3D ratio
0.966, ESTIMATE) and places CLAVICLE_L/R (SC → AC) and SCAPULA_L/R (AC → inferior angle) from BodyParts3D offsets
(×1.0358, ISB landmarks of Wu et al. 2005; DERIVED from one subject, ESTIMATE): SC relative to the canonical
STERNUM head (incisura jugularis), AC and the inferior angle relative to the new shoulder joint centre. Elbows,
forearms, hands and the hierarchy are unchanged (no re-parent here). Deterministic and idempotent; refuses the
frozen ``_backup`` fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

GH_HALF_SPACING_M = 0.2034            # ESTIMATE (A24): 0.966 × 421.1 mm / 2
SC_FROM_IJ = (0.0220, 0.0080, -0.0058)    # left side, x lateral; BodyParts3D × 1.0358 (ESTIMATE)
AC_FROM_GH = (-0.0172, 0.0037, 0.0377)
AI_FROM_GH = (-0.0685, 0.0718, -0.1365)


def _r(v: float) -> float:
    v = round(v, 4)
    return 0.0 if v == 0 else v


def _pt(base: dict, off, lateral: float) -> dict:
    return {"x": _r(base["x"] + lateral * off[0]), "y": _r(base["y"] + off[1]), "z": _r(base["z"] + off[2])}


def fix(data: dict) -> tuple[dict, dict]:
    out = json.loads(json.dumps(data))
    B = {b["canonical_name"]: b for b in out["bones"]}
    ij = B["STERNUM"]["head"]
    info = {}
    for side, lateral in (("L", 1.0), ("R", -1.0)):
        hum = B[f"HUMERUS_{side}"]
        hum["head"]["x"] = _r(lateral * GH_HALF_SPACING_M)
        gh = hum["head"]
        sc = _pt({"x": ij["x"], "y": ij["y"], "z": ij["z"]}, SC_FROM_IJ, lateral)
        ac = _pt(gh, AC_FROM_GH, lateral)
        ai = _pt(gh, AI_FROM_GH, lateral)
        B[f"CLAVICLE_{side}"]["head"], B[f"CLAVICLE_{side}"]["tail"] = sc, ac
        B[f"SCAPULA_{side}"]["head"], B[f"SCAPULA_{side}"]["tail"] = dict(ac), ai
        info[side] = {"GH": gh, "SC": sc, "AC": ac, "AI": ai}
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
    names = ("HUMERUS_L", "CLAVICLE_L", "SCAPULA_L", "HUMERUS_R", "CLAVICLE_R", "SCAPULA_R")
    report = {
        "finding": "A24 shoulder girdle (GH spacing = biacromial; clavicle / scapula stubs on the shoulder joint)",
        "variant": "A: shoulder girdle and humeral heads only; arm chain and hierarchy unchanged",
        "file": str(a.json.resolve().relative_to(ROOT)).replace("\\", "/"),
        "sha256_lf_before": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
        "sha256_lf_after": hashlib.sha256(new_text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
        "changed_bones": sorted(n for n in after if after[n] != before[n]),
        "parameters": info,
        "provenance": {
            "gh_half_spacing_m": "ESTIMATE — ANSUR II biacromial 421.1 mm (men 1.75-1.85 m, n 1814) × BodyParts3D "
                                 "GH / acromion ratio 0.966; pending SHOULDER_JOINT_CENTRE_SPACING",
            "girdle_offsets": "DERIVED from BodyParts3D (one subject, internal use) × 1.0358, ISB landmarks "
                              "(Wu et al. 2005); ESTIMATE; pending SHOULDER_GIRDLE_LANDMARKS",
            "unchanged": "humerus head y/z, elbows, forearms, hands, hierarchy (CLAVICLE parent ROOT_SKELETON)",
        },
        "samples": {n: {"before": {k: before[n][k] for k in ("head", "tail")},
                        "after": {k: after[n][k] for k in ("head", "tail")}} for n in names},
        "applied": bool(a.apply),
    }
    print(json.dumps({k: v for k, v in report.items() if k not in ("samples", "parameters")}, indent=2))
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.apply:
        a.json.write_bytes(new_text.encode("utf-8"))
        print(f"rewritten: {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
