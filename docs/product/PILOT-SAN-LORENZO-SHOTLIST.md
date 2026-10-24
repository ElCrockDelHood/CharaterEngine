# Piloto D1 — San Lorenzo: lista de tomas (BORRADOR)

**Piloto D1 (autor, 2026-10-24):** mezcla de entrenamiento, previos a la batalla con cotidianos de la época, y la
batalla de San Lorenzo (3-feb-1813, fecha a citar). Estructura general y escenarios: `PILOT-SAN-LORENZO.md`.
**Referencia de investigación:** video EducaciónSantaFe "San Martín y la Batalla de San Lorenzo" (Nivel 1 · Lección 1,
10:23), resumen aportado por Mariano. El guion y los bocetos son del autor; **no** se copia texto, narración ni
imágenes del video.
**Plantilla:** modelo de boceto PROPUESTO (matriz, STORYBOARD-TO-SHOT). Todas las tomas están vacías.

Campos por toma: `shot_id` · `boceto` (archivo + SHA-256) · `escena/lugar` · `plano` · `movimiento de cámara` ·
`duración s` · `acción` · `lente mm (ESTIMATE)` · `engagement` · `notas` · `procedencia`.

---

## A) Cotidiano de época

| shot_id | boceto | escena/lugar | plano | movimiento de cámara | duración s | acción | lente mm | engagement | notas | procedencia |
|---------|--------|--------------|-------|----------------------|------------|--------|----------|------------|-------|-------------|
| SL-A-01 | | | | | | | | — | | |
| SL-A-02 | | | | | | | | — | | |

## B) Entrenamiento

| shot_id | boceto | escena/lugar | plano | movimiento de cámara | duración s | acción | lente mm | engagement | notas | procedencia |
|---------|--------|--------------|-------|----------------------|------------|--------|----------|------------|-------|-------------|
| SL-B-01 | | | | | | | | | | |
| SL-B-02 | | | | | | | | | | |

## C) Batalla

### Línea de tiempo NARRATIVA (según el resumen del video; marcas del video)

Todo dato de esta lista está **SIN VERIFICAR – según relato del video**.

| Marca | Momento |
|-------|---------|
| 00:02–01:56 | Contexto y misión: San Martín organiza el Regimiento de Granaderos a Caballo (1812) para proteger la costa del Paraná |
| 01:57–02:38 | Detección: 28 de enero, noticia de la flota realista; salida con ~120 granaderos |
| 02:39–04:06 | Aproximación al convento San Carlos Borromeo ~02:00 del 3-feb; observación desde un punto elevado; combate ~05:00 |
| 04:07–05:26 | Ataque envolvente en dos columnas de ~60 (San Martín y Bermúdez); retraso de la columna de Bermúdez; cae el caballo de San Martín |
| 05:09–06:37 | Intervención y muerte de Cabral; los granaderos se reorganizan y vuelven a cargar; retirada realista a la barranca |
| 07:03–08:31 | Asistencia médica en el convento a heridos de ambos bandos |
| 08:32–10:23 | Memoria histórica (restos, urnas, Marcha de San Lorenzo, monumento) |

Nota: el esquema de dos columnas es **conceptual, no a escala**.

**Verificación pendiente (fuentes citadas antes de usar en una toma):** fecha; duración (los 15 min son una
estimación narrativa); bajas realistas (la cifra de 52 no es el total); causa de la muerte de Bermúdez; pesos y
protecciones del uniforme; datos del monumento.

| shot_id | boceto | escena/lugar | plano | movimiento de cámara | duración s | acción | lente mm | engagement | notas | procedencia |
|---------|--------|--------------|-------|----------------------|------------|--------|----------|------------|-------|-------------|
| SL-C-01 | | | | | | | | | | |
| SL-C-02 | | | | | | | | | | |

---

## Necesidades del piloto para el motor (sin valores inventados)

| Necesidad | Para | Estado hoy |
|-----------|------|------------|
| Marcha / caminata | A, B, C | no hay ciclo de caminata (LOCOMOTION-STANDALONE); velocidades con fuente citada (REALISM-UNITS) |
| Montar / desmontar, a caballo | A, B, C | caballo **SIN DATOS** de esqueleto (ANATOMY-MESH) |
| Ejercicio de armas (sable, carabina) | B | combate actual sin armas (estilo Shenmue); golpes de sable a especificar |
| Momentos standalone (quieto, mate, fogón) | A | no hay animaciones standalone |
| Carga de caballería, caída de caballo | C | simulación offline en Blender (Decisión 45); caballo sin datos |
| Heridas y atención | C | sistema de heridas por hueso (ESTIMATE) |
