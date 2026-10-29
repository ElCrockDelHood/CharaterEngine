# A09 (sample 2) — Hollow layers, blunt impact model: thorax with ribs, cavity and padded vest

**Date:** 2026-10-29 · **Status:** IMPLEMENTED (data status ESTIMATE / ASSUMED, nothing PROVEN) · **Scope:** core
domain (`domain/materials`, `domain/physics`), driver `scripts/material_sample.py`, Blender scene
`runtime/blender/ce_material_sample.py` · **Decisions:** 49 (sample 1), 55 (sample 2). Sample 1 has its own report, `A09_MATERIAL_SAMPLE_1.md`; this one
adds sample 2 and the shared notes (what is tuned, solver stability, open items)

Both samples take a block-dummy capsule (`rigging/block_dummy.py`), split it into concentric material shells from the
regional tissue profile (`tissue/layers.py`), add garments / armour as outer shells, simulate the cloth with a
pure-Python XPBD solver, and send the depth reached by the impactor through the unchanged trauma entry points
(`assess_wound`). Blender draws what the domain computed; it computes nothing physical.

## 1. What is where

| Piece | File | Notes |
|-------|------|-------|
| Material catalogue | `domain/materials/catalog.py` | Mechanical face (density, modulus, friction, cut energy, XPBD compliances, crush stress / strain, rib fracture energy) + OpenPBR-named optical face; every value is a `Quantity` with range and provenance |
| Layered capsule | `domain/materials/layered_capsule.py` | Solid fit (limbs: bone core = half bone thickness) and hollow fit (thorax, head, pelvis, abdomen: bone shell around a cavity) |
| XPBD solver | `domain/physics/xpbd.py` | Small-steps XPBD, distance constraints (stretch + bend), capsule colliders with friction, local `skip` collider, seeded constraint order, state hash |
| Cut model | `domain/physics/cut.py` | Blade energy spent on cut area per shell (sample 1) |
| Blunt model | `domain/physics/blunt.py` | Plateau crush per layer + all-or-nothing rib fracture (sample 2) |
| Samples | `domain/physics/forearm_strike.py`, `torso_strike.py` | Scenario, report JSON, sha256 |
| Tests | `tests/unit/test_materials_xpbd.py` (15), `tests/unit/test_blunt_torso.py` (17) | |

## 2. Sample 1 — summary (full report: `A09_MATERIAL_SAMPLE_1.md`)

Run on the owner's PC 2026-10-25 (Blender 3.6.23, Cycles CUDA on a GeForce GT 740M, seed 0).

| Variant | Blade stopped in | Depth below skin | Wound | Deepest layer | Severity | Sleeve links cut |
|---------|------------------|------------------|-------|---------------|----------|------------------|
| unarmored | bone | 39.4 mm | incision | bone | 3 | 113 |
| armored | bracer | 0 mm | blunt (residual 30 J, upper bound) | fat | 1 | 0 |

Reproducibility: re-running the simulation reproduced the result `sha256` exactly
(`cf245455…` unarmored, `93789334…` armored). Renders at 1920×1080, 512 samples: EEVEE 23.8 s; Cycles 946 s
(comparison) and about 2050–2160 s per close-up (total 5190 s). The first close-up cameras were too tight; they were
widened (lens 50 mm) and re-rendered.

## 3. Sample 2 — thorax, wool coat, optional padded vest, blunt impactor (48.6 J)

Run on the owner's PC on 2026-10-29 (Blender 3.6.23, Cycles CUDA on a GeForce GT 740M, seed 0). Impactor: 1.2 kg (PLACEHOLDER) at 9 m/s
(ESTIMATE), end-on contact radius 30 mm (ESTIMATE). Layer capacities at that contact area:

| Shell | Capacity (J) | Unvested | Vested |
|-------|--------------|----------|--------|
| coat | 0.12 | crushed | crushed |
| vest | 17.0 | – | crushed |
| skin / fat / muscle / tendon | 2.3 / 1.5 / 7.1 / 2.0 | crushed | crushed |
| rib shell (fracture energy) | 25 (ASSUMED) | breaks | holds, 18.7 J stored |
| cavity (lung-dominated) | 2.0 | crushed, 8.6 J left | not reached |

| Variant | Stopped in | Affected depth | Ribs fractured | Deepest layer | Severity | Legacy mapping |
|---------|------------|----------------|----------------|---------------|----------|----------------|
| unvested | through the cavity | 130 mm (skin to axis) | yes | viscera | 5 | fat, severity 1 |
| vested | rib shell (holds) | 48.7 mm | no | tendon | 2 | fat, severity 1 |

Energy sweep (1.2 kg, speed 2–14 m/s): ribs first break at **8 m/s (38 J) unvested** and **10 m/s (60 J) vested**.
The legacy mapping (`blunt_impact_to_wound`: `E / 400 J` × depth to bone) stays at fat / severity 1 up to 14 m/s
(118 J) because 400 J is its single reference constant; it never reaches the rib layer in this range.

Reproducibility: two simulation runs gave identical result `sha256` (`e75bfcc7…` unvested, `acab4965…` vested).
Renders at 1920×1080, Cycles 128 samples (final pass): EEVEE 10.6 s; Cycles 319.1 s (comparison), 311.9 s and
316.0 s (close-ups); Blender total 960.7 s. Earlier passes, kept for the record: the first (EEVEE 9.9 s, Cycles
243.5 / 284.6 / 293.5 s, total 836 s) showed the coat z-fighting with skin and vest; the next three fixed the cloth,
framing and exposure but still looked washed out. Presentation-only changes in `ce_material_sample.py` (the domain
result and its hash are untouched): the cloth vertices are clamped radially just outside the outermost solid shell;
the steel impactor is rougher (0.45); the comparison camera is closer and the close-ups use a 75 mm lens; scene
exposure is −1.5 EV; bone / tendon / viscera / padded vest get presentation colours **in linear space** (Blender
reads Base Color as scene-linear, so the catalog colours, which look like sRGB values, render far too pale: the
vest's brown came out cream, the coat's navy lavender); the impactor is drawn with its face at the blunt model's
displacement (outer radius − `displacement_m`: 115 mm from the axis vested, in the fat above the ribs; 86 mm
unvested, inside the cavity) instead of where the cloth XPBD stopped it.

What the images show: the cutaway reads maroon cavity, beige rib shell, thin white tendon, red muscle, yellow fat,
skin, (brown vest), blue coat from the inside out. Unvested: the impactor tip sits inside the cavity, matching
"through". Vested: the impactor goes through coat and vest and does not appear in the cutaway, matching "ribs
hold". Still wrong: the crush is **not drawn** (layers stay undeformed, so the rod simply intersects them); the rod
still takes a blue cast next to the coat; EEVEE still shows a dark, smeared rod where it meets the cloth.

## 4. What is tuned, not measured (read before quoting any number)

* **Rib fracture energy 25 J, ASSUMED.** All-or-nothing; after the shell breaks nothing but the cheap cavity is left,
  so the model has a cliff between "ribs hold" and "through the chest" (8 → 9 m/s unvested). A real chest has
  intermediate outcomes (flail segments, contusion without fracture) that are not modelled.
* **Crush stress / strain for skin, fat, muscle, tendon, wool, padded cloth, cavity: ASSUMED**, order of magnitude only.
* **Bone chopping energy (sample 1) and steel blade-defeat energy: ASSUMED tuning constants**, not material properties.
  With bone fracture toughness alone a 30 J cut would sever the forearm.
* XPBD compliances and damping: ASSUMED. Optics: ASSUMED look-dev.
* Impactor mass PLACEHOLDER; speeds, contact radius, garment thicknesses and gaps ESTIMATE.
* **Geometry:** the thorax block is a sphere (T12–T1 span 0.146 m is shorter than two radii of 0.13 m); sample 2 stacks
  the layers on a cylinder along that span. It shows layer behaviour, not chest shape. Block-dummy radii are ESTIMATE.
* Not modelled: rate dependence, pressure waves through a shell that holds, glancing blows, rib flexion, steel plate
  under blunt load (rejected on purpose by `blunt_through`), force-based injury criteria.

## 5. Solver stability finding

A structured Gauss-Seidel sweep over the closed sleeve lattice injected mechanical energy (+4.4 % in 0.5 s at 20
substeps, +48 % at 80); the same constraints in a seeded shuffled order do not (about −0.003 %). Constraint order is
therefore a seeded permutation (`tube(..., seed=...)`), and the settle-phase energy check is part of the tests.
Contact velocity projection removes the separating velocity that position projection otherwise adds.

## 6. Open items

1. Source tissue crush behaviour, rib fracture energy and bone chopping energy (register in `source_registry`).
2. Intermediate chest outcomes (rib fracture without cavity penetration) and a force / acceleration criterion.
3. A real thorax shape (the sphere block) before judging silhouettes.
4. Steel plate / lamellar armour under blunt load.
5. Godot port of the layer contact (GDScript first) once the interface with the wound thread is agreed.
6. Draw the blunt crush (dent the layers down to the affected depth) in the Blender scene.
7. Presentation: remove the rod's blue cast and the EEVEE smear.
8. Colour space of `optical_openpbr.base_color` in `domain/materials/catalog.py`: OpenPBR defines it as linear, the
   values look like sRGB. A data decision for the owner; the Blender scene currently overrides four of them.
