# A17 — Registros de golpeador por movimiento y sensibilidad del impacto en la cabeza

Estado: ESTIMATE / ASSUMED, aditivo y opcional (Decisión 60). Código: `domain/physics/move_strikers.py`; tests:
`tests/unit/test_move_strikers.py`; herramientas: `scripts/head_sensitivity.py` (`--summary` para una línea por
movimiento). No cambia nada existente: `Striker.from_move`, `strike_model.py`, `head_kinematics.py` (la palanca del
gancho sigue en 0,08 m), la tabla de gameplay y todos los hashes anteriores quedan igual. Inglés: `A17_MOVE_STRIKERS.md`.

## Registros de golpeador por movimiento

Cada movimiento de `gameplay_shenmue.json` tiene masa efectiva, velocidad y brazo de palanca en la cabeza como
baja / nominal / alta, con procedencia por campo: SOURCED (leído en un trabajo), ESTIMATE (derivado de números con
fuente o de estimaciones del motor), ASSUMED (valor de relleno). Fuentes: Walilko 2005 (2,9 ± 2,0 kg, 9,14 ± 2,06
m/s, rectos); Mosler 2024 (velocidad en la fuerza máxima: jab 6,8, recto 8,6 m/s); Natale 2026 (masa cinemática de la
piña 3,5–10 kg, preprint); velocidad del pie en la patada circular 5,6–7,2 m/s (Gavagan y Sayers 2017); patadas de
hasta 18 m/s (Corcoran 2024); pierna entera ≈ 15 kg y fracciones de segmento (A14, ESTIMATE). Regla: ½ m v² nominal
debe quedar dentro del 25 % del `energy_j` de la tabla; si no, el registro lleva una marca y los números no se fuerzan.

| Movimiento | m kg (baja / nom / alta) | v m/s (baja / nom / alta) | palanca cabeza m | E nominal J | E tabla J | nominal vs tabla | rango E J | procedencia |
|---|---|---|---|---|---|---|---|---|
| jab | 0.9 / 2.9 / 4.9 | 4.74 / 6.8 / 8.86 | 0.03 / 0.04 / 0.06 | 67 | 60 | ok +12 % | 10–192 | mass SOURCED, speed SOURCED, speed_range ESTIMATE, lever_arm ASSUMED |
| straight | 0.9 / 2.9 / 4.9 | 6.54 / 8.6 / 10.66 | 0.03 / 0.04 / 0.06 | 107 | 90 | ok +19 % | 19–278 | mass SOURCED, speed SOURCED, speed_range ESTIMATE, lever_arm ASSUMED |
| hook | 0.9 / 2.9 / 4.9 | 7.08 / 9.14 / 11.2 | 0.04 / 0.08 / 0.1 | 121 | 130 | ok -7 % | 23–307 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| elbow_assault | 3.5 / 5 / 10 | 6.8 / 8 / 9.14 | 0.04 / 0.08 / 0.1 | 160 | 170 | ok -6 % | 81–418 | mass ESTIMATE, speed ASSUMED, lever_arm ASSUMED |
| front_kick | 4.27 / 15 / 33 | 5.6 / 6.4 / 18 | 0.03 / 0.04 / 0.06 | 307 | 150 | **marca** +105 % | 67–5346 | mass ESTIMATE, speed ESTIMATE, speed_high SOURCED, lever_arm ASSUMED |
| crescent_kick | 4.27 / 15 / 33 | 5.6 / 6.4 / 18 | 0.04 / 0.08 / 0.1 | 307 | 220 | **marca** +40 % | 67–5346 | mass ESTIMATE, speed SOURCED, speed_high SOURCED, lever_arm ASSUMED |
| sweep | 4.27 / 15 / 33 | 5.6 / 6.4 / 18 | 0.03 / 0.04 / 0.06 | 307 | 140 | **marca** +119 % | 67–5346 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| shoulder_throw | 40 / 75 / 100 | 3 / 4.41 / 5.5 | 0.03 / 0.04 / 0.06 | 729 | 260 | **marca** +181 % | 180–1512 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |

### Movimientos marcados (la física nominal no coincide con la energía de la tabla)

* **front_kick (+105 %), crescent_kick (+40 %), sweep (+119 %)**: una pierna entera (≈ 15 kg) a la velocidad medida
  del pie en la patada circular (6,4 m/s, mitad del rango) lleva ≈ 307 J; la tabla da 140–220 J. O la masa acoplada
  de una patada se parece más a pierna + pie (≈ 4,3 kg) que a la pierna entera, o las energías de la tabla son bajas.
  Ninguna fuente lo resuelve: no se encontró masa efectiva de patada en kg (A14).
* **shoulder_throw (+181 %)**: una proyección es el cuerpo del defensor cayendo; 75 kg cayendo desde la altura del
  centro de masa (4,41 m/s, DERIVED) son ≈ 729 J, la tabla tiene 260 J. La energía de la tabla se lee como una
  fracción de la energía de la caída, no como un golpe.
* Las piñas y el codazo quedan dentro de la banda (jab +12 %, recto +19 %, gancho −7 %, codazo −6 %).

## Sensibilidad del impacto en la cabeza (no hay brazo de palanca publicado para ganchos)

Esto es un **análisis de sensibilidad, no una predicción**. En la literatura leída no apareció un brazo de palanca
para ganchos (ni para ningún golpe); la tabla de riesgo (Rowson 2012) sale de impactos de fútbol americano con casco,
no de golpes a cabeza descubierta ni con guantes. Grilla: palanca 0,03 / 0,04 / 0,06 / 0,08 / 0,10 m × golpeador
bajo / nominal / alto (masa baja con velocidad baja, etc.). `python scripts/head_sensitivity.py --summary`:

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

Lectura: cada movimiento recorre casi todo el rango de probabilidad (≈ 0,05 → 0,99). La curva de Rowson es empinada
(10 % → 90 % entre 5260 y 7483 rad/s²), así que un cambio de 2 cm en la palanca, bien adentro de la banda ASSUMED,
lleva un golpe de "poco probable" a "casi seguro". **La salida de conmoción está dominada por un parámetro sin
fuente**: usarla para ordenar movimientos a palanca fija, no como probabilidad.

Grilla completa (`python scripts/head_sensitivity.py`):

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

## Límites

* No se agrega la velocidad rotacional (segunda columna de Rowson): con la misma fuerza pico, tiempo de contacto y
  palanca sale de los mismos datos y no aporta información.
* Las patadas y la proyección quedan marcadas, no resueltas; sus energías de tabla nunca se descompusieron en
  masa × velocidad.
* Bajo / alto combinan masa baja con velocidad baja y alta con alta, así que el rango de energía es el más amplio
  posible (patadas 67–5346 J); los golpes reales quedan adentro.
* Los brazos de palanca, la velocidad del codazo y todas las masas de patada / proyección son ESTIMATE o ASSUMED.

## Pendientes

1. Un brazo de palanca (o impulso angular) con fuente por tipo de golpe, o una función de riesgo propia del boxeo.
2. Una masa efectiva de patada en kg, para resolver las marcas de las patadas.
3. Un modelo de caída / proyección (contacto con el suelo) en vez de tratar la proyección como un golpe.
