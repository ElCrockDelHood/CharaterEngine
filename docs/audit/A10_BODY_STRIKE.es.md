# A10 — Golpe sobre el cuerpo completo con capas (muestra de material 3, Python puro)

Estado: ESTIMATE / ASSUMED en todo. Nada de esto está medido. Código: `domain/physics/body_strike.py`, tests: `tests/unit/test_body_strike.py`.

## Qué es

La interfaz única de contacto para el mockup de pelea: `LayeredBody(points)` arma una cápsula con capas por cada segmento del block dummy (17, huecas donde la región tiene cavidad), y `strike(weapon, origin, direction)` devuelve el segmento golpeado, el punto, la incidencia, cuánto penetraron las capas y el `Wound` / `WoundAssessment` de `assess_wound`, que no se tocó. Las armas son el `Blade` (modelo de corte) y el `Impactor` (modelo de aplastamiento) que ya existían. Las prendas son capas exteriores opcionales por segmento.

## Simplificaciones (todas quedan en el resultado)

- El rayo choca con la envolvente de piel de la primera cápsula que encuentra. Los segmentos que se superponen (hombro, cadera, cuello bajo la esfera del tórax) no se resuelven.
- Los modelos de capas son unidimensionales a través del espesor, así que solo cuenta la componente normal: energía x cos(incidencia)^2. Los golpes rasantes pierden casi toda la energía; la parte tangencial se descarta, no se convierte en un tajo.
- No hay simulación de tela (eso queda en las muestras XPBD): las prendas son capas de material simples.
- Solo se tabulan golpes centrales; los golpes descentrados usan la misma cuerda a través de las capas (aproximación).

## Resultados (golpe frontal central, uno por segmento, determinista: prefijo sha256 de la tabla sable `286ab4a06de9758e`, garrote `60ffb62fb53165fa`)

Sable: 0,6 kg de masa efectiva (PLACEHOLDER) a 10 m/s (ESTIMATE), 30 J.

| Segment | Hit | Stopped in | Depth (mm) | Severity | Deepest layer | Fracture |
|---|---|---|---|---|---|---|
| head | self | bone | 15.6 | SERIOUS | bone | no |
| neck | thorax | tendon | 48.5 | SERIOUS | tendon | no |
| thorax | self | bone | 50.9 | SERIOUS | bone | no |
| abdomen | self | viscera | 97.4 | CRITICAL | viscera | no |
| pelvis | self | bone | 78.7 | SERIOUS | bone | no |
| upper_arm.L | self | bone | 44.7 | SERIOUS | bone | no |
| forearm.L | self | bone | 39.6 | SERIOUS | bone | no |
| hand.L | self | through | 36.0 | SERIOUS | bone | no |
| thigh.L | self | bone | 69.8 | SERIOUS | bone | no |
| leg.L | self | bone | 48.3 | SERIOUS | bone | no |
| foot.L | self | bone | 33.2 | SERIOUS | bone | no |
| upper_arm.R | self | bone | 44.7 | SERIOUS | bone | no |
| forearm.R | self | bone | 39.6 | SERIOUS | bone | no |
| hand.R | self | through | 36.0 | SERIOUS | bone | no |
| thigh.R | self | bone | 69.8 | SERIOUS | bone | no |
| leg.R | self | bone | 48.3 | SERIOUS | bone | no |
| foot.R | self | bone | 33.2 | SERIOUS | bone | no |

Garrote: 1,2 kg (PLACEHOLDER) a 9 m/s (ESTIMATE), 48,6 J, radio de contacto 30 mm.

| Segment | Hit | Stopped in | Depth (mm) | Severity | Deepest layer | Fracture |
|---|---|---|---|---|---|---|
| head | self | through | 85.0 | CRITICAL | viscera | yes |
| neck | thorax | bone | 48.7 | MODERATE | tendon | no |
| thorax | self | through | 130.0 | CRITICAL | viscera | yes |
| abdomen | self | through | 130.0 | SEVERE | viscera | yes |
| pelvis | self | through | 140.0 | SEVERE | viscera | yes |
| upper_arm.L | self | through | 50.0 | MODERATE | bone | yes |
| forearm.L | self | through | 40.0 | MODERATE | bone | yes |
| hand.L | self | through | 18.0 | MODERATE | bone | yes |
| thigh.L | self | through | 80.0 | MODERATE | bone | yes |
| leg.L | self | through | 55.0 | MODERATE | bone | yes |
| foot.L | self | through | 30.0 | MODERATE | bone | yes |
| upper_arm.R | self | through | 50.0 | MODERATE | bone | yes |
| forearm.R | self | through | 40.0 | MODERATE | bone | yes |
| hand.R | self | through | 18.0 | MODERATE | bone | yes |
| thigh.R | self | through | 80.0 | MODERATE | bone | yes |
| leg.R | self | through | 55.0 | MODERATE | bone | yes |
| foot.R | self | through | 30.0 | MODERATE | bone | yes |

## Qué dicen las tablas y qué no

- La fila del tórax reproduce exactamente la muestra 2 (garrote: 130 mm, costillas fracturadas, severidad 5). La fila del cuello golpea el bloque del tórax, porque ese bloque es una esfera que cubre el cuello desde el frente: es un problema de forma del block dummy, no de las capas.
- Todos los huesos largos se fracturan con el garrote (energía de fractura del hueso 25 J, ASSUMED, todo o nada). Es consecuencia de una constante sin fuente, no un hallazgo sobre brazos. El sable amputa la mano y se detiene en el hueso en el resto, por la energía de corte del hueso (ASSUMED).
- La severidad sale de las reglas de trauma existentes, que no se cambiaron. Donde la conversión legacy de 400 J y este modelo discrepan (muestra 2), la discrepancia se reporta, no se resuelve: reemplazar la constante es decisión del hilo de heridas.

## Puntos abiertos

1. Resolver la superposición de segmentos y una intersección rayo-cápsula propia (hoy la búsqueda avanza de a 2 mm y bisecta).
2. Longitud de cuerda para golpes descentrados y una componente de tajo para cortes rasantes.
3. Portar a Godot (donde vive el mockup de pelea): el modelo es aritmética simple sobre capas, sin solver, así que se porta directo; la parte de tela no.
4. Las constantes ajustadas (energía de fractura y de corte del hueso, mesetas de aplastamiento) necesitan fuentes antes de afirmar nada sobre cuerpos reales.

## Apéndice: el modelo en capas contra la tabla de gameplay vigente

`scripts/gameplay_vs_layered.py` (solo lectura) convierte cada uno de los 168 pares (movimiento, hueso de hitbox) de `gameplay_shenmue.json` en un golpe contundente frontal central (energía cinética y radio de contacto del movimiento) y compara la severidad con la conversión legacy de 400 J que ya está en la tabla.

Catálogo por defecto (una sola energía de 25 J para la cáscara rígida en todo el cuerpo):

| Move | Energy (J) | Legacy severity | Layered severity | Layered fractures (of 21) |
|---|---|---|---|---|
| crescent_kick | 220.0 | 1x1, 2x20 | 2x8, 4x2, 5x11 | 21 |
| elbow_assault | 170.0 | 1x5, 2x16 | 2x8, 4x2, 5x11 | 21 |
| front_kick | 150.0 | 1x13, 2x8 | 2x8, 4x2, 5x11 | 21 |
| hook | 130.0 | 1x13, 2x8 | 2x8, 4x2, 5x11 | 21 |
| jab | 60.0 | 1x21 | 2x9, 4x1, 5x11 | 18 |
| shoulder_throw | 260.0 | 2x21 | 2x8, 4x2, 5x11 | 21 |
| straight | 90.0 | 1x21 | 2x8, 4x2, 5x11 | 21 |
| sweep | 140.0 | 1x13, 2x8 | 2x8, 4x2, 5x11 | 21 |

168 pairs: layered higher in 120, lower in 0.

Con energías por región (`FIGHT_RIGID_SHELL_ENERGY_J`, opt-in, ASSUMED: órdenes de magnitud recordados de la literatura de biomecánica, NO verificados contra fuentes; cabeza 80 J, tórax 150 J, pelvis y muslo 300 J, mano 20 J ...):

| Move | Energy (J) | Legacy severity | Layered severity | Layered fractures (of 21) |
|---|---|---|---|---|
| crescent_kick | 220.0 | 1x1, 2x20 | 2x9, 4x1, 5x11 | 16 |
| elbow_assault | 170.0 | 1x5, 2x16 | 2x16, 4x1, 5x4 | 9 |
| front_kick | 150.0 | 1x13, 2x8 | 2x16, 4x1, 5x4 | 7 |
| hook | 130.0 | 1x13, 2x8 | 2x16, 4x1, 5x4 | 7 |
| jab | 60.0 | 1x21 | 2x20, 4x1 | 5 |
| shoulder_throw | 260.0 | 2x21 | 2x16, 4x1, 5x4 | 9 |
| straight | 90.0 | 1x21 | 2x20, 4x1 | 5 |
| sweep | 140.0 | 1x13, 2x8 | 2x16, 4x1, 5x4 | 7 |

168 pairs: layered higher in 103, lower in 0.

Lectura: con el valor por defecto el modelo es degenerado (cualquier movimiento fractura casi todo). Los valores por región lo hacen discriminar (un jab fractura 5 de 21 zonas, una patada creciente 16) y nunca queda por debajo de la tabla legacy, pero siguen varios problemas que impiden conectarlo al juego: toda fractura de una región hueca da severidad 5 (al romperse la cáscara las vísceras casi no cuestan, así que el golpe "atraviesa"), y el radio de contacto cambia el resultado tanto como la energía (un shoulder throw de 260 J se lee como un hook de 130 J). Los valores no tienen fuente. Recomendación: no reemplazar todavía la constante de 400 J; dejar esto como herramienta de comparación.
