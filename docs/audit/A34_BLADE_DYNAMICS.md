# A34 — Sabre cut: effective mass, rotational inertia and impact point

Spec and research note, 2026-11-05, Decision 82. Spanish version: `A34_BLADE_DYNAMICS.es.md`. Regenerate the tables with
`python scripts/blade_dynamics_table.py`.

**Status.** Specified, implemented and unit tested as an opt-in. Not adopted: the shipped `Blade(0.6, 10.0, 0.028)` is
unchanged, so no A09 or A10 table moves. Nothing here is validated against a physical cut.

## 1. Spec

**Objective.** Replace "0.6 kg at 10 m/s" (mass PLACEHOLDER, speed ESTIMATE) with a calculation from the weapon's mass,
its rotational inertia, the swing and the point of the blade that hits.

**Files.** Changed: `domain/physics/cut.py` (additions only, `cut_through` and `Blade` untouched). New:
`tests/unit/test_blade_dynamics.py`, `scripts/blade_dynamics_table.py`, this note. Also an entry in `INDEX.md`,
`DECISION_LOG.md` and `NOTICE`. Not touched: `collision.py` (imported, read-only), `strike_model.py`, `head_kinematics.py`,
`body_strike.py`.

**Acceptance.** Closed forms of a uniform rod are reproduced; the free and pinned limits are recovered; the jolt at the grip
is zero at the centre of percussion; a free blade never gives contact more energy than the swing has; the result feeds the
existing cut unchanged; defaults and existing tests do not move.

**Risks.** Mass and balance come from an informal source, inertia rests on an assumed taper, and the swing is the largest
unknown (§4). A table adopting this would change gameplay-facing results, so adoption is the owner's decision.

## 2. Physics (DERIVED, textbook rigid-body impulse)

The weapon is a straight rigid body, with mass `M`, centre of gravity `x_cg` and inertia `I_cg`. Positions run along its
axis from the centre of the grip. A normal impulse at `x` acts through the arm `r = x − x_cg`, so:

- **Effective mass at the impact point:** `1 / m_eff = 1 / M + r² / I_cg`. It equals `M` at the centre of gravity and falls
  towards the tip, because the blade rotates away from the target instead of pushing into it.
- **Speed at the impact point:** `v(x) = v_grip + ω x`.
- **Energy contact can take out of the swing:** `½ m_eff v²`. The layer models then spend `½ μ v²` against the target
  (`collision.split`, A14), which already works from `Blade.effective_mass_kg`.
- **Centre of percussion:** `x_cop = I_grip / (M x_cg)`. An impact there gives no jolt at the grip. The jolt per unit impulse
  is `1 / M + (x − x_cg)(0 − x_cg) / I_cg`, and it changes sign at `x_cop`.
- **The hand:** a mass `m_c` rigidly attached at the grip changes `M`, `x_cg` and `I_cg`. At `m_c = 0` the blade is free. At
  `m_c → ∞` the grip is a pin and `m_eff = I_grip / x²`. So the arm's coupling needs no invented blend: it is one parameter
  between two exact limits, and at `x_cop` it makes no difference.

## 3. Data

| Value | Used | Provenance | Source and limit |
|---|---|---|---|
| Mass | 0.9375 kg (830–975 g) | ESTIMATE | Median of six sabres weighed by Easton. Instrument and method not stated |
| Balance | 16.75 cm (14.5–19 cm) | ESTIMATE | Same. The source says "from hilt"; reading it as from the guard is ASSUMED |
| Blade length | 0.82 m (78–83 cm) | ESTIMATE | Same. Arc or straight line not stated; treated as straight, ASSUMED |
| Hand centre to guard | 0.07 m | ASSUMED | No source |
| Hilt centre of gravity | 0.03 m from the grip centre | ASSUMED | No source |
| Blade taper (density tip / guard) | 0.45, tried 0.25–0.7 | ASSUMED | No source; **this sets the inertia** |
| Inertia, centre of percussion | Calculated | ESTIMATE | **No measurement found for any sabre** |
| Tip speed | 10, 13, 17.55 m/s, tried | ESTIMATE | See below |
| Grip speed / tip speed | 0 and 0.3, tried | ASSUMED | No source |
| Hand, forearm mass | 0.46, 1.67 kg (75 kg body) | ESTIMATE | de Leva 1996 fractions (A14); lumping them at the grip is ASSUMED |

Of Easton's six, No. 6 is an 1850–60 revival and No. 5 is non-regulation with an extra curve. Both are kept; the median limits
their weight. The fit to the balance implies a hilt of about 0.45 kg and a blade of about 0.49 kg; neither was checked against a
real sabre.

**Tip speed.** Greene, Barona and Simon 2023 (J Emerg Invest, doi:10.59720/21-230) filmed a vertical sabre cut at 240 FPS, 3
elite and 3 novice fencers; a press summary describes the analysis as 2D. Read in the article: the method and the sample. **Not
verified:** the peak ranges 17.55–19.53 m/s (elite) and 12.97–14.93 m/s (novice) come from a search summary of the article, and
they could not be found in the text extracted from its PDF. It is secondary-school research, n = 6, with a sport weapon rather
than a 0.94 kg sabre, whose mass the article text extracted does not give. A heavier sabre should be slower, by an amount unknown.

## 4. Results (every value ESTIMATE)

Sabre by assumed taper:

| Tip / guard density | I_cg (kg·m²) | I_grip (kg·m²) | Centre of percussion (m from grip) |
|---|---|---|---|
| 0.25 | 0.0573 | 0.1102 | 0.495 |
| 0.45 | 0.0632 | 0.1160 | 0.521 |
| 0.7 | 0.0678 | 0.1207 | 0.542 |

Along the blade, tip at 15 m/s, pure rotation about the grip (grip speed 0):

| Point | v (m/s) | m_eff free (kg) | E free (J) | E hand (J) | E hand + forearm (J) | E pinned (J) | Grip jolt (m/s per N·s) |
|---|---|---|---|---|---|---|---|
| 0.30 m | 5.1 | 0.886 | 11.3 | 13.3 | 14.9 | 16.5 | +0.83 |
| COP (0.521 m) | 8.8 | 0.427 | 16.5 | 16.5 | 16.5 | 16.5 | +0.00 |
| 0.65 m | 11.0 | 0.266 | 16.0 | 16.2 | 16.4 | 16.5 | -0.48 |
| 0.75 m | 12.6 | 0.191 | 15.3 | 15.8 | 16.2 | 16.5 | -0.86 |
| Tip (0.89 m) | 15.0 | 0.128 | 14.4 | 15.3 | 15.9 | 16.5 | -1.39 |

Same tip speed, grip moving at 0.3 of it. In the coupled columns the arm keeps pushing at the grip's speed, so its own energy
adds to the blade's:

| Point | v (m/s) | m_eff free (kg) | E free (J) | E hand (J) | E hand + forearm (J) | E pinned (J) | Grip jolt (m/s per N·s) |
|---|---|---|---|---|---|---|---|
| 0.30 m | 8.0 | 0.886 | 28.6 | 33.6 | 37.7 | 41.7 | +0.83 |
| COP (0.521 m) | 10.6 | 0.427 | 24.2 | 24.2 | 24.2 | 24.2 | +0.00 |
| 0.65 m | 12.2 | 0.266 | 19.7 | 20.0 | 20.2 | 20.3 | -0.48 |
| 0.75 m | 13.3 | 0.191 | 17.0 | 17.7 | 18.0 | 18.4 | -0.86 |
| Tip (0.89 m) | 15.0 | 0.128 | 14.4 | 15.3 | 15.9 | 16.5 | -1.39 |

The cut against the placeholder, on the 17 segments, frontal central strike, target masses on (A14):

| Tip speed | Grip fraction | Point | m_eff (kg) | v (m/s) | E (J) | Deeper / shallower / same | Severity changed | Where it stops |
|---|---|---|---|---|---|---|---|---|
| placeholder | - | - | 0.600 | 10.0 | 30.0 | - | - | bone 16, viscera 1 |
| 10.0 | 0.0 | COP | 0.427 | 5.9 | 7.3 | 0 / 17 / 0 | 6 | bone 11, muscle 6 |
| 10.0 | 0.0 | tip | 0.128 | 10.0 | 6.4 | 0 / 17 / 0 | 6 | bone 9, muscle 6, tendon 2 |
| 10.0 | 0.3 | COP | 0.427 | 7.1 | 10.8 | 0 / 17 / 0 | 4 | bone 12, muscle 3, tendon 2 |
| 13.0 | 0.0 | COP | 0.427 | 7.6 | 12.4 | 0 / 17 / 0 | 1 | bone 12, muscle 1, tendon 3, viscera 1 |
| 13.0 | 0.0 | tip | 0.128 | 13.0 | 10.8 | 0 / 17 / 0 | 4 | bone 12, muscle 3, tendon 2 |
| 13.0 | 0.3 | COP | 0.427 | 9.2 | 18.2 | 0 / 17 / 0 | 0 | bone 15, tendon 1, viscera 1 |
| 17.55 | 0.0 | COP | 0.427 | 10.3 | 22.6 | 0 / 17 / 0 | 0 | bone 16, viscera 1 |
| 17.55 | 0.0 | tip | 0.128 | 17.6 | 19.7 | 2 / 15 / 0 | 0 | bone 15, tendon 1, viscera 1 |
| 17.55 | 0.3 | COP | 0.427 | 12.5 | 33.2 | 17 / 0 / 0 | 0 | bone 16, viscera 1 |

With the tip fixed, the grip fraction does not change the row for a tip impact (x = tip), so those duplicates are left out here;
the script prints them.

## 5. What this shows

1. **The placeholder's 30 J sits near the top of the range.** The model gives about 6 to 33 J. Only the fastest tip speed tried,
   with the grip also moving, reaches it. That speed is unverified and comes from a lighter weapon.
2. **The swing matters more than the impact point.** At 13 m/s the energy at the COP goes from 12.4 to 18.2 J with the grip
   moving, and 10 against 17.55 m/s roughly triples it. Going from COP to tip changes it by 13 % in pure rotation.
3. **In pure rotation, where it hits barely changes the energy; it changes how it is delivered.** With a pinned grip the energy
   is exactly `½ I_grip ω²` all along the blade. Towards the tip the same energy arrives as less mass at more speed. This cut
   model only counts energy, so it cannot show that difference; for a cut it matters as much as the energy may.
4. **The COP is a real point of this weapon, but what it fixes is the jolt.** Taper moves it by 4.7 cm in total. In pure
   rotation the free blade also has its energy peak there; with the grip moving, the peak moves towards the hilt.
5. **The arm's coupling is a small correction past the COP** (14.4 to 16.5 J at the tip). Before the COP, and with the grip
   moving, it is larger: there the arm's own energy enters.

## 6. Not modelled

Draw and slice cuts (a sliding edge cuts with less force in real materials, and this model ignores the tangential motion), edge
angle and sharpness, blade vibration and its nodes, blade flex, curvature, the blade rotating or the grip giving way during
contact, wound-channel length along the blade, and a hilt with its own inertia (about 3 % of `I_cg`, estimated). Validation
against a cut test or a measured sabre does not exist in this repository.

## 7. Pending

- **The owner decides** whether and when a table adopts this, and which swing. It moves A09 and A10 and needs its own decision.
- **Would most reduce the uncertainty:** swinging a real sabre (or a replica) with a pendulum test for `I_grip`, which needs only
  a stopwatch, plus a video of the cut for tip and grip speed. A measured period replaces the assumed taper directly.
- The speed values of Greene et al. should be read directly from the article.

## Sources

- M. Easton, *How much do 1796 pattern light cavalry sabres weigh?*, Easton Antique Arms, 2018, republished 2019:
  <https://www.antique-swords.co.uk/how-much-do-1796-pattern-light-cavalry-sabres-weigh>
- A. Greene, F. Barona, X. Simon, *The effect of joint angle differences on blade velocity in elite and novice saber fencers: a
  kinematic study*, J Emerg Invest, 2023, doi:10.59720/21-230: <https://emerginginvestigators.org/articles/21-230>
- B. Wendell, USA Fencing, 2023 summary of that study:
  <https://www.usafencing.org/news/2023/march/23/unraveling-the-hidden-complexities-of-saber-fencing-7-fascinating-findings-from-yale-researchers-study>
- de Leva 1996, as verified in `VERIFICACION_FUENTES_A14_A16.es.md`.
