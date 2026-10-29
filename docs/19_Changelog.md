# 19 — Changelog

All notable changes to Character Engine. Dates are ISO 8601.

## [Unreleased] — 2026-10-29 · Retarget: IK foot locking (opt-in)

### Added
- `domain/animation/foot_lock.py` (pure): contact plan on heel / ball pivots (mean correction of the pivots on
  the ground, anchor = their mean XY per contact phase, 2-frame blend, loop clips merge the phase cut by the
  wrap using the cycle's root displacement, phases needing > 10 cm correction are left alone) and two-bone IK
  (knee kept in its bending plane). Thresholds ESTIMATE.
- Addon `foot_lock.py`: keys FEMUR / TIBIA / TALUS over the retarget keys (foot keeps its world orientation).
  World space only, so it runs on the root-motion variant. `scripts/retarget_batch.py --foot-lock`. Not a default.

### Findings (86 clips, foot lock vs. the default batch; ESTIMATE)
- QA 28 / 14 / 44 → 42 / 14 / 30 (ok / warn / fail); foot_sliding fails 35 → 13; 51 clips slide less, none more;
  no new penetration. Walk 0.31 → 0.09, Walk_Formal 0.27 → 0.09, Walk_Carry 0.20 → 0.05, Jog 0.88 → 0.00,
  Sprint 0.93 → 0.00, Zombie_Walk 0.72 → 0.03 m/s (source 0.11 / 0.11 / 0.10 / 0.59 / 1.74 / 2.40).
- Not locked by the 10 cm guard: Slide_*, Swim_Fwd_Loop, Push_Loop (feet move on purpose / no ground).
- Cost: knee accelerations rise on some clips (worst Walk_Formal 57 → 118 m/s², below Jog's 200 unlocked);
  near-straight standing legs hit the IK reach limit a few frames (e.g. Idle_No_Loop 1 → 15 m/s²).
  Not checked visually yet.
- QA contact and lock use the same height rule (3 cm), so the sliding gain is partly by construction.

### Tests
- `tests/unit/test_foot_lock.py` (10); Blender addon headless suite 37/37 (3.6.23).

## [Unreleased] — 2026-10-29 · Math follow-ups F-3 / F-4 (CE-Q4 review)

### Tests
- `tests/math/test_quaternion_sign_continuity.py`: covers the sign-continuity branch of
  `integrate_quaternion_angular_velocity` with a case that reaches it (F-3); no behaviour change.

### Docs
- `geodesic_distance` docstring: SO(3) rotation angle in [0, π], not the S³ geodesic (F-4, R10 #9); API unchanged.

## [Unreleased] — 2026-10-29 · Retarget: per-clip "stance" root scale (diagnostic)

### Added
- `domain/animation/stance_scale.py`: planted-foot speed relative to the hips on source and target, ratio as the
  clip's root scale (thresholds ESTIMATE; no stepping / too few planted frames / ratio outside 0.5–2 → none).
- `retarget_mocap(..., root_scale_mode="stance")` (first discarded pass at the stature scale, then the measured
  scale; falls back to "stature") and `root_scale=` override; stats carry the measurement. Batch `--root-scale
  stance`. Default unchanged ("stature").

### Findings (ual1 Walk / Jog / Sprint, ESTIMATE)
- Measured scales: walk 1.077, jog 1.128 (stature 1.126), sprint too few planted frames (fallback). Target
  sliding barely moves: walk 0.31 → 0.28 m/s (source 0.11), jog 0.88 → 0.87. With the root matched to the
  canonical feet's median stance speed the feet still slide, so the cause is the pose (copied rotations on
  different leg proportions make the planted foot's speed vary within the stance), not the root scale. Fix
  proposed: foot locking (IK) during contact. Not a default.

### Tests
- `tests/unit/test_stance_scale.py`; pytest 1035 passed; Blender addon headless suite 36/36 (3.6.23).

## [Unreleased] — 2026-10-29 · Game rig fixed: headless suite green again

### Fixed
- *game rig: build* and *game rig: hand pose library* (failing since the A13 foot rebuild, Decision 54; seen at
  `0644517`) are fixed by `0df8488`: `game_rig._refine_pole_angles` compared only heads and tails of the IK chain
  bones, so a twist about the bone axis passed unnoticed and swung the child bones (forward-pointing foot / ball,
  canonical toes off by up to 0.65 m; hand FK off by 0.34 m). It now compares each chain bone's full rest matrix
  and searches the whole circle before refining. The two headless checks are the regression tests (IK rest
  error 0.0003 mm, canonical layer at rest 0.0007 mm, hand FK 0.0004 mm).
- Note on the render-views entry below: its 36/36 relied on that change while it was still uncommitted; it is
  now in history.

### Test status
- Clean checkout of `de84d6c`: Blender 3.6.23 headless suite 35/35 (no `--save` check).
- Working tree: `python scripts/engine_tests.py blender --blender C:/DEV/Tools/Blender/blender.exe` 36 passed,
  0 failed; `python scripts/test.py` 1031 passed; `python scripts/lint.py` clean.

## [Unreleased] — 2026-10-29 · Automatic render views (stills, contact sheet, turntable, engine presets)

### Added
- `character_engine/pipeline/render_views.py` (pure Python): render spec over the batch-export body matrices
  (engine, device, samples, resolution, views `front` / `side` / `back`, contact sheet, turntable), engine presets
  WORKBENCH (default) / EEVEE / CYCLES, orbit camera in the canonical frame (front on −Y, side on the body's left
  +X, back on +Y) and a framing distance that fits the body from every azimuth. Refuses unavailable templates,
  unknown engines / devices / views, a device on a non-Cycles engine and clips (not rendered yet).
  Tests: `tests/unit/test_render_views.py` (10).
- `scripts/render_views.py` (through `_logrun`) + `runtime/blender/ce_render_views.py` + addon module `render.py`:
  per job the batch body builder + the *Cinematic preset* (floor, key / fill / rim lights, camera), then front /
  side / back stills, `contact_sheet.png`, `turntable/####.png` and, opt-in, `turntable.mp4` encoded by Blender's
  bundled FFmpeg (no external ffmpeg, nothing downloaded); `render.json` (body provenance, settings, engine and
  device used, seconds, sha256) per job and `manifest.json` (PASS/FAIL, one failing job does not stop the rest).
  Spec `scripts/render_specs/default.json` (male 1.80 + female 1.65 T-pose, Workbench, 24-frame turntable).
- `batch.build_body()` split out of `batch.run_job()` so renders and exports build bodies the same way;
  `reset_scene()` also clears lights and cameras.
- Measurement `docs/audit/RENDER-ENGINES-2026-10-29.md` (Blender 3.6.23, i3-3120M, GT 740M driver 388.73):
  Workbench, EEVEE, Cycles CPU and Cycles CUDA (precompiled sm_30 kernel) all render; OptiX unavailable.
  Body at 1920×1080, three stills: Workbench 9.2 / 2.2 / 2.1 s, EEVEE 16 spp 13.6 / 5.9 / 5.7 s,
  Cycles 32 spp GPU 201 / 217 / 155 s, CPU 254 / 214 / 207 s (first still of each process includes start-up).
  CYCLES `GPU` is refused without a CUDA device; `AUTO` falls back to CPU and records it.
- Headless check *render views: front/side/back + contact sheet + turntable mp4 (Workbench)*.

### Test status
- `python scripts/test.py`: 1022 passed. `python scripts/lint.py`: clean.
- `python scripts/engine_tests.py blender --blender C:/DEV/Tools/Blender/blender.exe` (3.6.23): 36 passed, 0 failed
  on the working tree. That tree held another session's uncommitted `game_rig.py` pole-angle change, which is
  what made the two *game rig* checks pass; they are not part of this commit.
- `python scripts/render_views.py --mp4` (default spec, Workbench): 2/2 PASS in 136 s (turntable 1.4–1.9 s per
  960×540 frame, mp4 encode 2.9–4.2 s).

## [Unreleased] — 2026-10-29 · Retarget: toe followers and root-scale modes (batch QA follow-up)

### Added
- Bone maps with a toe joint (`quaternius_ual`, `mixamo`, `cmu_bvh`, `rokoko`, `rigify_def`) carry
  `followers` (`TOE_FOLLOWERS`): toes 1, 2, 4, 5 copy the local rotation of toe 3 (ASSUMED: same flexion). The
  game-rig maps keep the field and skip it (no such bones).
- `domain/animation/retarget_scale.py`: root translation scale `"stature"` (whole-height ratio), `"leg"`
  (hip → knee → ankle chain ratio) or `"none"`. `retarget_mocap(..., root_scale_mode=...)` records
  `ce_root_scale` / `ce_root_scale_mode`; `scripts/retarget_batch.py --root-scale`.

### Unchanged
- Default root scale stays `"stature"` in the addon and the batch (D1 fight / reaction-library results do not move).

### Findings (batch QA, 86 clips, leg mode vs. the first run; ESTIMATE)
- Toe followers: clips whose big-toe tip goes > 1 cm below the ground 27 → 19; walks −5.0 → −3.9 cm. The driven
  foot points still sink ~2.5 cm on walks (foot geometry differs from the source), so toes alone do not fix it.
- `"leg"` (×1.065 instead of ×1.126) is not a net gain: walk sliding 0.31 → 0.26 m/s, but jog 0.88 → 1.20 and
  sprint 0.93 → 1.42 m/s, and seated clips float 2.3 cm more. On the canonical armature a walk implies ~1.0× the
  source speed and a run ~1.15×: no single constant ratio keeps every gait planted. Next step proposed: per-clip
  scale from the measured stance speed, or foot locking (IK).

### Tests
- `tests/unit/test_retarget_scale.py`; Blender addon headless suite 35/35 (3.6.23).

## [Unreleased] — 2026-10-29 · Batch asset export pipeline

### Added
- `character_engine/pipeline/batch_export.py` (pure Python, now under the lint `bpy` guard): JSON job spec, matrix
  expansion template × stature × pose × optional clip (file + bone map + clip name), deterministic names
  `<template>_<stature mm>mm_<pose>[__<bone map>_<clip>]`, validation that reports every error at once and
  **refuses** unknown or unavailable templates (horse, dog), poses, bone maps, missing clip files and duplicate jobs;
  provenance record and manifest builders. Tests: `tests/unit/test_batch_export.py` (12).
- `scripts/batch_export.py` (through `_logrun`) + `runtime/blender/ce_batch_export.py` + addon module `batch.py`:
  one Blender process runs every job from an emptied scene with the panel operators (Generate body, Import &
  retarget animation) and the block dummy; writes `builds/exports/batch/<job>.glb`, `<job>.provenance.json`
  (template, stature, pose, clip, bone map, provenance states, Blender/addon version, repo commit, sha256) and
  `manifest.json` (PASS/FAIL per job, rewritten after each job; a failing job does not stop the others).
  `--check` validates and lists jobs without Blender; `--validate-godot` runs `ce_skeleton_validator.gd` (new
  `-- --glb <path>` argument) on each GLB, SKIPPED when Godot is not found.
- Specs: `scripts/batch_specs/default.json` (male 1.80 / female 1.65 × tpose / anatomical, no clip; the repo
  ships no animation fixture) and `ual1_local.json` (Jog_Fwd from the owner's local UAL1 file, outside the repo).
- `build.export_scene_glb()` (shared by *Export scene GLB* and the batch); `force_sampling=False` for retargeted
  clips: the Jog_Fwd job went from 268 s to 8.9 s.
- Headless check *batch export: one job -> GLB + provenance, a failing job does not stop the next*.

### Test status
- `python scripts/test.py`: 988 passed. `python scripts/lint.py`: clean.
- `python scripts/engine_tests.py blender --blender C:/DEV/Tools/Blender/blender.exe` (3.6.23): 33 passed,
  2 failed; the failures (*game rig: build*, *game rig: hand pose library*) fail the same way on a clean
  checkout of `0644517`, so this change did not cause them, and they are still open.
- Batch on Blender 3.6.23 + Godot 4.7.2: `default.json` 4/4 PASS, Godot 4/4 PASS (208 bones), 6.7 s in Blender;
  `ual1_local.json` 1/1 PASS, Godot PASS, 8.9 s.

## [Unreleased] — 2026-10-29 · Batch retarget + clip QA (Quaternius UAL1/UAL2)

### Added
- `scripts/retarget_batch.py` + `runtime/blender/ce_batch_retarget.py`: every clip of UAL1/UAL2 (`*_Standard.glb`
  in place and `*_Standard_RM.glb` root motion, 86 clips, read in place) retargeted with the addon's
  `retarget_mocap` (bone map `quaternius_ual`) onto a 1.80 m canonical T-pose armature; one GLB per clip and variant
  in `builds/animations/<lib>/` (git-ignored), QA in `builds/animations/retarget_report.json` / `.md`. One Blender
  process per library and variant through `_logrun` (`logs/<UTC>_retarget_batch.log`); `--report-only` recomputes
  the QA from the stored samples. Scene at 30 fps before import, so the glTF seconds land on whole frames.
- `domain/animation/clip_qa.py` (pure Python): height-based foot contact, foot sliding, ground penetration /
  floating, loop seam (pose + velocity), root speed from the RM variant vs. the stance speed of the in-place feet,
  "glide" detection (root travels over planted feet), per-category summary. All thresholds ESTIMATE.
- The driver also reads each clip's `root` translation channel straight from the GLB (stdlib parser, no Blender).

### Findings (first run, Blender 3.6.23, all values ESTIMATE)
- 86/86 clips retargeted and exported (172 GLB), 0 errors; QA 28 ok / 14 warn / 44 fail. By category
  (ok / warn / fail): combat 8/6/17, idle 10/1/1, jump 0/0/4, locomotion 3/1/5, other 2/4/14, pose 2/0/0,
  seated 2/1/2, swim 1/0/1, traversal 0/1/0. Foot sliding is the most common failure (height-only contact also
  catches feet that skim the floor while stepping); the loop-seam check is the least robust (one-frame
  differences at 30 fps).
- Jog_Fwd_Loop (5.0 m in 0.933 s) and Sprint_Loop (5.5 m in 0.667 s) are not misread: the raw GLB channel holds
  exactly those values (29 / 21 keys) and the in-place feet move back at 5.90 / 8.90 m/s while planted (root /
  stance ratio 0.91 / 0.93). The clips really travel 5.36 / 8.25 m/s; stride 5.0 / 5.5 m per cycle, stance
  0.79 / ~0.9 m, so most of each step is flight. Whether that suits a "jog" is not checked against a source.
- Retarget: root motion is scaled by the whole-height ratio (×1.126), but the canonical feet imply about the
  source speed on walks, so retargeted walks over-travel ~11 % and slide 0.27–0.31 m/s (source 0.08–0.11 m/s).
- Retarget: only toe 3 follows the source ball joint; toes 1, 2, 4, 5 stay rigid and their tips go below the
  ground at toe-off (`undriven_toe_tip_min_height_m`, ungraded).
- Source: dash / attack clips (e.g. Sword_Dash, Shield_Dash, Roll, Sword_Attack) move the RM root while the
  in-place feet stay planted (glide).
- Export: sampled glTF export of the 208-bone armature took ~260 s per clip; keys are now exported as keyed
  (`export_force_sampling=False`, 3–5 s per clip).

## [Unreleased] — 2026-10-29 · Foot layout rebuilt (finding A13)

### Changed
- `human_adult_206.json`: the 26 bones of each foot rebuilt by `scripts/rebuild_foot_layout.py` — atlas parents
  (tarsal, tarsometatarsal, metatarsophalangeal chains; were all on `TIBIA_*`), foot forward on the ground,
  heel → toe 0.152 H, rays within 0.055 H (Drillis & Contini); split 3 : 5 : 3 PLACEHOLDER, spacing / heel offset /
  arch ESTIMATE. Report `docs/audit/A13_FOOT_LAYOUT_REPORT.json`, audit `docs/audit/A13_FOOT_LAYOUT.md`.
- `source_registry.json`: `FOOT_SEGMENT_PROPORTIONS` registered as NOT_ACQUIRED.
- Block dummy: foot capsules stay above z = 0 (`BlockSegment.on_ground`).
- Fingerprints of `human_adult_206.json` and `source_registry.json` updated; gameplay table unchanged.

### Tests
- `tests/unit/test_foot_layout.py` (new); foot parents in `test_extremity_spine_topology.py` no longer xfail;
  `test_block_dummy.py::test_foot_capsule_stays_above_the_ground`.

### Decisions
- Decision 54: finding A13, foot layout.

## [Unreleased] — 2026-10-29 · Souls-like placeholder clips baked in Blender (STYLE-SOULS-001 step 4)

### Added
- `domain/animation/souls_clips.py` (11 PLACEHOLDER clips, lengths from the frame data, staff grips),
  `scripts/export_souls_clips.py` (`souls_clips.json`), `scripts/bake_souls_clips.py` +
  `runtime/blender/ce_bake_souls_clips.py` (Blender 3.6 bake → `souls_clips.glb`, 66 game bones only).
- Godot `ce_souls_animator.gd`: rest-frame retarget of the baked clips; the Souls arena plays the clip of each
  combat state; over-the-shoulder camera. Checks in pytest, the Blender suite and the Godot runner.

## [Unreleased] — 2026-10-29 · Playable Souls-like arena (STYLE-SOULS-001 step 3)

### Added
- Godot `gameplay/ce_souls_arena.gd` + `souls_arena.tscn`: player vs Sentinel on the game rig, keyboard controls,
  HUD (health, stamina, poise, state), wound markers. Runner checks: arena builds, keys → scenario commands, two
  Sentinel scenarios through the arena equal Python. Shenmue arena untouched.

## [Unreleased] — 2026-10-25 · Souls-like in Godot (STYLE-SOULS-001 step 2)

### Added
- Gameplay table `ce-gameplay/3`: `souls_like_rules` (tuning, per-weapon moves with energy and impacts, 9 reference
  scenarios). Godot `ce_souls_combat.gd` port + `CEGameplayData.souls_rules()`; runner checks: all 9 scenarios
  identical to Python. Shenmue fights unchanged.
- Material layers and physics (Decision 49): `domain/materials` (layer catalogue, layered capsule),
  `domain/physics` (pure-Python XPBD reference, cut-energy model, forearm strike), `scripts/material_sample.py` +
  `runtime/blender/ce_material_sample.py`; evidence `docs/audit/A09_MATERIAL_SAMPLE_1.md`. All values ESTIMATE /
  ASSUMED / PLACEHOLDER. DECISION_LOG totals corrected to the real numbering (53 total, 49 final + 4 deferred).

## [Unreleased] — 2026-10-25 · Souls-like domain (STYLE-SOULS-001 step 1)

### Added
- `domain/gameplay/souls.py`: stamina, dodge roll with i-frames, guard break, light chains and heavies per weapon
  (unarmed, staff, short blade), poise and hyper-armour, deterministic Sentinel (bo), 9 reference scenarios;
  all tuning PLACEHOLDER. Tests `test_souls.py`. Shenmue fights and the gameplay JSON unchanged.

### Decisions
- Decision 53: STYLE-SOULS-001 approved (Sentinel with the bo, keyboard only in v1).

## [Unreleased] — 2026-10-25 · Canonical bone maps corrected to the standard correspondence

### Changed
- `domain/animation/bone_map.py` (owner decision "corregir al estándar"): Mixamo / CMU / Rokoko / Quaternius
  `*Index1..Pinky1` → proximal phalanx (were metacarpals), `*3` → distal, `*4` end joints unmapped; `ToeBase` and
  Rigify `toe` → TOE_PHALANX_PROXIMAL_3 (ball joint; were METATARSAL_3). `Head` → CERVICAL_1 unchanged (skull
  base). Mixamo coverage 63 → 55 (the 8 `*4` end joints). Canonical and game retarget checks unchanged (Blender 3.6).

## [Unreleased] — 2026-10-25 · Mocap / clip retarget onto the game rig (RIG-GAME-001 step 6)

### Added
- `domain/animation/game_bone_map.py`: game-rig bone maps (Mixamo, CMU, Rokoko, Quaternius UAL, Rigify) using the
  Mixamo → UE5 correspondence; `BoneMap.target_rig`; `differences_from_canonical()` reports where the canonical
  maps differ (27 joints: fingers 2–5, Head, ToeBase — finding, canonical maps unchanged).
- Addon *Retarget to game rig* (FK bake, canonical layer follows); Blender suite checks for BVH and glTF clips.
  Tests `test_game_bone_map.py`.

## [Unreleased] — 2026-10-25 · Face contract, jaw and eye look-at (RIG-GAME-001 step 5)

### Added
- Domain `rigging/face.py`: ARKit-52 names (Blender), owner-approved 20 game shapes, jaw open and clamped eye
  look-at (ASSUMED limits). Game GLB `face` block (game data only); Godot `CECharacter.set_jaw_open()` /
  `look_at_point()` with parity checks against Python. Tests `test_face.py`.

### Decisions
- Owner rule recorded in Decision 51: cinematography authored and polished in Blender; only finished assets go
  to Godot.

## [Unreleased] — 2026-10-25 · GT 740M benchmark (RIG-GAME-001 step 4)

### Added
- `scripts/godot_perf.py` + `runtime/godot/tests/ce_perf_bench.gd` (windowed Godot benchmark). Measured on the
  GT 740M (A12): game rig −21 % frame time at 8 characters; 52 face shapes ≈ 3.8× the cost of 20.

## [Unreleased] — 2026-10-25 · Blender game rig, hands and pose library (RIG-GAME-001 step 3)

### Added
- Domain `rigging/hand_poses.py`: hand controls (curl, spread, opposition, cup), pose library and weapon → grip
  pose, hand forward kinematics; angle limits ASSUMED. `GAME_CONTROL_RIG` (IK/FK arms and legs on the game rig).
- Addon `game_rig.py`: *Build game rig* (66 DEF + IK/FK + `MCH-anat_*` helpers driving the canonical armature),
  hand sliders, *Hand pose*, *Weapon grip*; Blender suite checks (Blender 3.6.23). Tests `test_hand_poses.py`.

## [Unreleased] — 2026-10-25 · Godot on the game rig (RIG-GAME-001 step 2)

### Changed
- Godot `CECharacter` / `CEArena` default to `human_game_v1_tpose.glb`; canonical names resolve through the GLB's
  `canonical_to_game` / `canonical_points` (new asset extra); validator knows the CE-GAME-v1 contract; dock lists
  the game rig first. `engine_tests.py godot` exports the game GLBs too. Fights identical (runner check).

## [Unreleased] — 2026-10-25 · Game rig CE-GAME-v1 (RIG-GAME-001 step 1)

### Added
- Spec `docs/architecture/RIG-GAME-001_SPEC.md` (owner-approved): two-level skeleton, hands and face plan.
- Domain `rigging/game_rig.py`: 66-bone game skeleton (UE5 Mannequin names) derived from canonical joints, with a
  validated canonical → game coverage map (208 nodes); `export/gltf_game.py` and `scripts/export_gltf.py --skeleton
  game` → `builds/gltf/human_game_v1.glb`. Canonical skeleton, combat and runtimes unchanged.
- Tests: `tests/unit/test_game_rig.py`.

### Decisions
- Decision 51: RIG-GAME-001 (see DECISION_LOG).

## [Unreleased] — 2026-10-25 · Weapons (runtime plan step 1)

### Added
- Domain `gameplay/weapons.py`: `Weapon` (category unarmed/blunt/blade, reach bonus, mass, energy multiplier,
  grip bone `METACARPAL_3_R` / `SOCKET-hand_grip.R`, wound type BLUNT or INCISION, placeholder size) and the
  registry `unarmed`, `staff`, `short_blade`; every value ESTIMATE/ASSUMED/PLACEHOLDER. `Fighter.weapon`
  (default unarmed) modifies hand strikes in `ShenmueCombat`; the 7 unarmed reference fights are unchanged.
- Gameplay table `ce-gameplay/2`: `weapons` + `default_weapon`, scenarios `short_blade_jab_reach` and
  `staff_chain_and_kick`.
- Godot: weapon port in `ce_shenmue_combat.gd` / `ce_gameplay_data.gd`, `CECharacter.equip_weapon()`
  placeholder on a `BoneAttachment3D`, runner checks. UPBGE: `weapon` property and
  `attach_weapon_placeholder()` in `ce_combat.py`, suite checks. Tests: `tests/unit/test_weapons.py`.

### Decisions
- Decision 50: weapons contract (see DECISION_LOG).

## [Unreleased] — 2026-10-24 (late night) · Debug consoles, blenderplayer waiver

### Added
- `scripts/_logrun.py`: live console output + `logs/<UTC>_<tool>.log` / `logs/latest_<tool>.log` for
  `scripts/test.py`, `scripts/lint.py` and every `scripts/engine_tests.py` step (`--verbose` for engine
  debug output). Guide: `docs/09_Debug_Consoles.md`.
- Experiment 0: `scripts/solver_benchmark.py` + `runtime/blender/ce_solver_benchmark.py` — Blender 3.6 solver
  benchmark (rigid/Bullet, cloth on a skeleton proxy, soft body, particles, geometry-nodes simulation, fluid), one
  process per case with a timeout; results in `docs/audit/EXPERIMENT-0-RESULTS-2026-10-24.md` (18/18 ok).
- Block dummy (17 capsule blocks, 100 % per bone, collision capsules) and mesh scale normalizer: domain
  `rigging/block_dummy.py`, `assets/normalize.py`; addon operators *Block dummy* and *Normalize mesh scale*.
- Bone map `quaternius_ual` (Quaternius UAL / Universal Base Characters, CC0, 65-bone UE-style rig → 52 canonical
  bones via the Mixamo equivalents). Retarget fix: root motion moves the canonical hierarchy root (trunk no longer
  detaches in deep poses).
- Draft rows WORKBENCH-LAYOUT and MATERIAL-SWATCHES; engagement clarified as adaptive movement cinematography by
  proximity and attack direction (draft §10).

### Decisions
- Decision 41: **CE-Q4 unblocked** by the owner (RG-005).
- Decision 42: production line in Blender (modelling, rigging, cinematography, render); gameplay runtime in Godot.
  Clarified: simulation (PBD/XPBD, materials) also in Blender; Godot hosts the fight engagement system;
  simulation bake/export format not yet specified.
- Decision 41 follow-up done: Godot arena played windowed on the GT 740M (OpenGL 3.3 Compatibility, 0 errors,
  autoplay to frame 180).
- Decision 43: Godot project file accepted as written by Godot 4.7 (features 4.3 → 4.7, owner-authorized);
  `runtime/godot/arena_play.tscn` is the main scene (F5 plays the arena).
- Decision 44: engagement three-layer design confirmed; draft rows ANATOMY-MESH, RIG-PARTS, MUSCLE-FASCIA-MESH,
  TREAT-HANDS/HEAD-FACE/BODY, FK-FROM-SIM (owner request; candidate sources listed, nothing downloaded).
- Decision 45: simulation (L2) offline in Blender, baked mesh manifestations; Godot plays baked reactions by state
  and collision point (no runtime simulation).
- Decision 40: Godot 4 is the primary runtime and the only one that gates CE-Q4 and later phases; UPBGE stays
  supported but optional and non-blocking (no code or tests removed).
- Decision 39: blenderplayer smoke check dispensed for CE-Q4 (NVIDIA 388.73 / GT 740M cannot compile UPBGE
  0.50 EEVEE shaders; environmental). UPBGE suite on this PC: 26/27.

### Test status
pytest 762 passed; ruff and architecture guard clean; Godot 4.7.2 21/21.

## [Unreleased] — 2026-10-24 (night) · CE-Q4 gate review

### Added
- `docs/audit/CE-Q4-GATE-REVIEW-2026-10-24.md` (read-only review, approved by the owner: RG-001, RG-002,
  RG-004 accepted).
- `tests/math/test_quaternion_convergence.py`: integrator convergence, R10 criterion corrected (Decision 38).

### Test status
pytest 755 passed; ruff and architecture guard clean. UPBGE 0.50 suite pending the owner's run.

## [Unreleased] — 2026-10-24 (evening) · CINE-GR-001 step 1

### Added
- Equipment sockets `SOCKET-sabre_hip.L` / `SOCKET-hand_grip.R` (`domain/rigging/sockets.py`, ASSUMED placement),
  built by the addon as MCH bones; PLACEHOLDER sabre on the hip socket.
- Addon operators *Add equipment sockets* and *Cinematic preset: full body, Workbench* (floor, 3 lights,
  framed camera, 1920×1080 render to `builds/renders/`, ignored).

### Test status
pytest 753 passed; addon headless 24/24 on Blender 3.6.23 (CINE-GR-001 checks (a)–(d), render 2.38 s);
Godot 4.7.2 21/21.

## [Unreleased] — 2026-10-24 (late afternoon) · Finding A11: forearm layout

### Fixed
- **Forearm** (`scripts/fix_forearm_layout.py`, `docs/audit/A11_FOREARM_LAYOUT.md`): radius and ulna were
  split antero-posteriorly; the radius is now lateral to the ulna (same midpoint, lengths and z; the
  pre-existing 0.0333 m half-separation moved from Y to X, PLACEHOLDER). Hand re-anchored on the radius tail.

### Test status
pytest 747 passed; addon headless 20/20 on Blender 3.6.23 (IK rest deviation 11.8 mm, unchanged);
Godot 4.7.2 21/21; gameplay table unchanged.

## [Unreleased] — 2026-10-24 (afternoon) · Finding A10: hand layout

### Fixed
- **Hands** (`scripts/rebuild_hand_layout.py`, `docs/audit/A10_HAND_LAYOUT.md`): metacarpals and
  phalanges were 15–20 cm medial to the wrist and parented to the radius. Rebuilt from the wrist
  (radius tail) to the sourced fingertip height (0.377 H) with atlas topology (carpal rows,
  MC1←trapezium … MC4/MC5←hamate, phalangeal chains). Intra-hand proportions remain PLACEHOLDER
  (pre-existing values), registered as `HAND_SEGMENT_PROPORTIONS` (source pending).

### Test status
pytest 743 passed (`test_hand_layout.py` new); addon headless 20/20 on Blender 3.6.23; Godot 4.7.2 21/21;
gameplay table unchanged.

## [Unreleased] — 2026-10-24 (afternoon) · Decision 17 closed: left is +X

### Changed
- **Canonical skeleton mirrored across X** (`scripts/mirror_canonical_x.py`, report
  `docs/audit/A09_D17_MIRROR_X_REPORT.json`): `*_L` bones now at +X, `*_R` at −X, front still −Y.
  Same convention as Blender, glTF/Godot and Mixamo. `human_adult_206_backup.json` (frozen fixture)
  is not migrated.
- Side signs (`tpose.py`, `rig_definition.py`, legacy `landmark_positioner.py`), `coordinate_system.py`
  (`get_right_direction() = (-1,0,0)`, `get_side_from_x(+x) = LEFT`).
- Blender addon mocap import: `axis_forward` is now the opposite of the clip's facing axis, so
  Mixamo/CMU/Rokoko clips face −Y with their left at +X (they used to be imported turned round).

### Test status
pytest 734 passed; new `test_left_right_convention.py`; addon headless 20/20 on Blender 3.6.23 with a new
mocap side/direction check; Godot 4.7.2 21/21 (left arm now spreads to +X). `builds/tests/validation.blend`
(versioned, old labels) was not regenerated.

## [Unreleased] — 2026-10-24 · Blender addon on Blender 3.6 LTS (reference) and 4.x

### Changed
- Addon `bl_info` 0.3.1, minimum Blender `(3, 6, 0)` (was 4.2). Decision 20: Blender 3.6 is the
  project reference version; 4.x stays supported.
- `addon/build.py`: new `assign_bone_layer()` / `bone_layer_names()` — bone collections
  `DEF`/`MCH`/`CTRL` on Blender 4.x, armature layers 0/1/2 on Blender 3.6 (which has no
  `Armature.collections`); bones also get the custom property `ce_layer`.
- `runtime/blender/ce_addon_headless_test.py`: the rig check reads layers through
  `bone_layer_names()` and checks `ce_layer`.
- `scripts/engine_tests.py`: `--blender <exe>` and `C:/DEV/Tools/Blender/blender.exe` in Blender
  discovery. `scripts/install_blender_addon.py`: `--blender <exe>` (default `$CE_BLENDER`) installs
  into that Blender's user addons folder.

### Test status
Addon headless suite 20/20 on Blender 3.6.23 (background) and 20/20 on Blender 4.2.23 LTS
(background); before the change Blender 3.6 failed 10/20 (`'Armature' object has no attribute
'collections'`). pytest 713 passed. UPBGE 0.50 suite not run (needs a window).

### Fixed
- `export/gltf.py`: the canonical GLB was not byte-reproducible — container centroids
  (`ROOT_SKELETON`, `CRANIUM`) were summed in `frozenset` order of random `uuid4` child ids, changing
  the last float bit between runs. Children are now summed in canonical-name order.
  `tests/export/test_gltf_determinism.py` exports fresh skeletons 5× in-process and in 5 interpreters
  with different `PYTHONHASHSEED` and requires identical bytes (fails on the old code). pytest 716 passed.

## [Unreleased] — 2026-09-29 (night) · A08 osteometry, tissues, T-pose, Blender addon, UPBGE/Godot gameplay

### Added
- **Data**: `references/osteometry.json` v1.1.0 — Trotter (1970) male white + Trotter & Gleser
  1952 female white / female Black (all six long bones PROVEN); derived lengths at 1.80 m and
  1.65 m; shaft diameters ESTIMATE. Drives bone *mesh extents*, never joints (Decision 16).
- **Domain** (pure Python, all tested): `anatomy/osteometry`, `anatomy/pose` (T-pose / A-pose),
  `anatomy/proportions/stature_retarget.py` (moved from the CLI), `tissue` (layers, regions, 50
  bilateral muscle attachments), `trauma` (wound types, AIS-like severity, regional caps,
  `blunt_impact_to_wound(energy_j=…)`), `character` (templates male/female/child 5y/10y/elderly,
  horse & dog `available=False`), `rigging` (`HUMANOID_RIG`), `animation` (Mixamo/CMU/Rokoko/Rigify
  bone maps), `gameplay` (Shenmue-style 60 Hz combat + `runtime_table` JSON generator).
- **glTF exporter**: `--pose {anatomical,tpose,apose}`, `--template`, `--stature`.
- **Blender addon** `infrastructure/blender/addon/` (Blender 4.2+/UPBGE 0.50): Body, Tissues, Rig
  (IK/FK, foot roll, breathing), Mocap (BVH retarget), Wounds (raycast), Export, Runtime panels;
  `scripts/install_blender_addon.py`; guide `docs/08_Blender_Addon.md`.
- **UPBGE runtime**: `runtime/upbge/components/ce_combat.py` (component + logic-brick entry embedding
  the Python combat domain), arena set-up operator, `blenderplayer.exe` autoplay smoke.
- **Godot addon** `runtime/godot/addons/character_engine/`: dock (asset, stature, gameplay style
  selector with planned styles), `CECharacter`, `CEBreathing` (`SkeletonModifier3D`),
  `CEShenmueCombat` (GDScript port replaying 7 reference fights identically), `CEFighterController`,
  `CEArena`; `data/gameplay_shenmue.json` generated by `scripts/export_gameplay_data.py`;
  `runtime/godot/tests/ce_test_runner.gd`.
- **Orchestration**: `scripts/engine_tests.py` — Blender (background) → UPBGE (UI mode) → Godot
  (headless), each closed before the next; reports in `builds/tests/` (git-ignored).
- Docs: `docs/audit/A08_OSTEOMETRY_TISSUES_TPOSE.md`, `docs/08_Blender_Addon.md`, sections in
  `06_UPBGE.md` / `07_Godot.md`, roadmap status in `PRODUCTION_VS_RUNTIME.md`, Decisions 16–19
  (17 = left/right labelling vs −Y forward, **OPEN**), `.cursor/rules/coordinate-system.mdc` corrected.

### Fixed
- `default_osteometry_path()` / `default_canonical_json()` parent-depth off-by-one.
- Blunt wounds were always lethal (energy passed as impulse); severity now capped per region.
- UPBGE 0.50 background-mode crashes (`bpy.ops.logic.*`, `view3d.game_start`) worked around:
  deferred binding in `-b`, component in UI mode, game via `blenderplayer.exe`, deferred quit.

### Test status
627 passed (pytest) · ruff clean · architecture guard OK · Blender 23/23 · UPBGE 23/23 · Godot 21/21.

## [Unreleased] — 2026-09-29 (evening) · A07 stature retarget, engine installs, architecture

### Changed
- **Canonical skeleton retargeted to 1.80 m** (`scripts/retarget_stature.py`, A07). Joint heights
  from Drillis & Contini (1966) via Winter (2009) Fig. 4.1; three piecewise-linear Z maps
  (axial/arm/leg), XY scaled to biacromial breadth 0.259 H. Topology unchanged (206/208).
  Provenance: ratios PROVEN, landmarks DERIVED, interpolated bones ESTIMATE.
- `references/anthropometry.json` v1.1.0: segment ratios and joint-height ratios now PROVEN with
  `source_id = DRILLIS_CONTINI_1966`; base stature 1.80 m as `USER_INPUT`;
  `canonical_landmark_heights_m` added. `source_registry.json` v1.1.0 registers the source.
- `docs/audit/A02_CANONICAL_DATA_AUDIT.md`: header note pointing to A07 for the scale findings.
- `docs/reorientation/DECISION_LOG.md` §15: stature retarget decision.

### Added
- `docs/audit/A07_STATURE_RETARGET_180.md` + `A07_STATURE_RETARGET_REPORT.json`.
- `docs/architecture/PRODUCTION_VS_RUNTIME.md`: boundary between canonical core, Blender production
  and Godot/UPBGE runtime; file contracts; roadmap P1–P6 (character editor, IK/FK rig generator,
  mocap, runtime IK layers incl. breathing, simulation recording/extraction, animals).
- Local engine installs: Godot 4.7.2 stable (`C:\Tools\Godot`) and UPBGE 0.50 / Blender 5.0.1
  (`C:\Tools\UPBGE\upbge-0.50-windows-x64`). Both runtime validators PASS (208 bones, ground contact,
  upright, State Auditor PASS).

### Test status
566 passed, 0 failed · ruff clean · architecture guard OK.

## [Unreleased] — 2026-09-29 · Repository stabilisation, C6, glTF export, engine runtimes

### Fixed
- `backend/database/models.py`: `UserRole` active-uniqueness expressed as a partial unique
  `Index` (`revoked_at IS NULL`) instead of an invalid `UniqueConstraint(sqlite_where=...)`
  that prevented the whole backend test suite from importing.
- `backend/database/connection.py`: removed duplicated `drop_tables`; TEST environment uses
  in-memory SQLite with `StaticPool` (opt-out via `CHARACTER_ENGINE_TEST_DB_FILE`).
- `backend/authentication/password_service.py`: Argon2id parameters per `Environment`
  (OWASP in production, fast in tests). Backend suite time 290 s → ~15 s.
- `backend/authentication/authentication_service.py`: SQLAlchemy `Session` no longer
  shadowed by the domain `Session` (`DbSession` alias).
- `domain/anatomy/reference/source.py`: `ReferenceValue.is_measured()` added;
  `is_derived()`/`is_assumed()` honour the derivation method as well as provenance.
- `tests/backend/test_config.py`: default-environment tests clear `CHARACTER_ENGINE_ENV`.
- C6 authorization: `UserRole.role_id` stored a label instead of the FK; `.count()` on a
  `Result`; `has_permission` used a non-existent permission format; `datetime.utcnow()`.
- Lint: 3 858 ruff findings → 0 (safe fixes + manual fixes; no wholesale reformat).

### Added
- `backend/authorization/authorization_service.py` — `AuthorizationService` implementing
  the C6 contract (deterministic 7-step decision, IDOR → 404, no SYSTEM bypass, audit hook);
  `RoleService` rewritten; domain exceptions and `DenialReason.http_status`.
- `tests/backend/test_c6_authorization.py` — 66 tests.
- `src/character_engine/export/gltf.py` — pure-stdlib glTF 2.0/GLB exporter with Z-up → Y-up
  conversion, skin + inverse bind matrices, provenance in `extras`; CLI `ce-export-gltf`;
  `tests/export/` (23 tests).
- `runtime/godot/` — `ce_skeleton_validator.gd` + project preset for the Compatibility renderer.
- `runtime/upbge/ce_import_and_validate.py` — headless GLB import + validation for UPBGE/Blender.
- Tooling: `pyproject.toml` (extras, pytest `pythonpath`, ruff config), `scripts/`
  (`bootstrap`, `test`, `lint` with `bpy` architecture guard, `format`, `clean`, `export_gltf`),
  `.github/workflows/ci.yml`, `.vscode/`, `.editorconfig`, `.gitattributes`, PR template.
- Agent guidance: `AGENTS.md`, `.cursor/rules/` (domain purity, provenance, coordinate system,
  backend contracts, testing), `.cursor/skills/` (`run-tests`, `export-gltf`, `validate-godot`,
  `validate-upbge`, `audit-phase-closure`).
- Docs: `README.md`, `docs/06_UPBGE.md`, `docs/07_Godot.md`, this changelog.

### Removed
- Committed virtual environment `.venv-py310` (pointed to another user's Python), `src/UNKNOWN.egg-info`,
  `__pycache__` directories, `character_engine.db`, `temp_*` files, `builds/tests/*.blend1`,
  109 empty placeholder files and empty packages (`src/character_engine/anatomy/`, `blender/`,
  `.ai/`, `.engine/`, `config/`).

### Test status
`tests/anatomy + unit + integration` 282 · `tests/export` 23 · `tests/backend` 261 → **566 passed, 0 failed**.

## [0.1.0] — first commit
Canonical 206-bone skeleton, anatomy domain (A02–A05 audits), backend phases C1–C5,
reorientation plan.
