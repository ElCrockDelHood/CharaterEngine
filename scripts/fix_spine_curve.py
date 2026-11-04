"""Give the canonical spine its sagittal curves (Decision 71, variant A of docs/architecture/SPINE_THORAX_PROPOSAL.md).

    python scripts/fix_spine_curve.py                     # dry run
    python scripts/fix_spine_curve.py --apply --report docs/audit/A26_SPINE_CURVE_REPORT.json

CERVICAL_1 … LUMBAR_5 keep their x and z (Drillis & Contini heights) and get an antero-posterior (y) offset that
follows the BodyParts3D spine **vertebra by vertebra** (identity, not height: the canonical cervical spine is only
30 mm tall against ~95 mm in BodyParts3D, so a height mapping would shift the curves). The table holds the offset of
each BodyParts3D vertebral body centroid (anterior 40 % of the vertebra) from the straight C1 → sacrum line, scaled
×1.0269 to the canonical frame. A vertebra's head takes the mean of its own and the vertebra above, its tail the mean
of its own and the vertebra below (C1 above = 0, sacrum below = 0), so each stub follows the local tangent. Shape descriptor of one subject: cervical lordosis 24.5°,
thoracic kyphosis 42.2°, lumbar lordosis 24.3° (angles between centroid tangents, **not** Cobb angles) — ESTIMATE.
Pró, *Anatomía Clínica*, ch. 2 (book pp. 86–88) is cited only for the qualitative pattern of the curves. SACRUM,
COCCYX, ribs, sternum and skull are not moved. Deterministic and idempotent; refuses the frozen ``_backup`` fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

# AP offset (m, +y = posterior) of each vertebral body from the C1 -> sacrum line; BodyParts3D x 1.0269, ESTIMATE
OFFSETS = {
    "CERVICAL_1": 0.0, "CERVICAL_2": 0.0005, "CERVICAL_3": -0.0004, "CERVICAL_4": -0.0047, "CERVICAL_5": -0.0074,
    "CERVICAL_6": -0.0088, "CERVICAL_7": -0.0032, "THORACIC_1": 0.0016, "THORACIC_2": 0.0069, "THORACIC_3": 0.0167,
    "THORACIC_4": 0.0235, "THORACIC_5": 0.0281, "THORACIC_6": 0.0306, "THORACIC_7": 0.0298, "THORACIC_8": 0.0214,
    "THORACIC_9": 0.0169, "THORACIC_10": 0.0107, "THORACIC_11": 0.0009, "THORACIC_12": -0.0114, "LUMBAR_1": -0.022,
    "LUMBAR_2": -0.0275, "LUMBAR_3": -0.0278, "LUMBAR_4": -0.0258, "LUMBAR_5": -0.0178,
}
VERTEBRAE = tuple([f"CERVICAL_{i}" for i in range(1, 8)] + [f"THORACIC_{i}" for i in range(1, 13)]
                  + [f"LUMBAR_{i}" for i in range(1, 6)])


def _r(v: float) -> float:
    v = round(v, 4)
    return 0.0 if v == 0 else v


def fix(data: dict) -> tuple[dict, dict]:
    out = json.loads(json.dumps(data))
    B = {b["canonical_name"]: b for b in out["bones"]}
    seq = [0.0] + [OFFSETS[n] for n in VERTEBRAE] + [0.0]      # C1 above = 0, sacrum below = 0
    info = {}
    for i, n in enumerate(VERTEBRAE, start=1):
        B[n]["head"]["y"] = _r((seq[i - 1] + seq[i]) / 2)
        B[n]["tail"]["y"] = _r((seq[i] + seq[i + 1]) / 2)
        info[n] = {"body_offset_m": OFFSETS[n], "head_y": B[n]["head"]["y"], "tail_y": B[n]["tail"]["y"]}
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
        "finding": "A26 spine without sagittal curves (straight vertical stubs)",
        "variant": "A: z kept, AP offsets from BodyParts3D (ESTIMATE)",
        "sha256_lf_before": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
        "sha256_lf_after": hashlib.sha256(new_text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
        "changed_bones": sorted(n for n in after if after[n] != before[n]),
        "offsets_m": OFFSETS, "parameters": info,
        "provenance": {"offsets": "ESTIMATE — BodyParts3D body centroids, one subject, ×1.0269; tangent angles are not Cobb",
                       "pattern": "Pró, Anatomía Clínica, ch. 2 pp. 86-88: cervical / lumbar lordosis, thoracic / sacral kyphosis",
                       "unchanged": "x and z of every vertebra; SACRUM, COCCYX, ribs, sternum, skull"},
        "applied": bool(a.apply),
    }
    print(json.dumps({k: v for k, v in report.items() if k not in ("parameters", "offsets_m")}, indent=2))
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.apply:
        a.json.write_bytes(new_text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
