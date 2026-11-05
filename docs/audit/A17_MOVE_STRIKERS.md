# A17 — Per-move striker records and head-impact sensitivity

Status: ESTIMATE / ASSUMED, additive and opt-in (Decision 60, kicks and fall: Decision 81). Code: `domain/physics/move_strikers.py`; tests:
`tests/unit/test_move_strikers.py`; tools: `scripts/head_sensitivity.py` (`--summary` for one line per move).
Nothing existing changes: `Striker.from_move`, `strike_model.py`, `head_kinematics.py` (hook lever arm stays 0.08 m),
the gameplay table and every earlier hash are as before. Spanish: `A17_MOVE_STRIKERS.es.md`.

## Per-move striker records

Each move of `gameplay_shenmue.json` gets effective mass, speed and head lever arm as low / nominal / high, with
provenance per field: SOURCED (read in a paper), ESTIMATE (derived from sourced numbers or the engine's estimates),
ASSUMED (placeholder). Sources: Walilko 2005 (2.9 ± 2.0 kg, 9.14 ± 2.06 m/s, straight punches); Mosler 2024 (velocity
at max force: jab 6.8, cross 8.6 m/s); Natale 2026 (kinematic punch mass 3.5–10 kg, preprint); the kick and fall sources
are listed below; segment fractions de Leva 1996 (SOURCED; A14). Rule: nominal ½ m v² must be within 25 % of the table's
`energy_j`; where it is not, the record carries a flag and the numbers are not bent.

| Move | m kg (low / nom / high) | v m/s (low / nom / high) | head lever m | E nominal J | E table J | nominal vs table | E range J | provenance |
|---|---|---|---|---|---|---|---|---|
| jab | 0.9 / 2.9 / 4.9 | 4.74 / 6.8 / 8.86 | 0.03 / 0.04 / 0.06 | 67 | 60 | ok +12 % | 10–192 | mass SOURCED, speed SOURCED, speed_range ESTIMATE, lever_arm ASSUMED |
| straight | 0.9 / 2.9 / 4.9 | 6.54 / 8.6 / 10.66 | 0.03 / 0.04 / 0.06 | 107 | 90 | ok +19 % | 19–278 | mass SOURCED, speed SOURCED, speed_range ESTIMATE, lever_arm ASSUMED |
| hook | 0.9 / 2.9 / 4.9 | 7.08 / 9.14 / 11.2 | 0.04 / 0.08 / 0.1 | 121 | 130 | ok -7 % | 23–307 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| elbow_assault | 3.5 / 5 / 10 | 6.8 / 8 / 9.14 | 0.04 / 0.08 / 0.1 | 160 | 170 | ok -6 % | 81–418 | mass ESTIMATE, speed ASSUMED, lever_arm ASSUMED |
| front_kick | 4.27 / 5.32 / 33 | 7.7 / 8.56 / 9.61 | 0.03 / 0.04 / 0.06 | 195 | 150 | **flag** +30 % | 127–1524 | mass ESTIMATE, mass_high ASSUMED, speed SOURCED, lever_arm ASSUMED |
| crescent_kick | 3.85 / 5.24 / 15.09 | 5.57 / 6.38 / 14.34 | 0.04 / 0.08 / 0.1 | 107 | 220 | **flag** -52 % | 60–1552 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| sweep | 3.85 / 5.24 / 15.09 | 5.57 / 6.38 / 14.34 | 0.03 / 0.04 / 0.06 | 107 | 140 | ok -24 % | 60–1552 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| shoulder_throw | 26.08 / 32.59 / 43.46 | 3.52 / 4.13 / 5.01 | 0.03 / 0.04 / 0.06 | 278 | 260 | ok +7 % | 162–545 | mass ESTIMATE, speed ESTIMATE, release_height ASSUMED, lever_arm ASSUMED |

### Flagged moves (nominal physics ≠ table energy)

* **front_kick (+30 %)**: the measured leg speeds give 195 J at maximum speed, against 150 J in the table. A novice
  gives 172 J and an elite 236 J, so the table sits a little below every level. It was +105 % when a whole leg was
  given a roundhouse foot speed.
* **crescent_kick (−52 %)**: no crescent data exists in what was read, so it carries roundhouse values. The energy a
  roundhouse delivers at impact is 86–138 J; its leg carries 395 J at maximum speed. The table's 220 J sits between the
  two, so it is possible but not what was measured at impact.
* The sweep (−24 %) and the throw (+7 %) are now inside the band, and the punches and the elbow stay there (jab +12 %,
  straight +19 %, hook −7 %, elbow −6 %). **The table was not changed**: whether a crescent kick should be worth 220 J
  is a gameplay decision for the owner.

## Kick effective mass

"Effective mass" names three different quantities in the kick literature, and they differ by a factor of ten. Only the
first two can go into ½ m v².

| Definition | Kick | Value | At 75 kg | Source |
|---|---|---|---|---|
| Leg energy at the foot's speed, 2E / v_foot² | front, novice / sub-elite / elite | DERIVED | 5.79 / 5.32 / 5.10 kg | Vagner 2023 Table 1 speeds, de Leva fractions |
| Same | roundhouse, elite | DERIVED | 3.85 kg | Vagner 2023 Table 2 |
| Impulse / foot speed at impact | roundhouse, Muay Thai / karate / taekwondo | 5.28 / 5.55 / 6.10 kg (8.0 / 6.6 / 6.4 % body) | 5.24 kg (mean 7.0 %) | DERIVED from Gavagan 2017, Tables 1-2 and Results |
| Peak force / foot acceleration | turning; side | 20.12 %; 73.09 % (medians, 4 men) | 15.1; 54.8 kg | Góra 2024 |
| Same method family, abstract only | turning; side | ≈ 18 %; ≈ 85 % (5 women) | 13.5; 63.8 kg | Góra 2025, Acta Bioeng Biomech |
| Not read directly | front | 44 % (one master) | 33 kg | Wąsik 2023, via A14 and Corcoran 2024 |

Reading: the two energy and momentum routes use different data and agree, at 4–6 kg, a little over the shank and foot
(4.27 kg). Force over acceleration is measured at one instant against a fixed plate, and it counts the rest of the body
braced behind the leg: real, but it is not the energy of a moving limb. It is kept only as the high bound. Góra's own
Discussion says the value "requires confirmation". `Striker.from_move` already gave 3.7–5.4 kg for these moves (9 m/s),
which is consistent with this.

Leg energy: `leg_chain_energy_j` gives thigh, shank and foot their de Leva masses, with thigh and shank at the mean speed
of their end joints (mid-length centre of mass, ASSUMED); rotation about the segment's own centre adds under 3 %.

Speeds differ just as much: a roundhouse reaches 13.2–14.7 m/s at its maximum but 5.6–7.2 m/s at impact, 41–54 % of the
maximum (Gavagan 2017). The front kick has no measured speed at impact in what was read, so its record uses the maximum,
which makes 195 J an upper estimate of what arrives. The ratio was not transferred from the roundhouse: a front kick
extends in a line, and 38 J would contradict its measured forces (2846 ± 805 N sub-elite, Vagner 2023).

## Fall model

`FallLanding` replaces a 75 kg striker falling on itself. It drops the body from a release height onto its back:

| Release height of the centre of mass (ASSUMED) | Speed m/s | Total fall energy J | Trunk J (32.6 kg) | Limbs and head J |
|---|---|---|---|---|
| 0.75 m, lowered by the thrower | 3.52 | 464 | 201 | 262 |
| 0.99 m, standing (0.55 × 1.80 m) | 4.13 | 640 | 278 | 362 |
| 1.40 m, lifted over the back | 5.01 | 942 | 409 | 533 |

The record is the trunk (thorax + abdomen + pelvis, 43.46 %), the part that lands as one block. Its 278 J sits at +7 % of
the table's 260 J; that agreement rests on two ASSUMED heights, so it is a plausibility check, not a validation. The
resting height of the centre of mass is 0.12 m (ASSUMED).

Measured head and neck loads for seoi-nage, which the head grid below must not override:

| Subject | Breakfall | Surface | Linear g | Angular rad/s² | Source |
|---|---|---|---|---|---|
| Dummy 75 kg, 5 throws by one expert | no | tatami over 60 mm sponge | 20.3 ± 9.8 (9.1–30.8) | 1890 ± 1152 (641–3195) | Murayama 2020 |
| Novice judoka | yes | not read | not read | 276 | Ishikawa 2018 as printed in Lockhart 2022 |

Same dummy setup, Nakanishi 2021: upper neck compression 4223 N, Nij median 0.68, beam criterion median 0.90. Reading:
seoi-nage stays below the Rowson 10 % line (5260 rad/s²) even without a breakfall, and the neck is the larger concern.
The head grid below still simulates a blow to the head, so for the throw it answers a different question.

## Head-impact sensitivity (no published lever arm exists for hooks)

This is a **sensitivity analysis, not a prediction**. No lever arm for hooks (or any blow) was found in the
literature read; the risk table (Rowson 2012) comes from helmeted American-football impacts, not from bare-headed or
gloved blows. Grid: lever arm 0.03 / 0.04 / 0.06 / 0.08 / 0.10 m × striker low / nominal / high (low mass with low
speed, and so on). `python scripts/head_sensitivity.py --summary`:

| Move | Default lever (m) | P at nominal, default lever | P range over the grid | alpha range (rad/s^2) |
|---|---|---|---|---|
| crescent_kick | 0.08 | 0.99 | 0.07-0.99 | 3494-39648 |
| elbow_assault | 0.08 | 0.99 | 0.08-0.99 | 4148-23768 |
| front_kick | 0.04 | 0.92 | 0.09-0.99 | 4972-28638 |
| hook | 0.08 | 0.99 | 0.05-0.99 | 2615-25008 |
| jab | 0.04 | 0.10 | 0.03-0.99 | 1751-19783 |
| shoulder_throw | 0.04 | 0.09 | 0.06-0.99 | 3092-15181 |
| straight | 0.04 | 0.60 | 0.05-0.99 | 2416-23802 |
| sweep | 0.04 | 0.24 | 0.07-0.99 | 3494-39648 |

Reading: every move spans almost the whole probability range (≈ 0.05 → 0.99). The Rowson curve is steep (10 % →
90 % between 5260 and 7483 rad/s²), so a lever arm change of 2 cm, well inside the ASSUMED band, moves a blow from
"unlikely" to "almost certain". **The concussion output is dominated by an unsourced parameter**: use it as an
ordering between moves at a fixed lever arm, not as a probability.

Full grid (`python scripts/head_sensitivity.py`):

### crescent_kick

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 3.85 | 5.57 | 2620 | 0.07 (3.5 k) | 0.09 (4.7 k) | 0.76 (7.0 k) | 0.99 (9.3 k) | 0.99 (11.6 k) |
| nominal | 5.24 | 6.38 | 3260 | 0.08 (4.3 k) | 0.24 (5.8 k) | 0.97 (8.7 k) | 0.99 (11.6 k) | 0.99 (14.5 k) |
| high | 15.09 | 14.34 | 8921 | 0.99 (11.9 k) | 0.99 (15.9 k) | 0.99 (23.8 k) | 0.99 (31.7 k) | 0.99 (39.6 k) |

### elbow_assault

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 3.5 | 6.8 | 3111 | 0.08 (4.1 k) | 0.17 (5.5 k) | 0.95 (8.3 k) | 0.99 (11.1 k) | 0.99 (13.8 k) |
| nominal | 5.0 | 8.0 | 4040 | 0.13 (5.4 k) | 0.82 (7.2 k) | 0.99 (10.8 k) | 0.99 (14.4 k) | 0.99 (18.0 k) |
| high | 10.0 | 9.14 | 5348 | 0.80 (7.1 k) | 0.99 (9.5 k) | 0.99 (14.3 k) | 0.99 (19.0 k) | 0.99 (23.8 k) |

### front_kick

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 4.27 | 7.7 | 3729 | 0.09 (5.0 k) | 0.61 (6.6 k) | 0.99 (9.9 k) | 0.99 (13.3 k) | 0.99 (16.6 k) |
| nominal | 5.32 | 8.56 | 4391 | 0.26 (5.9 k) | 0.92 (7.8 k) | 0.99 (11.7 k) | 0.99 (15.6 k) | 0.99 (19.5 k) |
| high | 33.0 | 9.61 | 6444 | 0.97 (8.6 k) | 0.99 (11.5 k) | 0.99 (17.2 k) | 0.99 (22.9 k) | 0.99 (28.6 k) |

### hook

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 0.9 | 7.08 | 1961 | 0.05 (2.6 k) | 0.07 (3.5 k) | 0.10 (5.2 k) | 0.76 (7.0 k) | 0.97 (8.7 k) |
| nominal | 2.9 | 9.14 | 3944 | 0.10 (5.3 k) | 0.77 (7.0 k) | 0.99 (10.5 k) | 0.99 (14.0 k) | 0.99 (17.5 k) |
| high | 4.9 | 11.2 | 5627 | 0.90 (7.5 k) | 0.99 (10.0 k) | 0.99 (15.0 k) | 0.99 (20.0 k) | 0.99 (25.0 k) |

### jab

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 0.9 | 4.74 | 1313 | 0.03 (1.8 k) | 0.04 (2.3 k) | 0.07 (3.5 k) | 0.09 (4.7 k) | 0.26 (5.8 k) |
| nominal | 2.9 | 6.8 | 2935 | 0.07 (3.9 k) | 0.10 (5.2 k) | 0.92 (7.8 k) | 0.99 (10.4 k) | 0.99 (13.0 k) |
| high | 4.9 | 8.86 | 4451 | 0.30 (5.9 k) | 0.93 (7.9 k) | 0.99 (11.9 k) | 0.99 (15.8 k) | 0.99 (19.8 k) |

### shoulder_throw

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 26.08 | 3.52 | 2319 | 0.06 (3.1 k) | 0.08 (4.1 k) | 0.41 (6.2 k) | 0.95 (8.2 k) | 0.99 (10.3 k) |
| nominal | 32.59 | 4.13 | 2767 | 0.07 (3.7 k) | 0.09 (4.9 k) | 0.87 (7.4 k) | 0.99 (9.8 k) | 0.99 (12.3 k) |
| high | 43.46 | 5.01 | 3416 | 0.09 (4.6 k) | 0.36 (6.1 k) | 0.99 (9.1 k) | 0.99 (12.1 k) | 0.99 (15.2 k) |

### straight

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 0.9 | 6.54 | 1812 | 0.05 (2.4 k) | 0.06 (3.2 k) | 0.09 (4.8 k) | 0.53 (6.4 k) | 0.93 (8.1 k) |
| nominal | 2.9 | 8.6 | 3711 | 0.09 (4.9 k) | 0.60 (6.6 k) | 0.99 (9.9 k) | 0.99 (13.2 k) | 0.99 (16.5 k) |
| high | 4.9 | 10.66 | 5356 | 0.80 (7.1 k) | 0.99 (9.5 k) | 0.99 (14.3 k) | 0.99 (19.0 k) | 0.99 (23.8 k) |

### sweep

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 3.85 | 5.57 | 2620 | 0.07 (3.5 k) | 0.09 (4.7 k) | 0.76 (7.0 k) | 0.99 (9.3 k) | 0.99 (11.6 k) |
| nominal | 5.24 | 6.38 | 3260 | 0.08 (4.3 k) | 0.24 (5.8 k) | 0.97 (8.7 k) | 0.99 (11.6 k) | 0.99 (14.5 k) |
| high | 15.09 | 14.34 | 8921 | 0.99 (11.9 k) | 0.99 (15.9 k) | 0.99 (23.8 k) | 0.99 (31.7 k) | 0.99 (39.6 k) |

Cell: concussion probability (rotational acceleration, thousands of rad/s^2).

## Limits

* Rotational velocity (Rowson's second column) is not added: with the same peak force, contact time and lever arm it
  follows from the same data and adds no information.
* The crescent kick and the sweep carry roundhouse numbers: no kinematic data for either was read.
* The front kick's push during contact (0.119 s in one subject) has no model. Its momentum is larger than its energy
  suggests, and only the 33 kg high bound hints at that.
* The fall has no contact time, peak ground force or surface: no landing force or body speed of a thrown person was
  read. Unread: Ishii & Koshida 2025 (the PDF could not be extracted), the Wąsik 2023 paper, a 2026 preprint on front-kick
  impulse (its site refused automated reading) and the 2001 harai-goshi sweep paper.
* Most subjects are small samples of trained men, and the measured kicks are mostly to pads, not bodies.
* Low / high combine low mass with low speed and high with high, so the energy range is the widest possible (kicks
  60–1552 J); real blows sit inside it.
* Lever arms, the elbow's speed and every kick / throw mass are ESTIMATE or ASSUMED.

## Open items

1. A sourced lever arm (or angular impulse) per blow type, or a boxing-specific risk function.
2. Measured speed at impact and impulse for the front kick, and any kinematic data for crescent kicks and sweeps.
3. Landing force and contact time of a thrown body, to add ground contact to `FallLanding`.

Closed (owner, 2026-11-15): the table energies of `front_kick` (150 J) and `crescent_kick` (220 J) stay as gameplay values; both
records keep their flag.
