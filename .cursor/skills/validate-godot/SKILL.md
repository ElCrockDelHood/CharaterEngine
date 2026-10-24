---
name: validate-godot
description: Load the exported skeleton GLB in Godot 4 (headless or editor) and run the GDScript validator (node count, required bones, ground contact, Y-up orientation). Use when the user asks to test in Godot, validate the Godot import, or debug Skeleton3D issues.
---

# Validate in Godot 4

Requires Godot **4.x standard** build (not .NET). On Intel HD 620 use the
**Compatibility (OpenGL 3)** renderer — `runtime/godot/project.godot` already sets it.

## Headless (CI-style)

```bash
$PY scripts/export_gltf.py
cp builds/gltf/human_adult_206.glb runtime/godot/          # git-ignored there
godot --headless --path runtime/godot --script res://ce_skeleton_validator.gd
echo "exit=$?"                                             # 0 = passed
```

On Windows set the executable path first; on this machine:
`GODOT="/c/Tools/Godot/Godot_v4.7.2-stable_win64_console.exe"` and use `"$GODOT"` instead of `godot`.
The `_console.exe` variant prints to the terminal; the plain `.exe` does not.

## In the editor

1. Open `runtime/godot/project.godot` (first open imports the `.glb`; `.godot/` and
   `*.import` are git-ignored).
2. Drag `human_adult_206.glb` into a scene → instance → inspect `Skeleton3D`
   (should show 208 bones, `ROOT_SKELETON` at root, feet at `y ≈ 0`, upright along +Y).
3. Attach `ce_skeleton_validator.gd` to any node and call
   `validate_skeleton(skeleton)` (static) from `_ready()`, then `print_report(report)`.

## Report fields (`validate_skeleton` → `Dictionary`)

`passed`, `errors`, `warnings`, `bone_count` (208), `roots` (≥ 1), `ground_y` (|y| ≤ 0.05,
warning only), `height_m` (≥ 1.0 → orientation OK).
Canonical stature is 1.80 m since A07 (`docs/audit/A07_STATURE_RETARGET_180.md`); `height_m`
reads bone heads so ~1.76 is expected. Never rescale in the exporter — stature is a data decision
(`scripts/retarget_stature.py`).

## Common failures

- **`no .glb found`**: copy the file into `runtime/godot/` or set `glb_path`.
- **Skeleton lying down / sideways**: exported with `--keep-z-up`; re-export without it.
- **Bones count ≠ 208**: exporter input is not the canonical JSON; check `-i`.
- **Blank window / GPU error**: renderer is Forward+; switch to Compatibility in
  Project Settings → Rendering → Renderer, or run with `--rendering-driver opengl3`.
