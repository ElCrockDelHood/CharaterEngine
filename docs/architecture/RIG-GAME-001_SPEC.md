# RIG-GAME-001 — Game rig, hands and face (SPECIFICATION, awaiting owner approval)

**Date:** 2026-10-25 · **Status:** APPROVED by the owner (Decision 51); steps 1–3 implemented, steps 4–6 pending ·
**Context:** the owner chose the Souls-like as the
first genre and asked for an industry-standard rig, sized for the GT 740M, with emphasis on hands and face.

## 1. Problem

The runtime GLB carries all 208 canonical nodes (54 hand bones incl. carpals, 52 foot bones, 29 skull bones incl.
ossicles, 26 vertebrae, 25 rib/sternum bones). That is correct anatomy, but as a *game* skeleton it is:

- non-standard: no mocap source, animation pack or DCC tool expects carpals, ossicles or 26 vertebrae, so every
  retarget needs spline/IK guesswork (`domain/animation/bone_map.py` already maps only 52 bones);
- heavy for authoring and runtime on the target PC (CPU pose updates, viewport, skinning weights spread over
  bones that never move independently);
- missing what games need: twist bones, an explicit face rig (eyes, blendshapes) and hand pose controls.

## 2. Proposal: two levels, the canonical skeleton stays the truth

| Level | Skeleton | Used by | Changes |
|-------|----------|---------|---------|
| L0 canonical | `human_adult_206.json` (208 nodes) | domain, trauma, simulation (Blender offline), production reference | **none** (invariant 4) |
| L1 game | `CE-GAME-v1`, ~66 deform bones (§3) | Godot, UPBGE, animation clips, mocap | new, **derived** from L0 |

- Every L1 bone is placed at canonical joint points (head or tail of an L0 bone, or the midpoint of the two
  femoral heads for the hip), so positions and proportions are **DERIVED** from canonical data and follow pose and
  stature retargeting. No new numbers are invented. Vertebra heads are their superior end, so a spine segment
  pivots at the tail of its lowest vertebra.
- Twist bones sit at fixed fractions of their parent segment (0.5 upper arm and thigh, 0.75 forearm) and the eyes
  at the orbit centre between LACRIMAL and ZYGOMATIC (no canonical eyeball): ASSUMED rig placements.
- `covers` assigns each of the 208 canonical nodes to exactly one game bone (validated).
- Gameplay keeps anatomical meaning: hitboxes become attachments on L1 bones that **carry the canonical bone id**
  (e.g. hitbox `RIB_08_L` rides on `spine_03`), so trauma still receives canonical bones. Fight parity with Python
  must stay bit-identical.
- Production exports both GLBs: `human_adult_206.glb` (anatomy / simulation) and `human_game_v1.glb` (runtime).

## 3. CE-GAME-v1 bone list (deform)

Naming follows the UE5 Mannequin convention (`pelvis`, `spine_01`, `upperarm_l`…), the most common target of
animation packs and retargeters; Quaternius UAL (already mapped) uses the same style.

| Group | Bones | Count |
|-------|-------|-------|
| Core | root, pelvis, spine_01, spine_02, spine_03, neck_01, head | 7 |
| Arms (×2) | clavicle, upperarm, upperarm_twist_01, lowerarm, lowerarm_twist_01, hand | 12 |
| Legs (×2) | thigh, thigh_twist_01, calf, foot, ball | 10 |
| Hands (×2) | thumb_01–03, index_01–03, middle_01–03, ring_01–03, pinky_01–03, ring_metacarpal, pinky_metacarpal | 34 |
| Face | jaw, eye_l, eye_r | 3 |
| **Total deform** | | **66** |

Non-deform sockets: `hand_grip_r`, `hand_grip_l` (from `SOCKET-hand_grip.R`, Decision 48), `weapon_back`, `hip_l`.
UE5 Mannequin has ~89 bones; we drop extra twists and the index/middle metacarpals (rigid in the palm) to save cost.

## 4. Hands (priority)

- 3 bones per finger, thumb from its metacarpal; ring/pinky metacarpals for palm cupping (cheap, visible in fists).
- Animator controls (Blender): per-finger FK, per-finger **curl** and **spread** attributes, hand-wide **fist** and
  **cup** sliders, thumb opposition.
- **Hand pose library** as data (domain): `relaxed`, `open`, `fist`, `point`, `grip_staff`, `grip_blade`. Weapon grips
  are tied to `Weapon.grip_bone` / `hand_grip` socket, so a held weapon picks its pose.
- Godot: poses applied by a light `SkeletonModifier3D` (blend between pose rotations, no IK per finger at runtime).
- Joint limits per finger taken from the canonical joint data where present, otherwise marked ASSUMED.

## 5. Face (priority)

- Bones: `jaw` (canonical MANDIBLE head = TMJ), `eye_l`, `eye_r` (look-at).
- Expressions: **FACS-based blendshapes using the ARKit 52 names** (industry standard; works with phone face capture
  and most tools). Blender cinematics use all 52; the in-game set is a subset (blink, brows, jaw/visemes, ~15–20)
  chosen **after a hardware test** of morph targets in Godot 4.7 Compatibility on the GT 740M.
- Blender: face control panel (sliders / 2D controls) driving shape keys, like Rigify face panels.
- **Dependency:** blendshapes need a head mesh with face topology (draft rows ANATOMY-MESH / TREAT-HEAD-FACE). Until
  then only the bones and the shape-name contract are built; shape geometry is PENDING.

## 6. Steps (each one: spec → code → tests → owner OK)

1. **DONE** — `domain/rigging/game_rig.py`, `export/gltf_game.py`, `scripts/export_gltf.py --skeleton game`,
   `tests/unit/test_game_rig.py`; GLB imports with 66 bones in Blender 3.6.23 and Godot 4.7.2. Domain: `CE-GAME-v1` definition + L0→L1 mapping + validator + tests; glTF export `human_game_v1.glb`.
2. **DONE** — `CECharacter` defaults to `human_game_v1_tpose.glb` and resolves canonical names through the GLB's
   `canonical_to_game` / `canonical_points`; validator knows the CE-GAME-v1 contract; runner checks prove canonical
   positions (0 m error), marker on `spine_03`, weapon on `hand_r`, arena fight identical. Breathing modifier is a
   no-op on the game rig (no STERNUM/RIB bones) until chest breathing is redone (step 3 or face/shape work).
   Godot: `CECharacter` loads the game GLB; hitboxes and grip remapped; combat parity unchanged; weapon follows `hand_r`.
3. **DONE** — `domain/rigging/hand_poses.py` (controls, library `rest/relaxed/open/fist/point/grip_staff/grip_blade`,
   weapon → grip pose, hand FK; limits ASSUMED), `GAME_CONTROL_RIG` (IK arms/legs + foot roll), addon
   `game_rig.py` (*Build game rig*, hand sliders, *Hand pose*, *Weapon grip*); canonical armature driven through
   `MCH-anat_*` helpers (COPY_TRANSFORMS), its bones hidden (the object stays evaluated). Blender 3.6.23 checks:
   IK rest 0.0003 mm, hand pose = Python FK (0.0009 mm), canonical fingers on game bones (0.0001 mm).
   Blender: control rig over L1 DEF (body IK/FK as today) + hand controls + pose library; L0 kept as a hidden
   driven layer for simulation and trauma.
4. Hardware test: morph targets / bone count on the GT 740M (compatibility test before adopting).
5. Face: jaw + eyes now; ARKit-named shapes when the head mesh exists.
6. Bone maps (Mixamo, quaternius_ual) retargeted to L1 (near 1:1).

## 7. Owner decisions requested

1. Two levels (L0 canonical untouched, L1 game skeleton for runtimes) — yes / no.
2. Naming: UE5 Mannequin style (recommended) / Mixamo / Rigify.
3. Face: jaw + eyes + ARKit-52 shape names; game subset after the hardware test — yes / no.
4. Hands: 3 bones per finger + ring/pinky metacarpals, curl/spread + pose library with weapon grips — yes / no.
5. Start with step 1 only — yes / no.

## 8. Risks

- Hitbox remap could change fight results → parity test with the current JSON is the gate.
- Blendshape cost on the GT 740M is unmeasured → step 4 before any in-game face shapes.
- Without a face/hand mesh, skinning quality cannot be judged → block-dummy and placeholder meshes only.
