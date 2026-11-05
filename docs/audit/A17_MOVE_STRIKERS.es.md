# A17 — Registros de golpeador por movimiento y sensibilidad del impacto en la cabeza

Estado: ESTIMATE / ASSUMED, aditivo y opcional (Decisión 60, patadas y caída: Decisión 81). Código: `domain/physics/move_strikers.py`; tests:
`tests/unit/test_move_strikers.py`; herramientas: `scripts/head_sensitivity.py` (`--summary` para una línea por
movimiento). No cambia nada existente: `Striker.from_move`, `strike_model.py`, `head_kinematics.py` (la palanca del
gancho sigue en 0,08 m), la tabla de gameplay y todos los hashes anteriores quedan igual. Inglés: `A17_MOVE_STRIKERS.md`.

## Registros de golpeador por movimiento

Cada movimiento de `gameplay_shenmue.json` tiene masa efectiva, velocidad y brazo de palanca en la cabeza como
baja / nominal / alta, con procedencia por campo: SOURCED (leído en un trabajo), ESTIMATE (derivado de números con
fuente o de estimaciones del motor), ASSUMED (valor de relleno). Fuentes: Walilko 2005 (2,9 ± 2,0 kg, 9,14 ± 2,06 m/s, rectos); Mosler 2024 (velocidad en la fuerza máxima: jab 6,8,
recto 8,6 m/s); Natale 2026 (masa cinemática de la piña 3,5–10 kg, preprint); las fuentes de patadas y caída están más
abajo; fracciones de segmento de Leva 1996 (SOURCED; A14). Regla: ½ m v² nominal debe quedar dentro del 25 % del
`energy_j` de la tabla; si no, el registro lleva una marca y los números no se fuerzan.

| Movimiento | m kg (baja / nom / alta) | v m/s (baja / nom / alta) | palanca cabeza m | E nominal J | E tabla J | nominal vs tabla | rango E J | procedencia |
|---|---|---|---|---|---|---|---|---|
| jab | 0.9 / 2.9 / 4.9 | 4.74 / 6.8 / 8.86 | 0.03 / 0.04 / 0.06 | 67 | 60 | ok +12 % | 10–192 | mass SOURCED, speed SOURCED, speed_range ESTIMATE, lever_arm ASSUMED |
| straight | 0.9 / 2.9 / 4.9 | 6.54 / 8.6 / 10.66 | 0.03 / 0.04 / 0.06 | 107 | 90 | ok +19 % | 19–278 | mass SOURCED, speed SOURCED, speed_range ESTIMATE, lever_arm ASSUMED |
| hook | 0.9 / 2.9 / 4.9 | 7.08 / 9.14 / 11.2 | 0.04 / 0.08 / 0.1 | 121 | 130 | ok -7 % | 23–307 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| elbow_assault | 3.5 / 5 / 10 | 6.8 / 8 / 9.14 | 0.04 / 0.08 / 0.1 | 160 | 170 | ok -6 % | 81–418 | mass ESTIMATE, speed ASSUMED, lever_arm ASSUMED |
| front_kick | 4.27 / 5.32 / 33 | 7.7 / 8.56 / 9.61 | 0.03 / 0.04 / 0.06 | 195 | 150 | **marca** +30 % | 127–1524 | mass ESTIMATE, mass_high ASSUMED, speed SOURCED, lever_arm ASSUMED |
| crescent_kick | 3.85 / 5.24 / 15.09 | 5.57 / 6.38 / 14.34 | 0.04 / 0.08 / 0.1 | 107 | 220 | **marca** -52 % | 60–1552 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| sweep | 3.85 / 5.24 / 15.09 | 5.57 / 6.38 / 14.34 | 0.03 / 0.04 / 0.06 | 107 | 140 | ok -24 % | 60–1552 | mass ESTIMATE, speed ESTIMATE, lever_arm ASSUMED |
| shoulder_throw | 26.08 / 32.59 / 43.46 | 3.52 / 4.13 / 5.01 | 0.03 / 0.04 / 0.06 | 278 | 260 | ok +7 % | 162–545 | mass ESTIMATE, speed ESTIMATE, release_height ASSUMED, lever_arm ASSUMED |

### Movimientos marcados (la física nominal no coincide con la energía de la tabla)

* **front_kick (+30 %)**: las velocidades medidas de la pierna dan 195 J a velocidad máxima, contra 150 J de la tabla.
  Un novato da 172 J y un elite 236 J, así que la tabla queda un poco por debajo de todos los niveles. Antes era +105 %,
  cuando se le daba a la pierna entera la velocidad del pie de una patada circular.
* **crescent_kick (−52 %)**: en lo leído no hay datos de esta patada, así que lleva valores de patada circular. La
  energía que una circular entrega en el impacto es 86–138 J; su pierna lleva 395 J a velocidad máxima. Los 220 J de la
  tabla quedan entre ambos: es posible, pero no es lo que se midió en el impacto.
* La barrida (−24 %) y la proyección (+7 %) ahora quedan dentro de la banda, y las piñas y el codazo siguen adentro (jab
  +12 %, recto +19 %, gancho −7 %, codazo −6 %). **La tabla no se cambió**: si una crescent kick debe valer 220 J es una
  decisión de gameplay del dueño.

## Masa efectiva de una patada

"Masa efectiva" nombra tres cantidades distintas en la literatura de patadas, y difieren en un factor de diez. Solo las
dos primeras pueden entrar en ½ m v².

| Definición | Patada | Valor | Con 75 kg | Fuente |
|---|---|---|---|---|
| Energía de la pierna a la velocidad del pie, 2E / v_pie² | frontal, novato / sub-elite / elite | DERIVED | 5,79 / 5,32 / 5,10 kg | velocidades de Vagner 2023 Tabla 1, fracciones de de Leva |
| Igual | circular, elite | DERIVED | 3,85 kg | Vagner 2023 Tabla 2 |
| Impulso / velocidad del pie en el impacto | circular, muay thai / karate / taekwondo | 5,28 / 5,55 / 6,10 kg (8,0 / 6,6 / 6,4 % del cuerpo) | 5,24 kg (media 7,0 %) | DERIVED de Gavagan 2017, Tablas 1-2 y Resultados |
| Fuerza pico / aceleración del pie | turning; side | 20,12 %; 73,09 % (medianas, 4 hombres) | 15,1; 54,8 kg | Góra 2024 |
| Misma familia de método, solo resumen | turning; side | ≈ 18 %; ≈ 85 % (5 mujeres) | 13,5; 63,8 kg | Góra 2025, Acta Bioeng Biomech |
| No leído directamente | frontal | 44 % (un maestro) | 33 kg | Wąsik 2023, vía A14 y Corcoran 2024 |

Lectura: las dos vías de energía y de cantidad de movimiento usan datos distintos y coinciden, en 4–6 kg, un poco por
encima de pierna + pie (4,27 kg). Fuerza sobre aceleración se mide en un instante contra una placa fija y cuenta el resto
del cuerpo apoyado detrás de la pierna: es real, pero no es la energía de un miembro en movimiento. Queda solo como cota
alta. La propia Discusión de Góra dice que el valor "requires confirmation". `Striker.from_move` ya daba 3,7–5,4 kg para
estos movimientos (9 m/s), lo cual es coherente con esto.

Energía de la pierna: `leg_chain_energy_j` da a muslo, pierna y pie sus masas de de Leva, con muslo y pierna a la
velocidad media de sus articulaciones extremas (centro de masa a media longitud, ASSUMED); la rotación sobre el centro
propio del segmento agrega menos del 3 %.

Las velocidades difieren igual de mucho: una circular llega a 13,2–14,7 m/s en su máximo pero a 5,6–7,2 m/s en el impacto,
41–54 % del máximo (Gavagan 2017). La frontal no tiene velocidad medida en el impacto en lo leído, así que su registro usa
el máximo, y por eso 195 J es una estimación alta de lo que llega. El cociente de la circular no se trasladó: una frontal
se extiende en línea, y 38 J contradirían sus fuerzas medidas (2846 ± 805 N sub-elite, Vagner 2023).

## Modelo de caída

`FallLanding` reemplaza a un golpeador de 75 kg cayendo sobre sí mismo. Deja caer el cuerpo de espaldas desde una altura
de suelta:

| Altura de suelta del centro de masa (ASSUMED) | Velocidad m/s | Energía total J | Tronco J (32,6 kg) | Miembros y cabeza J |
|---|---|---|---|---|
| 0,75 m, bajado por quien proyecta | 3,52 | 464 | 201 | 262 |
| 0,99 m, de pie (0,55 × 1,80 m) | 4,13 | 640 | 278 | 362 |
| 1,40 m, levantado sobre la espalda | 5,01 | 942 | 409 | 533 |

El registro es el tronco (tórax + abdomen + pelvis, 43,46 %), la parte que aterriza como un bloque. Sus 278 J quedan a +7 %
de los 260 J de la tabla; esa coincidencia se apoya en dos alturas ASSUMED, así que es un control de plausibilidad, no una
validación. La altura de reposo del centro de masa es 0,12 m (ASSUMED).

Cargas medidas de cabeza y cuello en seoi-nage, que la grilla de cabeza de abajo no debe contradecir:

| Sujeto | Caída con técnica | Superficie | g lineal | Angular rad/s² | Fuente |
|---|---|---|---|---|---|
| Maniquí 75 kg, 5 proyecciones de un experto | no | tatami sobre esponja de 60 mm | 20,3 ± 9,8 (9,1–30,8) | 1890 ± 1152 (641–3195) | Murayama 2020 |
| Judoca novato | sí | no leída | no leído | 276 | Ishikawa 2018 según Lockhart 2022 |

Mismo montaje, Nakanishi 2021: compresión de cuello superior 4223 N, Nij mediana 0,68, criterio de viga mediana 0,90.
Lectura: el seoi-nage queda por debajo de la línea del 10 % de Rowson (5260 rad/s²) incluso sin técnica de caída, y lo que
más preocupa es el cuello. La grilla de cabeza de abajo sigue simulando un golpe en la cabeza, así que para la proyección
responde otra pregunta.

## Sensibilidad del impacto en la cabeza (no hay brazo de palanca publicado para ganchos)

Esto es un **análisis de sensibilidad, no una predicción**. En la literatura leída no apareció un brazo de palanca
para ganchos (ni para ningún golpe); la tabla de riesgo (Rowson 2012) sale de impactos de fútbol americano con casco,
no de golpes a cabeza descubierta ni con guantes. Grilla: palanca 0,03 / 0,04 / 0,06 / 0,08 / 0,10 m × golpeador
bajo / nominal / alto (masa baja con velocidad baja, etc.). `python scripts/head_sensitivity.py --summary`:

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

Lectura: cada movimiento recorre casi todo el rango de probabilidad (≈ 0,05 → 0,99). La curva de Rowson es empinada
(10 % → 90 % entre 5260 y 7483 rad/s²), así que un cambio de 2 cm en la palanca, bien adentro de la banda ASSUMED,
lleva un golpe de "poco probable" a "casi seguro". **La salida de conmoción está dominada por un parámetro sin
fuente**: usarla para ordenar movimientos a palanca fija, no como probabilidad.

Grilla completa (`python scripts/head_sensitivity.py`):

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

## Límites

* No se agrega la velocidad rotacional (segunda columna de Rowson): con la misma fuerza pico, tiempo de contacto y
  palanca sale de los mismos datos y no aporta información.
* La crescent kick y la barrida llevan números de patada circular: no se leyeron datos cinemáticos de ninguna.
* El empuje de la frontal durante el contacto (0,119 s en un sujeto) no tiene modelo. Su cantidad de movimiento es mayor
  de lo que sugiere su energía, y solo la cota alta de 33 kg lo insinúa.
* La caída no tiene tiempo de contacto, fuerza pico contra el suelo ni superficie: no se leyó fuerza de aterrizaje ni
  velocidad del cuerpo de una persona proyectada. Sin leer: Ishii y Koshida 2025 (no se pudo extraer el PDF), el trabajo
  de Wąsik 2023, un preprint de 2026 sobre impulso de la frontal (el sitio rechazó la lectura automática) y el trabajo de
  2001 sobre barrida en harai-goshi.
* La mayoría de las muestras son chicas y de hombres entrenados, y casi todas las patadas medidas van a escudos, no a cuerpos.
* Bajo / alto combinan masa baja con velocidad baja y alta con alta, así que el rango de energía es el más amplio
  posible (patadas 60–1552 J); los golpes reales quedan adentro.
* Los brazos de palanca, la velocidad del codazo y todas las masas de patada / proyección son ESTIMATE o ASSUMED.

## Pendientes

1. Un brazo de palanca (o impulso angular) con fuente por tipo de golpe, o una función de riesgo propia del boxeo.
2. Velocidad en el impacto e impulso medidos de la frontal, y cualquier dato cinemático de crescent kick y barrida.
3. Fuerza de aterrizaje y tiempo de contacto de un cuerpo proyectado, para agregar el contacto con el suelo a `FallLanding`.

Cerrado (dueño, 2026-11-15): las energías de tabla de `front_kick` (150 J) y `crescent_kick` (220 J) quedan como valores de juego;
los dos registros conservan su marca.
