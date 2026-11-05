# A31 — Head width and depth ratios from ANSUR II

**Date:** 2026-11-05 · **Status:** APPLIED (owner, card "Cráneo y ratios de cabeza", 02:14) · **Decision 75** · **Script:**
`scripts/fix_head_ratios.py` · **Tests:** `tests/unit/test_head_ratios.py`

## Change (`references/anthropometry.json`)

| Ratio | Before (ASSUMPTION, LOW) | After (DERIVED, MEDIUM) | At 1.80 m | Measure |
|-------|--------------------------|-------------------------|-----------|---------|
| `head_width_ratio` | 0.08 (0.07–0.09) | **0.0862** (0.0809–0.092) | 155.2 mm | head breadth 154.6 ± 5.6 mm |
| `head_depth_ratio` | 0.07 (0.06–0.08) | **0.1121** (0.1059–0.1183) | 201.8 mm | head length 201.0 ± 6.6 mm |

Source: ANSUR II (2012 US Army survey; Gordon et al. 2015, NATICK/TR-15/007; cleared for unlimited public release), men
1.75–1.85 m, n = 1814. Value = mean of the individual ratios to stature; range = p5–p95. Measured on the head (skin).
**Population:** US Army personnel, not the civilian population. Registered as `ANSUR_II_2012` in `source_registry.json`.
The old `head_depth` was 75 mm short of the measured head length.

Fingerprints (LF): `anthropometry.json` → `68691873…1343`; `source_registry.json` → `b57b70e1…8706`.

## What uses these ratios

Nothing reads them today: no code or runtime refers to `head_width_ratio`, `head_depth_ratio` or their groups by name.
`reference_manager` loads the whole table generally; the dummy, proxies, shaders and game rig do not depend on these two
keys. The change therefore corrects the reference data for future use (head proxy, skin fitting) and has no runtime
effect yet.

## Behaviour (measured before committing)

Gameplay table in sync; Godot 60/60 with every replay identical; Blender 40/40 (IK rest 13.6 mm, T-pose PASS); clips with
no changes; proxies in sync; pytest and lint green once the two fingerprints are updated. A22 is unaffected (no bone
moved).
