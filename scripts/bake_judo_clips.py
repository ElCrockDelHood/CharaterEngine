"""Bake the judo throws (A36) in Blender 3.6: two fighters, every frame, a rendered strip per throw.

    python scripts/bake_judo_clips.py                  # -> builds/judo/judo_throws.blend, builds/judo/<throw>_blender.png
    python scripts/bake_judo_clips.py --no-render      # keys and parity check only
    python scripts/bake_judo_clips.py --only seoi_nage --blender PATH

Solves every frame in Python first (``judo_clips.frame_table``; about half a minute per throw) and writes
``builds/judo/judo_frames.json`` (schema ``ce-judo-frames/1``), then runs ``runtime/blender/ce_bake_judo_clips.py``.
Live output + logs/<UTC>_bake_judo_clips.log (docs/09_Debug_Consoles.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _logrun import run_logged, utf8_console
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.animation.judo_clips import (  # noqa: E402
    FPS,
    JUDO_CLIPS,
    PROVENANCE,
    frame_table,
)
from character_engine.domain.rigging.hand_poses import apply_hand_pose, quat_rotate  # noqa: E402
from character_engine.export.gltf_game import game_skeleton_points  # noqa: E402

PROBES = ("pelvis", "head", "hand_l", "hand_r", "foot_l", "foot_r")


def frames_json(only: str = "") -> dict:
    points = game_skeleton_points(pose="anatomical")
    clips = {}
    for throw_id, clip in JUDO_CLIPS.items():
        if only and throw_id != only:
            continue
        rows = []
        for r in frame_table(points, clip):
            row = {"frame": r["frame"], "phase": r["phase"]}
            for who in ("tori", "uke"):
                d = r[who]
                body = apply_hand_pose(points, d["bones_wxyz"])
                probes = {b: [round(quat_rotate(d["rotation_wxyz"], body[b][1])[i] + d["location"][i], 6) for i in range(3)]
                          for b in PROBES}
                row[who] = {"location": [round(c, 6) for c in d["location"]],
                            "rotation_wxyz": [round(c, 7) for c in d["rotation_wxyz"]],
                            "bones_wxyz": {b: [round(c, 7) for c in q] for b, q in sorted(d["bones_wxyz"].items())},
                            "probes": probes}
            rows.append(row)
        clips[throw_id] = {"frames": rows, "key_frames": [k.frame for k in clip.keys]}
        print(f"solved {throw_id}: {len(rows)} frames", flush=True)
    return {"schema": "ce-judo-frames/1", "fps": FPS, "provenance": PROVENANCE.value, "rest_pose": "anatomical",
            "clips": clips}


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", default=None)
    ap.add_argument("--out", type=Path, default=ROOT / "builds" / "judo")
    ap.add_argument("--only", default="")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args(argv)
    exe = find_blender(a.blender)
    if exe is None:
        print("Blender not found (set CE_BLENDER or pass --blender)")
        return 1
    a.out.mkdir(parents=True, exist_ok=True)
    frames = a.out / "judo_frames.json"
    frames.write_text(json.dumps(frames_json(a.only), sort_keys=True) + "\n", encoding="utf-8")
    cmd = [exe, "-b", "--factory-startup", "--python-exit-code", "1", "--python",
           ROOT / "runtime" / "blender" / "ce_bake_judo_clips.py", "--", "--frames", frames, "--out", a.out]
    if a.no_render:
        cmd.append("--no-render")
    code, secs, log = run_logged(cmd, "bake_judo_clips", env={"CHARACTER_ENGINE_SRC": str(ROOT / "src")}, timeout=1800)
    print(f"bake exit {code} ({secs:.0f} s), log {log}")
    return code


if __name__ == "__main__":
    sys.exit(main())
