"""Bake the Souls-like placeholder clips in Blender (STYLE-SOULS-001 step 4).

    blender -b --python runtime/blender/ce_bake_souls_clips.py -- --out <souls_clips.glb>

Builds the bare 66-bone CE-GAME-v1 armature at the same T-pose points as the Python game GLB, keys every clip of
``domain/animation/souls_clips.py`` (stance + overrides + staff grips) and exports a glTF with one animation per
clip (game-rig bones only). Prints a CE_BAKE line per clip; exits 1 on failure.
"""

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import bpy  # noqa: E402

from character_engine.domain.animation.souls_clips import SOULS_CLIPS  # noqa: E402
from character_engine.export.gltf_game import game_skeleton_points  # noqa: E402
from character_engine.infrastructure.blender.addon import game_rig  # noqa: E402


def parity(ctx, arm):
    """Worst angle between Blender's posed probe-bone directions and the domain FK at every key."""
    import math

    from character_engine.domain.animation.souls_clips import PROBE_BONES, key_rotations
    from character_engine.domain.rigging.hand_poses import apply_hand_pose

    rest = game_rig.rest_points(arm)
    worst, where = 0.0, ""
    for clip in SOULS_CLIPS.values():
        arm.animation_data.action = bpy.data.actions[clip.clip_id]
        for frame, pose in clip.keys:
            ctx.scene.frame_set(frame)
            ctx.view_layer.update()
            want = apply_hand_pose(rest, key_rotations(rest, pose))
            for b in PROBE_BONES:
                pb = arm.pose.bones[b]
                got = (pb.tail - pb.head).normalized()
                w = [want[b][1][i] - want[b][0][i] for i in range(3)]
                n = math.sqrt(sum(c * c for c in w))
                ang = math.degrees(math.acos(max(-1.0, min(1.0, sum(got[i] * w[i] / n for i in range(3))))))
                if ang > worst:
                    worst, where = ang, f"{clip.clip_id}@{frame} {b}"
    arm.animation_data.action = None
    return worst, where


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--spec-sha256", default="")
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ctx = bpy.context
    ctx.scene.render.fps = 60
    arm = game_rig.build_game_armature_from_points(ctx, game_skeleton_points(pose="tpose"))
    made = game_rig.bake_souls_clips(ctx, arm)
    for cid, info in made.items():
        print(f"CE_BAKE clip {cid}: {info['frames']} frames, {info['keys']} keys")
    worst, where = parity(ctx, arm)
    print(f"CE_BAKE parity Blender vs Python FK: worst {worst:.4f} deg ({where})")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    game_rig.export_souls_clips(ctx, arm, a.out, a.spec_sha256)
    ok = a.out.exists() and len(made) == len(SOULS_CLIPS)
    print(f"CE_BAKE {'OK' if ok else 'FAIL'}: {a.out} ({a.out.stat().st_size if a.out.exists() else 0} bytes), "
          f"Blender {bpy.app.version_string}, spec {hashlib.sha256(a.spec_sha256.encode()).hexdigest()[:8]}")
    return 0 if ok else 1


if __name__ == "__main__":
    code = main()
    if code:
        sys.exit(code)
