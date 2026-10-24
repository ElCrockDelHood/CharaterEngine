# Experiment 0 — results (2026-10-24)

Spec: `docs/product/EXPERIMENT-0-SOLVER-BENCHMARK.md`. Baseline PC: i3-3120M 2c/4t, 15.5 GB RAM, GT 740M 2 GB
(driver 388.73) + Intel HD 4000, Windows 10, Blender **3.6.23** headless (`-b --factory-startup`). 48 frames per
case, seed 7, timeout 300 s per case, Workbench key frame at 960×540. Single run; every value is **ESTIMATE**.

Raw results (ignored by git): `builds/benchmarks/20261024T214818Z_solver_benchmark.{json,md}` (levels 0–1) and
`builds/benchmarks/20261024T214432Z_solver_benchmark.{json,md}` (level 2); key-frame PNGs with SHA-256 in the JSON,
under `builds/renders/benchmark/`. Logs: `logs/*_solver_bench.log`.

## Measurements

| Case | Size | Sim s/frame (mean / max) | Cached replay fps | Workbench render s (960×540) | Peak RAM MB | Status |
|------|------|--------------------------|-------------------|------------------------------|-------------|--------|
| rigid (Bullet) | 10 bodies | 0.001 / 0.0021 | 13 593 | 1.49 | 208 | ok |
| rigid (Bullet) | 100 bodies | 0.0133 / 0.0223 | 2 268 | 1.58 | 223 | ok |
| rigid (Bullet) | 500 bodies | 0.0893 / 0.136 | 307 | 1.57 | 285 | ok |
| geonodes sim zone | 1 000 points | 0.0004 / 0.0007 | 2 584 | 1.50 | 202 | ok |
| geonodes sim zone | 10 000 points | 0.001 / 0.0016 | 1 379 | 1.54 | 216 | ok |
| geonodes sim zone | 100 000 points | 0.0046 / 0.0061 | 266 | 1.75 | 311 | ok |
| particles | 1 000 | 0.0011 / 0.0028 | 1 768 | 1.46 | 202 | ok |
| particles | 10 000 | 0.0098 / 0.0237 | 233 | 1.53 | 224 | ok |
| particles | 50 000 | 0.0454 / 0.12 | 49 | 1.73 | 290 | ok |
| soft body | ico subdiv 2 (42 v) | 0.0018 / 0.024 | 5 331 | 1.53 | 200 | ok |
| soft body | ico subdiv 3 (642 v) | 0.0108 / 0.1067 | 3 842 | 1.59 | 200 | ok |
| soft body | ico subdiv 4 (2 562 v) | 0.5124 / 0.6502 | 2 223 | 2.04 | 203 | ok |
| cloth on skeleton proxy | 16² = 256 v | 0.0116 / 0.0203 | 2 150 | 1.58 | 207 | ok |
| cloth on skeleton proxy | 32² = 1 024 v | 0.0417 / 0.068 | 1 247 | 1.49 | 221 | ok |
| cloth on skeleton proxy | 64² = 4 096 v | 0.1588 / 0.2623 | 679 | 1.46 | 277 | ok |
| fluid (Mantaflow liquid) | res 32 | 0.2423 / 0.3097 | 40 | 1.61 | 382 | ok |
| fluid (Mantaflow liquid) | res 48 | 0.8597 / 1.5353 | 15 | 1.71 | 646 | ok |
| fluid (Mantaflow liquid) | res 64 | 2.3094 / 3.429 | 6 | 2.21 | 974 | ok |

"Cached replay fps" = re-evaluating already simulated frames in background mode (a playback proxy); it is
**not** viewport FPS, which cannot be measured headless. The render time includes Blender's per-render setup.

## Facts

* All 18 cases finished; **none exceeded** the 300 s limit and none failed.
* Highest peak RAM: 974 MB (fluid res 64) of 15.5 GB.
* Slowest simulation: fluid res 64, 2.31 s/frame (max 3.43 s).
* Collisions are visible in the Workbench key frames for rigid bodies, cloth on the skeleton proxy, soft body
  vs ground, particles vs ground and fluid vs domain walls.

## Observations (not defects of the benchmark)

* Soft body with Blender's default settings and no goal **collapses** on impact (shape not preserved): a
  tissue-like behaviour needs tuned stiffness parameters, which require sources or ESTIMATE marks.
* The geometry-nodes case has **no collision** (points fall through the ground by design: constant fall speed).
* The rigid impactor/particle "breaking" is a burst emitter, not a fracture solver (Blender 3.6 has no built-in
  fracture; Cell Fracture is a bundled add-on, not tested).

## Inferences (labelled; to be confirmed by further runs)

* For a 10 s shot at 24 fps (240 frames) the simulation alone would take about: fluid res 64 ≈ 9 min, res 48 ≈
  3.5 min, soft body 2 562 v ≈ 2 min, cloth 4 096 v ≈ 40 s, 500 rigid bodies ≈ 20 s, 50 000 particles ≈ 11 s,
  100 000 geonodes points ≈ 1 s; Workbench rendering at 960×540 would add about 6–9 min (1.5–2.2 s/frame).
* The machine's ceiling was **not reached** at these sizes (no timeout, RAM < 1 GB); a level-3 run (e.g. fluid
  96/128, cloth 128², 2 000 bodies) would be needed to find it.
