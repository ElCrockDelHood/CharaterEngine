# Experiment 0 — Blender solver benchmark on the baseline PC (spec)

**Owner approval:** 2026-10-24 ("Las dos en orden": first this benchmark, then a work-quantification document).
**Owner intent (verbatim, 21:32 UTC):** "en blender tenemos que usar bullet y todos los solvers que tenemos, y eso va
a marcar el maximo rendimiento de mi maquina, has ahi llegamos, vemos si podemos producir, o bocetar con gran
calidad. en worckbrenk pero estaria muy bueno ver las coliciones".

## Objective

Measure, on the baseline PC (i3-3120M 2c/4t, 15.5 GB RAM, GT 740M 2 GB / Intel HD 4000, Blender 3.6.23), how far
each solver shipped with Blender 3.6 can go before it becomes impractical, so that the machine's ceiling is
known before any production promise. Results feed the work-quantification document.

## Cases (each run in its own Blender process, light → heavy)

| Case | Solver | Sizes |
|------|--------|-------|
| `rigid` | Bullet rigid body world: capsules and boxes dropped in a grid onto a ground plane, colliding | N = 10 / 100 / 500 |
| `cloth` | Cloth draped over a **skeleton proxy** (collision capsules on the long bones of `human_adult_206.json`, read-only) | grid 16² / 32² / 64² vertices |
| `softbody` | Soft body sphere (tissue-like) struck by a rigid impactor | subdivision 2 / 3 / 4 |
| `particles` | Particle emitter bursting from a breaking object, colliding with the ground | N = 1 000 / 10 000 / 50 000 |
| `geonodes` | Geometry-nodes simulation zone (points falling under gravity, Blender 3.6 simulation nodes) | N = 1 000 / 10 000 / 100 000 |
| `fluid` | Mantaflow liquid domain with a falling block | resolution 32 / 48 / 64 |

## Measurements per case (conditions → measurements → representative expression → provenance)

* **Conditions:** solver, size, frames, gravity (−9.81 m/s²), seed, all parameters (recorded in the result).
* **Measurements:** simulation (bake) seconds per frame; peak process RAM (Windows `PeakWorkingSetSize`);
  cached-frame evaluation time (playback proxy — background mode has no viewport, so viewport FPS is **not**
  measured); Workbench render seconds per frame at 960×540; status `ok` / `exceeded` (timeout) / `error`.
* **Representative expression:** one Workbench PNG of a key frame per case, to check visually that collisions
  are visible.
* **Provenance:** every output is **ESTIMATE** (our own simulation), with seed and parameters; the JSON result
  records the SHA-256 of each rendered PNG.

## Authorized files

New: `runtime/blender/ce_solver_benchmark.py` (runs inside Blender), `scripts/solver_benchmark.py` (driver: one
Blender process per case, timeout per case, logs through `scripts/_logrun.py`), `tests/unit/test_solver_benchmark.py`,
this spec, changelog. Outputs (ignored by git): `logs/`, `builds/benchmarks/`, `builds/renders/benchmark/`.
**Forbidden:** `src/character_engine/domain/**`, canonical data, the Blender addon, any new dependency.

## Acceptance criteria

1. The driver runs every case of the selected sizes, each in its own Blender 3.6 process with a timeout;
   a case that exceeds the time limit is recorded as `exceeded`, never freezes the run.
2. Results: `builds/benchmarks/<UTC>_solver_benchmark.json` (schema validated by the unit test) and a
   markdown table `…​.md` (solver × size → s/frame, peak RAM, render s/frame, status), plus one PNG per case.
3. A smoke configuration (smallest size, few frames) passes headless in Blender 3.6 from pytest (skipped if
   Blender is missing).
4. pytest, ruff and the architecture guard stay green; no change to the domain, canonical data or the addon.

## Risks

* Heavy cases (fluid 64, rigid 500, cloth 64², particles 50 000, geonodes 100 000) can make the PC slow;
  they run last, with a timeout, and the owner is warned before they start.
* Timing noise (other programs, thermal throttling on a laptop): numbers are indicative, single run.
* Viewport FPS cannot be measured headless; render and cached-evaluation times are reported instead.
