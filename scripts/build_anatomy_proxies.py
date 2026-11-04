"""Write the PROXY anatomy pieces (A25) into assets/anatomy/proxies/ from the canonical skeleton.

    python scripts/build_anatomy_proxies.py            # write / refresh the files
    python scripts/build_anatomy_proxies.py --check    # exit 1 if the committed files are stale

Pieces with no real mesh in BodyParts3D: latissimus dorsi, rectus abdominis, tibialis anterior, peroneus group
(muscles, ESTIMATE from the MUSCLES catalogue), major knee / ankle / shoulder ligaments (PLACEHOLDER), coccyx and
ear ossicles (PLACEHOLDER). One OBJ + one asset manifest per piece, plus INDEX.json. Deterministic; reads the
canonical data, never writes it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.assets.proxies import build  # noqa: E402

CANONICAL = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
OUT = ROOT / "assets" / "anatomy" / "proxies"


def joints() -> dict:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    return {b["canonical_name"]: (tuple(b["head"].values()), tuple(b["tail"].values())) for b in data["bones"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = build(joints())
    if a.check:
        stale = [n for n, b in files.items() if not (OUT / n).exists() or (OUT / n).read_bytes() != b]
        extra = [p.name for p in OUT.glob("*") if p.name not in files and p.name != "README.md"]
        if stale or extra:
            print(f"STALE: {stale} EXTRA: {extra}; run scripts/build_anatomy_proxies.py")
            return 1
        print(f"OK: {len(files)} proxy files in sync")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (OUT / name).write_bytes(data)
    print(f"wrote {len(files)} files to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
