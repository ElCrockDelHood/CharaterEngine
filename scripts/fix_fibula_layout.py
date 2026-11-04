"""Put the fibula lateral to the tibia (finding A21, same method as A11).

    python scripts/fix_fibula_layout.py                     # dry run
    python scripts/fix_fibula_layout.py --apply --report docs/audit/A21_FIBULA_LAYOUT_REPORT.json

In the anatomical position the fibula is the **lateral** leg bone. The canonical data placed it on the tibia's
own knee → ankle segment, 0.0333 m **in front** of it (y −0.0333) at the same x. This script keeps the fibula's
z values (head 0.487 / tail 0.0702) and length, keeps the tibia untouched, and only moves the pre-existing
tibia → fibula offset (PLACEHOLDER, no source) from the −Y axis to the X axis with the lateral sign of each side
(left = +X, Decision 33). No posterior component is added: that needs a source (pending
``FIBULA_INTEROSSEOUS_OFFSET``). Nothing hangs from FIBULA_L/R, so no other bone moves.
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


def _r(v: float) -> float:
    v = round(v, 4)
    return 0.0 if v == 0 else v


def fix(data: dict) -> tuple[dict, dict]:
    out = json.loads(json.dumps(data))
    B = {b["canonical_name"]: b for b in out["bones"]}
    info = {}
    for side, lateral in (("L", 1.0), ("R", -1.0)):
        tib, fib = B[f"TIBIA_{side}"], B[f"FIBULA_{side}"]
        for end in ("head", "tail"):
            t, f = tib[end], fib[end]
            dx, dy = f["x"] - t["x"], f["y"] - t["y"]
            offset = (dx * dx + dy * dy) ** 0.5
            f["x"], f["y"] = _r(t["x"] + lateral * offset), _r(t["y"])
            info[f"{side}_{end}"] = {"tibia_xy_m": [t["x"], t["y"]], "offset_m": _r(offset)}
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
    names = ("TIBIA_L", "FIBULA_L", "TIBIA_R", "FIBULA_R")
    report = {
        "finding": "A21 fibula layout (fibula in front of the tibia instead of lateral to it)",
        "file": str(a.json.resolve().relative_to(ROOT)).replace("\\", "/"),
        "sha256_before": hashlib.sha256(raw).hexdigest(),
        "sha256_after": hashlib.sha256(new_text.encode("utf-8")).hexdigest(),
        "sha256_lf_before": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
        "sha256_lf_after": hashlib.sha256(new_text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
        "changed_bones": sorted(n for n in after if after[n] != before[n]),
        "parameters": info,
        "provenance": {
            "z_and_length": "unchanged existing data (head 0.487 / tail 0.0702, same as the tibia)",
            "tibia": "unchanged",
            "offset": "PLACEHOLDER — pre-existing 0.0333 m, moved from −Y to lateral X; pending FIBULA_INTEROSSEOUS_OFFSET",
            "posterior_component": "not added (no source); pending FIBULA_INTEROSSEOUS_OFFSET",
            "fibula_lateral_to_tibia": "PROVEN topology (anatomical position)",
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
