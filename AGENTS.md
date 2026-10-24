# Character Engine — Agent Guide

Character Engine is an **engine-agnostic canonical anatomy system**: a 206-bone human
skeleton with provenance-tracked reference data, exported to neutral formats (JSON, glTF 2.0)
and consumed by runtimes (Godot 4, UPBGE/Blender). It also ships a backend (FastAPI + SQLAlchemy)
for users, accounts, authentication and RBAC authorization.

## Layout

| Path | Role | Rules |
|------|------|-------|
| `src/character_engine/domain/` | Pure-Python anatomy domain (osteology, joints, landmarks, proportions, reconstruction, reference) | **No `bpy`, no I/O, no engine code** |
| `src/character_engine/data/anatomy/` | Canonical data (`human_adult_206.json`, `references/`) | Never edit numbers without provenance |
| `src/character_engine/{loader,dto,serialization,schema,validation,pipeline}/` | JSON ↔ DTO ↔ domain | Pure Python |
| `src/character_engine/export/` | glTF 2.0 exporter (Z-up → Y-up) | Pure Python, stdlib only |
| `src/character_engine/infrastructure/blender/` | Blender/UPBGE adapters | Only place `bpy` is allowed (plus `runtime/`) |
| `runtime/godot/`, `runtime/upbge/` | Runtime validators (GDScript, bpy) | Consume `builds/gltf/*.glb`, never the domain |
| `backend/` | Config, DB models, users, accounts, authentication, authorization | SQLAlchemy 2, Argon2id, tests on in-memory SQLite |
| `tests/` | pytest (`anatomy`, `unit`, `integration`, `export`, `backend`) | ~570 tests, all must pass |
| `docs/audit/`, `docs/reorientation/` | Forensic audits, contracts, decision log | Source of truth for phase closure |
| `scripts/` | `bootstrap`, `test`, `lint`, `format`, `clean`, `export_gltf`, `acceptance_gate` | Cross-platform Python |

## Commands

```bash
python scripts/bootstrap.py          # create venv (outside repo) + install extras
python scripts/test.py               # full pytest suite (CHARACTER_ENGINE_ENV=test)
python scripts/lint.py               # ruff + architecture guard (bpy only in infrastructure/runtime)
python scripts/export_gltf.py        # -> builds/gltf/human_adult_206.glb
python -m pytest tests/backend -q    # backend only (~15 s)
```

Environment: `CHARACTER_ENGINE_ENV` = `development | test | production`. Tests use `test`
(in-memory SQLite, fast Argon2 params). `tests/conftest.py` sets it automatically.

## Invariants

1. **Never invent anatomical data.** Every numeric value carries a provenance state
   (`PROVEN`, `DERIVED`, `ESTIMATE`, `ASSUMED`, `PLACEHOLDER`, `UNKNOWN`). If a source
   is missing, mark `UNKNOWN`/`PLACEHOLDER` — do not guess.
2. **Canonical coordinate system:** Z-up, right-handed, -Y forward, metres, origin at
   foot midline. Engines convert at the boundary (`export/gltf.py`: `(x, y, z) → (x, z, -y)`).
3. **Domain purity:** `src/character_engine/domain/**` imports nothing from `bpy`,
   `backend`, or any engine. `scripts/lint.py` enforces this.
4. **Skeleton contract:** 208 nodes = 206 anatomical bones + `ROOT_SKELETON` + `CRANIUM`
   containers; unique `canonical_name`; acyclic hierarchy; single root.
5. **Authorization (C6):** deterministic 7-step decision, RBAC only, `UserRole` history is
   append-only (revoke, never delete), IDOR → 404 not 403, no global SYSTEM bypass.
6. **Backend tests never touch a real DB**; use fixtures in `tests/backend/conftest.py`.

## Working style

- Read the relevant `docs/audit/*` contract before changing `backend/` or domain semantics.
- Add or update tests in the same change; run `python scripts/test.py` before finishing.
- Keep diffs surgical; do not run `ruff format` over untouched files.
- Write commit messages and docs in English; user-facing chat may be in Spanish.
- Record contract-level decisions in `docs/reorientation/DECISION_LOG.md`.

See `.cursor/rules/` for file-scoped rules and `.cursor/skills/` for runnable workflows
(test, export glTF, Godot validation, UPBGE/Blender headless validation).
