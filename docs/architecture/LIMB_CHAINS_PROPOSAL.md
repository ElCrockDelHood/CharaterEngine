# Proposal A29 — limb chains, hands and feet: diagnosis (recommendation: do NOT move the limbs)

**Status:** PROPOSAL, measured in a throw-away working copy (reverted; canonical data and fingerprints unchanged) ·
**Date:** 2026-11-05 · a data change needs the owner's OK and a numbered Decision · Related: A10, A13, A20, A22,
Decision 16.

> Owner, 2026-11-05: limb joints not moved; variant F of the foot is left to the animation thread.

## Conclusion

The large A22 distances of the hand (97 mm) and foot (90 mm) are **not canonical defects**. The canonical limbs
agree with Drillis & Contini (PROVEN) and with ANSUR II. The odd one out is the BodyParts3D subject and its pose.
Moving limb joints towards it would replace sourced values by one subject. **Recommendation: do not move the limb
joints.** The only sourced refinement found is one foot proportion (below), and it is optional.

## Evidence per segment (mm at 1.80 m; ANSUR II = men 1.75–1.85 m, n = 1814, ratio × 1800)

| Quantity | Canonical | Drillis & Contini | ANSUR II | BodyParts3D (×1.0468) | Reading |
|----------|-----------|-------------------|----------|------------------------|---------|
| Wrist height | 873 | 873 (0.485 H) | 870 | **935** | BP3D 62 mm high: forearm flexed forward |
| Fingertip height | 678.6 | 678.6 (0.377 H) | — | — | canonical = source |
| Wrist → fingertip | 194.4 | 194.4 (0.108 H) | 197.6 (hand length) | 187 | agree; BP3D short |
| Elbow joint height | 1135 (mid of gap) | 1134 (0.630 H) | — | 1182 | canonical = source |
| Shoulder height | 1472 | 1472 (0.818 H) | 1479 (acromial, skin) | 1459 | agree |
| Upper arm (joint → joint) | 338 vertical | 335 (0.186 H) | 344 (acromion–radiale) | 282 | BP3D short |
| Forearm (joint → joint) | 261 vertical | 263 (0.146 H) | 275 (radiale–stylion) | 234 | BP3D short |
| Hip height | 954 | 954 (0.530 H) | 926 (trochanterion, skin) | 931 | keep source |
| Knee height | 512 (mid of gap) | 513 (0.285 H) | 503 (mid-patella) | 500 | agree |
| Tibia top | 487 | — | 482 (tibial height) | 460 | agree |
| Ankle height | 70.2 | 70.2 (0.039 H) | 74.7 (lateral malleolus) | 92.5 | agree; BP3D high |
| Foot length | 273.6 | 273.6 (0.152 H) | 277.6 | **230** | BP3D 44 mm short |
| Foot breadth | 99 | 99 (0.055 H) | 103.5 | — | agree |
| Heel → ball of foot | **178.9** | — | 205.7 (202.8 on the canonical foot length) | — | **real difference**, see below |

**Pose of the BodyParts3D subject** (not anatomy): forearm direction (x 0.15, y −0.20, z −0.97), i.e. about 12° forward;
hand (0.08, −0.42, −0.90), about 25° forward; foot toe-out 14.5°. The canonical pose is straight down, feet forward.

**Measured:** registering the hand or foot **alone** (similarity on bone centroids, no limb chain):

| Region | Rotation | Scale | Centroid error, median / max |
|--------|----------|-------|------------------------------|
| Hand (27 bones) | 27° | 0.90 | **14 / 40 mm** (97 mm in A22) |
| Foot (26 bones) | 33° | 1.19 | **13 / 33 mm** (90 mm in A22) |

So the layouts of A10 and A13 are close to the real ones once pose and subject are removed. The foot's scale 1.19
is the subject's short foot; the hand's 0.90 is partly its flexed fingers. A22's single global similarity cannot
separate these. A pose-normalised metric would be a useful follow-up (measurement only).

**Joint gaps:** `FEMUR` tail → `TIBIA` head 49 mm and `HUMERUS` tail → `RADIUS` head 54 mm, each centred on the
Drillis joint. BP3D's own bones, with landmark rules, show 40 mm at the knee and 21 mm at the elbow. They are segment
conventions, not defects. Under Decision 16, osteometry sizes meshes and never moves joints.

## Pending proportions (`HAND_SEGMENT_PROPORTIONS`, `FOOT_SEGMENT_PROPORTIONS`)

ANSUR II is a legal, citable source (cleared for unlimited public release) already downloaded, and it can replace
PLACEHOLDER splits:

- **Foot, heel → ball:** `balloffootlength` / `footlength` = 0.1143 / 0.1542 = 0.741, against the canonical 178.9 / 273.6
  = 0.654 (the A13 split 3:5:3, PLACEHOLDER). Both landmarks are foot landmarks, so this is a like-for-like comparison.
- **Hand, palm:** `palmlength` / `handlength` = 0.601. It ends at the finger-base **crease**, which lies beyond the
  MCP **joint** that the canonical metacarpal tail represents (canonical 91.5 / 194.4 = 0.471). **Not comparable; no
  change proposed.** `handbreadth` 89.8 mm could check the ray spacing.

### Variant F (optional): foot split from ANSUR II

Ball of the foot moves forward 23.9 mm (heel and toe tips fixed: foot length stays PROVEN; toes shorten).

| Gate (trial with a simple y remap, reverted) | Result |
|----------------------------------------------|--------|
| Gameplay table, Godot 60/60, replays | in sync, identical |
| Blender | 40/40, IK rest 13.6 mm, T-pose OK |
| Clips | no field changes |
| pytest | fingerprint, proxies (tibialis anterior inserts in the foot), `test_foot_layout::test_joints_are_continuous` (the trial's remap broke tarsal continuity; a real change would go through `scripts/rebuild_foot_layout.py`, not this remap) |
| A22 foot | 89.7 → 101.9 mm **(worse, as expected: it moves away from BP3D's short foot, towards ANSUR)** |

## Recommendation

1. **Do not move** arm, leg, hand or foot joints.
2. Optional, your call: variant F, as a rebuild of A13 with the ANSUR ratio. It replaces a PLACEHOLDER with a population
   source, but the benefit is small and it touches foot IK references, so I would do it only together with the
   foot-contact work of the animation thread.
3. When fitting real meshes, register hands and feet with their own anchors and handle the pose (F2 already works per
   bone), instead of expecting the BP3D rest pose to match.
