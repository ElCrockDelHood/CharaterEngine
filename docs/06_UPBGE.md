# 06 — UPBGE / Blender Runtime

UPBGE (the Blender game-engine fork) shares Blender's Python API (`bpy`), so the same two
validation paths work in UPBGE and vanilla Blender:

- **Path A — GLB import** (`runtime/upbge/ce_import_and_validate.py`): imports the neutral
  glTF artifact and checks the engine-agnostic contract. This is the path that proves the
  "no DCC dependency" claim.
- **Path B — Rebuild from JSON** (`scripts/validate_blender_headless.py`): uses the Blender
  adapter in `src/character_engine/infrastructure/blender/` (State Auditor R1.3) to build the
  armature directly from `human_adult_206.json`.

## Recommended installation (Lenovo T470s · i7-7600U · Intel HD Graphics 620 · 16 GB)

| Item | Recommendation | Why |
|------|----------------|-----|
| Primary | **UPBGE 0.50** (based on Blender 5.0.1, released 2026-01) | Current stable; GPU skinning, Vulkan optional |
| Fallback | **UPBGE 0.44** (based on Blender 4.4) | If the 5.x viewport misbehaves on your driver |
| Historical | UPBGE 0.36 (Blender 3.6) | The version the repo's Blender adapter was originally validated against (see `MASTER_REORIENTATION_AUDIT.md`); keep only for comparison |
| Avoid | Weekly builds (0.53 alpha) | Unstable; not needed for validation |
| Driver | Latest Intel Graphics driver from intel.com | Blender 5.0 requires OpenGL 4.3 + `GL_ARB_shader_draw_parameters`/`GL_ARB_clip_control`; HD 620 (Kaby Lake) is the **minimum supported** Intel GPU, so an up-to-date driver matters |
| Backend | Leave OpenGL (default); do not force Vulkan | Vulkan 1.3 works on HD 620 but is newer in Blender; OpenGL is the safer path for headless runs |

Download: <https://upbge.org/#/download> or the GitHub release
`upbge-0.50-windows-x64.7z` (needs 7-Zip or `py7zr` to extract).

**Installed on this machine (2026-09-29):** `C:\Tools\UPBGE\upbge-0.50-windows-x64\blender.exe`
(Blender 5.0.1 base, `blenderplayer.exe` alongside).

Last validation runs (canonical skeleton at 1.80 m):

```
Path A  bone_count: 208 · roots: 1 · height_m: 1.761 · ground_z: 0.0055 · tails_fixed: 206 · RESULT: PASS
Path B  Huesos 208/208 · State Auditor Global PASS · Diff PASS · VALIDATION_STATUS=PASS
```

Known harmless noise in UPBGE 0.50 background mode: the bundled `bge_netlogic` add-on prints
`register_class(...): already registered as a subclass 'LogicNodeTree'` on start-up. It does not
affect `bpy` scripts or the exit code.

Hardware notes: the T470s has 16 GB RAM and shared video memory, which is plenty for an
armature-only scene. EEVEE-Next in 5.x is heavier than the 3.6 EEVEE; for editing use the
*Solid* viewport shading, and run validations headless (`-b`) so the GPU is not involved.

## Workflow

```bash
UPBGE="/c/Tools/UPBGE/upbge-0.50-windows-x64/blender.exe"   # or vanilla blender.exe ≥ 3.6

# Path A — GLB contract
python scripts/export_gltf.py
"$UPBGE" -b --python runtime/upbge/ce_import_and_validate.py -- \
    --glb builds/gltf/human_adult_206.glb \
    --save builds/tests/upbge_validation.blend     # optional, git-ignored

# Path B — adapter / State Auditor
"$UPBGE" -b --python scripts/validate_blender_headless.py
# Windows helper: edit $blenderPath in validar_blender_headless.ps1 and run it
```

Both paths exit `0` on success and `1` on failure. Everything after `--` goes to the script.

## What Path A checks

| Report key | Expected |
|------------|----------|
| `bone_count` | 208 (206 anatomical + `ROOT_SKELETON` + `CRANIUM`) — error otherwise |
| required bones | `ROOT_SKELETON`, `CRANIUM`, `SACRUM`, `CERVICAL_1`, `FEMUR_L`, `FEMUR_R`, `FRONTAL` — error if missing |
| `roots` | ≥ 1 — error if 0 |
| `tails_fixed` | number of tails rebuilt from glTF `extras.ce_tail` (skip with `--no-fix-tails`) |
| `ground_z` | within ±0.05 m of 0 — warning otherwise |
| `height_m` | ≥ 1.0 m along +Z — error otherwise (Blender's glTF importer converts Y-up back to Z-up) |

Scale note: since A07 the canonical skeleton is 1.80 m (`docs/audit/A07_STATURE_RETARGET_180.md`).
The validator checks orientation (`height_m ≥ 1.0`), not an exact stature.

## Gameplay runtime (UPBGE game engine)

`runtime/upbge/components/ce_combat.py` is the UPBGE **runtime** side: it embeds the Python
combat domain (`character_engine.domain.gameplay.ShenmueCombat`) as a `KX_PythonComponent`
(`ce_combat.CEFighter`) with a logic-brick fallback (`ce_combat.run`). Component / game
properties: `fighter_id`, `is_player`, `style`, `stature_m`, `weapon`, `move_speed`, `ai_aggression`,
`autoplay_frames`, `report_path`. Keys: W/S move, J punch, K kick, L throw, Space guard.

`weapon` names an entry of `character_engine.domain.gameplay.WEAPONS` (`unarmed` default, `staff`,
`short_blade`; Decision 50); the domain applies reach, energy and wound type. `ce_combat.attach_weapon_placeholder(
armature, weapon_id)` (authoring time, `bpy`) creates a PLACEHOLDER box bone-parented to the grip bone
(`METACARPAL_3_R`), which the game engine keeps following. Suite checks: weapon replays match the committed
Godot table; the placeholder stays rigid on the grip bone when HUMERUS_R is posed.

Set up an arena from the addon panel (*Runtime → Set up UPBGE scene*, `docs/08_Blender_Addon.md`)
or run the suite: `python scripts/engine_tests.py upbge` — UI mode (UPBGE 0.50 crashes when
registering components with `-b`), 23 checks including a `blenderplayer.exe` autoplay smoke
(180 frames, hits > 0, report `builds/tests/upbge_game_autoplay.json`).

## Mapping canonical → Blender/UPBGE

| Canonical (domain/JSON) | Blender |
|-------------------------|---------|
| Z-up, -Y forward, metres | identical frame — no conversion |
| Bone head / tail | `EditBone.head` / `EditBone.tail` |
| `canonical_name` | bone name |
| Containers (`ROOT_SKELETON`, `CRANIUM`) | regular bones flagged `ce_is_container` in custom properties |

## Compatibility with Blender 5.x API

`bpy` changes that affect this repo between 3.6 and 5.0 are small (glTF importer options,
`bpy.context.temp_override`). If Path B fails on 5.x but Path A passes, the problem is in
`infrastructure/blender/`, not in the canonical data — fix the adapter and add the case to
`docs/reorientation/DECISION_LOG.md`.

## Troubleshooting

- `This script must be executed inside UPBGE/Blender` → you ran it with plain Python.
- `ModuleNotFoundError: character_engine` (Path B) → run from the repo root.
- Bones with zero length → tails not rebuilt; drop `--no-fix-tails`.
- Crash at startup on the viewport → update the Intel driver, or use the 0.44 fallback.
