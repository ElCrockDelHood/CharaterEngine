# Proposal: measured pelvic landmarks for the canonical skeleton

**Status:** PROPOSAL, nothing applied · **Date:** 2026-11-04 · Related: A22 (`docs/audit/A22_SKELETON_REGIONS_FIT.md`),
Decision 66, `FEMUR_ANCHOR_LANDMARKS_PROPOSAL.md`.

The canonical pelvis today has only schematic segments: `COXAL_L/R` is a vertical stub (z 1.0512 → 0.9864) at
x ±0.0999 and `SACRUM` is a vertical stub on the midline. The hip joint centres are the `FEMUR_*.head` points,
133.2 mm apart. No pelvic landmark is measured. The landmarks below would give the pelvis a measured frame. They
are the standard ones of motion analysis, and the hip-centre regressions use them.

## Proposed landmarks (names to add to `domain/anatomy/landmarks` only with a source and the owner's OK)

| Landmark | Definition (atlas) | How to extract it from a mesh (ESTIMATE, as in `skeleton_regions.pelvis_landmarks`) |
|----------|--------------------|-------------------------------------------------------------------------------------|
| `asis_L/R` (anterior superior iliac spine) | anterior end of the iliac crest | most anterior (−Y) vertex of the upper 40 % of the hip bone |
| `psis_L/R` (posterior superior iliac spine) | posterior end of the iliac crest | most posterior (+Y) vertex of the upper 40 % of the hip bone |
| `pubic_symphysis` | midline joint of the two pubic bodies (superior margin) | midpoint of the most medial vertices of the lower 30 % of each hip bone |
| `acetabular_centre_L/R` (= hip joint centre) | centre of the acetabulum / femoral head | sphere fit on the femoral head (A19/A20). A sphere fit on the acetabular surface is possible but not implemented |

## What BodyParts3D shows (internal use, Decision 62; evidence, not a source)

Distances from these rules on BP3D, scaled by the global similarity (×1.032) to the canonical frame:
inter-ASIS width 267 mm, inter-PSIS width 93 mm, pelvic depth (mid-ASIS → mid-PSIS) 143 mm, **inter-hip-centre
width 180 mm**, symphysis → mid-ASIS 105 mm. The canonical inter-hip-centre width is **133 mm**: 47 mm narrower.
This is the main pelvic finding of A22 (not corrected).

## Sources to cite (references only; nothing downloaded; verify the exact text before use)

- **Definitions:** Standring S. (ed.), *Gray's Anatomy: The Anatomical Basis of Clinical Practice*, 41st ed., Elsevier, 2016:
  pelvic girdle chapter (ASIS, PSIS, pubic symphysis, acetabulum).
- **Pelvic coordinate system:** Wu G. et al. (2002), "ISB recommendation on definitions of joint coordinate system of
  various joints for the reporting of human joint motion — part I: ankle, hip, and spine", *J Biomech* 35(4):
  543–548. It defines the pelvic frame from both ASIS and both PSIS, with the origin at the hip joint centre.
- **Hip joint centre from pelvic landmarks:** Harrington M.E. et al. (2007), "Prediction of the hip joint centre in
  adults, children, and patients with cerebral palsy based on magnetic resonance imaging", *J Biomech* 40(3):
  595–602: regression of the hip centre on pelvic width (inter-ASIS) and depth. Bell A.L., Pedersen D.R., Brand
  R.A. (1990), "A comparison of the accuracy of several hip center location prediction methods", *J Biomech*
  23(6): 617–621.

The regression coefficients are **not** copied here: they must be read from the paper itself (Decision 46: legal
source, owner's OK) before any number enters the canonical data.

## Next steps (owner)

1. Approve the landmark names and the source.
2. Decide whether the canonical hip width (133 mm) is re-derived from a sourced regression (it would be a canonical
   data change with fingerprint and Decision, like A21).
3. Optionally, an acetabular sphere fit as a second estimate of the hip centre.
