# Quality tolerances (Decision 89)

**Status:** first batch IN FORCE (owner, 2026-11-25, "me gusta la idea, sigamos adelante con lo del primer lote
vigente"); every other row is a TARGET, not in force · **Date:** 2026-11-25 · All values **ESTIMATE**: set from what the
repository already measured and production judgement, not from a published norm · Code:
`src/character_engine/domain/quality/tolerances.py` · Report: `python scripts/quality_report.py` · Tests:
`tests/unit/test_quality_tolerances.py`

## Axes

- **Profile:** `game` (real time, Godot) or `cinema` (offline, Blender). One character can ship in both; each has its
  own bar. Character Engine is a general engine for film and games, so no threshold is tied to one title.
- **Quality level:** `Q0` is what runs today on the GT 740M with Blender 3.6 and Godot `gl_compatibility`; Q1 and Q2
  open with better hardware. "Q" avoids a clash with the engagement layers L1–L3 of Decision 44.
- **Canonical anatomy has one bar** for every profile and level (`all`). Profile and level only change derived output:
  animation, skinning and performance.

## In force (first batch)

| ID | Name | Profile | Level | Threshold | Status | Measured by |
|----|------|---------|-------|-----------|--------|-------------|
| AN-1 | Per-bone fit to the reference, anchor RMS (acceptance) | all | all | ≤ 4 mm per bone and side | ESTIMATE, in force | A20 long-bone fit (`scripts/f2_femur_fit.py`) |
| AN-3 | Left/right mirror symmetry | all | all | mean ≤ 2.5 mm and p95 ≤ 6 mm per pair | ESTIMATE, in force | A22 region fit, 83 mirror pairs |
| MO-2 | Sole height on stance frames, median per clip | game | all | \|h\| ≤ 1 cm | ESTIMATE, in force | batch retarget with leg grounding (`domain/animation/leg_quality.py`) |
| MO-2 | same | cinema | all | \|h\| ≤ 0.3 cm | ESTIMATE, in force | same |
| MO-3 | Knee direction against the mocap source, per clip | game | all | median ≤ 5°, p90 ≤ 10° | ESTIMATE, in force | same |
| MO-3 | same | cinema | all | median ≤ 3°, p90 ≤ 6° | ESTIMATE, in force | same |
| RG-1 | Game rig against canonical rig in the rest pose | all | all | ≤ 0.1 mm | ESTIMATE, in force | Blender headless check "game rig: build" |
| RG-6 | ARKit face shapes | game | all | ≤ 20 | ESTIMATE, in force | face contract (`domain/rigging/face.py`); head mesh when one exists |
| RG-6 | same | cinema | all | 52 | ESTIMATE, in force | same |
| PF-1 | Frame time, 2-character arena | game | Q0 | mean ≤ 16.7 ms and p95 ≤ 20 ms | ESTIMATE, in force | `scripts/godot_perf.py`, scenario `souls_arena_2_bodies`, GT 740M |
| PF-4 | Workbench test render 1920×1080 | cinema | Q0 | ≤ 30 s | ESTIMATE, in force | Blender headless check "CINE-GR-001 (a)+(d)" |

### Definitions

- **MO-2:** stance is taken from the *source*: a source foot is in contact when its lowest point (ankle, ball, toe tip)
  is within 3 cm of its rest height. On those frames the sole height *h* is the lowest target foot point (heel, ball,
  toe tip) minus its rest height. The clip value is the median *h* over the stance frames of both feet; the p95 of
  \|h\| is reported beside it. Excluded: jumps (for now: pointed toes in the air, Decision 85) and swimming (no ground).
- **MO-3 (knee hinge axis, amendment 2, owner 2026-11-25):** per leg and frame, the hinge axis is the normal of the
  thigh–shin plane, (knee − hip) × (ankle − knee), in the source and in the target, and the angle between the two axes.
  Only frames where the source knee is bent at least **15°** count, because a straight leg has no plane. A target leg that stays
  straight against a bent source counts as 90°. No rest pose is involved. The target knee is the middle of the `FEMUR` tail –
  `TIBIA` head gap.
  - **Choosing 15°:** rest bends are 3.5° (canonical) and 4.2° (source), and the source bend's 10th percentile is 15°.
  - **Sensitivity (pass in game / cinema, leg frames left out of 8536):** 10° gives 80 / 80 (5 %), 15° gives 80 / 80 (10 %),
    20° gives 80 / 80 (18 %). At 25°, 10 clips lose every frame.
  - **Earlier definitions:** the plain knee offset (first run), then the offset relative to rest (amendment 1).
- **MO-2 and MO-3** count one value per clip, from the root-motion variant when the library has one; the two variants gave
  identical values in the 2026-11-25 run.
- **RG-6:** the contract counts are judged now. The count on a head mesh is not measured, because no head mesh with ARKit
  shapes exists yet. That test is skipped with this reason.
- **PF-1:** judged only on Q0 hardware (the GT 740M); a report from other hardware gives NOT_MEASURED.

## Results on 2026-11-25 (`main` + this change)

| ID | Profile | Result | Measured |
|----|---------|--------|----------|
| AN-1 | all | **PASS** | worst RADIUS_R 3.99 mm (12 bone sides), re-fitted on today's canonical skeleton |
| AN-3 | all | **FAIL** | 82 of 83 pairs pass; INFERIOR_NASAL_CONCHA mean 2.43 mm, **p95 8.15 mm** |
| MO-2 | game | **FAIL** | 7 of 79 clips over 1 cm, worst Sword_Heavy_Combo +1.79 cm (ClimbUp +1.61, LayToIdle −1.76, Slide ×3, Hit_Knockback) |
| MO-2 | cinema | **FAIL** | 12 of 79 clips over 0.3 cm (adds Crouch_Idle −0.70, Jog −0.46, Sprint −0.31, Death01, Zombie_Walk) |
| MO-3 | game | **FAIL** | hinge axis: 80 of 84 clips pass; the 4 failures are jumps: Jump_Land p90 78.0°, NinjaJump_Land p90 49.7°, NinjaJump_Idle median 6.8°, NinjaJump_Start median 6.7°; Idle 2.1°, Walk 2.1°, Crouch_Idle 2.0° |
| MO-3 | cinema | **FAIL** | hinge axis: 80 of 84 pass, the same 4 jumps fail |
| RG-1 | all | **PASS** | 0.0553 mm (IK rest 0.0019 mm) |
| RG-6 | game / cinema | **PASS (contract)** | 20 / 52 names; the asset part is not measurable yet |
| PF-1 | game, Q0 | **PASS** | GT 740M: mean 11.08 ms, p95 13.71 ms (2026-10-30: 2.93 / 4.18 ms) |
| PF-4 | cinema, Q0 | **PASS** | 3.46 s |

**Reading:**

- **MO-3, plain definition (first run):** 33 of 86 clips failed in game and 61 in cinema; `A_TPose` read 8.7° with no motion,
  because in rest the canonical knee sits 13.5 mm *sideways* of its line and the source's 15 mm *forward*.
- **MO-3, relative to rest (amendment 1):** worse, 73 / 84 and 82 / 84 fail (Idle 2.8° → 6.4°, Walk 3.9° → 7.3°). The canonical rest
  offset is a straight-leg artefact of the bone layout: it does not stay with the thigh when the knee bends, so subtracting it
  adds about 11 mm sideways in Idle. On almost straight source legs the subtraction creates a 14 mm offset where there was
  1 mm, which passes the 1 cm gate and reads about 157° (Sprint, Roll).
- **MO-3, hinge axis (amendment 2, in force):** 80 of 84 clips pass in both profiles (game: plain 53 / 86, amendment 1 11 / 84).
  Only jumps fail. No limit was changed.
- **PF-1:** the arena frame time grew from 2.9 to 11.1 ms since October. It still passes, with a smaller margin.

## Targets (not in force)

| ID | Name | Threshold (game / cinema) | In force when |
|----|------|---------------------------|---------------|
| AN-1 target | Per-bone fit | ≤ 2 mm | measured anchors closed (canonical epicondyles) |
| AN-2 | Long-bone length against Trotter | ≤ 5 % | measured with Trotter's definition (maximum length) |
| AN-4 | Global joint centres against the reference | ≤ 20 mm per centre | re-measured after A23 / A24 |
| AN-5 | Canonical data without unauthorised changes | exact equality | already in force (Decision 52, fingerprints) |
| AN-6 | Provenance of every value | 100 % with a state | already in force (source registry tests) |
| MO-1 | Foot sliding in stance | ≤ 2 cm / ≤ 0.5 cm per stance | the metric enters the retarget report |
| MO-4 | Realistic speeds and distances | within the cited source | sources acquired |
| MO-5 | Strike contact timing | ≤ 1 frame at 60 Hz / 24 fps | — |
| RG-2 | Grip error, weapon against hand socket | ≤ 5 mm, 5° / ≤ 2 mm, 2° | measured in the addon |
| RG-3 | Body and equipment interpenetration | ≤ 5 mm / 0 on camera | a real mesh exists |
| RG-4 | Skin stretch in extreme poses | 0.7–1.3 / 0.8–1.2 of rest | a base mesh exists |
| RG-5 | Weights per vertex | ≤ 4 / ≤ 8 influences, sum 1 ± 1e-4 | the first weighted mesh |
| PF-2 | Frame time with 8 characters | mean ≤ 16.7 ms with real meshes (Q0) | real meshes |
| PF-3 | Blender viewport with the character | ≥ 15 fps (Q0) | measured |
| DT-1 | Same input, same output | SHA-256 identical in 3 runs | — |
| DT-2 | Every baked output records parameters, seed and SHA-256 | 100 % | in force by Decision 45 |

## How to re-measure

```bash
python scripts/retarget_batch.py --out-dir builds/animations/quality --no-export --quiet     # MO-2, MO-3 (Blender, UAL)
python scripts/engine_tests.py blender godot --keep-going                                    # RG-1, PF-4
python scripts/godot_perf.py                                                                 # PF-1 (GT 740M, opens a window)
python scripts/f2_femur_fit.py --bp3d <BodyParts3D OBJ folder> --out <folder outside the repo> --no-summary   # AN-1
python scripts/quality_report.py --a20 <that folder>/f2_long_bones_fit_results.json        # all verdicts
```

A known failure is a strict `xfail` in the tests, with its measured value as the reason. When it is fixed, the test
turns red and asks for the update. Limits are never relaxed to make a test pass.
