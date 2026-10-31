# A16 — Cinemática de la cabeza, probabilidad de conmoción y tambaleo por empuje

Estado: ESTIMATE / ASSUMED, aditivo y opcional (Decisión 59). Código: `domain/physics/head_kinematics.py`; tests:
`tests/unit/test_head_kinematics.py`; herramienta: `scripts/gameplay_head_kinematics.py`. Se apoya en `collision.py`
(Decisión 58, A14) y `strike_model.py` (A15). No cambia nada existente: `blunt.py`, `body_strike.py`,
`strike_model.py`, la tabla de gameplay y todos los hashes anteriores quedan igual. Inglés: `A16_HEAD_KINEMATICS_KNOCKDOWN.md`.

## Números con fuente (páginas leídas por la sesión coordinadora; los textos completos no están en el repositorio)

| Fuente | Qué | Valores |
|---|---|---|
| Walilko, Viano y Bir 2005, *Br J Sports Med* 39(10):710 | 7 boxeadores olímpicos, 18 rectos a la cara de un Hybrid III | fuerza 3427 ± 811 N; velocidad de la mano 9,14 ± 2,06 m/s; masa efectiva 2,9 ± 2,0 kg; carga en mandíbula 876 ± 288 N; aceleración lineal de la cabeza 58 ± 13 g; aceleración rotacional 6343 ± 1789 rad/s²; corte en el cuello 994 ± 318 N |
| Rowson et al. 2012, *Ann Biomed Eng* 40(1):1–13 | 335 jugadores de fútbol americano, 300 977 impactos, 57 conmociones | probabilidad de conmoción según aceleración / velocidad rotacional: 10 % 5260 rad/s² / 23,3 rad/s; 25 % 5821 / 25,8; 50 % 6383 / 28,3; 75 % 6945 / 30,8; 90 % 7483 / 33,2. Impactos con conmoción: media ≈ 100–106 g, ≈ 5000 rad/s² |
| Sturnieks et al. 2013, *PLoS ONE* 8(8):e70981 | 242 adultos de ≈ 80 años, tirón en la cintura (rampa 300 ms, 200 ms sostenido, 100 ms de bajada) | umbral de paso de recuperación 50,3 ± 14,0 N adelante, 45,6 ± 13,2 N atrás, 70,5 ± 21,1 N lateral |
| Batcir et al. 2020, *BMC Geriatr* 20:249 | 83 adultos de 70+ | nivel de varios pasos ≈ 1,3 × el de un paso (11,9 contra 8,9) en una plataforma que se desplaza hacia los lados: cociente de niveles ordinales, no de fuerza ni de impulso |

El ajuste logístico de Rowson es α = −12,531, β = 0,002 (β impreso redondeado: con 0,002 el 50 % cae en 6266 rad/s²; β ≈ 0,001963 reproduce la tabla con error menor a 0,01 en las cinco filas, con test). La implementación sigue interpolando la tabla. Fuentes verificadas en `VERIFICACION_FUENTES_A14_A16.es.md`.

## Modelo

1. **Aceleración lineal** `a = F_pico / M_cabeza`: `F_pico` de `strike_model.peak_force` para la región cabeza,
   `M_cabeza` = 5,2 kg de la tabla compartida (`collision.py`, ESTIMATE).
2. **Aceleración rotacional** `α = F_pico · d / I_cabeza`: brazo de palanca `d` ASSUMED 0,04 m (recto) o 0,08 m (tipo
   gancho); `I_cabeza` ASSUMED 0,0225 kg·m² (rango 0,02–0,025, sin verificar).
3. **Probabilidad de conmoción**: tabla de Rowson 2012 sobre `α`, lineal entre filas; de 0 a 10 % lineal entre 0 y
   5260 rad/s², de 90 a 99 % lineal entre 7483 y 9000 rad/s² (colas ASSUMED).
4. **Tambaleo**: impulso `J = μ · v` que recibe el cuerpo a través del segmento golpeado (inelástico, `collision.py`).
   Un paso a `P_PASO` = 25 N·s (ASSUMED para un peleador joven). Adultos mayores: área fuerza–tiempo del tirón en
   la cintura 0,40 s × F (Sturnieks 2013), ≈ 20 / 18 / 28 N·s adelante / atrás / lateral (DERIVED de valores con
   fuente). Varios pasos a 1,3 × (ASSUMED, inspirado en los niveles de plataforma de Batcir 2020), caída a 2 ×
   (ASSUMED). `bracing` ≥ 1 multiplica los
   umbrales. `knocked_down` = caída o probabilidad de conmoción ≥ 0,5.

## Aceptación (medias de Walilko: Striker 2,9 kg, 9,14 m/s, radio de contacto 0,04 m, a la cabeza)

| Magnitud | Modelo | Medido | Cota | Resultado |
|---|---|---|---|---|
| Fuerza pico | 3944 N | 3427 ± 811 N | dentro del 35 % | +15 %, pasa |
| Aceleración lineal | 77,3 g | 58 ± 13 g | dentro de × 1,5 | × 1,33, pasa |
| Aceleración rotacional (d 0,04 m) | 7012 rad/s² | 6343 ± 1789 rad/s² | dentro de × 2 | × 1,11, pasa |
| Probabilidad de conmoción | 0,77 | (≈ nivel 50 % de Rowson) | 0,2–0,9 | pasa |

No se ajustó ninguna constante a estos números. La aceleración lineal queda 1,5 desvíos por encima de la media
medida: la cabeza golpeada se modela como una masa libre de 5,2 kg, mientras que el cuello del Hybrid III se lleva
parte de la carga.

## Movimientos de gameplay que pegan en la cabeza (solo lectura; `python scripts/gameplay_head_kinematics.py`)

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

## Qué dice esto y qué no

* Los golpes rectos dan valores razonables: jab ≈ 10 %, recto ≈ 30 %, patadas a la cabeza 85–90 %.
* **Los golpes tipo gancho saturan en 0,99**: con `d` = 0,08 m todo gancho, codazo y patada creciente supera la fila
  superior de Rowson (13–16 mil rad/s²). El brazo de palanca es ASSUMED y la tabla de fútbol americano no se armó con
  golpes a cabeza descubierta ni con guantes; hasta tener un brazo de palanca con fuente o una curva de riesgo de
  boxeo, la probabilidad de los ganchos es una cota superior.
* **Ningún golpe a la cabeza hace tambalear al cuerpo**: la cabeza (5,2 kg) toma poca cantidad de movimiento
  (≤ 24 N·s < 25 N·s). Los golpes al cuerpo sí (impulso en el tórax de una patada creciente ≈ 33 N·s → un paso); el
  camino de la cabeza termina en conmoción, no en tambaleo.
* La proyección de hombro no es un golpe a la cabeza; aparece acá solo porque su movimiento lista hitboxes de cabeza.
* No modelado: velocidad rotacional e impulso angular (Rowson también da umbrales de velocidad), rigidez del cuello,
  guantes, golpes acumulados, dirección de la rotación, barridas (quitan el apoyo), datos de equilibrio en adultos
  jóvenes (umbrales ASSUMED), historia temporal (solo picos).

Una grilla de sensibilidad sobre palanca y rango de golpeador para cada movimiento que pega en la cabeza está en
`A17_MOVE_STRIKERS.es.md` (Decisión 60): cada movimiento recorre aproximadamente 0,05–0,99.

## Pendientes

1. Velocidad rotacional / impulso angular, para poder usar la segunda columna de Rowson.
2. Un brazo de palanca con fuente por tipo de golpe, o una función de riesgo propia del boxeo.
3. Datos de perturbación del equilibrio en adultos jóvenes para reemplazar `P_PASO`.
4. Inercia de la cabeza y acople con el cuello desde un modelo cabeza–cuello con fuente.
