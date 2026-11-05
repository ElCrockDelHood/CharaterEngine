# A33 — Fragmentos de hueso de un golpe con fractura

Estado: ASSUMED, aditivo y opcional (Decisión 80). Código: `domain/physics/fracture_event.py`; tests:
`tests/unit/test_fracture_event.py`; ejemplos: `scripts/fracture_events_demo.py`. Inglés: `A33_FRACTURE_EVENT.md`.
Por qué: el dueño ve que al golpear el hueso se borronea o se va para otro lado; debería romperse como un cristal, en fragmentos.
`strike_model.py` decide *si* la cáscara se rompe; este módulo dice *cómo se deshace*, como datos que los hilos de Blender y Godot
pueden dibujar. Las heridas, `strike_model.py`, la tabla de gameplay y todos los resultados anteriores no cambian. (Se pensó como
A18; ese número es BodyParts3D.)

**No se usó ningún dato publicado de tamaño, cantidad ni velocidad de fragmentos.** La teoría de fragmentación (Mott, Grady) es el
marco de una ley de potencia en la energía; no se leyó ni usó ninguno de sus números, y ninguna constante está ajustada a datos. El
resultado es un dibujo plausible, no una predicción de cómo se rompe un hueso real.

## Modelo

1. **Patrón por región:** cráneo `spiderweb` (muchas esquirlas que irradian del impacto); tórax `transverse_ribs` (pocas piezas
   largas a lo ancho del cuerpo, empujadas hacia adentro); brazo, antebrazo, muslo, pierna `butterfly` (una cuña más piezas grandes a
   lo largo del hueso); cuello, abdomen, pelvis, mano, pie `small_pieces`.
2. **Masa que se desprende:** densidad del hueso (catálogo, 1900 kg/m³) × área del parche × espesor de la cáscara × fracción móvil.
   Radio del parche = factor × radio de contacto, sin superar la mitad golpeada del hueso (π × radio externo). Las masas de los
   fragmentos suman exactamente eso.
3. **Energía sobrante:** cráneo `E_diss − 23 J` (mitad de su criterio de energía); el resto `E_diss − F_mid² / 2k`, la energía ya
   gastada cuando la fuerza del resorte lineal llegó al punto medio del rango de la región.
4. **Cantidad:** `n = clamp(round(a · (E_sobrante / 50 J) ** 0,6), 3, tope)`.
5. **Tamaños:** pesos de Weibull con la forma del patrón, reescalados a la masa que se desprende.
6. **Velocidades:** el 10 % de la energía sobrante pasa a energía cinética de fragmentos, repartida por masa × un factor aleatorio de
   0,5 a 1,5; ningún fragmento supera 2 × la velocidad del golpe, así que la energía cinética informada puede quedar por debajo de esa
   parte. Los fragmentos internos (bajo el parche de contacto) salen en un cono de 20° alrededor de la normal hacia adentro (insumo de
   lesión secundaria); los externos se dispersan radialmente con un sesgo hacia adentro.
7. **Determinismo:** la semilla por defecto es un hash de 48 bits del segmento y los números del golpe (se mantiene exacta en los
   lectores de JSON que leen números como double).

8. **Sin hueso no hay fragmentos:** de los 17 segmentos solo el abdomen no tiene cáscara de hueso (espesor 0 en su perfil de tejidos:
   pared sobre vísceras). Ahí el evento da `fractured: false`, `reason: "no_bone_layer"` y ningún fragmento, aunque `strike_model.py`
   informe una fractura (ver A15); no se inventa una cáscara. Una cáscara que aguanta da `reason: "shell_held"`; una fractura, `reason: null`.

## Constantes

| Constante | Valor | Rango | Procedencia |
|---|---|---|---|
| Factor del parche (radio del parche / radio de contacto) | 2,0 | 1,5–3 | ASSUMED |
| Fracción móvil del parche | 0,6 | 0,4–0,9 | ASSUMED |
| Energía de referencia | 50 J | — | ASSUMED |
| Exponente de la cantidad | 0,6 | 0,4–0,8 | ASSUMED (forma de ley de potencia del marco Mott / Grady, ningún número de ahí) |
| Límites de cantidad | 3–24 | — | 24: presupuesto de hardware (GeForce 740M + i3) |
| Parte cinética de los fragmentos | 0,10 | 0,05–0,15 | ASSUMED |
| Límite de velocidad | 2 × velocidad del golpe | — | DERIVED (límite elástico para un cuerpo liviano) |
| Semiángulo del cono interno | 20° | 10–35° | ASSUMED |
| Giro (velocidad angular × tamaño / velocidad) | 0,2–1,0 | — | ASSUMED |
| Densidad del hueso | 1900 kg/m³ | 1800–2000 | catálogo, ESTIMATE |

| Patrón | a (n a 50 J) | Tope | Forma de Weibull | Relación de aspecto | Sesgo hacia adentro de los externos |
|---|---|---|---|---|---|
| spiderweb | 10 | 24 | 1,6 | 1,8 | 0,3 |
| transverse_ribs | 4 | 8 | 2,0 | 3,0 | 0,8 |
| butterfly | 3 | 6 | 1,0 | 2,0 | 0,4 |
| small_pieces | 6 | 12 | 1,4 | 1,2 | 0,5 |

Todos los valores de los patrones son ASSUMED.

## Esquema JSON `ce-fracture/1` (orden de claves fijo)

```json
{
  "schema": "ce-fracture/1",
  "segment": "thorax", "region": "thorax", "bone": "THORACIC_6",
  "fractured": true, "pattern": "transverse_ribs", "seed": 123456789,
  "impact_point_m": [x, y, z],
  "frame": {"x": [..], "y": [..], "z": [..]},
  "patch_radius_m": 0.09, "shell_thickness_m": 0.009,
  "patch_mass_kg": 0.46, "excess_energy_j": 80.5, "fragment_kinetic_j": 8.05,
  "provenance": "ASSUMED", "reason": null,
  "fragments": [
    {"id": 0, "kind": "piece", "inner": true, "size_m": 0.09, "aspect": 3.0, "mass_kg": 0.15,
     "position_m": [x, y, z], "velocity_m_s": [x, y, z],
     "angular_speed_rad_s": 12.0, "spin_axis": [x, y, z]}
  ]
}
```

`frame` está en coordenadas del mundo (Z arriba canónico, metros): `x` lateral, `y` a lo largo del segmento, `z` hacia adentro a lo
largo del golpe. `position_m` (desplazamiento desde el punto de impacto), `velocity_m_s` y `spin_axis` están en ese marco local.
`kind` es `wedge` o `piece`; `inner` marca un fragmento que arranca bajo el parche de contacto. `size_m` es el tamaño lateral de una
pieza plana del espesor de la cáscara; `aspect` es largo / ancho. Si `fractured` es falso, `fragments` está vacío y masas y energías
valen 0.

## Eventos de ejemplo (`python scripts/fracture_events_demo.py`)

| Segment | Striker | m (kg) | v (m/s) | F_peak (N) | Fractured | Pattern | Excess J | Fragments | Mass (g) | Largest (mm) | Fastest (m/s) | Fragment KE (J) | File |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| head | jab | 2.1 | 7.5 | 2917 | no | spiderweb | 0.0 | 0 | 0 | 0 | 0.0 | 0.00 | builds/fracture_events/head_jab.json |
| head | straight | 3.2 | 7.5 | 3339 | no | spiderweb | 0.0 | 0 | 0 | 0 | 0.0 | 0.00 | builds/fracture_events/head_straight.json |
| head | front_kick | 3.7 | 9.0 | 4187 | no | spiderweb | 0.0 | 0 | 0 | 0 | 0.0 | 0.00 | builds/fracture_events/head_front_kick.json |
| thorax | jab | 2.1 | 7.5 | 4037 | yes | transverse_ribs | 16.9 | 3 | 261 | 82 | 3.6 | 1.69 | builds/fracture_events/thorax_jab.json |
| thorax | front_kick | 3.7 | 9.0 | 6055 | yes | transverse_ribs | 80.5 | 5 | 464 | 85 | 7.0 | 8.05 | builds/fracture_events/thorax_front_kick.json |
| thigh.L | front_kick | 3.7 | 9.0 | 7457 | yes | butterfly | 70.7 | 4 | 168 | 51 | 10.2 | 7.07 | builds/fracture_events/thigh.L_front_kick.json |
| head | heavy_blow | 8.0 | 12.0 | 6739 | yes | spiderweb | 204.0 | 23 | 149 | 36 | 19.4 | 20.40 | builds/fracture_events/head_heavy_blow.json |

`builds/` guarda archivos generados; los JSON no se commitean. Se obtienen corriendo el script.

## Qué dice esto y qué no

* **Ningún movimiento del gameplay rompe el cráneo**: los golpes a la cabeza quedan por debajo del punto medio de su rango de fuerza
  ASSUMED (5 kN; el más alto probado aquí, una patada frontal, da 4187 N). Por eso `spiderweb` solo aparece con el golpe pesado de
  prueba (8 kg a 12 m/s, no es un movimiento).
* **Hasta un jab rompe el tórax** (4037 N contra un punto medio de 3300 N), igual que en A15, cuyo rango de tórax tiene fuente débil.
  El módulo dibuja lo que decide `strike_model.py`; no lo corrige.
* El parche es un círculo o una banda sobre una cápsula, no sobre un hueso real; `THORACIC_6` es el hueso de peso del bloque del
  tórax, mientras que los fragmentos representan costillas.
* En un núcleo sólido (miembros) el espesor es el radio del núcleo, así que la masa del parche sobreestima un medio cilindro hasta
  unas 2 ×.

## Límites

Sin desprendimiento hacia afuera, sin avance de grietas en el tiempo, sin choques entre fragmentos, sin freno en el tejido, sin
anisotropía del hueso, todavía sin modelo de lesión secundaria (los fragmentos internos son solo su insumo), y sin render acá: Blender
y Godot son de otros hilos.
