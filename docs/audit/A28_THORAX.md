# A28 — Thorax: sternum and ribs (variant A, ESTIMATE)

**Date:** 2026-11-05 · **Status:** APPLIED (owner, card "B y luego tórax, con Busscher", 01:38) · **Decision 73** ·
**Proposal:** `docs/architecture/THORAX_PROPOSAL.md` · **Script:** `scripts/fix_thorax.py` · **Report:**
`A28_THORAX_REPORT.json` · **Tests:** `tests/unit/test_thorax.py`

## Change

- **`STERNUM`:** the head (incisura jugularis) stays at (0, −0.0666, 1.4868), so the SC joint, clavicle, scapula and
  shoulders (A24, Decision 70) are untouched. The tail goes to the xiphoid tip (0, −0.1381, 1.318): length 47 → 183 mm.
- **24 ribs:** each runs from its costovertebral end to its free / costochondral end, placed relative to the mid-point
  of its own thoracic vertebra with BodyParts3D offsets ×1.0468 (one subject, ESTIMATE). Chords from 85 mm (rib 1) to
  223 mm (rib 7), descending forward; before, they were 37–74 mm horizontal stubs detached from the spine.
- **Rib 12:** its most anterior vertex is not its tip (27 mm chord, the artefact flagged in the proposal). It uses the
  vertex farthest from the head (86 mm). On ribs 10 and 11 this rule agrees with the general one within 3 mm.

A straight segment is only the chord of a curved bone; the visible curve belongs to the mesh or a proxy.
`THORAX_GEOMETRY` is registered in `source_registry.json`. Fingerprints (LF): `human_adult_206.json` → `a79f32f1…b7c0`;
`source_registry.json` → `a43ce624…a90b`.

## Behaviour (measured before committing)

| Gate | Result |
|------|--------|
| Gameplay table | in sync |
| Godot | 60/60; every replay identical (hit targets `RIB_08_L`, `RIB_10_L`, `STERNUM` use bone names and tables) |
| Blender | 40/40; T-pose PASS; IK rest deviation 13.6 mm (unchanged) |
| Clips | no field changes (ribs and sternum are only *covered* by `spine_03`) |
| `human_game_v1_body.glb` | re-baked, in sync |
| Proxies | regenerated (the rectus abdominis attaches to the sternum tail) |
| pytest / lint | 1262 passed; clean |

The Godot "CEBreathing" detail read 0.0029 m (range seen before this change: 0.0015–0.0026 m without any data change).
That check is timing-dependent and PASSes. It was not investigated further, and a contribution from the new geometry
cannot be ruled out.

## Re-measured A22 (spine already applied)

| Region / bone | Before | After |
|---------------|--------|-------|
| Thorax, centroid → segment median | 123.2 mm | **31.8 mm** |
| Thorax, axis angle median | 38.2° | **5.1°** |
| `STERNUM` | 74.7 mm | **4.8 mm** |
| `RIB_01_L` / `RIB_06_L` / `RIB_12_L` | 37.5 / 123.2 / 186.6 mm | 12.8 / 50.5 / 13.9 mm |

The remaining distance on the long ribs is expected: a curved rib's centroid lies away from its chord. Other regions
and the global RMS (29.7 mm, 42.5 mm in the original A22) are unchanged; 0 joints moved by the measurement.

## Open

No population source for rib geometry is registered (ESTIMATE, one subject, ±5 mm vertex resolution). Skull still
schematic (A22 median 50 mm). Hand and foot regions (97 / 90 mm) are dominated by a common shift of the limb chains.
