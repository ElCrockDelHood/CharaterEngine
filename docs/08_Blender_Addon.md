# 08 — Blender / UPBGE Addon (Character Engine panel)

The addon lives in `src/character_engine/infrastructure/blender/addon/` and is the **production
side** of the pipeline (see `docs/architecture/PRODUCTION_VS_RUNTIME.md`). It builds the canonical
208-node armature from the domain, adds tissue proxies, an IK/FK control rig, mocap retargeting,
wound probes and exports. It works on Blender 4.2+ and on UPBGE 0.50 (Blender 5.0.1).

## Install

```bash
python scripts/install_blender_addon.py            # copies to every detected addons folder
python scripts/install_blender_addon.py --zip      # builds a zip for "Install from disk"
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
| **Mocap** | Import mocap | BVH import (`bpy.ops.import_anim.bvh`) + rest-to-rest retarget through a bone map (`mixamo`, `cmu_bvh`, `rokoko`, `rigify_def`). Optional bake. |
| **Wounds** | Apply wound (click in viewport), Clear wounds | Raycast → nearest canonical bone → `assess_wound` (type, depth, width, energy). Marker sphere coloured by AIS severity, JSON report in `ce_report`. |
| **Export** | Export canonical GLB, Export scene GLB | Pure-Python exporter (skeleton contract) or Blender glTF exporter (meshes + active actions). |
| **Runtime** | Set up UPBGE scene, Attach runtime logic, Launch game, Open Godot project | Arena + two fighters with `ce_combat.CEFighter` (UPBGE only, UI mode) and game properties; Godot shortcut opens `runtime/godot`. |

## Provenance in the viewport

Every generated object carries custom properties (`ce_canonical`, `ce_rig_id`, `ce_report`,
template/provenance strings). Proxy meshes are **proxies**: only long-bone lengths are osteometric;
diameters, muscle bellies, skin thickness and tissue depths are ESTIMATE/PLACEHOLDER
(`docs/audit/A08_OSTEOMETRY_TISSUES_TPOSE.md`). Sculpt on top; the addon never invents anatomy.

## Headless tests

```bash
python scripts/engine_tests.py blender      # background mode, 23 checks
python scripts/engine_tests.py upbge        # UI mode (component registration) + blenderplayer smoke
python scripts/engine_tests.py              # blender -> upbge -> godot, each closed before the next
```

The test script is `runtime/blender/ce_addon_headless_test.py`; reports go to
`builds/tests/<engine>_addon_report.json`. Known UPBGE 0.50 limits: `bpy.ops.logic.*` and
`view3d.game_start` crash in background mode, so the UPBGE suite opens a small window and
runs the game through `blenderplayer.exe`.
