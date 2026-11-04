# Proposal A26a — re-parent CLAVICLE_L/R from ROOT_SKELETON to STERNUM (NOT applied)

**Status:** PROPOSAL, measured on a throw-away working copy (reverted) · **Date:** 2026-11-04 · needs the owner's OK
and a numbered Decision · Related: A24 / Decision 68 (clavicle now runs SC → AC).

## Finding

`CLAVICLE_L/R` hang from `ROOT_SKELETON`. Anatomically the clavicle's only bony joint with the axial skeleton is the
sternoclavicular joint (SC), with the manubrium. Since A24 the clavicle head *is* the SC point (22 mm beside the
sternum top). The natural parent is `STERNUM`. The change keeps 208 nodes, a single root and an acyclic graph
(contract invariant 4); only two `parent` fields change. No position changes.

## Trial (working copy, then `git checkout`; nothing committed)

| Check | Result with the re-parent |
|-------|---------------------------|
| pytest | 1233 passed, **3 failed**, all expected: the `human_adult_206.json` fingerprint, and the two `test_shoulder_girdle.py::test_girdle_layout` cases that assert today's parent `ROOT_SKELETON` |
| Gameplay table (`export_gameplay_data.py --check`) | in sync |
| Souls clips (`export_souls_clips.py --check`) | in sync (CE-GAME-v1 derives `clavicle_*` from joint positions, already parented to `spine_03`) |
| Blender addon | 40/40; IK rest deviation 13.6 mm (unchanged); game rig rest errors unchanged |
| Godot | 60/60; every replay identical; only the "CEBreathing" detail differs, and it varies between runs anyway |
| Block dummy, sockets | unchanged (they read positions, not parents) |
| `skeleton_serialized.json` | would change (2 parent fields) |

## Behaviour to expect

- In the Blender canonical rig, the clavicles (and with them the scapulae and arms) would follow the sternum. The
  breathing controller (`CTRL-breath`) and any spine posing would then move the shoulders slightly, which is
  anatomically correct. Today they ignore spine motion because they hang from the root. This is a production-rig
  change. CE-GAME-v1 and Godot gameplay do not change.
- Mocap maps (`bone_map.py`: `LeftShoulder` → `CLAVICLE_L`) only use names: no change.

## If applied (one commit)

`scripts/fix_clavicle_parent.py` (deterministic, idempotent, refuses the backup) · fingerprint of
`human_adult_206.json` · Decision 70 · `test_shoulder_girdle.py` expects `STERNUM` · regenerate
`skeleton_serialized.json` · re-run pytest, lint, Blender, Godot, the gameplay check and the replays.

**Recommendation: apply.** It is anatomically right, no gameplay or replay changes, and the only behaviour change
is the production rig's shoulders following the thorax, which is wanted for animation quality.
