# A23 proposal — canonical hip joint centre spacing (NOT applied)

**Status:** variant A APPLIED (Decision 67, `docs/audit/A23_HIP_CENTRES.md`); this file keeps the proposal as approved · **Date:** 2026-11-04 · **Owner's choice:** "Wu +
BodyParts3D as ESTIMATE" (Harrington regression not used) · Related: A22 / Decision 66,
`PELVIS_LANDMARKS_PROPOSAL.md`, ANSUR II download (`C:\DEV\Assets\ANSUR_II\REGISTRO_DESCARGA.md`).

## Finding

The canonical hip joint centres (`FEMUR_L/R.head`, x = ±0.0666 m) are **133.2 mm** apart. In BodyParts3D, with
the femoral head sphere centres scaled into the canonical frame (×1.032, A22), they are **180.1 mm** apart.

## Proposed value (ESTIMATE)

| Quantity | Value | Provenance |
|----------|-------|------------|
| Ratio hip-centre spacing / inter-ASIS width | **0.674** (174.6 / 259.1 mm, raw BP3D) | ESTIMATE: one subject (BP3D, internal use, Decision 62); landmarks by the A22 rules |
| Inter-ASIS width at the canonical scale | 267.4 mm | ESTIMATE: BP3D × 1.032 |
| **Proposed hip-centre spacing** | **180.1 mm** → `FEMUR_L/R.head` x = **±0.0901 m** (now ±0.0666) | ESTIMATE |
| Uncertainty (1 SD) | ±10 mm (170–190 mm) | ANSUR II bicristal CV 5.7 % (16.1 / 280.6) applied to the ratio's base |
| Uncertainty (p5–p95) | 163–196 mm | ANSUR II bicristal p5 / p95 (254 / 306 mm), scaled the same way |
| Method error | sphere RMS 0.68 mm; ASIS extreme-vertex rule ≈ ±5 mm (mesh resolution) → ratio ±2 % | measured in A19 / A22 |

**Wu et al. 2002 (ISB) as the contrast.** It defines the pelvic frame: both ASIS and both PSIS, with the origin
at the hip joint centre. It gives **no** spacing value, so it is used here to define the landmarks and to check the
**geometry**, not as a numeric source. Checks under that frame:

1. The hip centres lie medial to the ASIS on both sides (BP3D: 43 mm each side).
2. They lie posterior and inferior to the ASIS line.
3. The pelvis is left/right symmetric (A22 mirror COXAL: mean 2.1 mm).

The current canonical 133 mm passes 2 and 3 but gives a ratio of 0.50 to the inter-ASIS width, against 0.67 in BP3D.

## Plausibility control with ANSUR II (men 1.75–1.85 m, n = 1814; public release, US Army)

Expected order, from inside to outside: hip-centre spacing < bone inter-ASIS < bicristal **on skin** < hip
breadth on skin.

| Measure | Value | Order |
|---------|-------|-------|
| Hip-centre spacing (proposed) | 180 mm | 1 |
| Inter-ASIS, bone (BP3D scaled) | 267 mm | 2 |
| Bicristal breadth, skin (ANSUR II) | 280.6 ± 16.1 mm | 3 ✓ |
| Hip breadth, skin (ANSUR II / canonical Drillis & Contini 0.191 H) | 351.2 ± 23.2 / 343.8 mm | 4 ✓ |

ANSUR II cannot give the hip centres by itself: it measures on the skin and has no inter-ASIS or joint-centre
dimension.

## Variants (owner chooses)

| Variant | What moves | Effect |
|---------|-----------|--------|
| **A (recommended)** | Only `FEMUR_L/R.head` x: ±0.0666 → ±0.0901 | The femur becomes oblique (knee stays at ±0.0666): 3.2° from vertical. This matches the femur's real inward slope, which BP3D also shows. Femur segment 0.41780 → 0.41845 m (+0.65 mm, +0.16 %). Knees, shanks, feet and stance width unchanged |
| B | Hips as A and knees to BP3D ±0.0746 (×1.032) | Tibia oblique or the whole shank shifted; feet move; the knee spacing is also only ESTIMATE |
| C | Whole leg chain shifted 23.5 mm laterally | Femur stays vertical; stance 47 mm wider; feet move. Not anatomical (no femoral obliquity) |

## What would change if A is applied (to be measured before committing, as in A21)

| Area | Expected change | How it is checked |
|------|-----------------|-------------------|
| Canonical data | 4 numbers (`FEMUR_L/R.head.x`) in `human_adult_206.json` | new script `fix_hip_centres.py` (deterministic, idempotent, refuses the backup); `HIP_JOINT_CENTRE_SPACING` registered in `source_registry.json` as ESTIMATE / pending source |
| Fingerprints | `human_adult_206.json`, `source_registry.json` | `tests/anatomy/test_contract_fingerprint.py` with the new Decision |
| Derived | `builds/exports/skeleton_serialized.json`; `runtime/godot/human_adult_206.glb` (`export_gltf.py`) | regenerated, diff limited to the femur heads |
| Game rig CE-GAME-v1 | `thigh_l/r` start at the femur head (3.2° tilt); `pelvis` / `thigh_twist` positions; IK rest error | `tests/unit/test_game_rig.py`; Blender addon 40/40 (IK rest deviation reported) |
| Game GLBs | `human_game_v1_tpose.glb`, `human_game_v1_body.glb` (body spec SHA changes), `souls_clips.glb` (thigh directions at every key) | re-bake with `bake_game_body.py` / `bake_souls_clips.py`; Godot parity tests ("bone directions at every key equal Python") |
| Block dummy | `pelvis` segment spans the femur heads (47 mm wider); `thigh.*` capsules tilt 3.2° | `tests/unit/test_block_dummy.py`; collision tests |
| Leg IK / foot lock | Hip input moves 23.5 mm laterally; femur +0.65 mm | `tests/unit/test_foot_lock.py`, `test_stance_scale.py` |
| Kicks / gameplay | Kick reach from the hip may change by a few mm; strike lever arms unchanged (they do not read the hip x) | `export_gameplay_data.py --check`; Godot replays identical to Python. **If the gameplay table or any replay changes, stop and report before committing** |
| Tests with hard-coded femur coordinates | Only synthetic constants (`test_long_bone_fit.py`) and `test_fibula_layout.py` (tibia, unchanged): no edit expected | full `scripts/test.py` |
| Audits | A20 (femur fit targets) and A22 (global registration) re-measured; the hip residual (26 mm) should drop | `scripts/f2_femur_fit.py` and `--regions` |

## Not proposed here

The knee spacing (variant B), a sourced hip-centre regression (Harrington, set aside by the owner), the posterior
/ inferior offset of the hip centre relative to the ASIS (only checked, not changed), and the soft-tissue values
(ANSUR buttock circumference: skin layer, other thread).
