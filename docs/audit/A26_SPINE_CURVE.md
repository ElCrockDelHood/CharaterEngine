# A26 — Spine sagittal curves (variant A, ESTIMATE)

**Date:** 2026-11-04 · **Status:** APPLIED (owner, card "Ambas, columna con curva BP3D") · **Decision 71** ·
**Script:** `scripts/fix_spine_curve.py` · **Report:** `A26_SPINE_CURVE_REPORT.json` · **Tests:** `tests/unit/test_spine_curve.py`
· **Proposal:** `docs/architecture/SPINE_THORAX_PROPOSAL.md` (thorax and skull not touched)

## Change

`CERVICAL_1` … `LUMBAR_5` keep x = 0 and their z (Drillis & Contini heights) and get an antero-posterior offset
**vertebra by vertebra** from BodyParts3D: the body centroid's offset from the C1 → sacrum line, ×1.0269. A head takes
the mean of its own offset and the vertebra above; a tail, the mean with the vertebra below. The chain is therefore
continuous at each disc and follows the local tangent. Peak values (mid-bone): cervical −8.1 mm (C6, anterior),
thoracic +30.6 mm (T6, posterior), lumbar −27.8 mm (L3, anterior). `SACRUM`, `COCCYX`, ribs, sternum and skull are
unchanged.

Shape descriptor of the source subject: cervical lordosis 24.5°, thoracic kyphosis 42.2°, lumbar lordosis 24.3°.
These are **angles between body-centroid tangents, not Cobb angles**. Pró, *Anatomía Clínica*, ch. 2 (book
pp. 86–88), is cited for the qualitative pattern only: cervical and lumbar lordosis, thoracic and sacral kyphosis;
7 + 12 + 5 vertebrae. It gives no degrees. `SPINE_SAGITTAL_CURVE` is registered in `source_registry.json` (Cobb
reference pending).

**Why by identity and not by height:** a first attempt mapped the curve by normalised height. It put the thoracic
peak on T12, because the canonical cervical spine is only **30 mm** tall (C1 head 1.5516 → C7 tail 1.5214), against
~95 mm in BodyParts3D. That attempt was discarded before any commit. The compressed cervical spacing is a separate
**finding** (z kept by the approved variant A; it needs its own source and decision).

Fingerprints (LF): `human_adult_206.json` `83025e87…c5a9` → `2af551dd…87d4`; `source_registry.json` `96a7b9a6…f5ffa3` →
`18a5ebfe…c5e7a`.

## Behaviour (measured before committing)

| Gate | Result |
|------|--------|
| Gameplay table | in sync |
| Godot replays (souls, arena, autoplay) | identical; Godot 60/60 |
| Clips | re-exported / re-baked: the spine-dependent directions change (`spine_02`, `head`, and children through the chain); Godot parity worst 0.0001° |
| `human_game_v1_body.glb` | re-baked |
| Blender | 40/40; T-pose PASS; IK rest deviation 13.6 mm (unchanged); game rig IK rest error 0.0012 mm |
| pytest / lint | all green |

## Re-measured A22

Spine region, centroid → segment median: 87.3 → **79.1 mm**; axis angle median 34.3° → **24.2°**. T6 98 → 87 mm.
L3 104 → 109 mm and the after-shift median 64.5 → 65.6 mm both change little: the remaining spine error is mostly
the vertical spacing (cervical compression), not the curve. Every other region and the global RMS (29.7 mm) are
unchanged; 0 joints moved by the measurement.
