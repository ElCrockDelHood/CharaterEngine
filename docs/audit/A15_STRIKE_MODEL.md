# A15 — Reduced-mass strike with a force-based fracture criterion (material sample 4, pure Python)

Status: ESTIMATE / ASSUMED. Code: `domain/physics/strike_model.py`; tests: `tests/unit/test_strike_model.py`; comparison tool: `scripts/gameplay_vs_strike_model.py`. Sources and background: A11 (project notes) and `A14_EFFECTIVE_MASS.md`. Nothing existing changed: `blunt.py`, `body_strike.py`, the gameplay table and the 400 J constant are untouched, so no earlier hash moves.

## Model

- **Striker** = effective mass m, speed v, contact radius. `Striker.from_move` keeps each move's table `energy_j` and fixes v by kind (punch 7.5, kick 9.0, throw 6.0 m/s); m = 2E/v^2. The jab gets 2.1 kg, in line with the 2.9 +/- 2.0 kg measured on Olympic boxers (Walilko 2005, via A14).
- **Tissue energy** is only E_diss = 1/2 mu v^2 with mu = mM/(m+M), M = effective mass of the struck segment (shared table of `collision.py`, Decision 58). The remainder is reported as knock-back (input for a concussion / knockdown model, not for wounds).
- **Peak force** F = v sqrt(k mu) (linear collision), k = whole-region local stiffness. The thorax k (1.6e5 N/m) comes from cadaver data (3.4 kN at 26 mm; 10.6 kN at 55 mm).
- **Fracture** when F reaches the midpoint of a per-region force range; a probability is reported next to it. The skull also needs E_diss in 22-24 J (Delye 2007).
- **Depth** that reaches the wound is the peak compression F/k, capped by what the layer stack can crush; a fractured shell means the bone layer is breached. The layered stack (`blunt_through`) is reused unchanged.

## Acceptance against cadaver thorax data (13 cadavers, ballistic blunt impacts)

| Case | Model F (N) | Measured F (N) | Error |
|---|---|---|---|
| 140 g at 20 m/s | 2976 | 3383 | -12 % |
| 140 g at 40 m/s | 5952 | 10602 | -44 % |
| 40 g at 60 m/s | 4792 | 3158 | +52 % |

Within a factor two everywhere, and the sign flips with the case: a linear spring cannot follow the stiffening with speed and the small-mass local effects. The test asserts the factor-two bound, not a fit.

## Against the shipped gameplay table (read-only)

| Move | Energy (J) | m_eff (kg) | v (m/s) | Legacy severity | Model severity | Fractures (of 21) | Expected fractures | Tissue J (mean) | Knock-back J (mean) |
|---|---|---|---|---|---|---|---|---|---|
| crescent_kick | 220.0 | 5.4 | 9.0 | 1x1, 2x20 | 2x20, 4x1 | 15 | 16.1 | 116 | 104 |
| elbow_assault | 170.0 | 6.0 | 7.5 | 1x5, 2x16 | 2x20, 4x1 | 13 | 13.8 | 86 | 84 |
| front_kick | 150.0 | 3.7 | 9.0 | 1x13, 2x8 | 2x20, 4x1 | 15 | 14.7 | 91 | 59 |
| hook | 130.0 | 4.6 | 7.5 | 1x13, 2x8 | 2x21 | 12 | 12.4 | 73 | 57 |
| jab | 60.0 | 2.1 | 7.5 | 1x21 | 1x1, 2x20 | 11 | 7.9 | 43 | 17 |
| shoulder_throw | 260.0 | 14.4 | 6.0 | 2x21 | 2x20, 4x1 | 13 | 12.7 | 83 | 177 |
| straight | 90.0 | 3.2 | 7.5 | 1x21 | 2x21 | 12 | 10.1 | 57 | 33 |
| sweep | 140.0 | 3.5 | 9.0 | 1x13, 2x8 | 2x20, 4x1 | 15 | 14.4 | 87 | 53 |

Severity: model higher in 87 of 168 pairs, lower in 0.

## What this says, and what it does not

- Unlike the energy-only versions in A10, results now depend on the striker: a jab is expected to fracture 7.9 of 21 zones, a crescent kick 16.1. Order follows the legacy table, and the model is never below it in severity.
- Severity compresses to 2 almost everywhere because the trauma ladder gives blunt wounds that reach the bone but not the viscera the same grade; fracture probability and the knock-back column carry the information the severity loses.
- Fracture counts for the extremities are high because their force ranges are ASSUMED and wide (hand 0.5-2.5 kN, foot 1.5-5 kN); only thorax, forearm, thigh and leg have sourced ranges, and those are weak (reviews citing other work, one popular article). Skull force range is ASSUMED.
- Target masses come from `collision.regional_target_mass_kg()` (Decision 58: 75 kg body × segment fraction, de Leva 1996 recalled, unverified): head 5.2, thorax 12.0, thigh 10.6 kg ... The first version of this module carried its own table (head 5, thorax 25, thigh 8 kg); switching to the shared table moved the comparison by a few joules and the expected fractures by up to 0.8 (hook 13.2 -> 12.4), the cadaver forces by under 0.3 %, and left the severity count unchanged (87 higher, 0 lower).
- Not modelled: rate dependence beyond the linear spring, gloves and wraps, strike duration, rotation (the head accelerating angularly), glancing hits, repeated blows.
- The 400 J constant of the wounds thread is not replaced. Replacing it is a Decision, not part of this change.

## Open items

1. Verify the "(summary)" values (A11) and the thorax corridor paper's authors from the full texts.
2. A target-mass table from a real anthropometric source.
3. Fracture flag in `assess_wound` follows reaching the bone layer, not the shell breaking (it reports fractures on regions without a rib cage when the energy model is used): wounds thread.
4. Knock-back to concussion / knockdown, with head rotation.
5. Sabre (cut) equivalent: reduced mass changes it little (30 -> 27 J) because the blade is light against the target.
