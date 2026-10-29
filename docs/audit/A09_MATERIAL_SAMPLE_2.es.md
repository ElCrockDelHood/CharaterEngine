# A09 (muestra 2) — Capas huecas y modelo de impacto contundente: tórax con costillas, cavidad y chaleco acolchado

*(Traducción al español de `A09_MATERIAL_SAMPLE_2.md`, para lectura. La versión en inglés es la del repo.)*

**Fecha:** 2026-10-29 · **Estado:** IMPLEMENTADO (estado de los datos: ESTIMATE / ASSUMED, nada PROVEN) ·
**Alcance:** dominio central (`domain/materials`, `domain/physics`), driver `scripts/material_sample.py`, escena de
Blender `runtime/blender/ce_material_sample.py` · **Decisiones:** 49 (muestra 1), 55 (muestra 2). La muestra 1 tiene su propio informe, `A09_MATERIAL_SAMPLE_1.md`; este
agrega la muestra 2 y las notas comunes (qué es ajuste, estabilidad del solver, pendientes)

Las dos muestras toman una cápsula del maniquí de bloques (`rigging/block_dummy.py`), la dividen en capas de material
concéntricas a partir del perfil de tejido de la región (`tissue/layers.py`), agregan ropa o armadura como capas
exteriores, simulan la tela con un solver XPBD en Python puro y mandan la profundidad que alcanzó el impactor por los
puntos de entrada de trauma sin cambios (`assess_wound`). Blender dibuja lo que calculó el dominio; no calcula nada
físico.

## 1. Qué está dónde

| Pieza | Archivo | Notas |
|-------|---------|-------|
| Catálogo de materiales | `domain/materials/catalog.py` | Cara mecánica (densidad, módulo, fricción, energía de corte, compliances XPBD, esfuerzo y deformación de aplastamiento, energía de fractura de costilla) + cara óptica con nombres OpenPBR; cada valor es una `Quantity` con rango y procedencia |
| Cápsula en capas | `domain/materials/layered_capsule.py` | Ajuste sólido (miembros: núcleo de hueso = mitad del espesor del hueso) y ajuste hueco (tórax, cabeza, pelvis, abdomen: cáscara de hueso alrededor de una cavidad) |
| Solver XPBD | `domain/physics/xpbd.py` | XPBD de pasos pequeños, restricciones de distancia (estiramiento + flexión), colisionadores cápsula con fricción, colisionador local `skip`, orden de restricciones con semilla, hash del estado |
| Modelo de corte | `domain/physics/cut.py` | Energía de la hoja gastada en área de corte capa por capa (muestra 1) |
| Modelo contundente | `domain/physics/blunt.py` | Aplastamiento en meseta por capa + fractura de costilla de todo o nada (muestra 2) |
| Muestras | `domain/physics/forearm_strike.py`, `torso_strike.py` | Escenario, JSON de reporte, sha256 |
| Tests | `tests/unit/test_materials_xpbd.py` (15), `tests/unit/test_blunt_torso.py` (17) | |

## 2. Muestra 1 — resumen (informe completo: `A09_MATERIAL_SAMPLE_1.md`)

Corrida en la PC del dueño el 2026-10-25 (Blender 3.6.23, Cycles CUDA en una GeForce GT 740M, semilla 0).

| Variante | La hoja se frenó en | Profundidad bajo la piel | Herida | Capa más profunda | Severidad | Eslabones de manga cortados |
|----------|---------------------|--------------------------|--------|-------------------|-----------|-----------------------------|
| sin armadura | hueso | 39,4 mm | incisión | hueso | 3 | 113 |
| con armadura | brazal | 0 mm | contundente (residual 30 J, cota superior) | grasa | 1 | 0 |

Reproducibilidad: al volver a correr la simulación, el `sha256` del resultado salió idéntico
(`cf245455…` sin armadura, `93789334…` con armadura). Renders a 1920×1080 y 512 samples: EEVEE 23,8 s; Cycles 946 s
(comparación) y unos 2050–2160 s por primer plano (total 5190 s). Las primeras cámaras de los primeros planos
quedaron demasiado cerradas; se alejaron (lente de 50 mm) y se rerenderizaron.

## 3. Muestra 2 — tórax, abrigo de lana, chaleco acolchado opcional, impactor contundente (48,6 J)

Corrida en la PC del dueño el 2026-10-29 (Blender 3.6.23, Cycles CUDA en una GeForce GT 740M, semilla 0). Impactor: 1,2 kg (PLACEHOLDER) a
9 m/s (ESTIMATE), radio de contacto de punta 30 mm (ESTIMATE). Capacidad de cada capa con esa área de contacto:

| Capa | Capacidad (J) | Sin chaleco | Con chaleco |
|------|---------------|-------------|-------------|
| abrigo | 0,12 | aplastada | aplastada |
| chaleco | 17,0 | – | aplastado |
| piel / grasa / músculo / tendón | 2,3 / 1,5 / 7,1 / 2,0 | aplastadas | aplastadas |
| cáscara de costillas (energía de fractura) | 25 (ASSUMED) | se rompe | aguanta, 18,7 J almacenados |
| cavidad (dominada por pulmón) | 2,0 | aplastada, quedan 8,6 J | no se alcanza |

| Variante | Se frenó en | Profundidad afectada | Costillas rotas | Capa más profunda | Severidad | Mapeo viejo |
|----------|-------------|----------------------|-----------------|-------------------|-----------|-------------|
| sin chaleco | atraviesa la cavidad | 130 mm (de la piel al eje) | sí | vísceras | 5 | grasa, severidad 1 |
| con chaleco | cáscara de costillas (aguanta) | 48,7 mm | no | tendón | 2 | grasa, severidad 1 |

Barrido de energía (1,2 kg, velocidad de 2 a 14 m/s): las costillas se rompen por primera vez a **8 m/s (38 J) sin
chaleco** y a **10 m/s (60 J) con chaleco**. El mapeo viejo (`blunt_impact_to_wound`: `E / 400 J` × profundidad hasta
el hueso) se queda en grasa / severidad 1 hasta 14 m/s (118 J), porque 400 J es su única constante de referencia;
en este rango nunca llega a la capa de costillas.

Reproducibilidad: dos corridas de la simulación dieron el mismo `sha256` del resultado (`e75bfcc7…` sin chaleco,
`acab4965…` con chaleco). Renders a 1920×1080, Cycles 128 samples (pasada final): EEVEE 21,1 s; Cycles 294,6 s (comparación), 329,5 s y
389,2 s (primeros planos); total de Blender 1038,6 s. Pasadas anteriores, para el registro: la primera (EEVEE 9,9 s,
Cycles 243,5 / 284,6 / 293,5 s, total 836 s) mostraba el abrigo parpadeando contra la piel y el chaleco
(z-fighting); las dos siguientes arreglaron la tela y el encuadre, pero seguían viéndose lavadas. Cambios solo de
presentación en `ce_material_sample.py` (el resultado del dominio y su hash no cambian): los vértices de la tela se
empujan radialmente justo por fuera de la capa sólida más externa; hueso / tendón / vísceras tienen colores base y de
subsurface de presentación; el impactor de acero es más rugoso (0,45) para que deje de reflejar el abrigo como un
espejo; la cámara de comparación está más cerca y los primeros planos usan lente de 75 mm; la exposición de la
escena es −1,5 EV, porque a 0 EV Filmic lavaba todas las capas a tonos pastel (la lana azul marino oscuro del abrigo
salía lavanda, el marrón del chaleco acolchado salía crema; verificado en el `.blend` guardado, donde los valores de
los materiales son correctos).

Qué muestran las imágenes: el corte se lee, de adentro hacia afuera, cavidad, cáscara de costillas, tendón, músculo,
grasa, piel, (chaleco), abrigo; el abrigo es una lámina azul limpia y el músculo y la cavidad se ven rojos. Sin
chaleco: la punta del impactor queda dentro de la cavidad, coherente con "atraviesa". Con chaleco: el impactor
termina en la superficie del chaleco y no aparece en el corte, coherente con "las costillas aguantan". Sigue mal: el
aplastamiento de 48,7 mm **no se dibuja** (las capas no se deforman y la barra queda donde la frenó el XPBD de la
tela, unos 20 mm bajo la superficie del abrigo, no a la profundidad afectada del modelo contundente); la cáscara de
costillas y el tendón siguen casi blancos y el chaleco sigue viéndose crema; la cavidad es apenas más oscura que el
músculo; la barra todavía toma un tinte azul junto al abrigo, y en EEVEE la barra se ve oscura y borroneada donde
toca la tela.

## 4. Qué es ajuste y no medición (leer antes de citar cualquier número)

* **Energía de fractura de costilla de 25 J, ASSUMED.** Todo o nada; una vez que la cáscara se rompe, solo queda la
  cavidad, que es barata, así que el modelo tiene un escalón entre "las costillas aguantan" y "atraviesa el pecho"
  (de 8 a 9 m/s sin chaleco). Un pecho real tiene resultados intermedios (segmentos flotantes, contusión sin
  fractura) que no están modelados.
* **Esfuerzo y deformación de aplastamiento de piel, grasa, músculo, tendón, lana, tela acolchada y cavidad: ASSUMED**,
  solo orden de magnitud.
* **Energía de corte de hueso (muestra 1) y energía de frenado de la hoja por el acero: constantes de ajuste
  ASSUMED**, no propiedades de material. Con solo la tenacidad a la fractura del hueso, un corte de 30 J cortaría el
  antebrazo entero.
* Compliances y amortiguación de XPBD: ASSUMED. Óptica: ASSUMED (look-dev).
* Masa del impactor PLACEHOLDER; velocidades, radio de contacto, espesores y huecos de la ropa ESTIMATE.
* **Geometría:** el bloque de tórax es una esfera (el tramo T12–T1 de 0,146 m es más corto que dos radios de 0,13 m);
  la muestra 2 apila las capas sobre un cilindro a lo largo de ese tramo. Muestra el comportamiento de las capas, no
  la forma del pecho. Los radios del maniquí de bloques son ESTIMATE.
* No modelado: dependencia de la velocidad, ondas de presión a través de una cáscara que aguanta, golpes rasantes,
  flexión de costilla, placa de acero bajo carga contundente (rechazada a propósito por `blunt_through`), criterios de
  lesión basados en fuerza.

## 5. Hallazgo de estabilidad del solver

Un barrido Gauss-Seidel estructurado sobre la malla cerrada de la manga inyectaba energía mecánica (+4,4 % en 0,5 s
con 20 subpasos, +48 % con 80); las mismas restricciones en un orden mezclado con semilla no lo hacen (alrededor de
−0,003 %). Por eso el orden de restricciones es una permutación con semilla (`tube(..., seed=...)`), y la
verificación de energía en la fase de asentamiento es parte de los tests. La proyección de velocidad de contacto
quita la velocidad de separación que la proyección de posición agrega de otro modo.

## 6. Pendientes

1. Conseguir fuentes para el aplastamiento de tejidos, la energía de fractura de costilla y la energía de corte de
   hueso (registrarlas en `source_registry`).
2. Resultados intermedios del pecho (fractura de costilla sin penetración de la cavidad) y un criterio de fuerza /
   aceleración.
3. Una forma real de tórax (el bloque esfera) antes de juzgar siluetas.
4. Placa de acero / armadura laminar bajo carga contundente.
5. Port a Godot del contacto por capas (primero GDScript) cuando se acuerde la interfaz con el hilo de heridas.
6. Dibujar el aplastamiento contundente (abollar las capas hasta la profundidad afectada) en la escena de Blender.
7. Presentación: los colores de hueso / tendón / chaleco siguen lavados (revisar los pesos de subsurface, no solo
   los colores); ubicar la barra a la profundidad afectada del modelo contundente; quitar el tinte azul de la barra y
   el borroneo en EEVEE.
