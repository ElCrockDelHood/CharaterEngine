# A10 — Hand layout of the canonical skeleton

**Date:** 2026-10-24 · **Status:** FIXED (layout) · proportions **PLACEHOLDER**, source pending
**Script:** `scripts/rebuild_hand_layout.py` · **Report:** `A10_HAND_LAYOUT_REPORT.json`
**Tests:** `tests/unit/test_hand_layout.py`

## Finding

In `human_adult_206.json` (both sides) the 8 carpals hung ~10 cm below the wrist in a synthetic
ramp (8.1 mm bones stepping 13.3 mm in Y), and the 5 metacarpals + 14 phalanges sat 15–20 cm medial
to the wrist, next to the thigh, all with uniform lengths (16 mm / 12 mm). Metacarpals and proximal
phalanges were parented to `RADIUS_*`. The jab's striking bone (`PHALANX_PROXIMAL_3_R`), the T-pose
hand and CINE-03 ("mano cinematográfica") all depended on this geometry.

## What was changed (27 bones per side, 54 total)

| Item | Value | Provenance |
|------|-------|------------|
| Wrist anchor | `RADIUS_*` tail (radiocarpal joint; the ulna does not articulate directly with the carpus) | existing data + PROVEN topology |
| Fingertip height (rays 2–5) | 0.377 H = 0.6786 m | PROVEN ratio, DRILLIS_CONTINI_1966 |
| Hand length wrist → fingertip | 0.108 H = 0.1944 m | DERIVED (0.485 H − 0.377 H) |
| Carpal rows, lateral → medial | proximal: scaphoid, lunate, triquetrum (+ pisiform, palmar on triquetrum); distal: trapezium, trapezoid, capitate, hamate | PROVEN topology (atlas) |
| Metacarpal parents | MC1←trapezium, MC2←trapezoid, MC3←capitate, MC4/MC5←hamate | PROVEN topology |
| Ray chains | MC → proximal → (intermediate) → distal; thumb has no intermediate | PROVEN topology |
| Orientation | anatomical position: palm −Y, fingers −Z, thumb lateral (+X left / −X right) | convention (Decision 17) |
| Length split carpal row : MC : phalanx | 2 : 4 : 3 (unit = hand length / 17) | **PLACEHOLDER** — ratio of the pre-existing bone lengths 0.0081 / 0.0162 / 0.0122 m |
| Ray spacing / pisiform palmar offset | 0.0133 m | **PLACEHOLDER** — pre-existing data step |

Fingers 2–5 have equal length and the thumb is a straight ray in the coronal plane: these are
placeholder simplifications, not anatomy. Real proportions (e.g. MC3 ≈ 1.5× proximal phalanx,
digit length differences, thumb opposition angle) need a source and are registered in
`references/source_registry.json → data_requirements.missing` as `HAND_SEGMENT_PROPORTIONS`
(NOT_ACQUIRED).

## Before / after (examples, metres)

| Bone | Before (parent · head) | After (parent · head) |
|------|------------------------|-----------------------|
| CAPITATE_L | RADIUS_L · (0.2597, −0.0799, 0.7596) | RADIUS_L · (0.2331, −0.0333, 0.8501) |
| METACARPAL_3_L | RADIUS_L · (0.0733, 0.0, 0.7394) | CAPITATE_L · (0.2331, −0.0333, 0.8273) |
| PHALANX_PROXIMAL_3_R | RADIUS_R · (−0.0599, 0.0, 0.7232) | METACARPAL_3_R · (−0.2331, −0.0333, 0.7815) |
| PHALANX_DISTAL_3_L (tail) | (0.0599, 0.0, 0.6867) | (0.2331, −0.0333, 0.6786) |

## Not changed / known limits

- 206 bones, 208 nodes, names, carpal parents, all non-hand bones.
- `RADIUS`/`ULNA` are still separated antero-posteriorly (Y) instead of side by side (X) in the
  anatomical position — a separate forearm finding, out of scope here.
- `gameplay_shenmue.json` is unchanged (moves resolve bones by name).
- `human_adult_206_backup.json` (frozen fixture) is untouched.
