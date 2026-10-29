# A09 — Muestra de material 1: golpe al antebrazo (evidencia para la Decisión 49)

> Traducción al español de `A09_MATERIAL_SAMPLE_1.md`. El original en inglés es la fuente de verdad; si difieren,
> manda el original.

**Corrida:** 2026-10-25, `builds/material_sample/20261025T143422Z/` (salidas ignoradas por git). Corrida del probe de
GPU: `builds/material_sample/20261025T143401Z/`. Driver `scripts/material_sample.py` (simulación en Python puro
`domain/physics/forearm_strike.py`) y `runtime/blender/ce_material_sample.py` (solo dibujo y renders).
Log: `logs/20261025T143522Z_material_sample.log`. Blender 3.6.23 en la PC de referencia (i3-3120M, GeForce GT 740M).
Cada valor de abajo está copiado de los archivos JSON / summary de la corrida; no se agrega nada.

## Configuración (del `config` del JSON)

* Segmento de antebrazo izquierdo del maniquí de bloques (`forearm.L`, radio de envolvente 0.040 m, ESTIMATE) como
  **cápsula en capas**: núcleo de hueso 0.0075 m, tendón hasta 0.0105 m, músculo hasta 0.0319 m, grasa hasta
  0.0383 m, piel hasta 0.040 m (escala de tejido blando 0.855); todo ESTIMATE. Estatura 1.80 m (USER_INPUT).
* Manga de lana: espesor 0.002 m, separación 0.006 m, retícula 32 × 16 (ESTIMATE). La variante *armored* agrega un
  brazal de acero de 0.0015 m de espesor, separación 0.002 m, sobre el 15–85 % del segmento (ESTIMATE).
* Filo de sable: masa efectiva 0.6 kg (**PLACEHOLDER**), velocidad 10 m/s (**ESTIMATE**) → energía cinética
  **30.0 J**; ancho de hoja 0.028 m (PLACEHOLDER), radio del filo 0.002 m; golpe a mitad del segmento.
* XPBD: 60 fps, 40 cuadros de asentamiento + 40 de golpe, 20 subpasos, **seed 0**; cámara lenta ×20 para la
  presentación (ASSUMED).

## Resultados

| Variante | Hoja detenida en | Profundidad bajo la piel | Herida | Capa más profunda | Severidad | Letalidad | Eslabones de manga cortados | Tiempo de sim | Hash del estado final |
|----------|------------------|--------------------------|--------|-------------------|-----------|-----------|-----------------------------|---------------|-----------------------|
| unarmored | hueso | 39.4 mm (penetración 47.4 mm incl. manga) | incisión en RADIUS_L | hueso | 3 | 0.075 | 113 | 30.72 s | `f46978843a4c0346` |
| armored | brazal | 0.0 mm | contusa | grasa | 1 | — | 0 | 29.21 s | `80c8dbcb74877f6e` |

La herida la producen los puntos de entrada de trauma (`blade_contact_to_wound` / `blunt_impact_to_wound` +
`assess_wound`), no el código de física (Decisión 49). Sin armadura: se gastan los 30 J completos (manga → piel →
grasa → músculo → tendón → hueso, sin seccionarlo). Con armadura: el brazal de acero detiene el filo y el golpe llega
al brazo como contacto contuso.

## Renders (1920 × 1080, `render_report.json`)

| Archivo | Motor | Dispositivo | Samples | Segundos |
|---------|-------|-------------|---------|----------|
| comparison_eevee.png | EEVEE | GPU | 64 | 23.77 |
| comparison_cycles.png | Cycles | CUDA GeForce GT 740M | 512 | 946.51 |
| closeup_unarmored_cycles.png | Cycles | CUDA GeForce GT 740M | 512 | 2 054.67 |
| closeup_armored_cycles.png | Cycles | CUDA GeForce GT 740M | 512 | 2 162.68 |

Corrida completa (simulación + escena + renders): 5 190 s. Probe de GPU: Cycles CUDA en la GT 740M funciona (render
mínimo 1.764 s). Las imágenes fijas de Cycles a 512 samples tardan 16–36 min en esta máquina; EEVEE tarda unos 24 s.

## Procedencia y límites

* Nada es PROVEN. Mecánica de tejidos ESTIMATE (orden de magnitud, sin fuente); energía de corte de hueso, energía
  para que el acero detenga la hoja y compliances de XPBD son ajustes ASSUMED; la óptica es look-dev ASSUMED
  (Decisión 49).
* La masa de la hoja es PLACEHOLDER y la velocidad ESTIMATE, así que los 30 J no son una medición. Una fuente citada
  para masa del sable, velocidad del golpe y energía de corte por tejido los reemplazaría.
* Un solo segmento y una sola dirección de golpe; el resultado es una muestra reproducible (con seed, hashes de
  estado), no un modelo de lesión validado.
