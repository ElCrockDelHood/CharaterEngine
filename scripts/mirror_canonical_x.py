"""Mirror the canonical skeleton across X = 0 (Decision 17 / D-13): x -> -x for every bone head/tail.

    python scripts/mirror_canonical_x.py --check                 # dry run: report only
    python scripts/mirror_canonical_x.py --apply                 # rewrite human_adult_206.json
    python scripts/mirror_canonical_x.py --apply --report docs/audit/A09_D17_MIRROR_X_REPORT.json

Deterministic and reversible: applying it twice restores the original bytes. Names, parents,
y/z values, containers and formatting (indent, line endings) are unchanged; 0.0 never becomes -0.0.
``human_adult_206_backup.json`` is a frozen audit fixture and is never touched by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
SAMPLES = ("HUMERUS_L", "HUMERUS_R", "FEMUR_L", "NASAL_R", "STERNUM")


def _neg(x: float) -> float:
    return -x if x != 0 else 0.0


def mirror(data: dict) -> dict:
    out = json.loads(json.dumps(data))
    for b in out["bones"]:
        for end in ("head", "tail"):
            b[end]["x"] = _neg(b[end]["x"])
    return out


def dumps(data: dict, newline: str) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False).replace("\n", newline)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path, default=CANONICAL)
    ap.add_argument("--apply", action="store_true", help="rewrite the file (default: dry run)")
    ap.add_argument("--check", action="store_true", help="dry run (default)")
    ap.add_argument("--report", type=Path, default=None)
    a = ap.parse_args(argv)
    if a.json.name.endswith("_backup.json"):
        print("refusing to touch the frozen backup fixture")
        return 2

    raw = a.json.read_bytes()
    text = raw.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    data = json.loads(text)
    if dumps(data, newline) != text.rstrip("\r\n") and dumps(data, newline) + newline != text:
        print("formatting is not reproducible (indent/encoding differ); aborting")
        return 3
    trailing = text[len(dumps(data, newline)):]
    new_text = dumps(mirror(data), newline) + trailing
    back_text = dumps(mirror(json.loads(new_text)), newline) + trailing
    assert back_text == text, "mirror is not an involution on this file"

    before = {b["canonical_name"]: b for b in data["bones"]}
    after = {b["canonical_name"]: b for b in json.loads(new_text)["bones"]}
    left = [n for n in after if n.endswith("_L")]
    right = [n for n in after if n.endswith("_R")]
    report = {
        "decision": "Decision 17 / D-13 (option A: mirror X, keep -Y forward)",
        "file": str(a.json.relative_to(ROOT)).replace("\\", "/"),
        "bones": len(after),
        "containers": len(data.get("containers", [])),
        "sha256_before": hashlib.sha256(raw).hexdigest(),
        "sha256_after": hashlib.sha256(new_text.encode("utf-8")).hexdigest(),
        "involution_restores_original_bytes": True,
        "left_bones_x_positive": all(after[n][e]["x"] > 0 for n in left for e in ("head", "tail")),
        "right_bones_x_negative": all(after[n][e]["x"] < 0 for n in right for e in ("head", "tail")),
        "unchanged": "names, parents, y, z, containers, formatting",
        "samples": {n: {"before": {"head": before[n]["head"], "tail": before[n]["tail"]},
                        "after": {"head": after[n]["head"], "tail": after[n]["tail"]}} for n in SAMPLES},
        "applied": bool(a.apply),
    }
    print(json.dumps({k: v for k, v in report.items() if k != "samples"}, indent=2))
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"report: {a.report}")
    if a.apply:
        a.json.write_bytes(new_text.encode("utf-8"))
        print(f"rewritten: {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
