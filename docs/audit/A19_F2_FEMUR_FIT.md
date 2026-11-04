# A19: F2, fémur de BodyParts3D ajustado al rig canónico (Blender 3.6)

**Fecha:** 2026-11-04 · **Estado:** F1 implementado, F2 medido; tolerancias PENDIENTES (todo ESTIMATE) ·
**Uso:** INTERNO (Decisión 62). Ningún mesh entra al repo: los OBJ, el `.blend` y el JSON completo están en
`C:\DEV\Assets\BodyParts3D_4.0\out\`. Resumen numérico (sin geometría): `A19_F2_FEMUR_FIT.json`.

## Qué se hizo

1. **F1 (dominio puro):** `domain/assets/registration.py`, registro por landmarks. La rotación sale del
   cuaternión de Horn (1987), que siempre da una rotación propia (det +1), y la escala uniforme de Umeyama (1991).
   Devuelve rotación, traslación, escala, residuo por anclaje y RMS. Rechaza anclajes casi colineales (guarda
   numérica: razón de dispersión < 1e-3) y, con 4 o más anclajes no coplanares, las configuraciones que
   necesitan reflexión. Además, `fit_sphere` (esfera por mínimos cuadrados). Tests:
   `tests/unit/test_asset_registration.py`, que recupera transformaciones conocidas con error < 1e-6.
2. **F2 (Blender 3.6.23 headless):** `runtime/blender/ce_f2_femur_fit.py`, ejecutado por `scripts/f2_femur_fit.py`.
   Importa FJ3259 (fémur izquierdo) y FJ3365 (fémur derecho) sin conversión de ejes. Al importarlos coinciden con
   las cabeceras OBJ dentro de 1,4e-5 mm.

## Anclajes y objetivos (ESTIMATE)

| Anclaje | En el asset | Objetivo canónico (1,80 m, solo lectura) |
|---------|-------------|-------------------------------------------|
| Centro de la cabeza femoral | Esfera sobre el 12 % proximal, mitad medial, con una pasada de descarte de puntos a más de 3 mm: 290 puntos, r = 22,94 mm, RMS 0,68 mm | `FEMUR_L.head` (articulación de cadera) |
| Epicóndilo lateral | Vértice con x máxima en el 10 % distal (591 vértices) | `FEMUR_L.tail` + ½ ancho × s0 en la dirección lateral canónica ⟂ al eje |
| Epicóndilo medial | Vértice con x mínima en el 10 % distal | `FEMUR_L.tail` − ½ ancho × s0 |

No hay epicóndilos canónicos medidos. Por eso sus objetivos se **derivan del propio asset**: el centro de la
rodilla es el punto medio de los epicóndilos (`biomechanics.json`, equidistante, ASSUMPTION) y el ancho es el del
asset escalado por s0 = |cadera − rodilla| canónica / |cabeza − rodilla| del asset. Esos dos anclajes fijan la
rodilla y el roll, pero **no** son una medida independiente del ancho.

## Resultados

| Verificación | Resultado | Lectura |
|--------------|-----------|---------|
| (a) Joints canónicos | Huella de `human_adult_206.json` antes = después = `71c42ca0…e55d`; 206 huesos comparados head/tail, **0 movidos** | Exacto. El ajuste lleva el mesh al rig, nunca al revés (Decisión 16) |
| (b) Longitud | Fémur ajustado a lo largo del eje del hueso: 0,4735 m; Trotter (1,80 m, varón blanco): 0,4983 m → **−4,97 %**. Estiramiento a lo largo del eje que haría falta: ×1,052 (**no aplicado**: correría el anclaje de la rodilla fuera de `FEMUR_L.tail`) | Supera la tolerancia propuesta de 1 % (ESTIMATE). El asset BP3D es un sujeto de 1,72 m; el segmento canónico de cadera a rodilla mide 0,4178 m |
| (c) Roll | Razón de dispersión de los 3 anclajes 0,171 (guarda 1e-3) → roll **definido**; error de roll 0,0° | El 0° se da por construcción (objetivos derivados), no es una medición independiente |
| (d) Espejo | Volumen con signo: izquierdo +521,4 cm³; espejo sin corregir el winding −521,4; espejo con winding invertido **+521,4** → normales correctas. Espejo del izquierdo crudo frente al derecho real FJ3365: media **1,91 mm**, RMS 2,52, p95 5,0–5,5, máx 15,1 mm. Espejo del izquierdo ajustado frente al derecho ajustado con sus propios anclajes: media 2,26 mm, máx 16,2 mm | El espejo es correcto. La diferencia restante es asimetría real del sujeto BP3D y la resolución de la malla (arista mediana de 4,8 mm) |
| (e) RMS de anclajes | Izquierdo: **2,31 mm** (cabeza 0,55; lateral 2,78; medial 2,82). Derecho con sus propios anclajes: 1,32 mm | **No alcanza** los 2 mm propuestos (ESTIMATE) del lado izquierdo; el derecho sí |

Escala de similitud: izquierdo 1,0136, derecho 1,0122. det R = +1. `chirality_checked = false`: con 3
anclajes coplanares la quiralidad no se ve, así que el lado lo da el manifiesto (`side`).

## Lectura

- El error de los epicóndilos (≈ 2,8 mm) refleja que, en el asset, la línea de la cabeza a la rodilla no es
  perpendicular al eje de los epicóndilos, mientras que el objetivo derivado sí lo es. A eso se suma la
  resolución de la malla al 99 % (los vértices extremos tienen ≈ 5 mm de incertidumbre). Con anclajes así, 2 mm
  RMS queda en el límite.
- La longitud difiere un 5 % de Trotter. Si se ajusta la longitud (Decisión 16) sin mover joints, hay que decidir
  dónde va la diferencia: la longitud máxima de Trotter va del extremo de la cabeza al de los cóndilos, no del
  centro de la cabeza a la rodilla.

## Pendiente (dueño)

1. Tolerancias: RMS de anclajes (2 mm medido en 2,31 / 1,32), longitud (1 % medido en −5 %), espejo (1 mm
   propuesto; medido 1,9 mm de media contra el derecho real, que no es un espejo perfecto).
2. Si se aplica el estiramiento a lo largo del eje, y con qué ancla (cabeza fija, o repartido).
3. Fuente para los epicóndilos canónicos (hoy derivados del asset).

## Reproducir

```bash
python scripts/f2_femur_fit.py --bp3d C:/DEV/Assets/BodyParts3D_4.0/extracted/partof_BP3D_4.0_obj_99 --out C:/DEV/Assets/BodyParts3D_4.0/out
```

Blender: `C:/DEV/Tools/Blender/blender.exe` (3.6.23), o `CE_BLENDER`. Entradas: FJ3259 / FJ3365, con los SHA-256
en el JSON. El resultado es determinista.
