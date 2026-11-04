# A18: mapeo de BodyParts3D 4.0 (PART-OF) a los 206 huesos canónicos

**Fecha:** 2026-11-04 · **Estado:** VERIFICADO por nombre y lado; la geometría de ajuste queda para F2 ·
**Uso:** INTERNO (Decisión 62; la licencia para publicar está PENDIENTE)

Este informe no incluye geometría: solo nombres canónicos, IDs FMA/BP3D, el estado de cada hueso y notas. El
detalle por hueso está en `A18_BP3D_BONE_MAPPING.json` (58 KB). Los OBJ siguen fuera del repo, en
`C:\DEV\Assets\BodyParts3D_4.0\` (registro de descarga con los SHA-256 en esa misma carpeta).

## Fuente

- `partof_BP3D_4.0_obj_99.zip`, SHA-256 `9fbc713fffeee924a5a657d9813d84d7eb957bded63adb854931dd5e3eb61c97`:
  1258 OBJ, un elemento atómico por archivo (`FJxxxx.obj`). La cabecera de cada uno trae Concept ID (FMA),
  Representation ID (BP), nombre en inglés, límites en mm y volumen.
- Marco de los datos, medido en las cabeceras: mm, Z arriba, frente −Y, izquierda +X. Es el mismo marco
  canónico (Decisión 33); solo cambia la escala (mm → m). Pose anatómica, con los brazos al costado.

## Método

1. Nombre canónico → nombre FMA en inglés, con reglas explícitas (ordinales de vértebras y costillas,
   dedo/ortejo + falange, `navicular bone of <side> foot`, etc.). Coincidencia exacta, sin parecido difuso.
2. Lado según la caja: `_L` exige centro x > 0, `_R` exige centro x < 0 y un hueso de línea media exige que la
   caja cruce x = 0.
3. Simetría: el centro x de cada `_L` tiene que ser ≈ −(centro x de su `_R`). Los 83 pares dan
   |Δ| máx 2,61 mm y medio 0,41 mm.
4. Piezas múltiples: se resuelven con `partof_element_parts.txt` y comparando el contenido de los OBJ.

## Resultado

| Estado | Huesos | Nota |
|--------|--------|------|
| MAPPED (1:1, lado OK) | 197 | Un OBJ por hueso canónico |
| MAPPED_MULTI | 1 | STERNUM = compuesto FMA7485: manubrio FJ3290 (FMA7486) + cuerpo FJ3178 (FMA7487) + xifoides FJ3153 (FMA7488). Hay que unirlos en una sola malla para el único hueso canónico |
| MAPPED_DUPLICATE | 1 | HYOID: FJ2772 y FJ3201 tienen el mismo FMA52749 / BP10003 y vértices y caras **idénticos** (mismo SHA-256 del cuerpo del OBJ). Se usa FJ2772 |
| MISSING | 7 | MALLEUS_L/R, INCUS_L/R, STAPES_L/R, COCCYX |
| SIDE_MISMATCH | 0 | — |

**Cruzan la línea media** (lado correcto por el centro; son huesos pares que se tocan en una sutura):
PARIETAL_L/R, MAXILLA_L, NASAL_L, PALATINE_L/R, con hasta 7,9 mm del otro lado. No es un error, pero en F2 el
espejo L/R no puede suponer que todo el hueso queda de un solo lado.

## Faltantes

- **Huesecillos del oído** (martillo, yunque, estribo): no figuran en `partof_parts_list_e.txt` ni en los OBJ.
  Con 99 % de reducción de polígonos son de pocos milímetros. Quedan como proxy (ESTIMATE) o sin mesh.
- **Cóccix**: no aparece con ningún nombre (`coccyx`, `coccygeal…`) en las listas ni en los OBJ del árbol
  PART-OF. Puede estar en el árbol IS-A (no descargado, requiere OK) o en otra fuente. Mientras tanto, proxy.

Total con mesh real posible: **199 de 206** huesos canónicos (197 + esternón + hioides).

## Límites

- El mapeo es por nombre y lado, no por forma. Que la geometría coincida (longitud contra la osteometría,
  anclajes) se mide en F2 con el validador F0 y el registro por landmarks.
- Es un solo sujeto (varón adulto de BodyParts3D) a escala propia, de 1,72 m de piel a piel, no a la estatura
  canónica de 1,80 m. La escala se ajusta por segmento (Decisión 16), sin mover joints.
- Licencia: página CC BY 4.0 (2025) frente a las cabeceras OBJ, que dicen CC BY-SA 2.1 Japan (2013). Uso interno
  hasta que el dueño decida (Decisión 62).

## Reproducir

Los scripts son de solo lectura, procesan solo texto (`python -I`) y quedan fuera del repo. El JSON se
regenera con el mismo resultado si se parte de los mismos archivos (SHA-256 arriba). Resultado de esta corrida:
`A18_BP3D_BONE_MAPPING.json`, SHA-256 `fbc0ad299f7f4603e7c2b182ef5f0a3c09ba5e2c2f2f4cc3419a42849f251156`.
