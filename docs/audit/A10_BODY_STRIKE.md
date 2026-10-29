# A10 — Whole-body layered strike (material sample 3, pure Python)

Status: ESTIMATE / ASSUMED throughout. Nothing here is measured. Code: `domain/physics/body_strike.py`, tests: `tests/unit/test_body_strike.py`.

## What it is

The single contact interface for the fight mockup: `LayeredBody(points)` builds one layered capsule per block-dummy segment (17, hollow where the region has a cavity), and `strike(weapon, origin, direction)` returns the segment hit, the point, the incidence, how deep the layers took it and the `Wound` / `WoundAssessment` from the unchanged `assess_wound`. Weapons are the existing `Blade` (cut model) and `Impactor` (plateau-crush model). Garments are optional outer layers per segment.

## Simplifications (all reported in the result)

- The ray hits the skin envelope of the first capsule it meets; overlapping segments (shoulder, hip, neck under the thorax sphere) are not resolved.
- The layer models are one-dimensional through the thickness, so only the normal component counts: energy x cos(incidence)^2. Glancing blows lose most energy; the tangential part is dropped, not turned into a slash.
- No cloth simulation (that stays in the XPBD samples): garments are plain material layers.
- Central strikes are the only ones tabulated below; off-centre hits use the same chord through the layers (an approximation).

## Results (frontal central strike, one per segment, deterministic: table sha256 prefix sabre `286ab4a06de9758e`, club `60ffb62fb53165fa`)

Sabre: 0.6 kg effective mass (PLACEHOLDER) at 10 m/s (ESTIMATE), 30 J.

| Segment | Hit | Stopped in | Depth (mm) | Severity | Deepest layer | Fracture |
|---|---|---|---|---|---|---|
| head | self | bone | 15.6 | SERIOUS | bone | no |
| neck | thorax | tendon | 48.5 | SERIOUS | tendon | no |
| thorax | self | bone | 50.9 | SERIOUS | bone | no |
| abdomen | self | viscera | 97.4 | CRITICAL | viscera | no |
| pelvis | self | bone | 78.7 | SERIOUS | bone | no |
| upper_arm.L | self | bone | 44.7 | SERIOUS | bone | no |
| forearm.L | self | bone | 39.6 | SERIOUS | bone | no |
| hand.L | self | through | 36.0 | SERIOUS | bone | no |
| thigh.L | self | bone | 69.8 | SERIOUS | bone | no |
| leg.L | self | bone | 48.3 | SERIOUS | bone | no |
| foot.L | self | bone | 33.2 | SERIOUS | bone | no |
| upper_arm.R | self | bone | 44.7 | SERIOUS | bone | no |
| forearm.R | self | bone | 39.6 | SERIOUS | bone | no |
| hand.R | self | through | 36.0 | SERIOUS | bone | no |
| thigh.R | self | bone | 69.8 | SERIOUS | bone | no |
| leg.R | self | bone | 48.3 | SERIOUS | bone | no |
| foot.R | self | bone | 33.2 | SERIOUS | bone | no |

Club: 1.2 kg (PLACEHOLDER) at 9 m/s (ESTIMATE), 48.6 J, contact radius 30 mm.

| Segment | Hit | Stopped in | Depth (mm) | Severity | Deepest layer | Fracture |
|---|---|---|---|---|---|---|
| head | self | through | 85.0 | CRITICAL | viscera | yes |
| neck | thorax | bone | 48.7 | MODERATE | tendon | no |
| thorax | self | through | 130.0 | CRITICAL | viscera | yes |
| abdomen | self | through | 130.0 | SEVERE | viscera | yes |
| pelvis | self | through | 140.0 | SEVERE | viscera | yes |
| upper_arm.L | self | through | 50.0 | MODERATE | bone | yes |
| forearm.L | self | through | 40.0 | MODERATE | bone | yes |
| hand.L | self | through | 18.0 | MODERATE | bone | yes |
| thigh.L | self | through | 80.0 | MODERATE | bone | yes |
| leg.L | self | through | 55.0 | MODERATE | bone | yes |
| foot.L | self | through | 30.0 | MODERATE | bone | yes |
| upper_arm.R | self | through | 50.0 | MODERATE | bone | yes |
| forearm.R | self | through | 40.0 | MODERATE | bone | yes |
| hand.R | self | through | 18.0 | MODERATE | bone | yes |
| thigh.R | self | through | 80.0 | MODERATE | bone | yes |
| leg.R | self | through | 55.0 | MODERATE | bone | yes |
| foot.R | self | through | 30.0 | MODERATE | bone | yes |

## What the tables say, and what they do not

- The thorax row reproduces sample 2 exactly (club: 130 mm, ribs fractured, severity 5). The neck row hits the thorax block, because the thorax block is a sphere that covers the neck from the front: a block-dummy shape issue, not a layer issue.
- Every long bone fractures under the club (bone fracture energy 25 J, ASSUMED, all or nothing). That is a consequence of one unsourced constant, not a finding about arms. The sabre transects the hand and stops in bone elsewhere, which is the cut energy of bone (ASSUMED) at work.
- Severity comes from the existing trauma rules, which were not changed. Where the legacy 400 J mapping and this model disagree (sample 2), the disagreement is reported, not resolved: replacing the constant is the wounds thread's decision.

## Open items

1. Segment overlap resolution and a proper ray-capsule intersection (the hit search marches 2 mm and bisects).
2. Off-centre chord length and a slash component for glancing cuts.
3. Port to Godot (the fight mockup lives there): the model is plain arithmetic over shells, no solver, so it ports directly; the cloth part would not.
4. Tuned constants (bone fracture and cut energy, crush plateaus) need sources before any claim about real bodies.

## Appendix: layered model against the shipped gameplay table

`scripts/gameplay_vs_layered.py` (read-only) turns each of the 168 (move, hitbox bone) pairs of `gameplay_shenmue.json` into one central frontal blunt strike (kinetic energy and contact radius of the move) and compares severity with the legacy 400 J mapping already in the table.

Catalog default (one 25 J rigid-shell energy everywhere):

| Move | Energy (J) | Legacy severity | Layered severity | Layered fractures (of 21) |
|---|---|---|---|---|
| crescent_kick | 220.0 | 1x1, 2x20 | 2x8, 4x2, 5x11 | 21 |
| elbow_assault | 170.0 | 1x5, 2x16 | 2x8, 4x2, 5x11 | 21 |
| front_kick | 150.0 | 1x13, 2x8 | 2x8, 4x2, 5x11 | 21 |
| hook | 130.0 | 1x13, 2x8 | 2x8, 4x2, 5x11 | 21 |
| jab | 60.0 | 1x21 | 2x9, 4x1, 5x11 | 18 |
| shoulder_throw | 260.0 | 2x21 | 2x8, 4x2, 5x11 | 21 |
| straight | 90.0 | 1x21 | 2x8, 4x2, 5x11 | 21 |
| sweep | 140.0 | 1x13, 2x8 | 2x8, 4x2, 5x11 | 21 |

168 pairs: layered higher in 120, lower in 0.

With per-region rigid-shell energies (`FIGHT_RIGID_SHELL_ENERGY_J`, opt-in, ASSUMED: orders of magnitude recalled from the biomechanics literature, NOT verified against sources; head 80 J, thorax 150 J, pelvis and thigh 300 J, hand 20 J ...):

| Move | Energy (J) | Legacy severity | Layered severity | Layered fractures (of 21) |
|---|---|---|---|---|
| crescent_kick | 220.0 | 1x1, 2x20 | 2x9, 4x1, 5x11 | 16 |
| elbow_assault | 170.0 | 1x5, 2x16 | 2x16, 4x1, 5x4 | 9 |
| front_kick | 150.0 | 1x13, 2x8 | 2x16, 4x1, 5x4 | 7 |
| hook | 130.0 | 1x13, 2x8 | 2x16, 4x1, 5x4 | 7 |
| jab | 60.0 | 1x21 | 2x20, 4x1 | 5 |
| shoulder_throw | 260.0 | 2x21 | 2x16, 4x1, 5x4 | 9 |
| straight | 90.0 | 1x21 | 2x20, 4x1 | 5 |
| sweep | 140.0 | 1x13, 2x8 | 2x16, 4x1, 5x4 | 7 |

168 pairs: layered higher in 103, lower in 0.

Reading: with the default the model is degenerate (any move fractures nearly everything). The per-region values make it discriminate (a jab fractures 5 of 21 zones, a crescent kick 16) and it is never below the legacy table, but several things are still wrong and block wiring it into the game: severity 5 follows every fracture of a hollow region (after the shell breaks the viscera cost almost nothing, so the strike goes "through"), and the contact radius changes the outcome as much as the energy does (a 260 J shoulder throw reads like a 130 J hook). The table values are not sourced. Recommendation: do not replace the 400 J constant yet; keep this as a comparison tool.
