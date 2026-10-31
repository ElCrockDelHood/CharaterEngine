# A17 — Per-move striker records and head-impact sensitivity

Status: ESTIMATE / ASSUMED, additive and opt-in (Decision 60). Code: `domain/physics/move_strikers.py`; tests:
`tests/unit/test_move_strikers.py`; tools: `scripts/head_sensitivity.py` (`--summary` for one line per move).
Nothing existing changes: `Striker.from_move`, `strike_model.py`, `head_kinematics.py` (hook lever arm stays 0.08 m),
the gameplay table and every earlier hash are as before. Spanish: `A17_MOVE_STRIKERS.es.md`.

## Per-move striker records

Each move of `gameplay_shenmue.json` gets effective mass, speed and head lever arm as low / nominal / high, with
provenance per field: SOURCED (read in a paper), ESTIMATE (derived from sourced numbers or the engine's estimates),
ASSUMED (placeholder). Sources: Walilko 2005 (2.9 ± 2.0 kg, 9.14 ± 2.06 m/s, straight punches); Mosler 2024 (velocity
at max force: jab 6.8, cross 8.6 m/s); Natale 2026 (kinematic punch mass 3.5–10 kg, preprint); roundhouse foot speed
5.6–7.2 m/s (Gavagan & Sayers 2017); kicks up to 18 m/s (Corcoran 2024); whole leg ≈ 15 kg (ESTIMATE) from segment fractions
(de Leva 1996, SOURCED; A14). Rule: nominal ½ m v² must be within 25 % of the table's `energy_j`; where it is not, the record
carries a flag and the numbers are not bent.

| Move | m kg (low / nom / high) | v m/s (low / nom / high) | head lever m | E nominal J | E table J | nominal vs table | E range J | provenance |
|---|---|---|---|---|---|---|---|---|
| jab | 0.9 / 2.9 / 4.9 | 4.74 / 6.8 / 8.86 | 0.03 / 0.04 / 0.06 | 67 | 60 | ok +12 % | 10–192 | mass SOURCED, speed SOURCED, speed_range ESTIMATE, lever_arm ASSUMED |
| straight | 0.9 / 2.9 / 4.9 | 6.54 / 8.6 / 10.66 | 0.03 / 0.04 / 0.06 | 107 | 90 | ok +19 % | 19–278 | mass SOURCED, speed SOURCED, speed_range ESTIMATE, lever_arm ASSUMED |
| hook | 0.9 / 2.9 / 4.9 | 7.08 / 9.14 / 11.2 | 0.04 / 0.08 / 0.1 | 121 | 130 | ok -7 % | 23–307 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| elbow_assault | 3.5 / 5 / 10 | 6.8 / 8 / 9.14 | 0.04 / 0.08 / 0.1 | 160 | 170 | ok -6 % | 81–418 | mass ESTIMATE, speed ASSUMED, lever_arm ASSUMED |
| front_kick | 4.27 / 15 / 33 | 5.6 / 6.4 / 18 | 0.03 / 0.04 / 0.06 | 307 | 150 | **flag** +105 % | 67–5346 | mass ESTIMATE, speed ESTIMATE, speed_high SOURCED, lever_arm ASSUMED |
| crescent_kick | 4.27 / 15 / 33 | 5.6 / 6.4 / 18 | 0.04 / 0.08 / 0.1 | 307 | 220 | **flag** +40 % | 67–5346 | mass ESTIMATE, speed SOURCED, speed_high SOURCED, lever_arm ASSUMED |
| sweep | 4.27 / 15 / 33 | 5.6 / 6.4 / 18 | 0.03 / 0.04 / 0.06 | 307 | 140 | **flag** +119 % | 67–5346 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| shoulder_throw | 40 / 75 / 100 | 3 / 4.41 / 5.5 | 0.03 / 0.04 / 0.06 | 729 | 260 | **flag** +181 % | 180–1512 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |

### Flagged moves (nominal physics ≠ table energy)

* **front_kick (+105 %), crescent_kick (+40 %), sweep (+119 %)**: a whole leg (≈ 15 kg) at the measured roundhouse
  foot speed (6.4 m/s mid-range) carries ≈ 307 J; the table gives 140–220 J. Either the coupled mass of a kick is
  closer to the shank + foot (≈ 4.3 kg) than to the whole leg, or the table energies are low. No source settles it:
  no kick effective mass in kg was found (A14).
* **shoulder_throw (+181 %)**: a throw is the defender's body landing; 75 kg falling from centre-of-mass height
  (4.41 m/s, DERIVED) is ≈ 729 J, the table has 260 J. The table energy reads as a fraction of the fall energy, not
  as a strike.
* Punches and the elbow sit within the band (jab +12 %, straight +19 %, hook −7 %, elbow −6 %).

## Head-impact sensitivity (no published lever arm exists for hooks)

This is a **sensitivity analysis, not a prediction**. No lever arm for hooks (or any blow) was found in the
literature read; the risk table (Rowson 2012) comes from helmeted American-football impacts, not from bare-headed or
gloved blows. Grid: lever arm 0.03 / 0.04 / 0.06 / 0.08 / 0.10 m × striker low / nominal / high (low mass with low
speed, and so on). `python scripts/head_sensitivity.py --summary`:

| Move | Default lever (m) | P at nominal, default lever | P range over the grid | alpha range (rad/s^2) |
|---|---|---|---|---|
| crescent_kick | 0.08 | 0.99 | 0.07-0.99 | 3616-53641 |
| elbow_assault | 0.08 | 0.99 | 0.08-0.99 | 4148-23768 |
| front_kick | 0.04 | 0.79 | 0.07-0.99 | 3616-53641 |
| hook | 0.08 | 0.99 | 0.05-0.99 | 2615-25008 |
| jab | 0.04 | 0.10 | 0.03-0.99 | 1751-19783 |
| shoulder_throw | 0.04 | 0.16 | 0.05-0.99 | 2715-17194 |
| straight | 0.04 | 0.60 | 0.05-0.99 | 2416-23802 |
| sweep | 0.04 | 0.79 | 0.07-0.99 | 3616-53641 |

Reading: every move spans almost the whole probability range (≈ 0.05 → 0.99). The Rowson curve is steep (10 % →
90 % between 5260 and 7483 rad/s²), so a lever arm change of 2 cm, well inside the ASSUMED band, moves a blow from
"unlikely" to "almost certain". **The concussion output is dominated by an unsourced parameter**: use it as an
ordering between moves at a fixed lever arm, not as a probability.

Full grid (`python scripts/head_sensitivity.py`):

### crescent_kick

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 4.27 | 5.6 | 2712 | 0.07 (3.6 k) | 0.09 (4.8 k) | 0.83 (7.2 k) | 0.99 (9.6 k) | 0.99 (12.1 k) |
| nominal | 15.0 | 6.4 | 3978 | 0.11 (5.3 k) | 0.79 (7.1 k) | 0.99 (10.6 k) | 0.99 (14.1 k) | 0.99 (17.7 k) |
| high | 33.0 | 18.0 | 12069 | 0.99 (16.1 k) | 0.99 (21.5 k) | 0.99 (32.2 k) | 0.99 (42.9 k) | 0.99 (53.6 k) |

### elbow_assault

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 3.5 | 6.8 | 3111 | 0.08 (4.1 k) | 0.17 (5.5 k) | 0.95 (8.3 k) | 0.99 (11.1 k) | 0.99 (13.8 k) |
| nominal | 5.0 | 8.0 | 4040 | 0.13 (5.4 k) | 0.82 (7.2 k) | 0.99 (10.8 k) | 0.99 (14.4 k) | 0.99 (18.0 k) |
| high | 10.0 | 9.14 | 5348 | 0.80 (7.1 k) | 0.99 (9.5 k) | 0.99 (14.3 k) | 0.99 (19.0 k) | 0.99 (23.8 k) |

### front_kick

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 4.27 | 5.6 | 2712 | 0.07 (3.6 k) | 0.09 (4.8 k) | 0.83 (7.2 k) | 0.99 (9.6 k) | 0.99 (12.1 k) |
| nominal | 15.0 | 6.4 | 3978 | 0.11 (5.3 k) | 0.79 (7.1 k) | 0.99 (10.6 k) | 0.99 (14.1 k) | 0.99 (17.7 k) |
| high | 33.0 | 18.0 | 12069 | 0.99 (16.1 k) | 0.99 (21.5 k) | 0.99 (32.2 k) | 0.99 (42.9 k) | 0.99 (53.6 k) |

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
| low | 40.0 | 3.0 | 2036 | 0.05 (2.7 k) | 0.07 (3.6 k) | 0.15 (5.4 k) | 0.83 (7.2 k) | 0.99 (9.0 k) |
| nominal | 75.0 | 4.41 | 3077 | 0.08 (4.1 k) | 0.16 (5.5 k) | 0.94 (8.2 k) | 0.99 (10.9 k) | 0.99 (13.7 k) |
| high | 100.0 | 5.5 | 3869 | 0.10 (5.2 k) | 0.72 (6.9 k) | 0.99 (10.3 k) | 0.99 (13.8 k) | 0.99 (17.2 k) |

### straight

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 0.9 | 6.54 | 1812 | 0.05 (2.4 k) | 0.06 (3.2 k) | 0.09 (4.8 k) | 0.53 (6.4 k) | 0.93 (8.1 k) |
| nominal | 2.9 | 8.6 | 3711 | 0.09 (4.9 k) | 0.60 (6.6 k) | 0.99 (9.9 k) | 0.99 (13.2 k) | 0.99 (16.5 k) |
| high | 4.9 | 10.66 | 5356 | 0.80 (7.1 k) | 0.99 (9.5 k) | 0.99 (14.3 k) | 0.99 (19.0 k) | 0.99 (23.8 k) |

### sweep

| Striker | m (kg) | v (m/s) | F_peak (N) | d = 0.03 m | d = 0.04 m | d = 0.06 m | d = 0.08 m | d = 0.1 m |
|---|---|---|---|---|---|---|---|---|
| low | 4.27 | 5.6 | 2712 | 0.07 (3.6 k) | 0.09 (4.8 k) | 0.83 (7.2 k) | 0.99 (9.6 k) | 0.99 (12.1 k) |
| nominal | 15.0 | 6.4 | 3978 | 0.11 (5.3 k) | 0.79 (7.1 k) | 0.99 (10.6 k) | 0.99 (14.1 k) | 0.99 (17.7 k) |
| high | 33.0 | 18.0 | 12069 | 0.99 (16.1 k) | 0.99 (21.5 k) | 0.99 (32.2 k) | 0.99 (42.9 k) | 0.99 (53.6 k) |

Cell: concussion probability (rotational acceleration, thousands of rad/s^2).

## Limits

* Rotational velocity (Rowson's second column) is not added: with the same peak force, contact time and lever arm it
  follows from the same data and adds no information.
* Kicks and the throw are flagged, not resolved; their table energies were never decomposed into mass × speed.
* Low / high combine low mass with low speed and high with high, so the energy range is the widest possible (kicks
  67–5346 J); real blows sit inside it.
* Lever arms, the elbow's speed and every kick / throw mass are ESTIMATE or ASSUMED.

## Open items

1. A sourced lever arm (or angular impulse) per blow type, or a boxing-specific risk function.
2. A kick effective mass in kg, to resolve the kick flags.
3. A fall / throw model (ground contact) instead of treating the throw as a strike.
