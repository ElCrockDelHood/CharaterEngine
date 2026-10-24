"""Retarget the canonical skeleton to a reference stature using published proportions.

Thin CLI over ``character_engine.domain.anatomy.proportions.stature_retarget``
(method, ratios and provenance are documented there and in
``docs/audit/A07_STATURE_RETARGET_180.md``).

Usage::

    python scripts/retarget_stature.py --stature 1.80 \
        --input  src/character_engine/data/anatomy/human_adult_206.json \
        --output src/character_engine/data/anatomy/human_adult_206.json \
        --report docs/audit/A07_STATURE_RETARGET_REPORT.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from character_engine.domain.anatomy.proportions.stature_retarget import retarget_stature  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stature", type=float, default=1.80)
    ap.add_argument("--input", type=Path, default=Path("src/character_engine/data/anatomy/human_adult_206.json"))
    ap.add_argument("--output", type=Path, default=None, help="defaults to --input (in place)")
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    data = json.loads(a.input.read_text(encoding="utf-8"))
    bones, report = retarget_stature(data["bones"], a.stature)
    for k, v in report["landmarks"].items():
        print(f"{k:18s} {v['before_m']:7.3f} -> {v['after_m']:7.3f}  (target {v['target_m']:.3f})")
    if a.dry_run:
        return 0
    data["bones"] = bones
    out = a.output or a.input
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    if a.report:
        a.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"report {a.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
