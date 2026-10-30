"""Build and export the CE-GAME-v1 block body in Blender (Souls arena visuals).

    blender -b --python runtime/blender/ce_bake_game_body.py -- --out <human_game_v1_body.glb> --spec-sha256 <sha>

Bare 66-bone game armature at the Python game GLB's T-pose points + one capsule per game bone
(``domain/rigging/game_body.py``), 100 % weighted to its bone, exported as a skinned glTF. Prints CE_BODY lines.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import bpy  # noqa: E402

from character_engine.domain.rigging.game_body import game_body_placements  # noqa: E402
from character_engine.export.gltf_game import game_skeleton_points  # noqa: E402
from character_engine.infrastructure.blender.addon import game_rig  # noqa: E402


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--spec-sha256", default="")
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ctx = bpy.context
    points = game_skeleton_points(pose="tpose")
    arm = game_rig.build_game_armature_from_points(ctx, points, "CE_GAME_BODY_RIG")
    body = game_rig.build_game_body_mesh(ctx, arm, game_body_placements(points))
    me = body.data
    weights = [len(v.groups) for v in me.vertices]
    print(f"CE_BODY mesh: {len(me.vertices)} vertices, {len(me.polygons)} faces, {len(body.vertex_groups)} groups, "
          f"influences per vertex max {max(weights)} min {min(weights)}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    game_rig.export_game_body(ctx, arm, body, a.out, a.spec_sha256)
    ok = a.out.exists() and max(weights) == 1 and min(weights) == 1
    print(f"CE_BODY {'OK' if ok else 'FAIL'}: {a.out} ({a.out.stat().st_size if a.out.exists() else 0} bytes), "
          f"Blender {bpy.app.version_string}")
    return 0 if ok else 1


if __name__ == "__main__":
    code = main()
    if code:
        sys.exit(code)
