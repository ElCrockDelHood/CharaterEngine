# Traspaso — Character Engine (estado al 2026-11-04)

Documento de arranque para cualquier hilo nuevo. Leer **solo esto** primero; el resto se consulta bajo demanda.

## 1. Dónde está todo

- Repo: `C:\DEV\Proyectos\CharaterEngine-20261004T202505Z-1-001\CharaterEngine`, remoto
  `github.com/ElCrockDelHood/CharaterEngine`.
- `origin/main` = `75d0e93` (push del 2026-10-28). El trabajo posterior (de A13 a A26, Decisiones 54–71) está en la
  rama **`anatomy/a13-a24-base`**, pendiente de revisión antes de mergear a `main`.
- Herramientas en `C:\DEV\Tools`: Blender 3.6.23 (referencia), Godot 4.7.2 (tests), UPBGE 0.50 (opcional).
- Tests: `.venv\Scripts\python.exe scripts\test.py`, `scripts\lint.py`, `scripts\engine_tests.py blender godot`
  (logs en `logs/`). Último estado: pytest todo verde, lint OK, Blender 40/40, Godot 60/60.
- Decisiones: `docs/reorientation/DECISION_LOG.md` (última: **71**; siguiente libre: **72**).
  Índice de auditorías: `docs/audit/INDEX.md`.
- Referencias externas (fuera del repo, nunca se commitean): `assets/anatomy/README.md`.

## 2. Qué se hizo desde el 28/10 (en la rama)

| Tema | Auditoría / Decisión |
|------|----------------------|
| Pie reconstruido con largo con fuente | A13 / 54 |
| Masa efectiva, modelo de golpe, cinemática de cabeza, strikers por movimiento (opt-in) | A14–A17 / 58–60 |
| Biblioteca de reacciones D1 (esquema 6), arena souls-like, batch export / retarget, material sample 2 | 55–57 y commits de producto |
| Ajuste de assets: manifiesto F0, registro F1, ajuste F2 en Blender | 61, 63, 64, 66 (A19, A20, A22) |
| BodyParts3D: mapeo de huesos, uso interno | A18 / 62 |
| Proxies de lo que falta en BodyParts3D (músculos, ligamentos, cóccix, huesecillos) | A25 / 69 |
| Correcciones del esqueleto canónico: peroné lateral, centros de cadera 180,2 mm, cintura escapular (hombros 406,8 mm, clavícula SC→AC, escápula AC→AI) | A21, A23, A24 / 65, 67, 68 |

## 3. Reglas que siguen vigentes

- Spec antes que código; no inventar datos: todo valor lleva su procedencia (PROVEN / DERIVED / ESTIMATE / …).
- Datos canónicos con huella (Decisión 52): cada cambio necesita el OK del dueño, un script determinista,
  una Decisión nueva y la huella actualizada en el mismo commit.
- Si un cambio altera el gameplay o un replay de Godot, se para y se reporta antes del commit.
- Descargas solo con OK, archivo por archivo, guardadas fuera del repo con su hash y antivirus (Decisión 46).

## 4. Pendiente del dueño

1. Tolerancias del ajuste (A19 / A20 / A22 dan la dispersión medida).
2. Licencia de publicación de BodyParts3D (Decisión 62; precedente público: human-atlas la toma como CC BY 4.0).
3. ~~Reparentar `CLAVICLE_*` a `STERNUM`~~: hecho (Decisión 70).
4. Columna: curva aplicada (Decisión 71); pendiente el espaciado cervical (mide 30 mm). Siguientes: tórax, cráneo, altura del hombro.
5. Revisar la rama `anatomy/a13-a24-base` y decidir el merge a `main`.
6. `feature/audio-p0`: sigue "como está"; si se mergea, renumerar su decisión a la siguiente libre.
