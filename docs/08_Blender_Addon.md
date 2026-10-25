# 08 — Blender / UPBGE Addon (Character Engine panel)

The addon lives in `src/character_engine/infrastructure/blender/addon/` and is the **production
side** of the pipeline (see `docs/architecture/PRODUCTION_VS_RUNTIME.md`). It builds the canonical
208-node armature from the domain, adds tissue proxies, an IK/FK control rig, mocap retargeting,
wound probes and exports.

**Supported versions** (Decision 20): Blender **3.6 LTS is the project reference** (3.6.23 portable
in `C:\DEV\Tools\Blender`); Blender 4.x and UPBGE 0.50 (Blender 5.0.1) are also supported. The only
API difference the addon depends on is bone grouping: `build.assign_bone_layer()` uses bone
collections `DEF`/`MCH`/`CTRL` on 4.x and armature layers 0/1/2 on 3.6; every bone also carries the
custom property `ce_layer` with its role, on both.

## Install

```bash
python scripts/install_blender_addon.py            # copies to every detected addons folder
python scripts/install_blender_addon.py --zip      # builds a zip for "Install from disk"
python scripts/install_blender_addon.py --blender C:/DEV/Tools/Blender/blender.exe   # that Blender's user addons ($CE_BLENDER also works)
python scripts/install_blender_addon.py --target "C:/Tools/UPBGE/upbge-0.50-windows-x64/5.0/scripts/addons"
```

The installer writes `ce_src_path.txt` next to the addon so it can import the pure-Python domain
(`src/character_engine`). Alternatively set `CHARACTER_ENGINE_SRC=<repo>/src`.
Enable *Character Engine* in Preferences → Add-ons; the panel appears in the 3D viewport N-panel.

## Panels

| Panel | Operators | Notes |
|-------|-----------|-------|
| **Body** | Generate body | Template (`human_male_adult`, `human_female_adult`, `human_child_5y`, `human_child_10y`, `human_male_elderly_75y`; horse/dog listed but refused until data exists), stature override, pose `anatomical / tpose / apose`. Produces `CE_Skeleton` with 208 bones, `DEF` collection, provenance report in the console. |
| **Tissues** | Generate tissues | Bone proxies sized by osteometry (Trotter 1970 lengths) or fitted meshes from `assets/anatomy/meshes/<BONE>.{glb,gltf,obj,ply}`; 50 bilateral muscles with tendons from the attachment catalogue; skin envelope baked to a mesh. All weighted to the armature. |
| **Rig** | Build IK/FK rig, Set IK/FK | Adds `MCH`/`CTRL` collections: IK arms (target `CTRL-hand_ik.L/R`, auto-tuned pole), IK legs with foot roll, `arm_ik_L/R`, `leg_ik_L/R` blend properties (COPY_TRANSFORMS drivers), `CTRL-breath` driving sternum/ribs. |
| **Game rig (CE-GAME-v1)** | Build game rig, Hand pose, Weapon grip | `<armature>_GAME`: 66 game bones (DEF, UE5 Mannequin names), IK arms/legs + foot roll (`arm_ik_L/R`, `leg_ik_L/R`, pole angles refined so IK at rest is a no-op), one `MCH-anat_<BONE>` helper per canonical node. The canonical armature copies the helpers (`CE_GAME` constraints) and its bones are hidden: animate the game rig. Hand sliders per side (curl per finger, spread, thumb opposition, palm cup) pose the fingers through the domain hand model; *Hand pose* applies the library (`rest`, `relaxed`, `open`, `fist`, `point`, `grip_staff`, `grip_blade`, optional keys); *Weapon grip* picks the weapon's grip pose. Angle limits ASSUMED (RIG-GAME-001). |
| **Mocap** | Import mocap | BVH import (`bpy.ops.import_anim.bvh`) + rest-to-rest retarget through a bone map (`mixamo`, `cmu_bvh`, `rokoko`, `rigify_def`). Optional bake. |
| **Wounds** | Apply wound (click in viewport), Clear wounds | Raycast → nearest canonical bone → `assess_wound` (type, depth, width, energy). Marker sphere coloured by AIS severity, JSON report in `ce_report`. |
| **Export** | Export canonical GLB, Export scene GLB | Pure-Python exporter (skeleton contract) or Blender glTF exporter (meshes + active actions). |
| **Export → Equipment / Cinematic** | Add equipment sockets, Cinematic preset: full body, Workbench | Sockets `SOCKET-sabre_hip.L` / `SOCKET-hand_grip.R` as MCH bones (ASSUMED placement) + PLACEHOLDER sabre; floor, key/fill/rim lights, framed front camera, Workbench 1920×1080, optional render to `builds/renders/`. |
| **Runtime** | Set up UPBGE scene, Attach runtime logic, Launch game, Open Godot project | Arena + two fighters with `ce_combat.CEFighter` (UPBGE only, UI mode) and game properties; Godot shortcut opens `runtime/godot`. |

## Provenance in the viewport

Every generated object carries custom properties (`ce_canonical`, `ce_rig_id`, `ce_report`,
`ce_layer`, template/provenance strings). Proxy meshes are **proxies**: only long-bone lengths are osteometric;
diameters, muscle bellies, skin thickness and tissue depths are ESTIMATE/PLACEHOLDER
(`docs/audit/A08_OSTEOMETRY_TISSUES_TPOSE.md`). Sculpt on top; the addon never invents anatomy.

## Headless tests

```bash
python scripts/engine_tests.py blender      # background mode, 32 checks on vanilla Blender 3.6
python scripts/engine_tests.py blender --blender C:/DEV/Tools/Blender/blender.exe   # pick the Blender build
python scripts/engine_tests.py upbge        # UI mode (component registration) + blenderplayer smoke
python scripts/engine_tests.py              # blender -> upbge -> godot, each closed before the next
```

The test script is `runtime/blender/ce_addon_headless_test.py`; reports go to
`builds/tests/<engine>_addon_report.json`. Known UPBGE 0.50 limits: `bpy.ops.logic.*` and
`view3d.game_start` crash in background mode, so the UPBGE suite opens a small window and
runs the game through `blenderplayer.exe`.
