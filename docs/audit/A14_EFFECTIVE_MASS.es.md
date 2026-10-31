# A14 — Masa efectiva del golpe: concepto, literatura y cómo debería usarla el motor

Nota de investigación, 2026-10-29. No se cambió código ni datos. Cada número de literatura se cita del resumen o de
un resumen secundario y queda marcado así; ninguno entró todavía en `source_registry`. Las relaciones físicas son
mecánica de libro (DERIVED, no necesitan fuente). Versión en inglés: `A14_EFFECTIVE_MASS.md`.

## 1. El concepto

Un golpe no es "el brazo" ni "el cuerpo" pegando contra el blanco. En el contacto solo una parte de la masa del que
golpea está acoplada a la superficie de impacto: el segmento del miembro más lo que arrastran las articulaciones
rigidizadas en el impacto. Esa parte acoplada es la **masa efectiva** `m_s`. Solo existe durante el choque y depende
de la técnica, de la rigidez articular en el contacto y de la compliance del blanco. No es una propiedad del cuerpo.

Lo mismo vale para el blanco. Una cabeza sobre un cuello relajado se comporta como unos pocos kilos; un torso
apoyado, como bastante más. A eso lo llamamos `m_t`.

En la literatura hay tres definiciones de trabajo, y dan **números distintos para la misma piña**:

| Definición | Fórmula | Qué mide |
|---|---|---|
| Impulso–cantidad de movimiento | `m_s = J / Δv_puño` | Cantidad de movimiento realmente transferida, dividida por el cambio de velocidad del puño |
| Fuerza / aceleración | `m_s = F_pico / a_puño` | Cociente instantáneo en el pico de fuerza (se infla cuando el puño frena poco) |
| Implemento rígido (arma) | `1/m_s = 1/M + b²/I_cm` | Arma de masa `M` e inercia `I_cm`, golpeada a una distancia `b` de su centro de masa. Mano y brazo suman más masa, reducida de la misma forma |

## 2. Qué reporta la literatura (piñas)

| Fuente | Método | Masa efectiva | Velocidad al impacto | Estado |
|---|---|---|---|---|
| Walilko, Viano y Bir 2005, *Br J Sports Med* 39:710–719: 7 boxeadores olímpicos, 18 rectos a la cara de un Hybrid III | Fuerza/aceleración sobre maniquí instrumentado | **2,9 ± 2,0 kg** (sube con la categoría de peso) | 9,14 ± 2,06 m/s; fuerza media ≈ 3427 N | Resumen / resúmenes secundarios, texto completo no leído |
| Lenetsky et al. 2015, *Hum Mov Sci* 40:89–97 (revisión) | Discute el concepto, los métodos y la activación muscular de "doble pico"; no hay protocolo estándar | cita ≈ 2,86 ± 2,03 kg para boxeadores | — | Resumen + resumen secundario |
| MDPI *Appl Sci* 14(17):7785 (2024): jab y recto de atrás | No leído (el sitio rechazó el acceso automatizado) | media **18,75 ± 5,40 kg** | — | Solo resumen del buscador |
| MDPI *Appl Sci* 15(7):4008 (2025): 30 boxeadores varones | No leído; la regresión muestra que la masa efectiva es el mejor predictor de la fuerza | jab **30,4 ± 15,1**, recto **31,2 ± 16,2**, ganchos **12,6–14,4 kg** | — | Solo resumen del buscador |
| Natale 2026, arXiv:2607.18276 (preprint) | Modelo 1D elástico de masas puntuales, relevamiento de literatura | la mayoría de los estudios **≈ 5 kg o menos**; ≈ 30 kg solo en una serie de trabajos; masa de un brazo 3,5–7 kg | típico 8–10 m/s, >10 m/s raro | HTML legible (en parte) |

**Lectura.** Los métodos con maniquí o por impulso dan 2–7 kg (un brazo más un poco de cuerpo). Fuerza sobre
aceleración contra blancos fijos da 15–30 kg, porque el puño casi no frena mientras la fuerza llega al pico, y el
cociente sale grande. Para simular importa la cantidad de movimiento realmente transferida, así que la familia baja
(impulso–cantidad de movimiento) es la elección físicamente coherente.

## 3. Patadas y armas

* **Patadas:** ninguna fuente revisada por pares que haya leído reporta masa efectiva en kg para varios tipos de
  patada en una misma muestra. Un caso de un solo sujeto (maestro ITF, 60 kg) da la patada frontal con la mayor
  masa efectiva, "44 %" de la masa corporal, y tiempos de contacto de 0,026 s (circular) a 0,119 s (frontal). Las
  fuerzas pico en estudios de taekwondo van de ≈ 700 a 3000 N. La masa efectiva de patada queda **UNKNOWN**. Una
  pierna es ≈ 16 % de la masa corporal (≈ 11–12 kg con 70 kg) según tablas estándar de segmentos, así que una
  patada estaría plausiblemente entre 1 y 2 veces la pierna, pero eso es un ESTIMATE a verificar.
* **Armas:** se usa la fórmula de implemento. Un ejemplo con bate de béisbol (Cross, citado en resultados de
  búsqueda; texto completo no legible) da una masa equivalente ≈ 0,8 kg para un bate de 0,9 kg golpeado cerca del
  centro de percusión. El valor cae rápido hacia la punta. No se encontró un valor con fuente para espadas. La masa
  efectiva de una hoja es menor que su masa salvo que el impacto sea cerca del centro de masa o de la mano. El brazo
  suma solo a través de la rigidez de la muñeca.

## 4. Qué significa para el motor (propuesta; el punto 1 está implementado como opción, ver §5)

1. **La energía que entra en las capas debería usar la masa reducida, no ½ m v².** En un contacto perfectamente
   inelástico, la energía disponible para deformar tejido es `E_def = ½ μ v²`, con `μ = m_s m_t / (m_s + m_t)`
   (DERIVED). Hoy `blunt.py` / `cut.py` gastan `½ m_s v²`, lo que supone un blanco inamovible. Ejemplos, todos
   DERIVED de los números de arriba:

   | Golpe | ½ m_s v² | absorbida contra cabeza (m_t 5 kg) | absorbida contra torso (m_t 35 kg) |
   |---|---|---|---|
   | piña, m_s 2,9 kg, 9,14 m/s | 121 J | 77 J | 112 J |
   | piña, m_s 18,75 kg, 9,14 m/s | 783 J | 165 J | 510 J |
   | garrote de la muestra 1,2 kg, 9 m/s | 48,6 J | 39 J | 47 J |
   | sable de la muestra 0,6 kg, 10 m/s | 30 J | 27 J | 29,5 J |

   Las armas livianas casi no cambian. Los golpes con el cuerpo a la cabeza cambian mucho. El resto
   (`½ (m_s − μ) v²`) pasa a movimiento del segmento entero, es decir, empuje y aceleración de la cabeza: es la
   entrada de un modelo de conmoción / derribo, no de daño de tejido.
2. **Masa efectiva del blanco por región** (`m_t`): pasa a ser una tabla nueva, con procedencia ESTIMATE hasta tener
   fuente. Cabeza + cuello ≈ 5–8 kg relajado; torso, decenas de kg; miembros, aproximadamente la masa del segmento.
   Apoyarse o rigidizar la sube.
3. **Masa efectiva del que golpea por técnica**: guardarla como rango con procedencia (piña 2–7 kg por impulso;
   patada UNKNOWN; armas con la fórmula de implemento y `M`, `I_cm` y punto de impacto por arma). Esto reemplaza el
   único `energy_j` por movimiento de `gameplay_shenmue.json`, cuyos valores (jab 60 J … proyección de hombro 260 J)
   no tienen registrada una descomposición en masa y velocidad.
4. **Tiempo de contacto** (se reportan 5–120 ms): es lo que separa fuerza pico de impulso. Conviene dejarlo como
   salida, no como entrada, hasta que exista un modelo de compliance.

## 5. Implementado (Decisión 58, opcional)

`domain/physics/collision.py`: `reduced_mass`, `split` (inelástico: deformación / cantidad de movimiento / velocidad
común, conserva energía y cantidad de movimiento), `regional_target_mass_kg(masa_corporal, bracing)` = masa
corporal × fracción del segmento (ESTIMATE, de Leva 1996, Tabla 4, varones: SOURCED, verificado contra el texto completo en `VERIFICACION_FUENTES_A14_A16.es.md`; cabeza y cuello llevan los dos el segmento cabeza + cuello a propósito, así que la tabla suma 106,94 %). `LayeredBody(...,
target_mass_kg=regional_target_mass_kg())` le pasa a `cut.py` / `blunt.py` (sin cambios) la energía de deformación y
reporta `StrikeResult.collision`. Apagado por defecto: ningún hash existente cambia.

Qué les hace a las armas de las muestras (segmentos relajados, cuerpo de 75 kg, golpe frontal al centro): el sable
conserva el 95 % de sus 30 J en tronco y muslo, pero solo el 43 % en una mano libre (0,46 kg), porque la mano sale
despedida en vez de cortarse. Una piña de 2,9 kg conserva el 64 % en la cabeza y el 80 % en el tórax.

Tabla de gameplay con cáscaras calibradas más masa reducida (`python scripts/gameplay_vs_layered.py --calibrated
--reduced-mass`; masas del atacante en el script, ESTIMATE):

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

Lectura: con un atacante pesado (una pierna entera, ≈ 15 kg) contra segmentos livianos, casi toda la energía de una
patada pasa a empuje, así que en daño de tejido las patadas ahora se leen como jabs, y la proyección de hombro (cuerpo
entero) baja a leve. Es físicamente coherente, pero deja ver dos huecos: las energías de los movimientos de la tabla
nunca se descompusieron en masa × velocidad, y el daño de una patada o una proyección es sobre todo cantidad de
movimiento (derribo, aceleración de la cabeza), que todavía ningún modelo consume. Las 5 fracturas que quedan en
todos los movimientos son manos y pies (cáscaras calibradas de 20–30 J).

Un criterio de fractura por fuerza construido sobre este módulo (fuerza pico contra rangos de fuerza por región,
energía de cráneo, profundidad desde la deflexión) está en `A15_STRIKE_MODEL.es.md` (`domain/physics/strike_model.py`,
enmienda a la Decisión 58).

Qué hace la parte de cantidad de movimiento (aceleración de la cabeza → probabilidad de conmoción, impulso →
tambaleo) está en `A16_HEAD_KINEMATICS_KNOCKDOWN.es.md` (`domain/physics/head_kinematics.py`, Decisión 59).

Los rangos de golpeador por movimiento con procedencia, y la sensibilidad del impacto en la cabeza a la palanca,
están en `A17_MOVE_STRIKERS.es.md` (`domain/physics/move_strikers.py`, Decisión 60).

## 6. Pendientes

1. Leer los textos completos (MDPI 2024/2025, Walilko 2005, Lenetsky 2015, Cross) y registrarlos en
   `source_registry` con las tablas exactas. El acceso automatizado fue rechazado, así que hacen falta los PDF que
   pueda conseguir el dueño.
2. Un conjunto de datos de patadas con fuente (frontal / circular / lateral) con masa efectiva en kg.
3. Masa efectiva de espada y palo a partir de masa, inercia y punto de impacto (requiere mediciones de armas reales).
4. Hacer que la energía por masa reducida sea la opción por defecto (cambia todos los hashes de resultados) cuando
   se verifiquen las fracciones y las masas del atacante; pasar `momentum_j` / `target_speed_m_s` a un modelo de
   derribo / conmoción.

Fuentes: las mismas que la versión en inglés (`A14_EFFECTIVE_MASS.md`, final del documento).
