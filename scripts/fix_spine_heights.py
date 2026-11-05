"""Vertebral heights from BodyParts3D (Decision 72, variant B of docs/architecture/CERVICAL_SPACING_PROPOSAL.md).

    python scripts/fix_spine_heights.py                     # dry run
    python scripts/fix_spine_heights.py --apply --report docs/audit/A27_SPINE_HEIGHTS_REPORT.json

C1 … L5 and the sacrum take the z of their BodyParts3D namesake (mid-height of the vertebral body, mapped to the
canonical stature by the skin bottom…top → 0…1.80 m rule, ×1.0468; one subject, ESTIMATE). Below T1 a shift fades in
linearly up to +23.3 mm at the sacrum, so the BP3D hip height (0.9307 m) meets the canonical hip (0.954 m, Drillis &
Contini). Stub ends are the midpoints between neighbouring body mid-heights. The coccyx is absent from BodyParts3D: it
keeps its length and hangs from the new sacrum tail (DERIVED). x and y (the Decision 71 curve) are unchanged; stature,
hips, shoulders, ribs, sternum and skull are not moved. Deterministic and idempotent; refuses the ``_backup`` fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

# (top, bottom) of the vertebral body, m, stature map; BodyParts3D, ESTIMATE
BODIES = {
    "CERVICAL_1": (1.6325, 1.613), "CERVICAL_2": (1.6293, 1.5941), "CERVICAL_3": (1.5952, 1.5788),
    "CERVICAL_4": (1.5786, 1.5629), "CERVICAL_5": (1.5656, 1.5447), "CERVICAL_6": (1.5481, 1.5286),
    "CERVICAL_7": (1.5378, 1.5119), "THORACIC_1": (1.5231, 1.492), "THORACIC_2": (1.5058, 1.4705),
    "THORACIC_3": (1.4864, 1.4483), "THORACIC_4": (1.465, 1.4253), "THORACIC_5": (1.4398, 1.4012),
    "THORACIC_6": (1.4102, 1.3755), "THORACIC_7": (1.3813, 1.3463), "THORACIC_8": (1.3464, 1.3136),
    "THORACIC_9": (1.319, 1.2808), "THORACIC_10": (1.2917, 1.2494), "THORACIC_11": (1.2639, 1.2214),
    "THORACIC_12": (1.2349, 1.185), "LUMBAR_1": (1.2039, 1.1526), "LUMBAR_2": (1.1702, 1.1232),
    "LUMBAR_3": (1.1382, 1.1002), "LUMBAR_4": (1.1107, 1.0644), "LUMBAR_5": (1.0808, 1.0287),
    "SACRUM": (1.0524, 0.9863),
}
HIP_SHIFT_M = 0.954 - 0.9307          # canonical hip height − BP3D hip height on the stature map
COCCYX_LENGTH_M = 0.0324              # existing canonical length, kept


def _r(v: float) -> float:
    return round(v, 4)


def heights() -> dict:
    names = list(BODIES)
    t1, sacrum = names.index("THORACIC_1"), names.index("SACRUM")
    z = {n: (BODIES[n][0] + BODIES[n][1]) / 2 + HIP_SHIFT_M * max(0, i - t1) / (sacrum - t1) for i, n in enumerate(names)}
    out = {}
    for i, n in enumerate(names):
        up = z[names[i - 1]] if i else z[n] + (z[n] - z[names[1]])
        down = z[names[i + 1]] if i + 1 < len(names) else z[n] - (BODIES[n][0] - BODIES[n][1])
        out[n] = (_r((z[n] + up) / 2), _r((z[n] + down) / 2))
    return out


def fix(data: dict) -> tuple[dict, dict]:
    out = json.loads(json.dumps(data))
    B = {b["canonical_name"]: b for b in out["bones"]}
    h = heights()
    for n, (top, bottom) in h.items():
        B[n]["head"]["z"], B[n]["tail"]["z"] = top, bottom
    co = B["COCCYX"]
    co["head"]["z"] = h["SACRUM"][1]
    co["tail"]["z"] = _r(h["SACRUM"][1] - COCCYX_LENGTH_M)
    return out, {**{n: {"head_z": a, "tail_z": b} for n, (a, b) in h.items()},
                 "COCCYX": {"head_z": co["head"]["z"], "tail_z": co["tail"]["z"]}}


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
        "finding": "A27 vertebral heights: neck too short, trunk compressed (T4-L5 up to 164 mm too high)",
        "variant": "B: C1-L5, sacrum and coccyx; stature, hips, shoulders kept",
        "sha256_lf_before": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
        "sha256_lf_after": hashlib.sha256(new_text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
        "changed_bones": sorted(n for n in after if after[n] != before[n]),
        "parameters": info,
        "provenance": {
            "z": "ESTIMATE — BodyParts3D body mid-heights (one subject, internal use), stature map, hip shift fade",
            "coccyx": "DERIVED — hangs from the new sacrum tail, canonical length kept",
            "contrast": "Busscher et al. 2010, Eur Spine J 19:1104, PMC2900026 (CC BY-NC): total C3-L5 569.4 +/- 17.7 mm",
        },
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
