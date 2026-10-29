"""Write the Souls-like clip reference table for Blender (bake) and Godot (playback parity).

    python scripts/export_souls_clips.py            # -> runtime/godot/addons/character_engine/data/souls_clips.json
    python scripts/export_souls_clips.py --check    # exit 1 if the committed JSON is stale

The table is computed on the same T-pose game-rig points as ``human_game_v1_tpose.glb`` (STYLE-SOULS-001 step 4).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.animation.souls_clips import clip_reference  # noqa: E402
from character_engine.export.gltf_game import game_skeleton_points  # noqa: E402

DEFAULT_OUT = ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data" / "souls_clips.json"


def render() -> str:
    return json.dumps(clip_reference(game_skeleton_points(pose="tpose")), indent=2, sort_keys=True) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true", help="verify the file is up to date instead of writing")
    a = ap.parse_args(argv)
    text = render()
    if a.check:
        if not a.output.exists() or a.output.read_text(encoding="utf-8") != text:
            print(f"STALE: {a.output} does not match the domain; run scripts/export_souls_clips.py")
            return 1
        print(f"OK: {a.output} is in sync")
        return 0
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {a.output} ({a.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
