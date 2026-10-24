# A07 — Canonical Stature Retarget to 1.80 m

**Date:** 2026-09-29
**Status:** APPLIED (supersedes the scale findings of A02 §Coordinate Ranges)
**Decision:** `docs/reorientation/DECISION_LOG.md` §15
**Script:** `scripts/retarget_stature.py` · **Report:** `A07_STATURE_RETARGET_REPORT.json`

---

## 1. Problem

A02 (2026-08-12) found the canonical skeleton `human_adult_206.json` spanned **0.000–3.080 m**
in Z with an oversized head and legs too short relative to the torso. All positions were
generated geometric placeholders (provenance `PLACEHOLDER`).

## 2. Source

| Field | Value |
|-------|-------|
| `source_id` | `DRILLIS_CONTINI_1966` |
| Reference | Drillis, R. & Contini, R. (1966). *Body Segment Parameters*. Tech. Rep. 1166.03, NYU School of Engineering and Science |
| Reproduced in | Winter, D.A. (2009). *Biomechanics and Motor Control of Human Movement*, 4th ed., Wiley, Fig. 4.1 |
| Population | Healthy American males, 20–40 y |
| Confidence | MEDIUM — population means; the authors did not formalise landmark definitions; individual variance is large |
| Known discrepancy | Contini (1972, Part II) quotes 0.189/0.145/0.128 H for upper arm/forearm/hand; this project uses the Winter Fig. 4.1 set (0.186/0.146/0.108 H) consistently |

Self-consistency check of the ratio set (fraction of H):
`0.818 − 0.186 = 0.632 ≈ 0.630 (elbow)`, `0.630 − 0.146 = 0.484 ≈ 0.485 (wrist)`,
`0.485 − 0.108 = 0.377 (fingertip)`, `0.530 − 0.245 = 0.285 (knee)`, `0.285 − 0.246 = 0.039 (ankle)`.

## 3. Method

1. Base stature **H = 1.80 m** — a project design parameter (`USER_INPUT`), not a population value.
2. Landmarks measured on the placeholder skeleton (vertex, chin = lowest mandible point,
   shoulder = humerus head, elbow, wrist, fingertip, hip = femur head, knee, ankle, ground).
3. Three **monotonic piecewise-linear Z maps**, one per kinematic region, passing exactly
   through the sourced landmarks:
   - AXIAL (cranium, spine, ribs, sternum, pelvis, clavicle/scapula): hip → shoulder → chin → vertex
   - ARM (humerus + descendants): fingertip → wrist → elbow → shoulder
   - LEG (femur + descendants): ground → ankle → knee → hip
4. **XY uniform scale** 0.666 so the shoulder-joint spacing equals the biacromial breadth 0.259 H.
5. Names, parents, topology unchanged (206 bones, 208 nodes with containers).

## 4. Result

| Landmark | Ratio (H) | Before (m) | Target (m) | After (m) |
|----------|-----------|-----------|-----------|-----------|
| vertex | 1.000 | 3.080 | 1.800 | 1.800 |
| chin | 0.870 | 2.730 | 1.566 | 1.566 |
| shoulder | 0.818 | 2.080 | 1.472 | 1.472 |
| elbow | 0.630 | 1.705 | 1.134 | 1.135 |
| hip | 0.530 | 1.280 | 0.954 | 0.954 |
| wrist | 0.485 | 1.380 | 0.873 | 0.873 |
| fingertip | 0.377 | 0.900 | 0.679 | 0.679 |
| knee | 0.285 | 0.805 | 0.513 | 0.512 |
| ankle | 0.039 | 0.380 | 0.070 | 0.070 |
| ground | 0.000 | 0.000 | 0.000 | 0.000 |
| shoulder breadth | 0.259 | 0.700 | 0.466 | 0.466 |

Bounding box after: X −0.263…0.263 m · Y −0.093…0.067 m · Z 0.000…1.800 m.

## 5. Provenance after A07

| Item | State |
|------|-------|
| Ratios in `references/anthropometry.json` | **PROVEN** (cited) |
| Landmark heights in metres (`canonical_landmark_heights_m`) | **DERIVED** (ratio × 1.80) |
| Base stature 1.80 m | **USER_INPUT** |
| Position of the 11 landmark bones' anchors | **DERIVED** |
| Every other bone head/tail (interpolated) | **ESTIMATE** |
| XY scale, hip-joint spacing, depths | **ESTIMATE** |
| Per-vertebra heights, cranial bone layout, carpal/tarsal layout | still **PLACEHOLDER-quality** (inherited from A02) |

## 6. Known remaining issues (inherited, not fixed by A07)

- Joint gaps: femur tail → tibia head gap and humerus tail → radius head gap are preserved
  proportionally (femur length 0.418 m vs. 0.441 m thigh ratio). Needs osteometric data.
- Cervical spine compressed between shoulder (1.472) and chin (1.566) because the placeholder
  placed C1–C7 below the mandible; requires vertebral-height data.
- Hand/foot internal layout is schematic (metacarpal X offsets are not anatomical).
- Straight spine (no curvature), uniform rib layout — see A02.

## 7. Verification

- `python scripts/retarget_stature.py --dry-run` reproduces the table above from the pre-A07 file.
- `tests/anatomy`, `tests/unit`, `tests/integration`, `tests/export` pass on the new data.
- Godot / UPBGE validators: 208 bones, ground contact, height 1.80 m along the up axis.
