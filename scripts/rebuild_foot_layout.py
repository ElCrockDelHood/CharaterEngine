"""Rebuild the foot layout of the canonical skeleton (finding A13).

    python scripts/rebuild_foot_layout.py                    # dry run: print the report
    python scripts/rebuild_foot_layout.py --apply --report docs/audit/A13_FOOT_LAYOUT_REPORT.json

Problem: the 26 bones of each foot were a synthetic ramp (tarsals stepping 0.0133 m in -Y and
down in z, every bone vertical, toes at y = 0 under the ankle instead of in front of it) and every
tarsal except the talus, every metatarsal and every proximal toe phalanx was parented to TIBIA.

Provenance of every number (Decision 12 — nothing invented):
* Ankle anchor = TIBIA tail (talocrural joint; existing data at 0.039·H, DRILLIS_CONTINI_1966).
* Foot length heel -> longest toe tip = 0.152·H and foot breadth = 0.055·H (DRILLIS_CONTINI_1966,
  PROVEN ratios in references/anthropometry.json) -> DERIVED lengths at the canonical stature.
* Topology (PROVEN, any anatomy atlas): talus on the tibia; calcaneus and navicular on the talus;
  cuboid on the calcaneus; cuneiforms on the navicular; MT1/MT2/MT3 on the medial / intermediate /
  lateral cuneiform, MT4/MT5 on the cuboid; rays MT -> proximal -> (intermediate) -> distal; the
  hallux has two phalanges and is the medial ray; the foot points forward (-Y), sole on z = 0.
* Split of the foot length (tarsal : metatarsal : phalanx = 3 : 5 : 3) is the ratio of the
  **existing placeholder bone lengths of the data** (0.0055 / 0.0092 / 0.0055 m), only re-arranged
  and scaled to the sourced foot length: PLACEHOLDER.
* Ray spacing = breadth / 5 (equal lanes, ray 3 under the ankle), the position of the ankle over
  the hindfoot (one tarsal unit in front of the heel) and the medial arch (linear from the ankle to
  the metatarsal heads; lateral column on the ground) are geometric conventions: ESTIMATE. A sourced
  set (FOOT_SEGMENT_PROPORTIONS) is pending; see docs/audit/A13_FOOT_LAYOUT.md.
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
FOOT_LENGTH_RATIO = 0.152        # DRILLIS_CONTINI_1966 (anthropometry.json: foot_ratio)
FOOT_BREADTH_RATIO = 0.055       # DRILLIS_CONTINI_1966 (anthropometry.json: foot_breadth_ratio)
UNITS = {"tarsal": 3, "metatarsal": 5, "phalanx": 3}         # existing placeholder proportions
ANKLE_UNITS = UNITS["tarsal"]                                # ankle one tarsal unit in front of the heel
RAY_LANES = 5
MT_PARENT = {1: "CUNEIFORM_MEDIAL", 2: "CUNEIFORM_INTERMEDIATE", 3: "CUNEIFORM_LATERAL", 4: "CUBOID", 5: "CUBOID"}


def _r(v: float) -> float:
    v = round(v, 4)
    return 0.0 if v == 0 else v


def _pt(x, y, z):
    return {"x": _r(x), "y": _r(y), "z": _r(z)}


def rebuild(data: dict) -> tuple[dict, dict]:
    out = json.loads(json.dumps(data))
    B = {b["canonical_name"]: b for b in out["bones"]}
    stature = max(b[e]["z"] for b in out["bones"] for e in ("head", "tail"))
    length, breadth = FOOT_LENGTH_RATIO * stature, FOOT_BREADTH_RATIO * stature
    t, m, p = UNITS["tarsal"], UNITS["metatarsal"], UNITS["phalanx"]
    total_units = 4 * t + m + 3 * p                           # heel -> tip of rays 2-5
    u = length / total_units
    spacing = breadth / RAY_LANES
    s_ankle, s_mt_base, s_mt_head = ANKLE_UNITS * u, 4 * t * u, (4 * t + m) * u
    info = {"stature_m": stature, "foot_length_m": round(length, 4), "foot_breadth_m": round(breadth, 4),
            "unit_m": round(u, 6), "ray_spacing_m": round(spacing, 6),
            "units_tarsal_metatarsal_phalanx": [t, m, p], "sides": {}}

    for side, lateral in (("L", 1.0), ("R", -1.0)):          # left = +X (Decision 33)
        ankle = B[f"TIBIA_{side}"]["tail"]
        ax, ay, az = ankle["x"], ankle["y"], ankle["z"]

        def y_of(s, ay=ay):                                   # s = distance forward of the heel
            return ay + s_ankle - s

        def z_arch(s, az=az):                                 # medial arch: ankle -> metatarsal heads
            return max(0.0, az * (s_mt_head - s) / (s_mt_head - s_ankle))

        def x_ray(r, ax=ax, lateral=lateral):                 # ray 3 under the ankle, hallux medial
            return ax + lateral * (r - 3) * spacing

        def put(name, head, tail, parent, side=side):
            b = B[f"{name}_{side}"]
            b["head"], b["tail"] = _pt(*head), _pt(*tail)
            b["parent"] = f"{parent}_{side}"

        x_cuboid = ax + lateral * 1.5 * spacing
        nav_head = (x_ray(2), y_of(2 * t * u), z_arch(2 * t * u))
        put("TALUS", (ax, ay, az), nav_head, "TIBIA")
        put("CALCANEUS", (ax, y_of(0.0), 0.0), (x_cuboid, y_of(2 * t * u), 0.0), "TALUS")
        put("NAVICULAR", nav_head, (x_ray(2), y_of(3 * t * u), z_arch(3 * t * u)), "TALUS")
        put("CUBOID", (x_cuboid, y_of(2 * t * u), 0.0), (x_cuboid, y_of(s_mt_base), 0.0), "CALCANEUS")
        for r, cun in ((1, "CUNEIFORM_MEDIAL"), (2, "CUNEIFORM_INTERMEDIATE"), (3, "CUNEIFORM_LATERAL")):
            put(cun, (x_ray(r), y_of(3 * t * u), z_arch(3 * t * u)),
                (x_ray(r), y_of(s_mt_base), z_arch(s_mt_base)), "NAVICULAR")
        for ray in range(1, 6):
            x = x_ray(ray)
            z_base = z_arch(s_mt_base) if ray <= 3 else 0.0       # lateral column on the ground
            put(f"METATARSAL_{ray}", (x, y_of(s_mt_base), z_base), (x, y_of(s_mt_head), 0.0), MT_PARENT[ray])
            s = s_mt_head
            chain = ["PROXIMAL", "DISTAL"] if ray == 1 else ["PROXIMAL", "INTERMEDIATE", "DISTAL"]
            parent = f"METATARSAL_{ray}"
            for seg in chain:
                put(f"TOE_PHALANX_{seg}_{ray}", (x, y_of(s), 0.0), (x, y_of(s + p * u), 0.0), parent)
                parent = f"TOE_PHALANX_{seg}_{ray}"
                s += p * u
        info["sides"][side] = {"ankle_anchor_tibia_tail_m": [round(ax, 4), round(ay, 4), round(az, 4)],
                               "heel_y_m": round(y_of(0.0), 4), "toe_tip_y_m": round(y_of(total_units * u), 4)}
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
        "finding": "A13 foot layout (synthetic ramp, tarsals/metatarsals/toes parented to TIBIA)",
        "file": str(a.json.relative_to(ROOT)).replace("\\", "/"),
        "sha256_before": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
        "sha256_after": hashlib.sha256(new_text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
        "sha256_note": "LF-normalised, as pinned by tests/anatomy/test_contract_fingerprint.py",
        "bones": len(after), "changed_bones": len(changed), "changed": changed,
        "parameters": info,
        "provenance": {
            "ankle_anchor": "existing data (TIBIA tail at 0.039 H, DRILLIS_CONTINI_1966)",
            "foot_length_and_breadth": "DERIVED from PROVEN DRILLIS_CONTINI_1966 ratios (0.152 H, 0.055 H)",
            "tarsal_metatarsal_phalangeal_parents_and_ray_order": "PROVEN topology (anatomy atlas)",
            "segment_split_3_5_3": "PLACEHOLDER — existing data bone lengths, pending FOOT_SEGMENT_PROPORTIONS",
            "ray_spacing_ankle_offset_arch_profile": "ESTIMATE — geometric conventions, no source",
        },
        "samples": {n: {"before": {k: before[n][k] for k in ("parent", "head", "tail")},
                        "after": {k: after[n][k] for k in ("parent", "head", "tail")}}
                    for n in ("TALUS_L", "CALCANEUS_L", "METATARSAL_3_R", "TOE_PHALANX_DISTAL_2_L")},
        "applied": bool(a.apply),
    }
    print(json.dumps({k: v for k, v in report.items() if k not in ("samples", "changed")}, indent=2))
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.apply:
        a.json.write_bytes(new_text.encode("utf-8"))
        print(f"rewritten: {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
