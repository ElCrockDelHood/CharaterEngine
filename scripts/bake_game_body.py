"""Build the CE-GAME-v1 block body with Blender 3.6 (reference) into the Godot data folder.

    python scripts/bake_game_body.py                 # -> runtime/godot/addons/character_engine/data/human_game_v1_body.glb
    python scripts/bake_game_body.py --blender PATH

The GLB carries the SHA-256 of the domain body spec (``ce_body_spec_sha256``) so pytest can tell when it is stale.
Live output + logs/<UTC>_bake_game_body.log (docs/09_Debug_Consoles.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from _logrun import run_logged, utf8_console
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DATA = ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data"


def spec_sha256() -> str:
    from character_engine.domain.rigging.game_body import body_spec
    from character_engine.export.gltf_game import game_skeleton_points

    text = json.dumps(body_spec(game_skeleton_points(pose="tpose")), sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", default=None)
    a = ap.parse_args(argv)
    exe = find_blender(a.blender)
    if exe is None:
        print("Blender not found (set CE_BLENDER or pass --blender)")
        return 1
    code, secs, log = run_logged([exe, "-b", "--factory-startup", "--python-exit-code", "1", "--python",
                                  ROOT / "runtime" / "blender" / "ce_bake_game_body.py", "--",
                                  "--out", DATA / "human_game_v1_body.glb", "--spec-sha256", spec_sha256()],
                                 "bake_game_body", env={"CHARACTER_ENGINE_SRC": str(ROOT / "src")}, timeout=600)
    print(f"bake exit {code} ({secs:.0f} s), log {log}")
    return code


if __name__ == "__main__":
    sys.exit(main())
