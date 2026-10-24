# A11 — Forearm layout: radius lateral to ulna

**Date:** 2026-10-24 · **Status:** FIXED (topology) · separation **PLACEHOLDER**, source pending
**Script:** `scripts/fix_forearm_layout.py` · **Reports:** `A11_FOREARM_LAYOUT_REPORT.json`,
`A11_HAND_REANCHOR_REPORT.json` · **Tests:** `tests/unit/test_forearm_layout.py`

## Finding

In the anatomical position (standing, palms facing forward = −Y) the radius is the **lateral**
(thumb-side) forearm bone and the ulna the medial one, side by side in the coronal plane. The
canonical data had them one in front of the other: `RADIUS_*` at y = −0.0333, `ULNA_*` at y = +0.0333.

## Change

| Item | Value | Provenance |
|------|-------|------------|
| Radius lateral, ulna medial | left: radius x > ulna x; right: radius x < ulna x | PROVEN topology |
| Pair midpoint, z (elbow 1.1139 / wrist 0.873), lengths 0.2409 m | unchanged | existing data (z DERIVED from Drillis & Contini; lengths per A07) |
| Half-separation | 0.0333 m, moved from Y to X | **PLACEHOLDER** — pre-existing value; `FOREARM_INTEROSSEOUS_WIDTH` registered as NOT_ACQUIRED |

Before → after (left): `RADIUS_L` head (0.2331, −0.0333, 1.1139) → (0.2664, 0.0, 1.1139);
`ULNA_L` head (0.2331, 0.0333, 1.1139) → (0.1998, 0.0, 1.1139). Right side mirrored.

The hand (A10) is anchored on the radius tail, so `scripts/rebuild_hand_layout.py` was re-run:
the 27 hand bones per side move 0.0333 m laterally and to y = 0 (e.g. `CAPITATE_L` head
(0.2331, −0.0333, 0.8501) → (0.2664, 0.0, 0.8501)). Both scripts are idempotent.

## Verification

pytest 747 passed; addon headless 20/20 on Blender 3.6.23 with the IK rest deviation unchanged
(11.8 mm); Godot 4.7.2 21/21; `gameplay_shenmue.json` regenerated with its script: no diff.
`human_adult_206_backup.json` and `builds/tests/validation.blend` untouched.
