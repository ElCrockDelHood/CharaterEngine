# 19 — Changelog

All notable changes to Character Engine. Dates are ISO 8601.

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
