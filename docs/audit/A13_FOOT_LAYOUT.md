# A13 — Foot layout of the canonical skeleton

**Date:** 2026-10-29 · **Status:** FIXED (topology, layout) · proportions **PLACEHOLDER** / conventions **ESTIMATE**, source pending
**Decision:** 54 · **Script:** `scripts/rebuild_foot_layout.py` · **Report:** `A13_FOOT_LAYOUT_REPORT.json`
**Tests:** `tests/unit/test_foot_layout.py`, `tests/unit/test_extremity_spine_topology.py`, `tests/unit/test_block_dummy.py`

## Finding

In `human_adult_206.json` (both sides) the 26 foot bones were a synthetic ramp: the 7 tarsals stepped
0.0133 m in −Y and down in z, every bone was vertical (5.5 mm tarsals, 9.2 mm metatarsals, 5.5 mm phalanges),
and the metatarsals and toes stood at y = 0 directly under the ankle instead of in front of it. Every tarsal
except the talus, every metatarsal and every proximal toe phalanx was parented to `TIBIA_*`. Found by the
topology tests (P1.4, strict xfail). The block dummy's foot capsule had zero length (heel = forefoot point).

## What was changed (26 bones per side, 52 total)

| Item | Value | Provenance |
|------|-------|------------|
| Ankle anchor | `TIBIA_*` tail (talocrural joint), z = 0.039 H = 0.0702 m | existing data, PROVEN ratio (DRILLIS_CONTINI_1966) |
| Foot length heel → longest toe tip | 0.152 H = 0.2736 m | DERIVED from PROVEN ratio |
| Foot breadth | 0.055 H = 0.099 m → ray spacing = breadth / 5 = 0.0198 m, ray 3 under the ankle | breadth DERIVED; equal-lane spacing **ESTIMATE** |
| Parents | talus ← tibia; calcaneus, navicular ← talus; cuboid ← calcaneus; 3 cuneiforms ← navicular; MT1/2/3 ← medial / intermediate / lateral cuneiform; MT4/5 ← cuboid; proximal phalanx ← its metatarsal; proximal → (intermediate) → distal | PROVEN topology (atlas) |
| Rays | hallux medial with 2 phalanges, little toe lateral; left foot on +X | PROVEN topology, Decision 33 |
| Orientation | foot forward (−Y), sole on z = 0 (heel, metatarsal heads, toes) | convention (canonical frame) |
| Length split tarsal : metatarsal : phalanx | 3 : 5 : 3 (unit = foot length / 26 = 0.0105 m) | **PLACEHOLDER** — ratio of the pre-existing bone lengths 0.0055 / 0.0092 / 0.0055 m |
| Heel offset | ankle one tarsal unit (0.0316 m) in front of the heel | **ESTIMATE** |
| Arch | medial column linear from the ankle to the metatarsal heads; lateral column (calcaneus, cuboid, MT4/5) on the ground | **ESTIMATE** |

Rays 2–5 have equal length and the rays are straight and parallel: placeholder simplifications, not
anatomy. Real proportions (calcaneus length, metatarsal and toe lengths per ray, foot axis through the
second ray, arch heights) need a source and are registered in
`references/source_registry.json → data_requirements.missing` as `FOOT_SEGMENT_PROPORTIONS` (NOT_ACQUIRED).

## Before / after (examples, metres)

| Bone | Before (parent · head → tail) | After (parent · head → tail) |
|------|-------------------------------|------------------------------|
| TALUS_L | TIBIA_L · (0.0999, 0, 0.0517) → (0.0999, 0, 0.0462) | TIBIA_L · (0.0666, 0, 0.0702) → (0.0468, −0.0316, 0.0552) |
| CALCANEUS_L | TIBIA_L · (0.1032, −0.0133, 0.0499) → … 0.0443 | TALUS_L · (0.0666, 0.0316, 0) → (0.0963, −0.0316, 0) |
| METATARSAL_3_R | TIBIA_R · (−0.0733, 0, 0.0277) → (−0.0733, 0, 0.0185) | CUNEIFORM_LATERAL_R · (−0.0666, −0.0947, 0.0251) → (−0.0666, −0.1473, 0) |
| TOE_PHALANX_DISTAL_2_L (tail) | (0.0466, 0, 0.0055) | (0.0468, −0.2420, 0) |

## Effects on consumers

- **Gameplay table** (`gameplay_shenmue.json`): regenerated with its script, unchanged (moves resolve bones by name).
- **Kick** (`front_kick` strikes `METATARSAL_3_R`): the bone now lies in the forefoot, ~0.15 m in front of the
  old point; engines that use the bone position for contact reach further.
- **Game rig CE-GAME-v1**: `calf_*` now ends at the ankle, `foot_*` runs ankle → metatarsal heads, `ball_*`
  forefoot → toe tip on the ground (both were near-vertical before).
- **Mocap**: maps unchanged (foot = TALUS, toe = METATARSAL_3); the rest foot now points forward; clips baked
  against the old rest should be re-baked in Blender.
- **Block dummy**: the foot capsule (heel → MT3 tail, radius 0.03 m) is lifted so it touches z = 0 from above
  (`BlockSegment.on_ground`, ESTIMATE proxy); other segments unchanged.
- **Reaction library** (`reaction_library_d1.json`, baked in Blender by nearest canonical bone): contacts near the
  feet may change on the next bake.

## Not changed

206 bones, 208 nodes, names, every non-foot bone, `human_adult_206_backup.json` (frozen fixture; the script refuses it).
