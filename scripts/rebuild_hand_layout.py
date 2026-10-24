"""Rebuild the hand layout of the canonical skeleton (finding A10).

    python scripts/rebuild_hand_layout.py                    # dry run: print the report
    python scripts/rebuild_hand_layout.py --apply --report docs/audit/A10_HAND_LAYOUT_REPORT.json

Problem: metacarpals and phalanges sat 15-20 cm medial to the wrist (near the thigh) and ~10 cm
below the carpals; metacarpals and proximal phalanges were parented to RADIUS.

Provenance of every number (Decision 12 — nothing invented):
* Wrist height = RADIUS tail z, fingertip height = 0.377·H (DRILLIS_CONTINI_1966, PROVEN ratios
  already used by A07); hand length wrist→fingertip = 0.108·H is therefore DERIVED.
* Wrist anchor = RADIUS tail (existing data): the radiocarpal joint is radius ↔ scaphoid/lunate;
  the ulna does not articulate directly with the carpus (PROVEN topology). This also keeps the
  arm IK effector (CAPITATE head) on the forearm axis.
* Topology (PROVEN, any anatomy atlas): proximal carpal row scaphoid–lunate–triquetrum
  (+ pisiform, palmar on the triquetrum), distal row trapezium–trapezoid–capitate–hamate,
  lateral → medial; trapezium→MC1, trapezoid→MC2, capitate→MC3, hamate→MC4/MC5; rays
  MC→proximal→(intermediate)→distal; thumb on the lateral side; palm faces −Y, fingers −Z.
* Split of the hand length (carpal row : metacarpal : phalanx = 2 : 4 : 3) and the ray spacing /
  palmar offset are the **existing placeholder values of the data** (bone lengths 0.0081 / 0.0162 /
  0.0122 m and the 0.0133 m step), only re-arranged and scaled to the sourced hand length.
  They are PLACEHOLDER (not measured) and are registered in source_registry as pending a source.
Bone count, names and all other bones are unchanged; values are rounded to 4 decimals like A07.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
FINGERTIP_RATIO = 0.377          # DRILLIS_CONTINI_1966 (anthropometry.json: fingertip_height_ratio)
UNITS = {"carpal_row": 2, "metacarpal": 4, "phalanx": 3}     # existing placeholder proportions
LATERAL_STEPS = {1: 2.0, 2: 1.0, 3: 0.0, 4: -1.0, 5: -2.0}    # ray offsets in spacing units (thumb lateral)
PROXIMAL_ROW = {"SCAPHOID": 1.0, "LUNATE": 0.0, "TRIQUETRUM": -1.0}
DISTAL_ROW = {"TRAPEZIUM": 2.0, "TRAPEZOID": 1.0, "CAPITATE": 0.0, "HAMATE": -1.5}
MC_PARENT = {1: "TRAPEZIUM", 2: "TRAPEZOID", 3: "CAPITATE", 4: "HAMATE", 5: "HAMATE"}
# PLACEHOLDER values of the pre-A10 data (kept as constants so the script is idempotent):
RAY_SPACING_M = 0.0133      # step between metacarpal rays (METACARPAL_n x)
PALMAR_OFFSET_M = 0.0133    # step between carpal bones (SCAPHOID/LUNATE y)


def _r(v: float) -> float:
    v = round(v, 4)
    return 0.0 if v == 0 else v


def _pt(x, y, z):
    return {"x": _r(x), "y": _r(y), "z": _r(z)}


def rebuild(data: dict) -> tuple[dict, dict]:
    out = json.loads(json.dumps(data))
    B = {b["canonical_name"]: b for b in out["bones"]}
    stature = max(b[e]["z"] for b in out["bones"] for e in ("head", "tail"))
    fingertip_z = FINGERTIP_RATIO * stature
    spacing, palmar = RAY_SPACING_M, PALMAR_OFFSET_M
    info = {"stature_m": stature, "fingertip_z_m": round(fingertip_z, 4), "ray_spacing_m": spacing,
            "pisiform_palmar_offset_m": palmar, "sides": {}}

    for side, lateral in (("L", 1.0), ("R", -1.0)):          # left = +X (Decision 17)
        rad = B[f"RADIUS_{side}"]["tail"]
        wx, wy, wz = rad["x"], rad["y"], rad["z"]
        total_units = 2 * UNITS["carpal_row"] + UNITS["metacarpal"] + 3 * UNITS["phalanx"]
        u = (wz - fingertip_z) / total_units
        def x_of(steps, wx=wx, lateral=lateral):
            return wx + lateral * steps * spacing
        z_dist = wz - UNITS["carpal_row"] * u                  # distal carpal row starts here
        z_mc = wz - 2 * UNITS["carpal_row"] * u                # metacarpal bases

        def put(name, head, tail, parent=None, side=side):
            b = B[f"{name}_{side}"]
            b["head"], b["tail"] = _pt(*head), _pt(*tail)
            if parent is not None:
                b["parent"] = f"{parent}_{side}"

        for n, st in PROXIMAL_ROW.items():
            put(n, (x_of(st), wy, wz), (x_of(st), wy, z_dist))
        put("PISIFORM", (x_of(PROXIMAL_ROW["TRIQUETRUM"]), wy - palmar, wz),
            (x_of(PROXIMAL_ROW["TRIQUETRUM"]), wy - palmar, z_dist))
        for n, st in DISTAL_ROW.items():
            put(n, (x_of(st), wy, z_dist), (x_of(st), wy, z_mc))
        for ray, st in LATERAL_STEPS.items():
            x = x_of(st)
            z = z_mc
            put(f"METACARPAL_{ray}", (x, wy, z), (x, wy, z - UNITS["metacarpal"] * u), MC_PARENT[ray])
            z -= UNITS["metacarpal"] * u
            chain = ["PROXIMAL", "DISTAL"] if ray == 1 else ["PROXIMAL", "INTERMEDIATE", "DISTAL"]
            parent = f"METACARPAL_{ray}"
            for seg in chain:
                put(f"PHALANX_{seg}_{ray}", (x, wy, z), (x, wy, z - UNITS["phalanx"] * u), parent)
                parent = f"PHALANX_{seg}_{ray}"
                z -= UNITS["phalanx"] * u
        info["sides"][side] = {"wrist_anchor_radius_tail_m": [round(wx, 4), round(wy, 4), round(wz, 4)],
                               "unit_m": round(u, 6), "hand_length_m": round(wz - fingertip_z, 4)}
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
    new, info = rebuild(data)
    new_text = json.dumps(new, indent=2, ensure_ascii=False).replace("\n", newline) + text[len(body):]
    before = {b["canonical_name"]: b for b in data["bones"]}
    after = {b["canonical_name"]: b for b in new["bones"]}
    changed = sorted(n for n in after if after[n] != before[n])
    report = {
        "finding": "A10 hand layout (metacarpals/phalanges detached from the wrist)",
        "file": str(a.json.relative_to(ROOT)).replace("\\", "/"),
        "sha256_before": hashlib.sha256(raw).hexdigest(),
        "sha256_after": hashlib.sha256(new_text.encode("utf-8")).hexdigest(),
        "bones": len(after), "changed_bones": len(changed),
        "parameters": info,
        "provenance": {
            "wrist_and_fingertip_heights": "DERIVED from PROVEN DRILLIS_CONTINI_1966 ratios (0.485 H, 0.377 H)",
            "carpal_rows_order_articulations_and_parents": "PROVEN topology (anatomy atlas)",
            "segment_split_2_4_3_ray_spacing_palmar_offset": "PLACEHOLDER — existing data values, "
                                                              "pending HAND_SEGMENT_PROPORTIONS source",
        },
        "samples": {n: {"before": {k: before[n][k] for k in ("parent", "head", "tail")},
                        "after": {k: after[n][k] for k in ("parent", "head", "tail")}}
                    for n in ("CAPITATE_L", "METACARPAL_3_L", "PHALANX_PROXIMAL_3_R", "PHALANX_DISTAL_3_L")},
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
