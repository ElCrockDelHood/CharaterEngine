"""Re-parent CLAVICLE_L/R from ROOT_SKELETON to STERNUM (Decision 70, docs/architecture/CLAVICLE_REPARENT_PROPOSAL.md).

    python scripts/fix_clavicle_parent.py            # dry run
    python scripts/fix_clavicle_parent.py --apply

The clavicle's only bony joint with the axial skeleton is the sternoclavicular joint (PROVEN topology); since A24 the
clavicle head is the SC point. Only the two ``parent`` fields change: positions, node count (208), single root and
acyclicity are kept. Deterministic and idempotent; refuses the frozen ``_backup`` fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"


def fix(data: dict) -> tuple[dict, list]:
    out = json.loads(json.dumps(data))
    changed = []
    for b in out["bones"]:
        if b["canonical_name"] in ("CLAVICLE_L", "CLAVICLE_R") and b["parent"] != "STERNUM":
            b["parent"] = "STERNUM"
            changed.append(b["canonical_name"])
    return out, changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path, default=CANONICAL)
    ap.add_argument("--apply", action="store_true")
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
    new, changed = fix(data)
    new_text = json.dumps(new, indent=2, ensure_ascii=False).replace("\n", newline) + text[len(body):]
    print(json.dumps({"changed_bones": changed,
                      "sha256_lf_before": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
                      "sha256_lf_after": hashlib.sha256(new_text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
                      "applied": bool(a.apply)}, indent=2))
    if a.apply:
        a.json.write_bytes(new_text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
