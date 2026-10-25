# A12 — Godot hardware benchmark on the GT 740M (RIG-GAME-001 step 4)

**Date:** 2026-10-25 · **Status:** MEASURED (3 runs) · face subset APPROVED by the owner (20 shapes)

## Machine and method

- ASUS N56VB, GeForce GT 740M, NVIDIA driver 388.73, OpenGL 3.3 — Godot 4.7.2 `gl_compatibility`, window
  1280×720, vsync off, uncapped FPS.
- `python scripts/godot_perf.py` → `runtime/godot/tests/ce_perf_bench.gd`, report `builds/tests/godot_perf.json`,
  logs `logs/20261025T165817Z_godot_perf.log`, `…165902Z…`, `…165927Z…`.
- Per scenario: 60 warm-up frames, 300 timed frames (wall clock between frames, includes the GPU wait).
- **Bones:** every character carries the same procedural skinned mesh (7998 vertices, 1 influence each, spread over
  all bones) and the same 12 limb / spine bones are animated, so the difference is the bone count (skeleton update
  + skin matrices). **Face:** 4 game-rig characters, each with a 40×40 grid (1600 vertices) on `head` and 0 / 20 / 52
  blend shapes, all weights animated every frame.
- Meshes are **synthetic load**, not character art; animation is driven from GDScript. The numbers compare
  configurations on this PC; they are not a game budget.

## Results (average frame time, ms; three runs)

| Scenario | Bones | Run 1 | Run 2 | Run 3 | Mean | FPS (mean) |
|----------|------:|------:|------:|------:|-----:|-----------:|
| canonical ×1 | 208 | 2.030 | 2.091 | 2.262 | 2.13 | ~470 |
| game ×1 | 66 | 1.936 | 1.932 | 2.054 | 1.97 | ~507 |
| canonical ×4 | 208 | 2.764 | 2.953 | 2.839 | 2.85 | ~351 |
| game ×4 | 66 | 2.421 | 2.430 | 2.502 | 2.45 | ~408 |
| canonical ×8 | 208 | 3.746 | 3.654 | 3.796 | 3.73 | ~268 |
| game ×8 | 66 | 2.942 | 2.860 | 2.992 | 2.93 | ~341 |
| game ×4 + face, 0 shapes | 66 | 2.536 | 2.420 | 2.502 | 2.49 | ~402 |
| game ×4 + face, 20 shapes | 66 | 3.397 | 3.401 | 3.509 | 3.44 | ~291 |
| game ×4 + face, 52 shapes | 66 | 6.065 | 6.151 | 6.176 | 6.13 | ~163 |

Run-to-run spread is within ~5 %.

## Findings

1. **Game rig vs canonical:** the 66-bone rig saves ~0.4 ms at 4 characters (−14 %) and ~0.8 ms at 8 characters
   (−21 %) with identical vertex load. CONFIRMED: the two-level skeleton (Decision 51) pays off on this GPU.
2. **Face blend shapes:** per 1600-vertex face, 20 animated shapes cost ~0.24 ms and 52 shapes ~0.91 ms per frame
   (relative to 0 shapes). The cost grows with shapes × vertices; 52 is ~3.8× the cost of 20.
3. A Godot `Performance.TIME_PROCESS` reading was inconsistent with the frame times in this script context and was
   removed from the benchmark (not reported).

## Proposal (owner decision pending)

- In-game face: **≤ 20 ARKit-named shapes**, all 52 only in Blender cinematics (or a hero close-up). Candidate set
  (ARKit names): `eyeBlinkLeft`, `eyeBlinkRight`, `eyeSquintLeft`, `eyeSquintRight`, `browDownLeft`, `browDownRight`,
  `browInnerUp`, `browOuterUpLeft`, `browOuterUpRight`, `jawOpen`, `mouthClose`, `mouthSmileLeft`, `mouthSmileRight`,
  `mouthFrownLeft`, `mouthFrownRight`, `mouthFunnel`, `mouthPucker`, `cheekPuff`, `noseSneerLeft`, `noseSneerRight`.
- Re-measure with the real head mesh once it exists (vertex count drives the cost).
