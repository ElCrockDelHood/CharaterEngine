# 19 — Changelog

All notable changes to Character Engine. Dates are ISO 8601.

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
