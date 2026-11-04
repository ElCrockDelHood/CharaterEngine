# Verificación de fuentes de A14 / A15 / A16 contra los textos completos

Fecha: 2026-10-31. Alcance: solo lectura de fuentes y cotejo de números. No se modificó código
(`collision.py`, `strike_model.py`, `head_kinematics.py`, `move_strikers.py` son de otros hilos); las
correcciones quedan como PROPUESTAS al final.

Estados: **VERIFICADO** (texto completo leído), **VERIFICADO (resumen)** (solo el resumen oficial),
**PENDIENTE** (fuente no leída), **DISCREPANCIA**.

## Fuentes leídas

| Fuente | Qué se leyó | Dónde |
|---|---|---|
| de Leva 1996, *J Biomech* 29(9):1223–1230 | texto completo, Tablas 1 y 4 | PDF (copia ufabc.edu.br, descargado por Mariano) |
| Rowson et al. 2012, *Ann Biomed Eng* 40(1):1–13 | texto completo (versión PMC; nota: el artículo tiene una corrección del 16-11-2023) | PMC10465647 |
| Walilko, Viano y Bir 2005, *Br J Sports Med* 39(10):710–719 | resumen oficial (el texto completo es un PDF escaneado) | PMC1725037 |
| Sturnieks et al. 2013, *PLoS ONE* 8(8):e70981 | texto completo y Tabla 2 | journals.plos.org |
| Batcir et al. 2020, *BMC Geriatr* 20:249 (doi 10.1186/s12877-020-01650-4) | texto completo | bmcgeriatr.biomedcentral.com |
| Kennedy 2004, tesis de maestría Virginia Tech | resumen (el PDF no se pudo extraer) | vtechworks.lib.vt.edu/handle/10919/32216 |
| Delye et al. (cráneo, 18 cabezas) | resumen de la versión IUTAM 2005 | link.springer.com/doi/10.1007/1-4020-3796-1_19 |

## 1. Fracciones de masa de segmentos (de Leva 1996, Tabla 4, varones)

| Región del motor | Motor | de Leva (M) | de Leva (F) | Estado |
|---|---|---|---|---|
| HEAD | 0,0694 | 6,94 % | 6,68 % | VERIFICADO |
| NECK | 0,0694 | (no existe segmento cuello) | — | **DISCREPANCIA de modelado** |
| THORAX (UPT) | 0,1596 | 15,96 % | 15,45 % | VERIFICADO |
| ABDOMEN (MPT) | 0,1633 | 16,33 % | 14,65 % | VERIFICADO |
| PELVIS (LPT) | 0,1117 | 11,17 % | 12,47 % | VERIFICADO |
| UPPER_ARM | 0,0271 | 2,71 % | 2,55 % | VERIFICADO |
| FOREARM | 0,0162 | 1,62 % | 1,38 % | VERIFICADO |
| HAND | 0,0061 | 0,61 % | 0,56 % | VERIFICADO |
| THIGH | 0,1416 | 14,16 % | 14,78 % | VERIFICADO |
| LEG (shank) | 0,0433 | 4,33 % | 4,81 % | VERIFICADO |
| FOOT | 0,0137 | 1,37 % | 1,29 % | VERIFICADO |

Los diez valores coinciden exactamente con la columna de varones. Suma con brazos y piernas por
duplicado: 6,94 + 43,46 + 2 × 24,80 = 100,00 %.

**Discrepancia (modelado, no de dato):** en de Leva la cabeza va de *vertex* a *cervicale* (apófisis
espinosa de C7, Tabla 1), es decir que **6,94 % es cabeza + cuello**. El motor asigna 0,0694 a HEAD y otra
vez 0,0694 a NECK: el cuello cuenta dos veces (5,2 kg + 5,2 kg con 75 kg de cuerpo). Para la masa
efectiva de un golpe al cuello es defendible (cabeza y cuello se mueven juntos), pero el comentario del
código ("head and neck share the head+neck segment") no aclara que la suma de la tabla da 106,94 %.

Contexto de la muestra: Zatsiorsky et al., 100 varones (24 años, 73,0 kg, 1,741 m) y 15 mujeres (19 años,
61,9 kg); escaneo con rayos gamma de sujetos vivos. El cuerpo por defecto del motor (75 kg varón) es
compatible.

## 2. Conmoción (Rowson et al. 2012)

| Dato | Motor / A16 | Fuente | Estado |
|---|---|---|---|
| Riesgo 10/25/50/75/90 % (rad/s²) | 5260 / 5821 / 6383 / 6945 / 7483 | Tabla 3: igual | VERIFICADO |
| Velocidad rotacional para esos riesgos (rad/s) | 23,3 / 25,8 / 28,3 / 30,8 / 33,2 | Tabla 3: igual | VERIFICADO |
| Muestra | 335 jugadores, 300 977 impactos, 57 conmociones | igual (314 con HIT System, 21 con 6DOF) | VERIFICADO |
| Media de impactos con conmoción | ≈ 5000 rad/s², ≈ 100–106 g | 5022 ± 1791 rad/s², 22,3 rad/s; g por plano 102,7 / 105,8 / 100,6 (Tabla 4, no leída textual) | VERIFICADO / g PENDIENTE |
| Coeficientes logísticos | "se perdió un signo" (A16) | α = −12,531, β = 0,002 (impreso) | RESUELTO |

Nota sobre la logística: con β = 0,002 tal cual impreso el 50 % cae en 6266 rad/s², no en 6383; el β
impreso está redondeado (β ≈ 0,001963 reproduce la Tabla 3). Seguir interpolando la tabla, como hace el
motor, es la opción correcta. La rotacional ω ≈ α / 225,5 (s⁻¹, R² = 0,94) da la segunda columna si se
modela la velocidad.

## 3. Golpe de boxeo (Walilko, Viano y Bir 2005)

Todos los valores de A14 y A16 coinciden con el resumen oficial: fuerza 3427 ± 811 N; velocidad de la
mano 9,14 ± 2,06 m/s; masa efectiva 2,9 ± 2,0 kg; mandíbula 876 ± 288 N; aceleración traslacional
58 ± 13 g; rotacional 6343 ± 1789 rad/s²; corte en el cuello 994 ± 318 N; 7 boxeadores olímpicos de 5
categorías, 18 rectos. **VERIFICADO (resumen)**. PENDIENTE: fórmula de la masa efectiva y valores por
categoría (solo en el PDF escaneado).

## 4. Umbral de paso (Sturnieks 2013) y varios pasos (Batcir 2020)

| Dato | Motor / A16 | Fuente | Estado |
|---|---|---|---|
| Muestra | 242 adultos ≈ 80 años | 242 (132 varones, 110 mujeres), 80,0 ± 4,4 años | VERIFICADO |
| Perfil del tirón | rampa 300 ms, 200 ms sostenido, 100 ms bajada | igual | VERIFICADO |
| Umbral (N) adelante / atrás / lateral | 50,3 ± 14,0 / 45,6 ± 13,2 / 70,5 ± 21,1 | Tabla 2: igual (dirección del tirón) | VERIFICADO |
| Impulso derivado | "≈ 50 N sostenidos ≈ 0,35–0,5 s → 17–25 N·s" | área del trapecio = 0,15 + 0,20 + 0,05 = **0,40 s × F** | **DISCREPANCIA menor** |
| Varios pasos = 1,3 × un paso | Batcir 2020, "nivel 11,9 contra 8,9" | 11,90 ± 3,5 / 8,90 ± 3,5 en no caedores (1,34); 9,47 / 6,90 (1,37) en caedores de una vez; 10,27 / 8,08 (1,27) en recurrentes | **DISCREPANCIA de unidad** |

Detalle de las dos discrepancias:

* **Impulso.** Con el perfil real, el impulso del umbral es 0,40 × F: 20,1 N·s adelante, 18,2 N·s atrás,
  28,2 N·s lateral. El rango "17–25 N·s" debería ser "≈ 18–20 N·s antero-posterior, ≈ 28 N·s lateral".
  `P_STEP_N_S = 25` sigue siendo un supuesto razonable para un luchador joven (≈ 1,25–1,4 × el de un
  adulto de 80 años), pero su justificación cambia.
* **Unidad del 1,3.** Batcir no mide fuerza ni impulso: usa una **plataforma que se desplaza bajo los
  pies hacia los lados** con niveles ordinales de magnitud (desplazamiento 1–13 cm, velocidad y
  aceleración crecientes; tabla suplementaria 1). 11,90 / 8,90 es un cociente de **números de nivel**, no
  de fuerza. Aplicarlo a un umbral en N·s mezcla escalas; además los niveles no tienen por qué ser
  lineales en impulso. Recomendación: marcar `MULTI_STEP_RATIO = 1.3` como ASSUMED ("inspirado en el
  cociente de niveles de Batcir 2020, plataforma lateral, no convertible a N·s"). Muestra de Batcir: 83
  adultos (51 no caedores, 20 de una caída, 12 recurrentes).

Dato útil no usado: Sturnieks estima el umbral esperado con el peso corporal,
`E = 0,422·BW + 35,0` (antero-posterior) y `E = 0,1448·BW − 23,1` (lateral). El paper no aclara la unidad
de BW; con BW en kg y 75 kg da 66,7 N (AP), coherente con la Tabla 2. Serviría para escalar `P_STEP` con
la masa del personaje (PENDIENTE de confirmar la unidad).

## 5. Fuerzas de fractura (A15, `REGION_RESPONSE`)

| Región | Motor | Fuente leída | Estado |
|---|---|---|---|
| HEAD, energía 22–24 J | Delye 2007, 18 cabezas | 18 especímenes frescos, impacto frontal con doble péndulo, "22–24 J" sugerido; los autores piden más ensayos. La versión leída es de 2005 (IUTAM); el año 2007 no se confirmó | VERIFICADO (resumen); año PENDIENTE |
| THIGH, 3,8–4,8 kN medio, 45 fémures (Kennedy 2004) | | Resumen: 45 ensayos de flexión en tres puntos; momentos pico 352 ± 83 N·m (lateral) y 348 ± 96 N·m (posterior); 50 % de riesgo a 240 / 395 / 562 N·m para 5.ª mujer / 50.º varón / 95.º varón | **PENDIENTE**: el resumen da momentos, no kN. Las fuerzas en kN no se pudieron confirmar (el PDF no se pudo extraer) |
| THORAX, FOREARM, LEG | rangos "citados en una reseña" | no se identificó fuente primaria | PENDIENTE (siguen "weak") |
| NECK, ABDOMEN, PELVIS, UPPER_ARM, HAND, FOOT | ASSUMED | — | sin fuente, como ya declara el código |

Para el fémur, la cifra correcta de Kennedy es un **momento**: 395 N·m al 50 % para un varón percentil 50.
Pasarla a fuerza exige el brazo de palanca del golpe (en tres puntos, F = 4M / L con la luz L entre apoyos,
que no se leyó). Recomendación: guardar el criterio del muslo como momento o citar la luz al convertir.

## Propuestas (no aplicadas; requieren OK y al hilo dueño de cada módulo)

1. `collision.py`: cambiar el comentario de `SEGMENT_MASS_FRACTION` a VERIFIED para las diez fracciones
   (de Leva 1996, Tabla 4, varones) y documentar que NECK repite la masa cabeza + cuello a propósito (o
   bajarla, si se decide).
2. `head_kinematics.py`: el comentario de `P_STEP_N_S` pasa a "0,40 s × 45,6–50,3 N ≈ 18–20 N·s AP
   (Sturnieks 2013)"; `MULTI_STEP_RATIO` pasa a ASSUMED con la nota de unidad.
3. `strike_model.py`: THIGH cita a Kennedy como momento (395 N·m al 50 %) en vez de "3,8–4,8 kN" hasta
   leer la tesis completa.
4. A16: reemplazar "se perdió un signo" por los coeficientes α = −12,531, β = 0,002 (redondeado).
5. Pendientes de lectura: PDF de Walilko (fórmula de masa efectiva), tesis de Kennedy (fuerzas en kN y
   luz), fuentes primarias de tórax, antebrazo y tibia.
