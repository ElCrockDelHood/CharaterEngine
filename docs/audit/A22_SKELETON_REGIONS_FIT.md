# A22 — F2 by regions: the whole BodyParts3D skeleton against the canonical one

**Date:** 2026-11-04 · **Status:** measured; tolerances PENDING (everything ESTIMATE) · **Use:** INTERNAL
(Decision 62). No mesh in the repo: OBJ files, `f2_regions_fit.blend` (the registered skeleton) and the full
results are in `C:\DEV\Assets\BodyParts3D_4.0\out\`. Numeric summary (no geometry): `A22_SKELETON_REGIONS_FIT.json`.

## Method (`domain/assets/skeleton_regions.py`, `runtime/blender/ce_f2_regions_fit.py`)

1. **One global similarity** brings the BP3D skeleton into the canonical frame, using only joint centres that the
   canonical rig really carries: hip, knee, shoulder and elbow, left and right. That is 8 points from the A20 rules:
   femoral / humeral head spheres and epicondyle midpoints, mapped to `FEMUR_*` and `HUMERUS_*` head / tail. No
   derived target, so the residuals are real. 8 non-coplanar points, so chirality is checked.
2. **Every bone** (199 of 206) is compared with its canonical head → tail segment:
   - mesh centroid → segment distance;
   - end-slice centroids (10 % along the canonical direction) → head / tail;
   - extent along the segment / segment length;
   - angle between the axes.
3. **Per region:** median / p95 / max, plus the region's **mean shift** (a common offset). The same distance is
   then given **after removing that shift**: the layout inside the region.
4. **Mirror:** every bilateral pair (83), raw left mirrored (x → −x) against raw right.

Reused without duplication: `register` (F1), the A20 rules (`long_bone_fit`) and the Blender helpers of
`ce_f2_femur_fit.py`. The driver is `scripts/f2_femur_fit.py --regions`.

## Global registration

Scale 1.032, det R = +1, chirality checked, **RMS 42.4 mm**. Residuals: hip 26 mm, knee 19 mm, shoulder **68 mm**,
elbow 40 mm (each side the same within 0.5 mm). The canonical limb joints do not match one real body with a
single similarity: the hips are too narrow (below) and the shoulders too wide.

## Results per region (mm unless stated; median / p95 / max)

| Region | Fitted | Centroid → segment | Same, after region shift | Head error | Tail error | Extent / length (median) | Axis angle ° (median) | Mean shift x, y, z | Mirror mean (median) / worst p95 (pairs) |
|--------|--------|--------------------|---------------------------|------------|------------|--------------------------|------------------------|--------------------|------------------------------------------|
| pelvis | 3 / 4 | 31 / 31 / 65 | 35 / 35 / 38 | 38 / 38 / 65 | 109 / 109 / 145 | 3.28 | 18 | 0, +16, −54 | 2.10 / 5.20 (1) |
| spine | 24 / 24 | 86 / 135 / 143 | 66 / 104 / 133 | 83 / 135 / 144 | 122 / 172 / 176 | 5.66 | 34 | −1, +19, −56 | — |
| thorax | 25 / 25 | 122 / 181 / 186 | 80 / 125 / 143 | 118 / 169 / 181 | 151 / 228 / 231 | 2.33 | 38 | −1, +2, −99 | 0.99 / 2.25 (12) |
| shoulder girdle | 4 / 4 | 109 / 117 / 118 | 107 / 110 / 111 | 124 / 157 / 159 | 151 / 209 / 209 | 5.86 | 30 | −1, +32, −33 | 0.99 / 3.21 (2) |
| arm | 6 / 6 | 28 / 41 / 43 | 52 / 55 / 58 | 63 / 67 / 67 | 85 / 96 / 96 | 1.00 | 14 | 0, −11, +61 | 1.63 / 5.87 (3) |
| hand | 54 / 54 | 96 / 144 / 153 | 28 / 52 / 60 | 105 / 145 / 160 | 113 / 168 / 174 | 0.76 | 25 | 0, −74, +87 | 0.71 / 3.13 (27) |
| leg | 8 / 8 | 22 / 40 / 41 | 36 / 53 / 55 | 35 / 46 / 47 | 33 / 44 / 45 | 1.05 | 3 | 0, +3, +1 | 1.86 / 5.84 (4) |
| foot | 52 / 52 | 88 / 119 / 126 | 67 / 93 / 97 | 94 / 123 / 130 | 99 / 139 / 149 | 0.79 | 13 | 0, +53, +44 | 0.70 / 3.31 (26) |
| skull | 23 / 29 | 52 / 64 / 66 | 48 / 78 / 85 | 63 / 76 / 98 | 58 / 77 / 82 | 1.96 | 23 | −1, −17, +13 | 1.44 / 8.15 (8) |

Mirror over all 83 pairs: mean 0.38–2.43 mm (median 0.82). Correct for every pair; the remaining distance is
the subject's own asymmetry.

**Not fitted (7):** `COCCYX` (absent from the BP3D PART-OF set, A18; stays a proxy), `MALLEUS_L/R`, `INCUS_L/R`,
`STAPES_L/R` (absent). No bone failed to import or measure. Canonical joints moved: **0** (fingerprint
`59b1cce8…dd80` before = after, 206 bones compared).

## Reading (findings, not corrected; canonical data untouched)

1. **Pelvis / hips:** canonical hip-centre width 133 mm against BP3D 180 mm (scaled). The `COXAL_*` and `SACRUM`
   stubs (65 mm vertical) do not describe the hip bones: extent / length 3.3, sacrum 65 mm from its segment.
   Measured pelvic landmarks are proposed in `docs/architecture/PELVIS_LANDMARKS_PROPOSAL.md`, with a cited
   source and nothing applied.
2. **Spine:** canonical vertebrae are short vertical stubs on a straight line (x = y = 0, 4–26 mm long). BP3D has
   lordosis / kyphosis and vertebrae with processes: centroids 66–133 mm off after the shift, extent / length 5.7.
   The canonical spine has no curvature.
3. **Thorax:** ribs are short horizontal stubs at y = 0 (37–74 mm). Real ribs curve round to the front, so
   centroids are 80–143 mm off. The sternum's centroid lies 49 mm more anterior than its segment.
4. **Shoulder girdle:** `SCAPULA_*` sits on the shoulder joint (x ±0.233) and `CLAVICLE_*` is a short stub; the
   real scapula / clavicle centroids are ~10 cm more medial. Together with the 68 mm shoulder residual: the
   canonical shoulders are too wide.
5. **Hand / foot:** inside the region the layout is the closest (hand 28 mm median after the shift). The large
   common shift (hand −74 mm Y / +87 mm Z, foot +53 Y / +44 Z) comes from the arm and leg chains ending in a
   different place, not from the A10 / A13 layouts themselves.
6. **Skull:** bones as vertical stubs (`FRONTAL`, `TEMPORAL_*`, `OCCIPITAL` …); centroids 48–85 mm off after the shift.
7. **Long bones (leg / arm):** within 22–43 mm of their segments in this single global frame; A20 has the per-bone fit.

These distances measure how **schematic** each canonical region is compared with a real skeleton (one subject,
1.72 m). They are not errors of a fit, and they are not targets: changing the canonical layout needs a source
per region (as A10, A11, A13 and A21 did) and the owner's OK.

## Reproduce

```bash
python scripts/f2_femur_fit.py --regions --bp3d C:/DEV/Assets/BodyParts3D_4.0/extracted/partof_BP3D_4.0_obj_99 --out C:/DEV/Assets/BodyParts3D_4.0/out
```

Blender 3.6.23. Deterministic. Tests: `tests/unit/test_skeleton_regions.py`.
