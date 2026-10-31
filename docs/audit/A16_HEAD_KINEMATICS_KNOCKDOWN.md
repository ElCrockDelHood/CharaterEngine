# A16 — Head kinematics, concussion probability and knock-back stagger

Status: ESTIMATE / ASSUMED, additive and opt-in (Decision 59). Code: `domain/physics/head_kinematics.py`; tests:
`tests/unit/test_head_kinematics.py`; tool: `scripts/gameplay_head_kinematics.py`. Builds on `collision.py`
(Decision 58, A14) and `strike_model.py` (A15). Nothing existing changes: `blunt.py`, `body_strike.py`,
`strike_model.py`, the gameplay table and every earlier hash stay as they are. Spanish: `A16_HEAD_KINEMATICS_KNOCKDOWN.es.md`.

## Sourced numbers (pages read by the coordinator session; full texts not in the repository)

| Source | What | Values |
|---|---|---|
| Walilko, Viano & Bir 2005, *Br J Sports Med* 39(10):710 | 7 Olympic boxers, 18 straight punches into a Hybrid III face | punch force 3427 ± 811 N; hand speed 9.14 ± 2.06 m/s; effective mass 2.9 ± 2.0 kg; jaw load 876 ± 288 N; head linear acceleration 58 ± 13 g; rotational acceleration 6343 ± 1789 rad/s²; neck shear 994 ± 318 N |
| Rowson et al. 2012, *Ann Biomed Eng* 40(1):1–13 | 335 football players, 300 977 impacts, 57 concussions | concussion probability vs rotational acceleration / velocity: 10 % 5260 rad/s² / 23.3 rad/s; 25 % 5821 / 25.8; 50 % 6383 / 28.3; 75 % 6945 / 30.8; 90 % 7483 / 33.2. Concussive impacts: mean ≈ 100–106 g, ≈ 5000 rad/s² |
| Sturnieks et al. 2013, *PLoS ONE* 8(8):e70981 | 242 adults aged ≈ 80, waist pull (300 ms ramp, 200 ms hold, 100 ms off) | recovery-step threshold 50.3 ± 14.0 N forward, 45.6 ± 13.2 N backward, 70.5 ± 21.1 N lateral |
| Batcir et al. 2020, *BMC Geriatr* 20:249 | 83 adults aged 70+ | multiple-step level ≈ 1.3 × single-step level (11.9 vs 8.9) on a lateral moving platform: a ratio of ordinal platform levels, not of force or impulse |

Rowson's logistic fit is α = −12.531, β = 0.002 (β printed rounded: with 0.002 the 50 % point falls at 6266 rad/s²; β ≈ 0.001963 reproduces the table within 0.01 at all five rows, tested). The interpolated table stays the implementation. Sources verified in `VERIFICACION_FUENTES_A14_A16.es.md`.

## Model

1. **Linear acceleration** `a = F_peak / M_head`: `F_peak` from `strike_model.peak_force` for the head region,
   `M_head` = 5.2 kg from the shared table (`collision.py`, ESTIMATE).
2. **Rotational acceleration** `α = F_peak · d / I_head`: lever arm `d` ASSUMED 0.04 m (straight) or 0.08 m (hook
   type); `I_head` ASSUMED 0.0225 kg·m² (0.02–0.025 range, unverified).
3. **Concussion probability**: Rowson 2012 table on `α`, linear between rows; 0 → 10 % linear from 0 to 5260
   rad/s², 90 → 99 % linear from 7483 to 9000 rad/s² (tails ASSUMED).
4. **Stagger**: impulse `J = μ · v` given to the body through the struck segment (perfectly inelastic, `collision.py`).
   One step at `P_STEP` = 25 N·s (ASSUMED for a young fighter). Older adults: force–time area of the waist pull
   0.40 s × F (Sturnieks 2013), ≈ 20 / 18 / 28 N·s forward / backward / lateral (DERIVED from SOURCED values).
   Several steps at 1.3 × (ASSUMED, inspired by Batcir 2020 platform levels), fall at 2 × (ASSUMED). `bracing` ≥ 1 multiplies the
   thresholds. `knocked_down` = fall or concussion probability ≥ 0.5.

## Acceptance (Walilko means: Striker 2.9 kg, 9.14 m/s, contact radius 0.04 m, onto the head)

| Quantity | Model | Measured | Bound | Result |
|---|---|---|---|---|
| Peak force | 3944 N | 3427 ± 811 N | within 35 % | +15 %, pass |
| Linear acceleration | 77.3 g | 58 ± 13 g | within × 1.5 | × 1.33, pass |
| Rotational acceleration (d 0.04 m) | 7012 rad/s² | 6343 ± 1789 rad/s² | within × 2 | × 1.11, pass |
| Concussion probability | 0.77 | (≈ 50 % level in Rowson) | 0.2–0.9 | pass |

No constant was fitted to these numbers. The linear acceleration sits 1.5 SD above the measured mean: the struck head
is modelled as a free 5.2 kg mass, while the Hybrid III neck carries part of the load.

## Gameplay moves that hit the head (read-only; `python scripts/gameplay_head_kinematics.py`)

| Move | Head hitboxes | m (kg) | v (m/s) | Lever (m) | F_peak (N) | a (g) | alpha (rad/s^2) | P(concussion) | m*v (N s) | Impulse mu*v (N s) | Stagger |
|---|---|---|---|---|---|---|---|---|---|---|---|
| crescent_kick | 4 | 5.4 | 9.0 | 0.08 | 4640 | 91 | 16498 | 0.99 | 48.9 | 23.9 | none |
| elbow_assault | 4 | 6.0 | 7.5 | 0.08 | 3966 | 78 | 14102 | 0.99 | 45.3 | 21.0 | none |
| front_kick | 4 | 3.7 | 9.0 | 0.04 | 4187 | 82 | 7443 | 0.89 | 33.3 | 19.5 | none |
| hook | 4 | 4.6 | 7.5 | 0.08 | 3711 | 73 | 13194 | 0.99 | 34.7 | 18.4 | none |
| jab | 4 | 2.1 | 7.5 | 0.04 | 2917 | 57 | 5186 | 0.10 | 16.0 | 11.3 | none |
| shoulder_throw | 4 | 14.4 | 6.0 | 0.04 | 3711 | 73 | 6598 | 0.60 | 86.7 | 23.0 | none |
| straight | 4 | 3.2 | 7.5 | 0.04 | 3339 | 65 | 5936 | 0.30 | 24.0 | 14.9 | none |
| sweep | 4 | 3.5 | 9.0 | 0.04 | 4102 | 80 | 7292 | 0.85 | 31.1 | 18.7 | none |

## What this says, and what it does not

* Straight blows read sensibly: a jab ≈ 10 %, a straight ≈ 30 %, kicks to the head 85–90 %.
* **Hook-type blows saturate at 0.99**: with `d` = 0.08 m every hook, elbow and crescent kick exceeds the top
  Rowson row (13–16 k rad/s²). The lever arm is ASSUMED and the football table was not built from bare-headed or
  gloved blows; until a sourced hook lever arm or a boxing risk curve exists, hook probabilities are an upper bound.
* **No head blow staggers the body**: the head (5.2 kg) takes too little momentum (≤ 24 N·s < 25 N·s). Body blows
  can (thorax impulse for a crescent kick ≈ 33 N·s → step); the head path ends in concussion, not in stagger.
* The shoulder throw is not a head blow; it appears here only because its move lists head hitboxes.
* Not modelled: rotational velocity and angular impulse (Rowson also gives velocity thresholds), neck stiffness,
  gloves, cumulative blows, the direction of rotation, sweeps (they remove support), young-adult balance data
  (thresholds ASSUMED), any time history (only peaks).

A sensitivity grid over lever arm and striker range for every head-hitting move is in `A17_MOVE_STRIKERS.md`
(Decision 60): every move spans about 0.05–0.99.

## Open items

1. Rotational velocity / angular impulse, so the second Rowson column can be used.
2. A sourced lever arm per blow type, or a boxing-specific risk function.
3. Young-adult balance perturbation data to replace `P_STEP`.
4. Head inertia and neck coupling from a sourced head–neck model.
