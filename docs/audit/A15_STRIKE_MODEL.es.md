# A15 — Golpe con masa reducida y criterio de fractura por fuerza (muestra 4, Python puro)

Estado: ESTIMATE / ASSUMED. Código: `domain/physics/strike_model.py`; tests: `tests/unit/test_strike_model.py`; herramienta de comparación: `scripts/gameplay_vs_strike_model.py`. Fuentes y contexto: A11 (notas del proyecto) y `A14_EFFECTIVE_MASS.md`. No cambió nada existente: `blunt.py`, `body_strike.py`, la tabla de gameplay y la constante de 400 J quedan intactos, así que no se mueve ningún hash anterior.

## Modelo

- **Golpeador** = masa efectiva m, velocidad v, radio de contacto. `Striker.from_move` conserva el `energy_j` de la tabla de cada movimiento y fija v según el tipo (puño 7,5; patada 9,0; proyección 6,0 m/s); m = 2E/v^2. El jab queda en 2,1 kg, en línea con los 2,9 +/- 2,0 kg medidos en boxeadores olímpicos (Walilko 2005, vía A14).
- **Energía al tejido**: solo E_diss = 1/2 mu v^2 con mu = mM/(m+M), M = masa efectiva del segmento golpeado (tabla compartida de `collision.py`, Decisión 58). El resto se informa como retroceso (insumo para un modelo de conmoción o derribo, no para heridas).
- **Fuerza máxima** F = v sqrt(k mu) (colisión lineal), k = rigidez local de toda la región. La k del tórax (1,6e5 N/m) sale de datos de cadáver (3,4 kN a 26 mm; 10,6 kN a 55 mm).
- **Fractura** cuando F llega al punto medio de un rango de fuerza por región; se informa también una probabilidad. El cráneo además exige E_diss entre 22 y 24 J (Delye 2007).
- **Profundidad** que llega a la herida: la compresión máxima F/k, acotada por lo que la pila de capas puede aplastar; una cáscara fracturada implica que se atraviesa la capa de hueso. La pila en capas (`blunt_through`) se reutiliza sin cambios.

## Aceptación contra datos de tórax de cadáver (13 cadáveres, impactos contundentes balísticos)

| Caso | F del modelo (N) | F medida (N) | Error |
|---|---|---|---|
| 140 g a 20 m/s | 2976 | 3383 | -12 % |
| 140 g a 40 m/s | 5952 | 10602 | -44 % |
| 40 g a 60 m/s | 4792 | 3158 | +52 % |

Dentro de un factor dos en todos los casos, y el signo cambia según el caso: un resorte lineal no sigue el endurecimiento con la velocidad ni los efectos locales de masas chicas. El test verifica la cota de factor dos, no un ajuste.

## Contra la tabla de gameplay vigente (solo lectura)

| Move | Energy (J) | m_eff (kg) | v (m/s) | Legacy severity | Model severity | Fractures (of 21) | Expected fractures | Tissue J (mean) | Knock-back J (mean) |
|---|---|---|---|---|---|---|---|---|---|
| crescent_kick | 220.0 | 5.4 | 9.0 | 1x1, 2x20 | 2x20, 4x1 | 15 | 16.1 | 116 | 104 |
| elbow_assault | 170.0 | 6.0 | 7.5 | 1x5, 2x16 | 2x20, 4x1 | 13 | 13.8 | 86 | 84 |
| front_kick | 150.0 | 3.7 | 9.0 | 1x13, 2x8 | 2x20, 4x1 | 15 | 14.7 | 91 | 59 |
| hook | 130.0 | 4.6 | 7.5 | 1x13, 2x8 | 2x21 | 12 | 12.4 | 73 | 57 |
| jab | 60.0 | 2.1 | 7.5 | 1x21 | 1x1, 2x20 | 11 | 7.9 | 43 | 17 |
| shoulder_throw | 260.0 | 14.4 | 6.0 | 2x21 | 2x20, 4x1 | 13 | 12.7 | 83 | 177 |
| straight | 90.0 | 3.2 | 7.5 | 1x21 | 2x21 | 12 | 10.1 | 57 | 33 |
| sweep | 140.0 | 3.5 | 9.0 | 1x13, 2x8 | 2x20, 4x1 | 15 | 14.4 | 87 | 53 |

Severity: model higher in 87 of 168 pairs, lower in 0.

## Qué dice esto y qué no

- A diferencia de las versiones solo-energía de A10, el resultado ahora depende del golpeador: se espera que un jab fracture 7,9 de 21 zonas y una patada creciente 16,1. El orden sigue al de la tabla legacy y el modelo nunca queda por debajo en severidad.
- La severidad se comprime a 2 casi siempre porque la escala de trauma da la misma nota a heridas contundentes que llegan al hueso pero no a las vísceras; la probabilidad de fractura y la columna de retroceso llevan la información que la severidad pierde.
- Las fracturas en extremidades salen altas porque sus rangos de fuerza son ASSUMED y anchos (mano 0,5-2,5 kN, pie 1,5-5 kN); solo tórax, antebrazo, muslo y pierna tienen rangos con fuente, y son débiles (revisiones que citan otros trabajos, una nota de divulgación). El rango de fuerza del cráneo es ASSUMED.
- Las masas del blanco salen de `collision.regional_target_mass_kg()` (Decisión 58: cuerpo de 75 kg × fracción del segmento, de Leva 1996 de memoria, sin verificar): cabeza 5,2, tórax 12,0, muslo 10,6 kg ... La primera versión de este módulo traía su propia tabla (cabeza 5, tórax 25, muslo 8 kg); pasar a la tabla compartida movió la comparación unos pocos joules y las fracturas esperadas hasta 0,8 (gancho 13,2 -> 12,4), las fuerzas de cadáver menos de 0,3 %, y no cambió el conteo de severidad (87 más alta, 0 más baja).
- No modelado: dependencia de la velocidad más allá del resorte lineal, guantes y vendas, duración del golpe, rotación (la cabeza acelerando angularmente), golpes rasantes, golpes repetidos.
- La constante de 400 J del hilo de heridas no se reemplaza. Reemplazarla es una Decisión, no parte de este cambio.

## Puntos abiertos

1. Verificar los valores "(summary)" (A11) y los autores del estudio de corredores de tórax en los textos completos.
2. Una tabla de masas del blanco desde una fuente antropométrica real.
3. La bandera de fractura de `assess_wound` sigue a llegar a la capa de hueso y no a que la cáscara se rompa (informa fracturas en regiones sin caja torácica cuando se usa el modelo de energía): hilo de heridas.
4. Retroceso a conmoción / derribo, con rotación de la cabeza.
5. Equivalente con sable (corte): la masa reducida lo cambia poco (30 -> 27 J) porque la hoja es liviana frente al blanco.
