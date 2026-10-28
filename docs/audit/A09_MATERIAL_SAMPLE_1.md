# A09 — Material sample 1: forearm strike (evidence for Decision 49)

**Run:** 2026-10-25, `builds/material_sample/20261025T143422Z/` (outputs ignored by git). GPU probe run
`builds/material_sample/20261025T143401Z/`. Driver `scripts/material_sample.py` (pure-Python simulation
`domain/physics/forearm_strike.py`) and `runtime/blender/ce_material_sample.py` (drawing and renders only).
Log: `logs/20261025T143522Z_material_sample.log`. Blender 3.6.23 on the baseline PC (i3-3120M, GeForce GT 740M).
Every value below is copied from the run's JSON / summary files; nothing is added.

## Set-up (from the JSON `config`)

* Left forearm block-dummy segment (`forearm.L`, envelope radius 0.040 m, ESTIMATE) as a **layered capsule**: bone
  core 0.0075 m, tendon to 0.0105 m, muscle to 0.0319 m, fat to 0.0383 m, skin to 0.040 m (soft scale 0.855);
  all ESTIMATE. Stature 1.80 m (USER_INPUT).
* Wool sleeve: thickness 0.002 m, gap 0.006 m, lattice 32 × 16 (ESTIMATE). Variant *armored* adds a steel bracer
  0.0015 m thick, gap 0.002 m, over 15–85 % of the segment (ESTIMATE).
* Sabre edge: effective mass 0.6 kg (**PLACEHOLDER**), speed 10 m/s (**ESTIMATE**) → kinetic energy **30.0 J**;
  blade width 0.028 m (PLACEHOLDER), edge radius 0.002 m; strike at mid-segment.
* XPBD: 60 fps, 40 settle + 40 strike frames, 20 substeps, **seed 0**; slow motion ×20 for presentation (ASSUMED).

## Results

| Variant | Blade stopped in | Depth below skin | Wound | Deepest layer | Severity | Lethality | Sleeve links cut | Sim time | Final state hash |
|---------|------------------|------------------|-------|---------------|----------|-----------|------------------|----------|------------------|
| unarmored | bone | 39.4 mm (penetration 47.4 mm incl. sleeve) | incision on RADIUS_L | bone | 3 | 0.075 | 113 | 30.72 s | `f46978843a4c0346` |
| armored | bracer | 0.0 mm | blunt | fat | 1 | — | 0 | 29.21 s | `80c8dbcb74877f6e` |

The wound is produced by the trauma entry points (`blade_contact_to_wound` / `blunt_impact_to_wound` +
`assess_wound`), not by the physics code (Decision 49). Unarmored: the whole 30 J is spent (sleeve → skin → fat →
muscle → tendon → bone, not transected). Armored: the steel bracer stops the edge and the strike reaches the arm
as a blunt contact.

## Renders (1920 × 1080, `render_report.json`)

| File | Engine | Device | Samples | Seconds |
|------|--------|--------|---------|---------|
| comparison_eevee.png | EEVEE | GPU | 64 | 23.77 |
| comparison_cycles.png | Cycles | CUDA GeForce GT 740M | 512 | 946.51 |
| closeup_unarmored_cycles.png | Cycles | CUDA GeForce GT 740M | 512 | 2 054.67 |
| closeup_armored_cycles.png | Cycles | CUDA GeForce GT 740M | 512 | 2 162.68 |

Whole run (simulation + scene + renders): 5 190 s. GPU probe: Cycles CUDA on the GT 740M works (tiny render
1.764 s). Cycles stills at 512 samples take 16–36 min on this machine; EEVEE takes about 24 s.

## Provenance and limits

* Nothing PROVEN. Tissue mechanics ESTIMATE (order of magnitude, unsourced); bone chopping energy, steel
  blade-defeat energy and XPBD compliances ASSUMED tuning; optics ASSUMED look-dev (Decision 49).
* Blade mass PLACEHOLDER and speed ESTIMATE, so the 30 J is not a measurement. A cited source for sabre mass, strike
  speed and cutting energy per tissue would replace them.
* One segment and one strike direction only; the result is a reproducible sample (seeded, state hashes), not a
  validated injury model.
