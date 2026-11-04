# Propuesta: landmarks de anclaje para el FÉMUR (F2)

**Estado:** PROPUESTA; todo es ESTIMATE · **Fecha:** 2026-11-04 · Relacionado: `ASSET_FITTING_PROPOSAL.md` §3–§4,
Decisión 61 (validador F0: mínimo 3 anclajes no colineales), Decisión 62 (BodyParts3D, uso interno),
`docs/audit/A18_BP3D_BONE_MAPPING.md`.

## Nombres: qué existe hoy

`src/character_engine/domain/anatomy/landmarks/` define el **modelo** (`Landmark`, `LandmarkRegion`,
`LandmarkSet`), pero **no tiene una lista cerrada de nombres**. Los nombres que ya figuran en el repo son estos:

| Nombre existente | Dónde | Observación |
|------------------|-------|-------------|
| `left_/right_acetabulofemoral_joint_center` | `docs/audit/A03_LANDMARK_MODEL.json`, `references/biomechanics.json` | Centro articular de la cadera (lado pelvis/fémur) |
| `SPHERE_FITTING_TO_FEMORAL_HEAD` | `docs/audit/A03_JOINT_CENTER_MODEL.json` | Método ya previsto para ese centro |
| `left_/right_medial_epicondyle` | `A03_LANDMARK_MODEL.json` (sección rodilla) | Sin hueso explícito en el nombre |
| `left_/right_lateral_epicondyle` | `A03_LANDMARK_MODEL.json` (sección **codo**, `HUMERUS_REFERENCE_FRAME`) | **Ambiguo**: hoy es del húmero |
| `left_/right_tibiofemoral_joint_center` | A03, `biomechanics.json` | Centro articular de la rodilla |
| `femoral_head_radius` | `biomechanics.json` | Rango 20–30 mm, ASSUMPTION |

Como el nombre "epicóndilo" es ambiguo entre húmero y fémur, se **propone agregar** (con fuente de atlas y OK
del dueño, §8.4 de la propuesta) nombres con el hueso explícito. Por ahora solo se proponen; **no se agrega
nada**:

`femoral_head_centre`, `greater_trochanter_apex`, `femoral_lateral_epicondyle`, `femoral_medial_epicondyle`,
`intercondylar_notch_centre` (el lado va en el campo `side` del manifiesto, no en el nombre).

## Candidatos

En el BP3D izquierdo (FJ3259) medí: 1623 vértices y arista mediana de 4,8 mm (media 7,4; máxima 106). Un
punto tomado de un **vértice** tiene, como mucho, la resolución de la malla; uno **ajustado** (esfera,
centroide) promedia muchos vértices.

| # | Landmark propuesto | Cómo se obtiene de la malla | Precisión esperada (ESTIMATE) | Rol |
|---|--------------------|-----------------------------|-------------------------------|-----|
| 1 | `femoral_head_centre` (= `acetabulofemoral_joint_center` del lado fémur) | Ajuste de esfera por mínimos cuadrados sobre los vértices de la cabeza (proximal y medial), con una pasada de rechazo de puntos lejanos. **Prueba hecha** en FJ3259: 290 puntos, r = 22,9 mm, RMS 0,68 mm (dentro del rango 20–30 mm de `biomechanics.json`) | ≈ 1 mm | Posición proximal; ancla el joint de cadera |
| 2 | `femoral_lateral_epicondyle` | Vértice extremo en la dirección lateral (±X según el lado), dentro del 10 % distal | ≈ 5 mm (1 arista); depende de la pose | Ancho y roll en la rodilla |
| 3 | `femoral_medial_epicondyle` | Igual que el 2, en la dirección medial | ≈ 5 mm | Ancho y roll en la rodilla |
| 4 | `intercondylar_notch_centre` | Centroide de los vértices de la escotadura (entre los cóndilos, distal-posterior), o punto medio de 2–3 si se usan los extremos | ≈ 3–5 mm | Posición distal; aproxima el joint de rodilla |
| 5 | `greater_trochanter_apex` | Vértice más proximal-lateral del 20 % proximal, lateral al cuello | ≈ 5 mm | Tercer punto no colineal proximal; roll del cuello |

**Mínimo para F2:** 1 + 2 + 3 (no colineales: fijan posición, rotación y roll; cumplen la Decisión 61). Los 4 y
5 son redundancia para medir el error de registro (RMS de anclajes).

## Reglas al aplicar (Decisión 16)

- Los anclajes **llevan el mesh al rig**; nunca mueven joints canónicos. El centro de la cabeza y la escotadura
  se comparan con el head y el tail de `FEMUR_L/R` y se reportan como error, sin corregir el esqueleto.
- "Lateral" y "medial" dependen del lado: en `_L`, lateral = +X (Decisión 33). BP3D usa los mismos ejes (A18).
- Los extremos por vértice dependen de la pose del asset (BP3D está en pose anatómica). Se miden después de la
  normalización de ejes y unidades.
- La tolerancia RMS de anclajes (2 mm propuesta, ESTIMATE) sigue PENDIENTE del dueño. Con epicóndilos de ~5 mm
  de resolución, 2 mm puede no alcanzarse con la malla al 99 %; hay que medirlo en F2 antes de fijarla.

## Pendiente

- Fuente de atlas para las definiciones exactas de cada landmark (§8.4).
- OK para agregar los nombres a una lista cerrada en `domain/anatomy/landmarks`.
- Desambiguar `lateral_epicondyle` / `medial_epicondyle` de A03 (húmero frente a fémur).
