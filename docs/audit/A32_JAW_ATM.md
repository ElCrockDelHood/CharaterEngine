# A32 — Jaw pivot at the temporomandibular joint

**Date:** 2026-11-05 · **Status:** APPLIED (owner, card "Aplicar A, apertura en 25°", 17:50) · **Decision 78** · **Script:**
`scripts/fix_jaw_atm.py` · **Report:** `A32_JAW_ATM_REPORT.json` · **Tests:** `tests/unit/test_jaw_atm.py` · **Proposal,
measurements and sources:** `docs/architecture/JAW_ATM_PROPOSAL.md`

## Change (`human_adult_206.json`)

| `MANDIBLE` | Before | After | Provenance |
|------------|--------|-------|------------|
| `head` | (0, 0, 1.566) chin | (0, −0.0168, 1.6539) TMJ axis, midline | ESTIMATE: BodyParts3D `FJ3289`, one subject |
| `tail` | (0, 0, 1.5994) | (0, −0.0914, 1.566) chin | z PROVEN (0.87 H, Drillis & Contini 1966); y ESTIMATE |

Length 33.4 → 115.3 mm. Topology unchanged: 208 canonical nodes, 66 game bones, `jaw` under `head`, `MANDIBLE` under `CRANIUM`.
The opening limit stays at 25° (ASSUMED) by the owner's decision: the chin now travels 49.9 mm and the anterior alveolar
point 42.8 mm. The condyle does not translate; that belongs to the face or cinematic work.

Fingerprints (LF): `human_adult_206.json` → `7d021249…d60f`; `source_registry.json` → `7c1ce374…d2e6` (new `TMJ_AXIS` note).

## Measured before committing

| Gate | Result |
|------|--------|
| pytest | 1280 passed |
| Lint | OK |
| Blender 3.6.23 | 40/40; IK rest 13.6 mm; game rig IK rest 0.0019 mm |
| Godot 4.7.2 | 60/60; replays identical |
| Gameplay table | in sync |
| Clips | no field changes; `souls_clips.json` byte-identical; `souls_clips.glb` and `human_game_v1_body.glb` re-baked |
| Proxies | 67 files in sync |
| A22 | `MANDIBLE` centroid → segment **64.7 → 8.3 mm**, axis angle 2.7°; skull maximum 64.7 → 9.3 mm; skull median 6.4 mm and global RMS 29.74 mm unchanged; 0 joints moved |

The one Godot detail that differed is `CEBreathing`: 0.0016 m on the base, 0.0017 m in the trial, 0.0016 m applied, all PASS.
It changes between runs in both directions and the modifier works on `STERNUM`, so it is not an effect of this change.

**Tests adjusted, with reason:** `test_vertex_and_mandible_unchanged` pinned the old stub on purpose until this step. It is now
`test_vertex_unchanged_and_chin_height_kept`, which keeps the vertex and the PROVEN chin height.

**Not verified:** UPBGE; a visual render; the opening on a real head (no head mesh exists yet).
