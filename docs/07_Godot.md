# 07 — Godot 4 Runtime

Godot consumes the canonical skeleton **only through the glTF 2.0 export**. Nothing in the
domain knows about Godot; the runtime validator in `runtime/godot/` proves that the neutral
artifact round-trips correctly.

## Recommended installation (Lenovo T470s · i7-7600U · Intel HD Graphics 620 · 16 GB)

| Item | Recommendation | Why |
|------|----------------|-----|
| Version | **Godot 4.7.2 stable** (released 2026-08-18) | Latest maintenance release; 4.8 is still `dev` |
| Build | `Godot_v4.7.2-stable_win64.exe.zip` (**Standard**, not .NET) | GDScript is enough for the validator; .NET adds the SDK dependency |
| Also download | `Godot_v4.7.2-stable_win64_console.exe` (inside the same zip) | Prints headless output to the terminal |
| Renderer | **Compatibility (OpenGL 3.3)** | HD 620 supports OpenGL 4.6 / Vulkan 1.3, but with 128 MB dedicated + shared memory the Compatibility renderer is faster and more stable than Forward+/Mobile |
| Driver | Latest Intel Graphics driver (Kaby Lake, HD 6xx) from intel.com | Vulkan/OpenGL fixes; Windows Update drivers are often outdated |

Download: <https://godotengine.org/download/archive/4.7.2-stable/>. Godot is portable:
unzip anywhere, no installer.

**Installed on this machine (2026-09-29):** `C:\Tools\Godot\Godot_v4.7.2-stable_win64.exe`
and `C:\Tools\Godot\Godot_v4.7.2-stable_win64_console.exe`.

Last validation run (canonical skeleton at 1.80 m):

```
Godot Engine v4.7.2.stable.official
bone_count: 208 · roots: 1 · height_m: 1.761 · ground_y: 0.0055 · RESULT: PASS
```
(`height_m` is measured on bone *heads*; the vertex at 1.800 m is the `FRONTAL` tail.)

`runtime/godot/project.godot` already sets `rendering/renderer/rendering_method="gl_compatibility"`.
If you create another project, set it in *Project Settings → Rendering → Renderer*, or launch
with `--rendering-driver opengl3`.

## Workflow

```bash
# 1. Export the canonical skeleton
python scripts/export_gltf.py                      # builds/gltf/human_adult_206.glb

# 2. Copy next to the Godot project (git-ignored there)
cp builds/gltf/human_adult_206.glb runtime/godot/

# 3. Headless validation (exit code 0 = passed)
GODOT="/c/Tools/Godot/Godot_v4.7.2-stable_win64_console.exe"
"$GODOT" --headless --path runtime/godot --script res://ce_skeleton_validator.gd
```

Editor workflow: open `runtime/godot/project.godot`, let Godot import the `.glb`, drag it
into a scene and inspect the `Skeleton3D` node (208 bones, `ROOT_SKELETON` as root,
feet at `y ≈ 0`, skeleton upright along +Y).

## What the validator checks (`ce_skeleton_validator.gd`)

| Report key | Expected |
|------------|----------|
| `bone_count` | 208 (206 anatomical + 2 containers) — error otherwise |
| required bones | `ROOT_SKELETON`, `CRANIUM`, `SACRUM`, `CERVICAL_1`, `FEMUR_L`, `FEMUR_R`, `FRONTAL` — error if missing |
| `roots` | ≥ 1 — error if 0 |
| `ground_y` | within ±0.05 m of 0 — warning otherwise |
| `height_m` | ≥ 1.0 m along +Y — error otherwise (means the Z-up → Y-up conversion failed) |

Note on scale: since A07 (`docs/audit/A07_STATURE_RETARGET_180.md`) the canonical skeleton is
**1.80 m** tall with Drillis & Contini joint heights. The validator still checks orientation
(`height_m ≥ 1.0`) rather than an exact stature so that future parametric characters
(different statures) pass unchanged.

## Character Engine addon (`runtime/godot/addons/character_engine/`)

Enabled in `project.godot`. The **Character Engine** dock (right panel) offers:

| Control | Effect |
|---------|--------|
| Asset (T-pose / anatomical) + stature | *Add character to scene* → `CECharacter` node: loads the GLB at runtime (`GLTFDocument`), scales to stature, installs `CEBreathing` (`SkeletonModifier3D`, sternum/ribs sinusoid), exposes `bone_global_position()` and `add_wound_marker()`. |
| *Validate skeleton GLB* | Runs `ce_skeleton_validator.gd` on the selected asset. |
| Gameplay style | `shenmue` (Shenmue-style free battle: J punch, K kick, L throw, Space guard, W/S move; `F,F+J` Elbow Assault, `F+K` Crescent Kick, `F+L` Vortex Throw). `souls_like` / `beat_em_up` are listed as *planned* (disabled). |
| *Create arena in scene* (+ autoplay) | `CEArena`: floor, two `CECharacter`s, camera, HUD, `CEFighterController`s (player keyboard / opponent AI), `CEShenmueCombat` stepped at 60 Hz in `_physics_process`. Landed hits attach severity-coloured wound markers. Press F6 to play. |
| *Replay reference fights* | Replays the 7 scripted fights from the gameplay table and reports whether the GDScript port matches the Python simulation. |

Data flow: Godot never imports Python. `scripts/export_gameplay_data.py` writes
`addons/character_engine/data/gameplay_shenmue.json` (moves, frame data, pre-computed wound
assessments per hitbox bone, reference scenarios) from `character_engine.domain.gameplay`;
`tests/unit/test_gameplay_runtime_table.py` fails if the committed JSON is stale.

Headless tests: `python scripts/engine_tests.py godot` (regenerates `assets/*.glb` and the table,
runs `res://tests/ce_test_runner.gd`, writes `builds/tests/godot_report.json`; 21 checks).

## Mapping canonical → Godot

| Canonical (domain/JSON) | Godot |
|-------------------------|-------|
| Z-up, -Y forward, metres | Y-up, metres; canonical forward (−Y) becomes **+Z** (glTF convention is −Z forward, so `CEArena` uses `look_at(..., use_model_front = true)`) |
| Bone head | `Skeleton3D` bone rest translation (local) |
| Bone tail | not native; stored in glTF `extras.ce_tail` |
| `canonical_name` | bone name |
| Provenance | `extras.ce_provenance` (available via `GLTFState` if needed) |

## Troubleshooting

- **Black/blank editor, GPU errors** → renderer set to Forward+; switch to Compatibility.
- **`no .glb found`** → copy the file into `runtime/godot/` or set `glb_path` on the script.
- **Skeleton lying on its side** → exported with `--keep-z-up`; re-export without the flag.
- **Import cache issues** → delete `runtime/godot/.godot/` (git-ignored) and reopen the project.
