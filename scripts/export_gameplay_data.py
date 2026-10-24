"""Write the engine-neutral gameplay table for the Godot runtime.

    python scripts/export_gameplay_data.py            # -> runtime/godot/addons/character_engine/data/gameplay_shenmue.json
    python scripts/export_gameplay_data.py --check    # exit 1 if the committed JSON is stale

Godot never imports the Python domain; it consumes this JSON (moves, frame data,
pre-computed blunt-impact assessments per hitbox bone and reference fight scenarios).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.gameplay import gameplay_runtime_table  # noqa: E402

DEFAULT_OUT = ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data" / "gameplay_shenmue.json"


def render() -> str:
    return json.dumps(gameplay_runtime_table(), indent=2, sort_keys=True) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true", help="verify the file is up to date instead of writing")
    a = ap.parse_args(argv)
    text = render()
    if a.check:
        if not a.output.exists() or a.output.read_text(encoding="utf-8") != text:
            print(f"STALE: {a.output} does not match the domain; run scripts/export_gameplay_data.py")
            return 1
        print(f"OK: {a.output} is in sync")
        return 0
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {a.output} ({a.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
