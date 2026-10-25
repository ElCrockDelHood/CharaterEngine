# Character Engine

Engine-agnostic canonical anatomy system. The core is a **206-bone human skeleton** with
provenance-tracked reference data, modelled in pure Python and exported to neutral formats
(JSON, glTF 2.0) so that any runtime — Godot 4 (primary gameplay runtime, Decision 40), UPBGE/Blender, or others — can consume it
without depending on a particular DCC tool or engine.

The repository also contains the backend foundation (FastAPI + SQLAlchemy 2): configuration,
database models, users, accounts/identities, Argon2id authentication and RBAC authorization.

```
canonical JSON ──► domain (pure Python) ──► glTF 2.0 (.glb) ──► Godot 4 / UPBGE / …
   Z-up, metres        validation,            Y-up conversion       runtime validators
   provenance          reconstruction         at the boundary       (runtime/)
```

## Quick start

```bash
git clone <repo> && cd CharaterEngine
python scripts/bootstrap.py            # venv outside the repo + `pip install -e .[backend,dev,schema]`
python scripts/test.py                 # ~850 tests
python scripts/lint.py                 # ruff + architecture guard
python scripts/export_gltf.py          # builds/gltf/human_adult_206.glb
```

Requirements: Python 3.10 or 3.11. Blender/UPBGE and Godot are optional and only needed
for the runtime validators.

## Repository map

| Path | Content |
|------|---------|
| `src/character_engine/domain/anatomy/` | Osteology, joints, landmarks, spine, hands, feet, proportions, reconstruction, reference data with provenance |
| `src/character_engine/data/anatomy/` | `human_adult_206.json` (canonical skeleton, 208 nodes), `references/` |
| `src/character_engine/{loader,dto,serialization,schema,validation,pipeline}/` | JSON ↔ DTO ↔ domain pipeline |
| `src/character_engine/export/gltf.py` | glTF 2.0 exporter (stdlib only), CLI `ce-export-gltf` |
| `src/character_engine/infrastructure/blender/` | Blender/UPBGE adapter (only place where `bpy` is allowed) |
| `runtime/godot/` | `ce_skeleton_validator.gd` + minimal project (Compatibility renderer) |
| `runtime/upbge/` | `ce_import_and_validate.py` headless GLB import + validation |
| `backend/` | Phases C1–C6: config, models, users, accounts, authentication, authorization |
| `tests/` | `anatomy`, `unit`, `integration`, `export`, `backend` |
| `docs/` | Audits (`docs/audit`), reorientation plan and decision log, engine guides |
| `scripts/` | Cross-platform tooling (`bootstrap`, `test`, `lint`, `format`, `clean`, `export_gltf`, `acceptance_gate`) |
| `AGENTS.md`, `.cursor/rules`, `.cursor/skills` | Guidance for AI agents working on the repo |

## Canonical contract

- **Skeleton**: 206 anatomical bones + `ROOT_SKELETON` + `CRANIUM` containers = 208 nodes,
  unique canonical names, acyclic hierarchy, single root.
- **Coordinate system**: Z-up, right-handed, -Y forward, metres, origin at the foot midline;
  the body's left is **+X** (`*_L` at +X, `*_R` at −X, Decision 33 / D-13).
  Exporters convert at the boundary (glTF/Godot: `(x, y, z) → (x, z, -y)`).
- **Fingerprint**: `tests/anatomy/test_contract_fingerprint.py` pins the canonical data files;
  changing them needs the owner's OK and a `DECISION_LOG.md` entry (Decision 52).
- **Provenance**: every value is `PROVEN`, `DERIVED`, `ESTIMATE`, `ASSUMED`, `PLACEHOLDER`
  or `UNKNOWN`. Data is never invented; missing data is marked as missing.

## Engine guides

- [docs/07_Godot.md](docs/07_Godot.md) — Godot 4 setup, recommended version, validator.
- [docs/06_UPBGE.md](docs/06_UPBGE.md) — UPBGE/Blender setup, recommended version, headless validation, gameplay component.
- [docs/08_Blender_Addon.md](docs/08_Blender_Addon.md) — Character Engine addon: body, tissues, IK/FK rig, mocap, wounds, export, runtime.
- [docs/19_Changelog.md](docs/19_Changelog.md) — changes per iteration.

```bash
python scripts/install_blender_addon.py   # install the Blender/UPBGE addon
python scripts/export_gameplay_data.py    # regenerate the Godot gameplay table
python scripts/engine_tests.py            # Blender -> UPBGE -> Godot suites (each closed before the next)
```

## Environment variables

| Variable | Values | Effect |
|----------|--------|--------|
| `CHARACTER_ENGINE_ENV` | `development` (default), `test`, `production` | Argon2 parameters, DB URL defaults |
| `CHARACTER_ENGINE_TEST_DB_FILE` | path | Use a file-based SQLite in tests instead of in-memory |
| `DATABASE_PASSWORD`, `SECRET_KEY` | secrets | Injected into `backend/config` (never stored in JSON config files) |

## Engine tools installed locally

`C:\Tools\Godot\Godot_v4.7.2-stable_win64_console.exe` ·
`C:\Tools\UPBGE\upbge-0.50-windows-x64\blender.exe` — both validators PASS on the
1.80 m canonical skeleton (2026-09-29).

## Status

Domain phases A02–A11 audited; canonical stature 1.80 m with Drillis & Contini (1966) joint
heights (`docs/audit/A07_STATURE_RETARGET_180.md`); osteometry, T-pose, tissue/wound layers,
character templates, IK/FK rig, mocap maps and Shenmue-style gameplay across Blender, UPBGE and
Godot (`docs/audit/A08_OSTEOMETRY_TISSUES_TPOSE.md`); left = +X (Decision 33), hand and forearm layout
(A10, A11). Godot is the primary gameplay runtime, UPBGE optional (Decision 40); Blender is the production
line (Decision 42). Backend phases C1–C6 implemented and tested.
Open gaps (events, rewards, assets API, HTTP layer) are tracked in
`docs/reorientation/OPEN_GAPS.md`. The production/runtime split and the roadmap (character
editor, IK/FK rig, mocap, runtime IK, simulation extraction, animals) are in
[docs/architecture/PRODUCTION_VS_RUNTIME.md](docs/architecture/PRODUCTION_VS_RUNTIME.md).
