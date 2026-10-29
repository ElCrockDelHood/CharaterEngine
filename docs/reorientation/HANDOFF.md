# Traspaso — Character Engine (estado al 2026-10-28)

Documento de arranque para cualquier hilo nuevo. Leer **solo esto** primero; el resto se consulta bajo demanda.
Reemplaza al hilo largo "Evaluar Character Engine y entorno C:\DEV".

## 1. Dónde está todo

- Repo: `C:\DEV\Proyectos\CharaterEngine-20261004T202505Z-1-001\CharaterEngine`, rama `main`,
  remoto `github.com/ElCrockDelHood/CharaterEngine`.
- `main` = `origin/main` = `75d0e93` (push hecho el 2026-10-28, 61 commits, aprobado por Mariano).
- Herramientas en `C:\DEV\Tools`: Blender 3.6.23 (referencia), Godot 4.7.2 (tests), UPBGE 0.50 (opcional).
- Tests: `.venv\Scripts\python.exe scripts\test.py` (logs en `logs/`). Último estado conocido:
  934 pytest + 2 fallos esperados, lint OK, Godot 46/46.
- Decisiones: `docs/reorientation/DECISION_LOG.md` (última: **53**). Siguiente número libre: **54**.
- Matriz de requisitos y borradores de producto: `docs/product/` (engagement: `ENGAGEMENT-SYSTEM-DRAFT-v0.md`).

## 2. Qué contienen los últimos commits (ya en origin)

| Commit | Contenido |
|---|---|
| `f6fb556` | Biblioteca de reacciones D1: 7 ataques × 2 guardias × 3 separaciones = 42 entradas JSON para Godot, deterministas (SHA-256). Contacto solo a 0,9 m (3 casos). |
| `eaf7cdd` | Esquema 2: el defensor reproduce su clip de reacción desde el primer contacto. |
| `81540fc` | Docs: respuestas de Mariano a Q10–Q14, orden de trabajo, primer escenario, ejemplos con fuente. |
| `a429692` | Esquema 3: mezcla de entrada de 4 cuadros (ASSUMED) y recuperación del atacante. |
| `75d0e93` | Esquema 4: detección de parry (hojas < 3,5 cm) y variedad de reacción por hueso y gravedad. |
| `d6bba77` … `c3b6982` | Decisiones 49–53: capas de materiales/XPBD, armas, rig de juego CE-GAME-v1, huella SHA-256 de datos canónicos, estilo Souls-like. |

## 3. Decisiones tomadas (resumen)

- Blender = línea de producción completa (modelado, rig, cinemáticas, simulación offline, render);
  Godot = runtime de juego que reproduce reacciones horneadas (Decisiones 40, 42, 45).
- Referencias legalmente seguras y sin malware (46). Regla de música en productos (47).
- Datos canónicos de anatomía con huella fija: cualquier cambio rompe la suite a propósito (52).
- Engagement (borrador, `81540fc`):
  - **Q10**: cambian encuadre de cámara, velocidades y sus efectos (p. ej. poder de ultra velocidad que se ve como cámara lenta o tipo fatality) y la mezcla de animaciones del cuerpo; quiere ejemplos exitosos.
  - **Q11**: 4 bandas de distancia (lejos / media / cerca / cuerpo a cuerpo, en múltiplos de alcance arma+brazo, valores ESTIMATE) × 3 sectores (frente / costado / espalda). PROPOSED.
  - **Q12**: cambia según el rival (vulnerabilidades y fortalezas).
  - **Q13**: aplica a cámara, movimientos y cinemáticas.
  - **Q14**: primer escenario: el granadero se aproxima con armas de distancia, intercambiando disparos, hasta la zona cuerpo a cuerpo. Armas de fuego de época **sin datos con fuente**: no inventar alcances ni velocidades.
  - Orden: enriquecer reacciones → pulirlas → experimento fácil → movilidad táctica/estratégica → áreas y distancias de combate.
- Audio `feature/audio-p0`: revisado, seguro; Mariano eligió **dejarlo como está** (2026-10-28).

## 4. Trabajo a medias SIN commitear en `main` (no perder, no mezclar)

- **Pulido de reacciones + experimento de umbral** (iniciado 2026-10-28 ~23:00 UTC, la sesión se cortó):
  `domain/gameplay/reaction_library.py` (esquema 5: filtro de parry en preparación y mezcla por tipo),
  `runtime/blender/ce_reaction_library.py`, `tests/unit/test_reaction_library.py`, `runtime/godot/tests/ce_test_runner.gd`,
  y nuevos `domain/gameplay/experiments.py`, `runtime/blender/ce_experiment_contact_threshold.py`,
  `scripts/plot_experiment.py`, `tests/unit/test_experiments.py`. Estado de tests desconocido.
- **Pies A13**: `scripts/rebuild_foot_layout.py`, `tests/unit/test_foot_layout.py`, `docs/audit/A13_FOOT_LAYOUT_REPORT.json`,
  cambios en `human_adult_206.json` (52 huesos), `source_registry.json`, `skeleton_serialized.json`,
  `test_contract_fingerprint.py`, `test_extremity_spine_topology.py`. Cambia datos canónicos (Decisión 52).
- **Batch export** (desde 2026-10-25): `runtime/blender/ce_batch_export.py`, `ce_batch_retarget.py`,
  `addon/batch.py`, `pipeline/batch_export.py` y cambios en `addon/__init__.py`, `build.py`, `operators.py`.
- Sin asignar con certeza: `domain/rigging/block_dummy.py`, `tests/unit/test_block_dummy.py`.

## 5. Decisiones pendientes de Mariano

1. **Pies A13**: ¿aceptar el nuevo layout del pie (cambia la huella canónica, requiere decisión nueva)?
2. **Batch export**: ¿terminarlo con tests y commitearlo, o descartarlo?
3. **`feature/audio-p0`**: hoy "dejar como está". Si algún día se mergea: renumerar su decisión 51 → **54**
   (o la siguiente libre) y revalidar Godot y changelog.
4. **Piloto San Lorenzo**: qué bloque boceta primero, duración y cantidad de tomas.

## 6. Próximos pasos acotados

1. Terminar o rehacer el pulido (esquema 5) y el experimento de 10 distancias 0,7–1,1 m; commit separado.
2. Pies A13: cerrar solo con OK de Mariano.
3. Batch export: cerrar solo con OK de Mariano.
4. Después del experimento: movilidad táctica/estratégica, luego bandas y sectores de combate (Q11).

## 7. Convenciones de trabajo

- Spec antes de código; OK explícito para borrados o cambios masivos; commits locales chicos y separados por tema; push solo con OK.
- Todo número no medido se marca ESTIMATE / ASSUMED; determinismo verificado con SHA-256 en dos corridas.
- Toda corrida pasa por `scripts/_logrun.py` → `logs/`.
- **Renders**: usar **EEVEE (o Workbench) para iterar**. Los renders largos de **Cycles** se lanzan como **script de Blender
  en segundo plano** (`blender -b archivo.blend -P script.py`, en background, con log en `logs/`), nunca bloqueando la sesión.
- Pies, batch export y el worktree de audio no se tocan salvo que el hilo sea específicamente para eso.
