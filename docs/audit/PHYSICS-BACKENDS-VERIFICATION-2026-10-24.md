# Physics backends — verification on the baseline PC (2026-10-24)

Read-only check: no installs, no downloads, no project changes. Owner request (verbatim): "Que con Blender y Godot
podes usar libreias Jolt PBD XPBD FEM Bullet, asi poder simular colisiones de materiales". The owner chose
"verify first on your PC". This report does **not** recommend an engine.

## Evidence

**Godot 4.7.2** (`C:\DEV\Tools\Godot4.7\Godot_v4.7.2-stable_win64_console.exe`), headless probe script
(scratchpad `physinfo2.gd`, run in `runtime/godot` and in an empty project):
* `physics/3d/physics_engine` options (property hint): `DEFAULT, Jolt Physics, GodotPhysics3D, Dummy`.
* Value in `runtime/godot` and in an empty project: `DEFAULT` (`project.godot` has no physics-engine key).
* 33 `physics/jolt_physics_3d/*` settings exist (e.g. `simulation/velocity_steps=10`, `position_steps=2`,
  `soft_body_point_radius=0.01`, `limits/max_bodies=10240`) → the Jolt module is compiled into this build.
* `ClassDB`: `SoftBody3D` exists; `BulletPhysicsServer3D` does not (Bullet was removed from Godot 4).
* Godot 4.6 release notes (godotengine.org/releases/4.6): Jolt became the default **for new 3D projects**;
  existing projects keep their settings.

**Blender 3.6.23** (`C:\DEV\Tools\Blender\blender.exe -b --factory-startup --python-expr …`):
* `bpy.app.build_options`: `bullet=True`, `fluid=True`, `openvdb=True`.
* Solver types present: `RigidBodyWorld` (Bullet), `ClothModifier`, `SoftBodyModifier`, `CollisionModifier`,
  `FluidModifier`, `ParticleSystemModifier`, `DynamicPaintModifier`, `GeometryNodeSimulationInput` (geometry-nodes
  simulation zone).
* No XPBD or FEM solver type in `bpy.types` (none of the listed names; no built-in FEM in Blender).
* Blender's Python: `numpy 1.23.5` available, `scipy` **not** available.
* Blender 4.2: **not installed** (sent to the Recycle Bin earlier) → not verified.
* UPBGE 0.50 (optional runtime) uses Bullet for game physics (scene capsules in `runtime_upbge.py`).

**Project `.venv`** (Python 3.10.11): `numpy` and `scipy` **not** installed.

**Repository:** no physics/XPBD/PBD/FEM/Jolt/Bullet code and no mechanical-material parameters (density,
Young's modulus, Poisson ratio, compliance). The only mentions are docs (Decision 42 clarification, engagement
draft). Tissues exist as per-region thickness ESTIMATES used by the wound assessment.

**Hardware:** Intel Core i3-3120M 2.50 GHz, 2 cores / 4 threads; RAM 15.5 GB; NVIDIA GeForce GT 740M 2 GB
(driver 23.21.13.8873 = 388.73, OpenGL 3.3 in Godot) + Intel HD Graphics 4000.

## Options table

| Option | Where it runs | Verified? | Deterministic? | Fits GT 740M / i3? | Notes |
|--------|---------------|-----------|----------------|--------------------|-------|
| Jolt Physics | Godot 4.7.2 (built in) | **Yes** (option + 33 settings) | UNVERIFIED in this build (Jolt has a cross-platform determinism compile option; not confirmed for Godot's official build) | Likely for a few bodies (CPU physics) — not measured | Switching needs a project setting change; what `DEFAULT` maps to for this existing project is **UNVERIFIED** (likely GodotPhysics3D per the 4.6 notes) |
| GodotPhysics3D | Godot 4.7.2 (built in) | **Yes** (option) | UNVERIFIED | Likely — not measured | Engine's own solver |
| SoftBody3D | Godot 4.7.2 | **Yes** (class exists) | UNVERIFIED | UNVERIFIED | Works with Jolt? **UNVERIFIED** (Jolt has soft-body settings, behaviour not tested) |
| Bullet | Blender 3.6 rigid bodies; UPBGE | **Yes** (`build_options.bullet=True`) | Not guaranteed bit-identical across runs/machines (UNVERIFIED here) | Yes offline (CPU) | Not available in Godot 4 |
| Blender cloth / soft body (mass-spring) | Blender 3.6 | **Yes** (types present) | UNVERIFIED (cache makes playback repeatable once baked) | Offline, slow for dense meshes | Bakeable → fits L2 record / L3 bake |
| Geometry-nodes simulation zone | Blender 3.6 | **Yes** (`GeometryNodeSimulationInput`) | UNVERIFIED | Offline | Could host a custom XPBD-like solver in nodes (not tested) |
| XPBD / PBD | Would be own code (Python domain + GDScript port, like the combat) | **Not present** anywhere | Can be made deterministic (fixed step, fixed order) — design property, not yet implemented | Pure Python is slow for many particles; numpy available only inside Blender | No new dependency if pure Python/GDScript |
| FEM | Not built into Blender 3.6 or Godot 4.7.2 | **Not present** | Depends on implementation | Offline only on this hardware (assessment, not measured) | Would need new technology or own implementation (dossier rule) |

## Constraints that apply (not decisions)

* Dossier rule: no new technology before a complete, validated flow. Jolt and Bullet ship inside the tools
  already in use; an external FEM/XPBD library would be new technology.
* Mechanical material parameters (density, Young's modulus, Poisson ratio, damping, fracture thresholds) need
  **cited sources** or must be marked ESTIMATE/PLACEHOLDER (Decision 12).
* Where L2 physics runs (Blender / Godot / both) is the owner's open engagement question 3.
