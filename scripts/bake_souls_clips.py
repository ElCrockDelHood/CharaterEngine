"""Bake the Souls-like placeholder clips with Blender 3.6 (reference) into the Godot data folder.

    python scripts/bake_souls_clips.py                 # -> runtime/godot/addons/character_engine/data/souls_clips.glb
    python scripts/bake_souls_clips.py --blender PATH  # pick the Blender build

Regenerates souls_clips.json first; the GLB carries its SHA-256 (``ce_clips_spec_sha256``) so pytest can tell when
the bake is stale. Live output + logs/<UTC>_bake_souls_clips.log (docs/09_Debug_Consoles.md).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from _logrun import run_logged, utf8_console
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data"


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", default=None)
    a = ap.parse_args(argv)
    exe = find_blender(a.blender)
    if exe is None:
        print("Blender not found (set CE_BLENDER or pass --blender)")
        return 1
    code, _, _ = run_logged([sys.executable, ROOT / "scripts" / "export_souls_clips.py"], "bake_souls_clips_json")
    if code:
        return code
    sha = hashlib.sha256((DATA / "souls_clips.json").read_bytes()).hexdigest()
    code, secs, log = run_logged([exe, "-b", "--factory-startup", "--python-exit-code", "1", "--python",
                                  ROOT / "runtime" / "blender" / "ce_bake_souls_clips.py", "--",
                                  "--out", DATA / "souls_clips.glb", "--spec-sha256", sha],
                                 "bake_souls_clips", env={"CHARACTER_ENGINE_SRC": str(ROOT / "src")}, timeout=600)
    print(f"bake exit {code} ({secs:.0f} s), log {log}")
    return code


if __name__ == "__main__":
    sys.exit(main())
