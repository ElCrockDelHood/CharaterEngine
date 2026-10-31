# A14 — Effective mass of a strike: concept, literature, and how the engine should use it

Research note, 2026-10-29. No code or data changed. Every literature number below is quoted from the cited
abstract or a secondary summary and is marked accordingly; none is entered into `source_registry` yet. Physics
relations are textbook mechanics (DERIVED, no source needed). Spanish version: `A14_EFFECTIVE_MASS.es.md`.

## 1. The concept

A strike is not "the arm" or "the body" hitting the target. At contact only part of the striker's mass is coupled
to the striking surface: the limb segment plus whatever the joints, stiffened at impact, drag along. That coupled
part is the **effective mass** `m_s`. It exists only during the collision. It depends on technique, joint
stiffness at contact, and target compliance. It is not a property of the body.

The same applies to the target. A head on a relaxed neck behaves like a few kilograms. A braced torso behaves like
much more. Call that `m_t`.

Three working definitions appear in the literature, and they give **different numbers for the same punch**:

| Definition | Formula | What it measures |
|---|---|---|
| Impulse–momentum | `m_s = J / Δv_fist` | Momentum actually transferred, divided by the fist's speed change |
| Force / acceleration | `m_s = F_peak / a_fist` | Instantaneous ratio at the force peak (inflated when the fist decelerates little) |
| Rigid implement (weapon) | `1/m_s = 1/M + b²/I_cm` | Weapon of mass `M` and inertia `I_cm`, struck at distance `b` from its centre of mass. The hand and arm add more mass, reduced the same way |

## 2. What the literature reports (punches)

| Source | Method | Effective mass | Speed at impact | Status |
|---|---|---|---|---|
| Walilko, Viano & Bir 2005, *Br J Sports Med* 39:710–719: 7 Olympic boxers, 18 straight punches into a Hybrid III face | Force/acceleration on an instrumented dummy | **2.9 ± 2.0 kg** (increases with weight class) | 9.14 ± 2.06 m/s; mean force ≈ 3427 N | Abstract / secondary summaries, full text not read |
| Lenetsky et al. 2015, *Hum Mov Sci* 40:89–97 (review) | Discusses the concept, the methods and "double peak" muscle activation; no standard protocol exists | cites ≈ 2.86 ± 2.03 kg for boxers | — | Abstract + secondary summary |
| MDPI *Appl Sci* 14(17):7785 (2024): jab and rear cross | Not read (site refused automated access) | mean **18.75 ± 5.40 kg** | — | Search-engine summary only |
| MDPI *Appl Sci* 15(7):4008 (2025): 30 male boxers | Not read; regression shows effective mass is the strongest predictor of force | jab **30.4 ± 15.1**, cross **31.2 ± 16.2**, hooks **12.6–14.4 kg** | — | Search-engine summary only |
| Natale 2026, arXiv:2607.18276 (preprint) | 1D elastic point-mass model, literature survey | most studies **≈ 5 kg or less**; ≈ 30 kg only in one paper series; single-arm mass 3.5–7 kg | typical 8–10 m/s, >10 m/s rare | Readable HTML (partly) |

**Reading.** Dummy and impulse-based methods give 2–7 kg (one arm plus a little body). Force-over-acceleration
on fixed targets gives 15–30 kg, because the fist barely decelerates while the force peaks, so the ratio is
large. For simulation, the momentum actually transferred is what matters, so the low family (impulse-momentum) is
the physically consistent choice.

## 3. Kicks and weapons

* **Kicks:** no peer-reviewed source read reports effective mass in kg for several kick types in one sample. A
  single-subject case (ITF master, 60 kg) reports the front kick with the highest effective mass, "44 %" of body
  mass, and contact times of 0.026 s (roundhouse) to 0.119 s (front kick). Peak forces in taekwondo studies span
  ≈ 700–3000 N. Treat kick effective mass as **UNKNOWN**. A leg is ≈ 16 % of body mass (≈ 11–12 kg at 70 kg) by
  standard segment tables, so a kick plausibly sits at 1–2 × the leg, but that is an ESTIMATE to verify.
* **Weapons:** use the implement formula. A baseball-bat example (Cross, cited in search results; full text not
  readable) gives an equivalent mass ≈ 0.8 kg for a 0.9 kg bat struck near the centre of percussion. The value
  drops fast toward the tip. No sourced value for swords was found. A blade's effective mass is below its mass
  unless the impact is near the centre of mass or the hand. The arm adds to it only through the wrist's stiffness.

## 4. What this means for the engine (proposal; item 1 implemented opt-in, see §5)

1. **Energy into the layers should use the reduced mass, not ½ m v².** In a perfectly inelastic contact, the
   energy available to deform tissue is `E_def = ½ μ v²`, with `μ = m_s m_t / (m_s + m_t)` (DERIVED). Today
   `blunt.py` / `cut.py` spend `½ m_s v²`, which assumes an immovable target. Examples, all DERIVED from the numbers
   above:

   | Striker | ½ m_s v² | absorbed vs head (m_t 5 kg) | absorbed vs torso (m_t 35 kg) |
   |---|---|---|---|
   | punch, m_s 2.9 kg, 9.14 m/s | 121 J | 77 J | 112 J |
   | punch, m_s 18.75 kg, 9.14 m/s | 783 J | 165 J | 510 J |
   | club sample 1.2 kg, 9 m/s | 48.6 J | 39 J | 47 J |
   | sabre sample 0.6 kg, 10 m/s | 30 J | 27 J | 29.5 J |

   Light weapons barely change. Body strikes into the head change a lot. The rest (`½ (m_s − μ) v²`) becomes
   whole-segment motion, which is knockback and head acceleration: the input for a concussion / knockdown model,
   not for tissue damage.
2. **Target effective mass per region** (`m_t`) becomes a new table, provenance ESTIMATE until sourced. Head + neck
   ≈ 5–8 kg relaxed; torso tens of kg; limbs about segment mass. Bracing raises it.
3. **Striker effective mass per technique** should be stored as a range with provenance (punch 2–7 kg
   impulse-based; kick UNKNOWN; weapons from the implement formula with a per-weapon `M`, `I_cm`, impact point).
   This replaces the single `energy_j` per move in `gameplay_shenmue.json`, whose values (jab 60 J … shoulder throw
   260 J) have no recorded mass/speed decomposition.
4. **Contact time** (5–120 ms reported) is what separates peak force from impulse. Keep it as an output, not an
   input, until a compliance model exists.

## 5. Implemented (Decision 58, opt-in)

`domain/physics/collision.py`: `reduced_mass`, `split` (inelastic: deformation / momentum / common speed, energy and
momentum conserved), `regional_target_mass_kg(body_mass, bracing)` = body mass × segment fraction (ESTIMATE, de Leva
1996 recalled). `LayeredBody(..., target_mass_kg=regional_target_mass_kg())` feeds the unchanged `cut.py` /
`blunt.py` with the deformation energy and reports `StrikeResult.collision`. Default off: no existing hash changes.

What it does to the sample weapons (relaxed segments, 75 kg body, frontal centre): the sabre keeps 95 % of its 30 J on
the trunk and thigh, but only 43 % on a free hand (0.46 kg), because the hand flies away instead of being cut. A
2.9 kg punch keeps 64 % on the head and 80 % on the thorax.

Gameplay table with calibrated shells plus reduced mass (`python scripts/gameplay_vs_layered.py --calibrated
--reduced-mass`; striker masses in the script, ESTIMATE):

| Move | Energy (J) | Legacy severity | Layered severity | Layered fractures (of 21) |
|---|---|---|---|---|
| crescent_kick | 220.0 | 1x1, 2x20 | 2x20, 4x1 | 5 |
| elbow_assault | 170.0 | 1x5, 2x16 | 2x16, 4x1, 5x4 | 5 |
| front_kick | 150.0 | 1x13, 2x8 | 2x20, 4x1 | 5 |
| hook | 130.0 | 1x13, 2x8 | 2x20, 4x1 | 5 |
| jab | 60.0 | 1x21 | 2x20, 4x1 | 5 |
| shoulder_throw | 260.0 | 2x21 | 1x19, 2x2 | 0 |
| straight | 90.0 | 1x21 | 2x20, 4x1 | 5 |
| sweep | 140.0 | 1x13, 2x8 | 2x20, 4x1 | 5 |

168 pairs: layered higher in 87, lower in 19.

Reading: with a heavy striker (a whole leg, ≈ 15 kg) against light segments, most of a kick's energy becomes
knockback, so kicks now read like jabs in tissue damage, and the shoulder throw (whole body) drops to minor. That is
physically consistent but exposes two gaps: the move energies in the table were never decomposed into mass × speed,
and the damage a kick or throw does is mostly momentum (knockdown, head acceleration), which no model consumes yet.
The 5 fractures left on every move are hands and feet (20–30 J calibrated shells).

A force-based fracture criterion built on this module (peak force against per-region force ranges, skull energy,
depth from deflection) is in `A15_STRIKE_MODEL.md` (`domain/physics/strike_model.py`, amendment to Decision 58).

What the momentum part does (head acceleration → concussion probability, impulse → stagger) is in
`A16_HEAD_KINEMATICS_KNOCKDOWN.md` (`domain/physics/head_kinematics.py`, Decision 59).

Per-move striker ranges with provenance, and the head-impact sensitivity to the lever arm, are in
`A17_MOVE_STRIKERS.md` (`domain/physics/move_strikers.py`, Decision 60).

## 6. Open items

1. Read the full texts (MDPI 2024/2025, Walilko 2005, Lenetsky 2015, Cross) and register them in `source_registry`
   with exact tables. Automated access was refused, so this needs PDFs from the owner.
2. A sourced kick dataset (front / roundhouse / side) with effective mass in kg.
3. Sword and stick effective mass from mass, inertia and impact point (needs real weapon measurements).
4. Make the reduced-mass energy the default (changes every result hash) once the fractions and striker masses are
   verified; feed `momentum_j` / `target_speed_m_s` to a knockdown / concussion model.

Sources: [Walilko et al. 2005 (Semantic Scholar)](https://www.semanticscholar.org/paper/Biomechanics-of-the-head-for-Olympic-boxer-punches-Walilko-Viano/edbd929ed7812c983b4780fc106ecdf716b58a30) ·
[Lenetsky et al. 2015 (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0167945714002140) ·
[MDPI Appl Sci 14(17):7785](https://www.mdpi.com/2076-3417/14/17/7785) ·
[MDPI Appl Sci 15(7):4008](https://www.mdpi.com/2076-3417/15/7/4008) ·
[Natale 2026, arXiv:2607.18276](https://arxiv.org/abs/2607.18276) ·
[Natale 2026, arXiv:2609.25476](https://arxiv.org/abs/2609.25476) ·
[ITF kick effective mass (ResearchGate)](https://www.researchgate.net/publication/367041559_Conception_of_effective_mass_and_effect_of_force_-_measurement_of_taekwon-do_master) ·
[Gavagan & Sayers 2017, roundhouse kick (PLOS ONE)](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0182645) ·
[Cross, sweet spot of a baseball bat](https://baseball.physics.illinois.edu/CrossSweetSpotBat.pdf) ·
[Center of percussion (Wikipedia)](https://en.wikipedia.org/wiki/Center_of_percussion)
