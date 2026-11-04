# Propuesta: ajuste de assets mesh al rig canónico (huesos, músculos, tendones, fascia, grasa, piel)

**Estado:** PROPUESTA (no es decisión) · **Fecha:** 2026-11-04 · **Pedido del dueño:** "que cuando le agregue o
cree los assets mesh de huesos, músculos, tendones, grasa, piel… se ubique todo de la mejor manera … mi Rig tiene
que ser capaz de adaptarse a los demás meshes de esqueleto con músculos, sino lo tenemos que crear."
Restricciones: Decisión 4.2 (no inventar geometría; recibirla de especialistas), 16 (la osteometría dimensiona
meshes, nunca mueve joints), 46 (referencias legales y sin malware), 52 (datos canónicos con huella).

## 1. Qué existe hoy (auditado en el código)

| Pieza | Dónde | Qué hace | Límite |
|-------|-------|----------|--------|
| Normalizador | `domain/assets/normalize.py`, addon `normalize_mesh` / `normalize_rig` | Ejes declarados (up/forward) → Z-up, −Y; escala uniforme a una altura objetivo; origen en el piso | Solo transformación **global**; no reconoce partes ni proporciones |
| Asset por hueso | addon `build.py` `_asset_mesh_path` / `_fit_asset` | Busca `assets/anatomy/meshes/<HUESO>.glb/.gltf/.obj/.ply`; escala el eje más largo de la caja a la longitud de Trotter y lo alinea a cabeza→cola; peso 100 % a ese hueso | Un archivo por hueso; sin registro por landmarks; **roll** (giro sobre el eje largo) indefinido; el README dice que el lado opuesto se "espeja", pero `_fit_asset` **no espeja** (un fémur izquierdo quedaría con la forma del derecho); la carpeta está vacía |
| Proxies de hueso | `build_bone_meshes` | Conos con longitud osteométrica (DERIVED) y forma ESTIMATE | No es geometría real |
| Músculos y tendones | `domain/tissue/muscles.py` (50 entradas), `build_muscle_meshes` | Husos entre origen e inserción (topología PROVEN, geometría ESTIMATE); pesos lineales entre 2 huesos | No existe ruta de importación de músculos reales |
| Grasa, fascia, piel | `domain/tissue/layers.py` (espesores por región, ESTIMATE), `build_skin_envelope` | Piel = envoltura Skin-modifier, pesos al hueso más cercano | Sin mesh de grasa ni fascia; sin importación de piel |
| Dummy de bloques | `domain/rigging/block_dummy.py` | 17 cápsulas = colisión | Proxy; no se ajusta a un mesh de piel |
| Rig de juego | `domain/rigging/game_rig.py` (`canonical_to_game`) | 66 huesos derivados de los 208 nodos | Sirve de destino del skinning de juego, no del ajuste |
| Sockets | `domain/rigging/sockets.py` | Anclajes de equipo por hueso canónico | Mismo patrón que necesitan los assets |
| Modelo de mesh del dominio | Decisión 4.1 (`HumanMesh`…) | — | **No implementado** |

## 2. Respuesta: ¿puede hoy el rig adaptar un esqueleto o músculos de terceros?

**No, salvo el caso mínimo** de un hueso aislado ya modelado sobre su eje largo y nombrado con el nombre canónico.
No puede: (a) recibir un esqueleto completo en un archivo y separarlo en huesos; (b) registrar un mesh de otras
proporciones por landmarks (solo escala por un eje y alinea un vector); (c) fijar el roll ni espejar correctamente
L/R; (d) importar músculos, tendones, grasa, fascia o piel reales; (e) pesar un mesh deformable (piel, músculo)
con pesos suaves de calidad; (f) medir y reportar el error del ajuste. Hay que **crearlo** (fases en §7).

## 3. Contrato de asset (manifiesto)

Cada asset entra con un manifiesto JSON (uno por archivo), validado en dominio puro antes de abrir Blender:

```json
{
  "asset_id": "femur_bp3d_v4", "file": "FEMUR.glb", "sha256": "<de los bytes>",
  "layer": "bone | muscle | tendon | fascia | fat | skin",
  "parts": [{"mesh": "Femur", "canonical_bone": "FEMUR", "side": "L | R | mirror | midline",
             "anchors": [{"landmark": "femoral_head_centre", "vertex_or_point": [0.0, 0.0, 0.0]},
                         {"landmark": "lateral_epicondyle", "vertex_or_point": [0.0, 0.0, 0.0]}]}],
  "attachments": [{"muscle": "BICEPS_BRACHII", "origin_bone": "SCAPULA", "insertion_bone": "RADIUS"}],
  "source_units": "m | cm | mm", "up": "+Y", "forward": "+Z",
  "licence": "CC BY 4.0", "author": "…", "origin_url": "…", "provenance": "USER_INPUT"
}
```

* **Hueso canónico + landmarks de anclaje**: mínimo 3 por parte rígida (fija posición, rotación **y roll**);
  los nombres de landmark salen de `domain/anatomy/landmarks` (lista cerrada, a ampliar con fuente).
* **Músculos/tendones**: origen e inserción por hueso canónico (coherentes con `MUSCLES`, topología PROVEN).
* **Procedencia y licencia** obligatorias (Decisión 46); sin licencia leída → el asset se rechaza.
* **SHA-256** del archivo en el manifiesto; la carpeta de assets no entra en la huella canónica (Decisión 52).

## 4. Pipeline de ajuste (sin mover joints canónicos — Decisión 16)

1. **Validar manifiesto** (dominio): esquema, licencia, hash, huesos y landmarks existentes.
2. **Normalizar** unidades y ejes (`normalize.py` ya existe).
3. **Registro rígido por landmarks** (dominio): Kabsch/Umeyama con escala uniforme por parte → transformación y
   error RMS de anclajes. Si hay 2 landmarks + eje largo, el roll se fija con un tercer punto obligatorio.
4. **Deformación por segmento** (dominio genera los parámetros, Blender aplica): escala no uniforme acotada a lo
   largo del eje del hueso para llevar la longitud del asset a la osteométrica; los joints canónicos quedan fijos,
   el mesh se adapta a ellos y no al revés.
5. **Capas blandas** (músculo → fascia → grasa → piel): cada capa se ajusta sobre la anterior respetando los
   espesores por región (`layers.py`, ESTIMATE) como mínimo/máximo; músculos registrados por origen-inserción.
6. **Pesos / skinning**: hueso = rígido 100 %; músculo y tendón = entre origen e inserción (ya existe, mejorar con
   distancia geodésica); piel = pesos suaves (Blender *heat* / *data transfer* en 3.6) + normalización ≤ 4
   influencias por vértice para Godot.
7. **Colisión**: cápsulas del dummy re-ajustadas al volumen de la piel importada (hoy usan radios ESTIMATE).
8. **Reporte** por asset: error de anclajes, interpenetración entre capas, simetría L/R, pesos, procedencia.

**Dominio puro vs Blender 3.6**: manifiesto, registro por landmarks, parámetros de deformación, espesores,
validaciones numéricas y reportes → dominio (testeable con pytest, sin `bpy`). Importación, aplicación de la
deformación, pesos *heat*, decimado y render → addon Blender 3.6 (único lugar con `bpy`).

## 5. Validaciones medibles (tolerancias PENDIENTES del dueño; valores = ESTIMATE)

| Validación | Métrica | Tolerancia propuesta |
|------------|---------|----------------------|
| Anclajes | RMS landmark asset ↔ canónico | ≤ 2 mm (ESTIMATE) |
| Longitud ósea | asset vs osteometría (Decisión 16) | ≤ 1 % (ESTIMATE) |
| Joints | joints canónicos tras el ajuste | 0 movidos (exacto, hoy con huella) |
| Simetría | espejo L/R de partes `mirror` | ≤ 1 mm (ESTIMATE) |
| Capas | vértices de una capa dentro de la anterior | 0 % fuera, holgura PENDIENTE |
| Pesos | suma de pesos por vértice; influencias | = 1 ± 1e-6; ≤ 4 en juego |
| Deformación | estiramiento de aristas en 6 poses de prueba | PENDIENTE de fuente |

## 6. Calidad escalable por hardware

Un solo asset fuente de alta resolución; niveles generados en Blender y elegidos por perfil:

| Nivel | Uso | PC actual (GT 740M, 2 GB) | PC mejor |
|-------|-----|----------------------------|----------|
| Q0 proxy | gameplay, colisión | sí (hoy) | sí |
| Q1 juego | Godot, rig de 66 huesos, ≤ 4 influencias | sí, con presupuesto de vértices a medir (A12) | sí |
| Q2 trabajo | edición en Blender, capas visibles por separado | parcial (capas de a una) | sí |
| Q3 cine | render, todas las capas, subdivisión | render lento offline | sí |

Los presupuestos (vértices, ms por frame) se miden como en A12, no se suponen. Cambiar de PC no cambia datos: el
manifiesto, los hashes y el pipeline son los mismos; solo cambia el nivel por defecto.

## 7. Fases y criterios de aceptación

| Fase | Entregable | Aceptación |
|------|------------|------------|
| F0 | Esquema de manifiesto + validador (dominio) + tests | Rechaza sin licencia/hash/hueso; acepta un ejemplo sintético |
| F1 | Registro rígido por landmarks + reporte (dominio) | Recupera una transformación conocida con error < 1e-6 sobre datos sintéticos |
| F2 | Asset de hueso real en Blender 3.6: registro, roll, espejo correcto, longitud | Un hueso de prueba con licencia (a elegir por el dueño) dentro de las tolerancias §5 |
| F3 | Esqueleto completo en un archivo → partes por manifiesto | 206 partes asignadas o reportadas como faltantes |
| F4 | Músculos/tendones reales por origen-inserción + pesos | Topología igual a `MUSCLES`; pesos válidos; sin interpenetración con hueso |
| F5 | Fascia, grasa y piel por capas + pesos suaves + cápsulas desde la piel | Validaciones §5 en 6 poses; export Q1 a Godot pasa el contrato |
| F6 | Niveles Q0–Q3 y perfiles de hardware | Q1 medido en la GT 740M; Q3 medido en la PC nueva |

## 8. Decisiones que necesita Mariano

1. Aprobar el **manifiesto** (§3) como contrato de asset (sería una decisión numerada).
2. Fijar las **tolerancias** de §5 (o pedir fuente para cada una).
3. Elegir la **fuente del primer asset real** (p. ej. BodyParts3D: licencia a verificar; o modelado propio) — toda
   descarga con tu OK (Decisión 46).
4. Lista inicial de **landmarks** por hueso (¿ampliar `domain/anatomy/landmarks` con una fuente de atlas?).
5. Orden de fases (¿huesos primero, o piel primero para el juego?) y si F4–F5 esperan a la otra PC.
6. Corregir ya el README de `assets/anatomy/meshes` (dice que espeja y no lo hace) o esperar a F2.
