# Proposal A30 — skull bone positions (NOT applied)

**Status:** PROPOSAL, measured in a throw-away working copy (reverted; canonical data and fingerprints unchanged) ·
**Date:** 2026-11-05 · needs the owner's OK and a numbered Decision · low gameplay impact · Related: A22, A27.

## Finding

Canonical skull bones are schematic vertical stubs at positions not tied to the anatomy (A22 median centroid →
segment 50 mm), e.g. `SPHENOID` z 1.60–1.63, `NASAL` z 1.70–1.72 (above the eyes), `ZYGOMATIC` z 1.60–1.63,
`PALATINE` z 1.57–1.59 (at the chin). The neck now ends at C1 1.628 m (Decision 72), so the lower face overlaps the
neck region.

## Measurements (BodyParts3D ×1.0468, bone; y relative to the C1 body; ESTIMATE, one subject)

| Dimension | Canonical / Drillis | ANSUR II (men 1.75–1.85 m, skin) | BodyParts3D (bone) |
|-----------|--------------------|----------------------------------|--------------------|
| Vertex | 1.800 m (stature) | — | 1.795 m |
| Chin (menton) | 1.566 m (0.87 H, PROVEN; `MANDIBLE` head) | — | 1.570 m ✓ |
| Head height (vertex–menton) | 234 mm (0.13 H, PROVEN) | — | 225 mm ✓ |
| Eye height | 1.685 m (0.936 H, PROVEN); game rig `eye_*` today 1.650 m | — | orbit region ~1.665 m |
| Head length | `head_depth_ratio` 0.07 H = 126 mm (ASSUMPTION) | **201.8 mm** ± 6.6 (ratio 0.1121) | 204.5 mm |
| Head breadth | `head_width_ratio` 0.08 H = 144 mm (ASSUMPTION) | **155.2 mm** ± 5.6 (ratio 0.0862) | 158 mm |
| Head circumference | — | 580 mm | — |

BP3D's bone dimensions agree with ANSUR II's skin measurements within ~3 mm, which is suspiciously tight for bone vs
skin: this subject's head is large for its stature. **Finding about the tables:** the two ASSUMPTION ratios in
`anthropometry.json` are far from ANSUR II (`head_depth` by 75 mm); they could be sourced from ANSUR II, as a separate
reference-table change (fingerprinted).

## Variant A (trial): move each stub to the BP3D centroid

Each skull bone keeps its length and direction and moves to its BP3D centroid; pairs are mirror-averaged, midline bones
get x = 0. `FRONTAL` tail stays at z = 1.80 m (vertex, stature contract). Ossicles are not in BP3D (proxies, unchanged).

| Gate (working copy, reverted) | Result |
|-------------------------------|--------|
| Gameplay table | in sync |
| Godot | 60/60; replays identical |
| Blender | 40/40; IK rest 13.6 mm; vertex 1.800 m |
| Clips | only `head` directions (the game `head` bone ends at `FRONTAL` tail) |
| pytest | only the fingerprint |
| Proxies | in sync |
| A22 skull | **50.0 → 6.3 mm** |
| Godot height checks | canonical GLB joint height 1.767 → 1.733 m (`FRONTAL` **head** lower; a joint-head measure, PASS) · game GLB 1.650 → 1.666 m |

**Side effects to decide:**

- **`MANDIBLE`:** today its head is the chin at the PROVEN 1.566 m and it is also the game `jaw` pivot (a chin pivot is
  anatomically wrong: the jaw rotates at the TMJ). Moving the stub in the trial lifted that head to 1.595 m and lost
  the chin height. **Recommended: keep `MANDIBLE` out of this change** and fix it with the face work: head at the chin,
  pivot at the TMJ, jaw tests.
- **Eyes:** `eye_*` derives from `LACRIMAL` and `ZYGOMATIC`. The trial raises it from 1.650 to ~1.667 m, closer to the
  PROVEN 1.685 m but not on it.
- **`FRONTAL`** becomes longer (33 → ~98 mm), since its head moves and its tail stays at the vertex.

Variant B (not recommended): full principal-axis segments per bone. Flat bones have unstable axes (e.g. `SPHENOID` runs
sideways and breaks the midline convention); no benefit for gameplay.

## Uncertainty

One subject (and a large head for its stature); centroids are robust (±2 mm) but stubs are only labels for the bones,
not their shape. Label **ESTIMATE**. Real shapes belong to the meshes.

## Recommendation

Apply **variant A without `MANDIBLE`** (low risk, clear gain, no gameplay impact). Leave the jaw pivot and the two
ASSUMPTION head ratios as separate, explicit steps.
