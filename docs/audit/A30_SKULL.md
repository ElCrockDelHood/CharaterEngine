# A30 — Skull bones at their BodyParts3D positions (variant A without MANDIBLE, ESTIMATE)

**Date:** 2026-11-05 · **Status:** APPLIED (owner, card "Cráneo y ratios de cabeza", 02:14) · **Decision 74** · **Proposal:**
`docs/architecture/SKULL_PROPOSAL.md` · **Script:** `scripts/fix_skull_positions.py` · **Report:** `A30_SKULL_REPORT.json` ·
**Tests:** `tests/unit/test_skull_positions.py`

## Change

22 bones (cranial vault, face, hyoid) keep their segment length and direction and move to their BodyParts3D centroid
(stature map ×1.0468, y relative to the C1 body; one subject, ESTIMATE). Pairs are mirror-averaged; midline bones get
x = 0. `FRONTAL` keeps its tail at z = 1.80 m (vertex), so its head moves down and it becomes 98 mm long (was 33).

**Not moved:** `MANDIBLE` (its head is the chin, 0.87 H PROVEN, and the game jaw pivot; moving the pivot to the TMJ is
a separate step) and the ear ossicles (absent from BodyParts3D; canonical stubs and proxies unchanged).

`SKULL_BONE_POSITIONS` is registered in `source_registry.json`. Fingerprint of `human_adult_206.json` → `c3a5920a…f08d`.

## Behaviour (measured before committing)

| Gate | Result |
|------|--------|
| Gameplay table | in sync |
| Godot | 60/60; every replay identical |
| Blender | 40/40; T-pose PASS; IK rest 13.6 mm; vertex 1.800 m |
| Clips | only `head` directions; timings unchanged; parity PASS |
| pytest / lint | all green once the fingerprint is updated; clean |

Noted changes that pass:

- The Godot joint-height check reads 1.733 m (was 1.767): it measures joint **heads**, and `FRONTAL` head is lower. The
  vertex (`FRONTAL` tail) is still 1.80 m.
- The game GLB check reads 1.666 m (was 1.650).
- `eye_*` (derived from `LACRIMAL` and `ZYGOMATIC`) goes from 1.650 to about 1.667 m, closer to the PROVEN 1.685 m.

## Re-measured A22

Skull centroid → segment median **50.0 → 6.4 mm** (`FRONTAL` 59.7 → 6.4, `HYOID` 36.6 → 6.4). The region's maximum, 64.7 mm,
is `MANDIBLE`, left out on purpose. The other regions and the global RMS (29.7 mm) are unchanged; 0 joints moved by the
measurement.
