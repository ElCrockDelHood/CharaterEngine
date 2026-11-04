# A20 — F2 extended to the long bones: BodyParts3D femur, tibia, fibula, humerus, radius, ulna (L + R)

**Date:** 2026-11-04 · **Status:** measured; tolerances PENDING (everything ESTIMATE) · **Use:** INTERNAL (Decision 62).
No mesh in the repo: OBJ files, `f2_long_bones_fit.blend` and the full results JSON are in
`C:\DEV\Assets\BodyParts3D_4.0\out\`. Numeric summary (no geometry, no anchor coordinates):
`A20_F2_LONG_BONES_FIT.json`. Femur = A19 / Decision 63, reproduced (see §Femur vs A19).

## What changed (no duplicated code)

- `domain/assets/long_bone_fit.py` (new, pure Python): one `BoneRule` per bone (anchor rules, ESTIMATE), anchor
  extraction (sphere fit / slice centroid / extreme vertex), right side by mirroring the left rule, canonical
  targets, axial extent. The femur rule is exactly the A19 one. Tests: `tests/unit/test_long_bone_fit.py`.
- `runtime/blender/ce_f2_femur_fit.py` now loops over `--bones` (default: all six) and uses the domain module;
  `scripts/f2_femur_fit.py` writes this summary. `domain/assets/registration.py` is unchanged.
- Anchor names below are **proposals**, not added to the domain landmark list.

## Anchor rules (left frame: Z-up, lateral = +X; slices are fractions of the bone height)

| Bone | Proximal (→ canonical head) | Distal (→ canonical tail) | Roll |
|------|-----------------------------|---------------------------|------|
| FEMUR | `femoral_head_centre`: sphere, proximal-medial 12 % | pair `femoral_lateral/medial_epicondyle`: ±X extremes, distal 10 % | from the pair |
| TIBIA | pair `tibial_lateral/medial_condyle_edge`: ±X extremes, proximal 10 % | pair `tibial_fibular_notch_edge` / `tibial_medial_malleolus_edge`: ±X extremes, distal 8 % | both pairs (4 anchors, chirality checked) |
| FIBULA | `fibular_head_centroid`: proximal 5 % | `lateral_malleolus_centroid`: distal 5 % | `lateral_malleolus_lateral_point`: +X extreme, distal 15 % |
| HUMERUS | `humeral_head_centre`: sphere, proximal-medial 12 % | pair `humeral_lateral/medial_epicondyle`: distal 10 % | from the pair |
| RADIUS | `radial_head_centroid`: proximal 5 % (a disc, not a sphere) | pair `radial_styloid_tip` / `radial_ulnar_notch_edge`: distal 10 % | from the pair |
| ULNA | `ulnar_proximal_centroid`: proximal 10 % (includes the olecranon) | `ulnar_head_centroid`: distal 5 % | `ulnar_radial_notch_lateral_point`: +X extreme, proximal 15 % |

**Targets.** Proximal / distal joints go to the canonical `head` / `tail` (1.80 m skeleton, read-only). A pair's
midpoint is the joint (knee and elbow centres are equidistant from the epicondyles in `biomechanics.json`,
ASSUMPTION). Lateral, medial and roll targets are **not measured** in the canonical data, so they are derived from
the asset: offset × s0, **lateral component only**, along the canonical lateral ⟂ axis. Consequence: the anchor
RMS measures how far those points sit in front of or behind the bone's lateral plane (plus slice effects). It is
**not** an independent fit error. Roll error is 0° by construction for one pair or one roll point; it is not 0°
only where two pairs disagree (tibial torsion).

## Results per bone and side

| Bone | Side | Scale s | Anchor RMS mm | Max residual mm | Length along axis m | Trotter m | Δ vs Trotter | Roll ° | Spread |
|------|------|---------|---------------|-----------------|---------------------|-----------|--------------|--------|--------|
| FEMUR | L | 1.014 | 2.31 | 2.82 | 0.4735 | 0.4983 | −4.97 % | 0.0 | 0.171 |
| FEMUR | R | 1.012 | 1.32 | 1.61 | 0.4729 | 0.4983 | −5.10 % | 0.0 | 0.171 |
| TIBIA | L | 1.187 | 3.68 | 3.86 | 0.4509 | 0.4023 | +12.08 % | 4.6 | 0.184 |
| TIBIA | R | 1.191 | 2.99 | 3.81 | 0.4528 | 0.4023 | +12.55 % | 3.0 | 0.185 |
| FIBULA | L | 1.136 | 0.22 | 0.28 | 0.4368 | 0.4038 | +8.16 % | 0.0 | **0.022** |
| FIBULA | R | 1.140 | 0.05 | 0.06 | 0.4384 | 0.4038 | +8.56 % | 0.0 | **0.020** |
| HUMERUS | L | 1.172 | 3.11 | 3.80 | 0.3628 | 0.3557 | +2.00 % | 0.0 | 0.203 |
| HUMERUS | R | 1.174 | 2.89 | 3.53 | 0.3634 | 0.3557 | +2.15 % | 0.0 | 0.204 |
| RADIUS | L | 1.079 | 3.08 | 3.81 | 0.2565 | 0.2672 | −4.01 % | 0.0 | 0.122 |
| RADIUS | R | 1.078 | 3.99 | 4.96 | 0.2559 | 0.2672 | −4.22 % | 0.0 | 0.123 |
| ULNA | L | 1.028 | 1.04 | 1.31 | 0.2624 | 0.2864 | −8.37 % | 0.0 | 0.051 |
| ULNA | R | 1.024 | 0.63 | 0.80 | 0.2613 | 0.2864 | −8.78 % | 0.0 | 0.054 |

(a) **Canonical joints:** 206 bones compared, **0 moved**; fingerprint `71c42ca0…e55d` before = after.
Rotation det = +1 for all 12. Imported bounds match the OBJ headers to ≤ 5.1e-5 mm.

**Length.** The measured distance is the fitted mesh's extent along the canonical bone axis (head → tail). It
is **not** Trotter's definition (maximum length on an osteometric board, with bone-specific landmarks; e.g. the
tibia without the intercondylar eminence, a known ambiguity of Trotter's tibia). The scale comes from the
canonical joint segment vs the asset joint distance, so the length error mostly shows the canonical skeleton's
segment proportions relative to BodyParts3D's subject (1.72 m), not a mesh defect.

## Mirror (left mirrored x → −x, winding reversed, vs the real right bone)

| Bone | Volume L cm³ | Mirror without fix | Mirror with reversed winding | Raw mean / p95 / max mm | Fitted mean / p95 / max mm |
|------|--------------|--------------------|------------------------------|--------------------------|-----------------------------|
| FEMUR | 521.4 | −521.4 | +521.4 | 1.91 / 5.46 / 15.12 | 2.26 / 5.61 / 16.23 |
| TIBIA | 496.9 | −496.9 | +496.9 | 2.03 / 5.84 / 19.55 | 5.18 / 10.80 / 21.29 |
| FIBULA | 82.1 | −82.1 | +82.1 | 1.82 / 5.24 / 10.08 | 2.44 / 5.77 / 10.39 |
| HUMERUS | 250.5 | −250.5 | +250.5 | 1.07 / 3.38 / 9.81 | 1.37 / 4.03 / 11.72 |
| RADIUS | 50.2 | −50.2 | +50.2 | 2.02 / 5.87 / 12.36 | 2.38 / 6.68 / 13.78 |
| ULNA | 41.0 | −41.0 | +41.0 | 1.63 / 5.30 / 12.06 | 2.32 / 6.12 / 11.48 |

The mirror operation is correct for all six (the sign flips back with the reversed winding). The remaining
distance is real L/R asymmetry of the BodyParts3D subject plus mesh resolution. "Fitted" adds each side's own
registration; the tibia's 5.2 mm comes from the different roll of its two sides (4.6° vs 3.0°).

## Dispersion (12 bone-sides; mirror: 6 bones) — evidence for the owner, no tolerance fixed

| Metric | min | median | max | mean | stdev | Proposed (ESTIMATE) | Met |
|--------|-----|--------|-----|------|-------|---------------------|-----|
| Anchor RMS mm | 0.05 | 2.60 | 3.99 | 2.11 | 1.39 | 2 mm | 5 / 12 |
| Max anchor residual mm | 0.06 | 3.18 | 4.96 | 2.56 | 1.66 | — | — |
| abs length error vs Trotter % | 2.00 | 6.63 | 12.55 | 6.75 | 3.54 | 1 % | 0 / 12 |
| Similarity scale | 1.012 | 1.108 | 1.191 | 1.103 | 0.072 | — | — |
| abs roll error ° | 0.0 | 0.0 | 4.58 | 0.63 | 1.52 | — | — |
| Mirror mean mm | 1.07 | 1.86 | 2.03 | 1.75 | 0.36 | 1 mm | 0 / 6 |
| Mirror p95 mm | 3.38 | 5.38 | 5.87 | 5.18 | 0.92 | — | — |
| Mirror max mm | 9.82 | 12.21 | 19.55 | 13.16 | 3.67 | — | — |

Reading for setting tolerances:
- **Anchor RMS** passes only where the derived roll anchors are close to the lateral plane (fibula, ulna, right
  femur). It depends more on the anchor rule than on the mesh. A meaningful tolerance needs at least one
  measured (not derived) third landmark per bone.
- **Length** is never within 1 %: the canonical segments and BodyParts3D differ in proportion (scale 1.01–1.19).
  Choose which length governs (canonical segment, Trotter or the asset), and whether the along-axis stretch is
  applied (not applied here, Decision 16).
- **Mirror** mean 1.1–2.0 mm, p95 3.4–5.9 mm: this is the subject's own asymmetry. 1 mm compared with a real
  right bone is not reachable; mirror correctness is already proven exactly by the volume sign.

## Findings (not fixed; canonical data untouched)

1. **Canonical FIBULA_L/R** spans exactly the tibia's knee → ankle segment, 0.0333 m **in front of** the tibia (−Y)
   and on the same x. Anatomically the fibula is lateral and slightly posterior, and its head lies below the knee
   joint. This looks like the forearm layout before A11 (Decision 36). The fibula's scale (1.14) and length (+8 %)
   come from the segment length and the head at knee level, not from the antero-posterior offset: a per-bone
   similarity fit cannot see a pure translation. Correction: the lateral offset was fixed in A21 (Decision 65);
   re-measured, the per-bone metrics are identical, as expected.
2. **Fibula roll** is weak (spread ratio 0.02, the roll point only ~1 cm off the axis). Its roll should come from
   the tibia (both bones together), not from the fibula alone.
3. **Tibia:** the two ±X pairs are 3–4.6° apart (tibial torsion). One roll per bone cannot satisfy both ends.
4. **Ulna proximal centroid** includes the olecranon, so it sits above the elbow centre (ESTIMATE). A trochlear-notch
   fit would be better.
5. The radius / ulna canonical segments are equal (0.2409 m, same z); the real ulna is longer proximally.

No bone failed to fit.

## Femur vs A19

| Quantity | A19 | Now | abs diff |
|----------|-----|-----|----------|
| Left RMS mm | 2.305424 | 2.305424 | 1.0e-7 |
| Left scale | 1.0136092 | 1.0136092 | 2.7e-8 |
| Right RMS mm | 1.324815 | 1.324461 | 3.5e-4 |
| Left length m | 0.47354657 | 0.47354654 | 2.1e-8 |
| Mirror raw mean mm | 1.906811 | 1.906811 | 0 |

The tiny differences come from single precision (`mathutils.Vector`, A19) vs double precision (domain module,
now). For the right side there is also a change of method: A19 mirrored the left targets, while now the right
targets are derived from the right bone's own anchors.

## Reproduce

```bash
python scripts/f2_femur_fit.py --bp3d C:/DEV/Assets/BodyParts3D_4.0/extracted/partof_BP3D_4.0_obj_99 --out C:/DEV/Assets/BodyParts3D_4.0/out
```

Blender 3.6.23 (`C:/DEV/Tools/Blender/blender.exe` or `CE_BLENDER`); `--bones FEMUR` for the femur alone.
Deterministic.
