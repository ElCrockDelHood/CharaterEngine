---
name: validate-upbge
description: Run headless UPBGE/Blender validation of the canonical skeleton, either importing the exported GLB (runtime/upbge) or rebuilding the armature from JSON via infrastructure/blender (State Auditor). Use when the user asks to test in UPBGE or Blender, validate the armature, or debug bpy import problems.
---

# Validate in UPBGE / Blender (headless)

Two independent paths; both exit `0` on success, `1` on failure.

## Path A — Import the GLB (engine-agnostic contract)

```bash
$PY scripts/export_gltf.py
"$UPBGE" -b --python runtime/upbge/ce_import_and_validate.py -- \
    --glb builds/gltf/human_adult_206.glb \
    --save builds/tests/upbge_validation.blend      # optional
# flags: --no-fix-tails  (skip rebuilding tails from extras.ce_tail)
```

`$UPBGE` = `/c/Tools/UPBGE/upbge-0.50-windows-x64/blender.exe` on this machine (vanilla Blender
3.6+/4.x/5.x works too). UPBGE 0.50 prints a harmless `bge_netlogic` `register_class` error in
background mode; ignore it.
Everything after `--` goes to the script, not to Blender.

Checks: 208 bones, 206 anatomical, required bones present, single root, tails rebuilt
from `extras`, lowest head at `z ≈ 0`, Z-up orientation after glTF import.

## Path B — Rebuild from canonical JSON (Blender adapter, State Auditor R1.3)

```bash
"$UPBGE" -b --python scripts/validate_blender_headless.py
# Windows helper (edit $blenderPath inside): powershell -File validar_blender_headless.ps1
```

Uses `character_engine.infrastructure.blender.BlenderImporter` + `StateAuditor` to build
the armature directly from `human_adult_206.json` and audit hierarchy/positions.

## Rules

- `bpy` is allowed only in `src/character_engine/infrastructure/blender/` and `runtime/`.
- Never save into `builds/tests/*.blend` tracked by git; `*.blend1` and `builds/tmp/` are ignored.
- If Path A passes and Path B fails (or vice versa) the bug is in the adapter/exporter,
  not in the domain: compare head coordinates bone by bone before touching the JSON.

## Common failures

- `This script must be executed inside UPBGE/Blender`: you ran it with plain Python.
- `ModuleNotFoundError: character_engine`: Path B only — run from the repo root
  (the script inserts `src/` into `sys.path` relative to its own location).
- Bones with zero length: tails not rebuilt; drop `--no-fix-tails`.
