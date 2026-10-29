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

## 4. Qué significa para el motor (propuesta, no aplicada)

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

## 5. Pendientes

1. Leer los textos completos (MDPI 2024/2025, Walilko 2005, Lenetsky 2015, Cross) y registrarlos en
   `source_registry` con las tablas exactas. El acceso automatizado fue rechazado, así que hacen falta los PDF que
   pueda conseguir el dueño.
2. Un conjunto de datos de patadas con fuente (frontal / circular / lateral) con masa efectiva en kg.
3. Masa efectiva de espada y palo a partir de masa, inercia y punto de impacto (requiere mediciones de armas reales).
4. Decisión del dueño: adoptar la energía por masa reducida en `blunt.py` / `cut.py` (cambia todos los hashes de
   resultados) y sumar la tabla regional de `m_t`. Requiere una entrada en el Decision Log.

Fuentes: las mismas que la versión en inglés (`A14_EFFECTIVE_MASS.md`, final del documento).
