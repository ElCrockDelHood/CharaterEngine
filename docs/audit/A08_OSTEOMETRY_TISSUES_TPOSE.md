# A08 — Osteometry, Tissue Layers, T-Pose, Character Templates, Rig, Mocap Maps and Gameplay

**Date:** 2026-09-29 · **Status:** IMPLEMENTED (data status PARTIAL) · **Scope:** core domain,
Blender addon, UPBGE runtime, Godot runtime · **Supersedes:** nothing (extends A07)

This audit documents what was added on top of the 1.80 m canonical skeleton (A07) to reach a
*complete production/runtime loop*: osteometric bone extents, a T-pose rest, tissue layers for
wounds, character templates (sex/age/species), an IK/FK rig definition, mocap bone maps, a
Shenmue-style combat model, a Blender addon, a UPBGE component and a Godot addon. Every number
introduced carries a provenance state; nothing was upgraded to PROVEN without a verified source.

---

## 1. Data added

| File | Content | Provenance | Source |
|------|---------|------------|--------|
| `data/anatomy/references/osteometry.json` v1.1.0 | Long-bone maximum-length regressions; male white (Trotter 1970); female white + female Black (Trotter & Gleser 1952:495); derived lengths at 1.80 m (male) and 1.65 m (female white) | All six long bones **PROVEN** per acquired series; derived lengths **DERIVED** | Trotter (1970), Trotter & Gleser (1952) |
| same, `shaft_diameters` | Midshaft diameters for proxy bone meshes | **ESTIMATE** (LOW) | none — to be replaced by Terry / Hamann-Todd tables |
| `domain/tissue/layers.py` | Thickness per layer (skin, fat, muscle, tendon, bone, viscera) per body region | **ESTIMATE** | order-of-magnitude values; flagged for replacement with ultrasound / CT literature |
| `domain/tissue/muscles.py` | 50 bilateral muscle origin/insertion pairs on canonical bones (attachment *topology*, no geometry) | **PROVEN** (attachment bones are textbook anatomy) / geometry **PLACEHOLDER** | Gray's / Netter (topology only) |
| `domain/trauma/wound.py` | Wound types, AIS-like severity 1–6, region lethality caps, `REFERENCE_BLUNT_ENERGY_J = 400` | **ESTIMATE** (gameplay-oriented scoring, not clinical) | AIS scale structure; energies are tuning constants |
| `domain/character/templates.py` | Templates: male 1.80 (USER_INPUT), female 1.65 (ESTIMATE), child 5 y 1.10 / 10 y 1.38 (ESTIMATE, proportions PLACEHOLDER), elderly 75 y (DERIVED, Trotter & Gleser 1951 −0.06 cm/yr after 30), horse / dog (UNKNOWN, `available=False`) | as listed | WHO growth medians (children), Trotter & Gleser 1951 (ageing) |

Important boundary: Trotter coefficients describe **maximum bone length on an osteometric
board**, which exceeds the joint-centre distance stored in `human_adult_206.json`. They therefore
drive **bone mesh extents** in the Blender addon, never joint positions (Decision 16).

## 2. Domain modules (pure Python, no `bpy`)

| Package | Purpose | Tests |
|---------|---------|-------|
| `domain/anatomy/osteometry` | `load_osteometry`, `bone_length_from_stature(bone, stature, population)` | `tests/unit/test_osteometry.py` |
| `domain/anatomy/pose` | `apply_tpose` (rigid subtree rotation about the shoulder, palms down), `apply_pose(bones, "anatomical|tpose|apose")` | `tests/unit/test_tpose_and_templates.py` |
| `domain/anatomy/proportions/stature_retarget.py` | Piecewise-linear Drillis & Contini retarget (moved out of the CLI script) | `tests/unit/test_tpose_and_templates.py` |
| `domain/tissue`, `domain/trauma` | Layers, regions, muscle catalogue, wound assessment, blunt-impact conversion | `tests/unit/test_tissue_trauma.py` |
| `domain/character` | Templates + `build_character_bones(params)` (stature retarget + pose) | `tests/unit/test_tpose_and_templates.py` |
| `domain/rigging` | `HUMANOID_RIG` (IK arm/leg chains, spline spine/neck/fingers, breath control, FK/IK properties), `validate_rig_against_bones` | `tests/unit/test_rig_animation_combat.py` |
| `domain/animation` | Bone maps: Mixamo, CMU BVH, Rokoko, Rigify DEF → canonical | same |
| `domain/gameplay` | `ShenmueCombat` (60 Hz frame-data state machine), `GAMEPLAY_STYLES`, `runtime_table.gameplay_runtime_table()` (JSON for Godot) | same + `tests/unit/test_gameplay_runtime_table.py` |

`export/gltf.py` gained `--pose {anatomical,tpose,apose} --template <id> --stature <m>`.

## 3. Production side — Blender addon (`src/character_engine/infrastructure/blender/addon/`)

Panel *Character Engine* (N-panel, 3D viewport) with: Body (template, stature, pose → 208-bone
armature), Tissues (osteometric bone proxies or fitted meshes from `assets/anatomy/meshes/`,
muscle bellies + tendons from the catalogue, baked skin envelope), Rig (DEF/MCH/CTRL collections,
IK with auto-tuned pole angle, FK/IK sliders, foot roll, breathing control), Mocap (BVH import +
rest-to-rest retarget through a bone map), Wounds (raycast on the body → wound marker with the
domain assessment), Export (canonical GLB via the pure exporter, or full scene GLB), Runtime
(UPBGE scene set-up / component attach / launch, Godot project shortcut).

Mesh honesty: proxy bone meshes are labelled proxies; only the *length* is osteometric. Real bone
meshes must be supplied as assets with their own provenance — the addon fits them, it does not
sculpt anatomy.

## 4. Runtime side

* **UPBGE** — `runtime/upbge/components/ce_combat.py` embeds the Python combat domain (component
  `CEFighter` or logic-brick entry `run`). UPBGE 0.50 cannot register components in background
  mode (access violation) → UI-mode test run + `blenderplayer.exe` autoplay smoke.
* **Godot 4.7** — `runtime/godot/addons/character_engine/`: dock (`plugin.gd`, `ce_dock.gd`),
  `CECharacter` (GLB loader, stature scaling, wound markers), `CEBreathing`
  (`SkeletonModifier3D`), `CEShenmueCombat` (GDScript port), `CEFighterController`, `CEArena`.
  Godot consumes `data/gameplay_shenmue.json` generated by `scripts/export_gameplay_data.py`; the
  7 reference fights in that table are replayed by the Godot suite and must match the Python
  results exactly (they do).

## 5. Evidence (2026-09-29)

| Suite | Command | Result |
|-------|---------|--------|
| pytest | `python scripts/test.py` | **627 passed** |
| lint | `python scripts/lint.py` | ruff clean, architecture guard OK |
| Blender 5.0.1 (background) | `python scripts/engine_tests.py blender` | **23 passed** (`builds/tests/blender_addon_report.json`) |
| UPBGE 0.50 (UI mode + blenderplayer) | `python scripts/engine_tests.py upbge` | **23 passed**, blenderplayer autoplay 180 frames, 7 hits |
| Godot 4.7.2 (headless) | `python scripts/engine_tests.py godot` | **21 passed** (`builds/tests/godot_report.json`) |

## 6. Open items

1. Female / child / non-white osteometric regressions: UNKNOWN until sourced.
2. Tissue thicknesses and lethality scores are ESTIMATE; a clinical source pass is required
   before any medical claim.
3. Real bone / muscle / skin meshes are not in the repository (proxies only); the asset-fitting
   path (`assets/anatomy/meshes/<BONE>.glb`) is implemented and tested with proxies.
4. Animals: templates exist but are `available=False` (no canonical equine/canine skeleton).
5. Left/right labelling vs. −Y forward is geometrically mirrored (Decision 17, OPEN).
6. Gameplay styles `souls_like` and `beat_em_up` are declared without moves (planned).
