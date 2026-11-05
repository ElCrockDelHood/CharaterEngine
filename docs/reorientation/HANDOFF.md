# Traspaso — Character Engine (estado al 2026-11-05)

Documento de arranque para cualquier hilo nuevo. Leer **solo esto** primero; el resto se consulta bajo demanda.

## 1. Dónde está todo

- Repo: `C:\DEV\Proyectos\CharaterEngine-20261004T202505Z-1-001\CharaterEngine`, remoto
  `github.com/ElCrockDelHood/CharaterEngine`.
- `origin/main` = `75d0e93` (push del 2026-10-28). El trabajo posterior (de A13 a A31, Decisiones 54–77) está en la
  rama **`anatomy/a13-a24-base`**, pendiente de revisión antes de mergear a `main`.
- Herramientas en `C:\DEV\Tools`: Blender 3.6.23 (referencia), Godot 4.7.2 (tests), UPBGE 0.50 (opcional).
- Tests: `.venv\Scripts\python.exe scripts\test.py`, `scripts\lint.py`, `scripts\engine_tests.py blender godot`
  (logs en `logs/`). Último estado: pytest todo verde, lint OK; última corrida de motores (Decisión 75): Blender 40/40, Godot 60/60.
- Decisiones: `docs/reorientation/DECISION_LOG.md` (última: **77**; siguiente libre: **78**).
  Índice de auditorías: `docs/audit/INDEX.md`.
- Referencias externas (fuera del repo, nunca se commitean): `assets/anatomy/README.md`.

## 2. Qué se hizo desde el 28/10 (en la rama)

| Tema | Auditoría / Decisión |
|------|----------------------|
| Pie reconstruido con largo con fuente | A13 / 54 |
| Masa efectiva, modelo de golpe, cinemática de cabeza, strikers por movimiento (opt-in) | A14–A17 / 58–60 |
| Biblioteca de reacciones D1 (esquema 6), arena souls-like, batch export / retarget, material sample 2 | 55–57 y commits de producto |
| Ajuste de assets: manifiesto F0, registro F1, ajuste F2 en Blender | 61, 63, 64, 66 (A19, A20, A22) |
| BodyParts3D: mapeo de huesos; publicación bajo CC BY 4.0 con atribución (`NOTICE`) | A18 / 62, 76 |
| Proxies de lo que falta en BodyParts3D (músculos, ligamentos, cóccix, huesecillos) | A25 / 69 |
| Correcciones del esqueleto canónico: peroné lateral, centros de cadera 180,2 mm, cintura escapular (hombros 406,8 mm, clavícula SC→AC, escápula AC→AI), clavícula bajo el esternón, columna (curva y alturas), tórax, cráneo | A21, A23, A24, A26–A28, A30 / 65, 67, 68, 70–74 |
| Ratios de ancho y largo de cabeza desde ANSUR II | A31 / 75 |
| Diagnóstico de brazos, piernas, manos y pies: no mover articulaciones | A29 |
| Licencias: `NOTICE`, BodyParts3D bajo CC BY 4.0 con atribución, código del proyecto bajo MIT | 76, 77 |

## 3. Reglas que siguen vigentes

- Spec antes que código; no inventar datos: todo valor lleva su procedencia (PROVEN / DERIVED / ESTIMATE / …).
- Datos canónicos con huella (Decisión 52): cada cambio necesita el OK del dueño, un script determinista,
  una Decisión nueva y la huella actualizada en el mismo commit.
- Si un cambio altera el gameplay o un replay de Godot, se para y se reporta antes del commit.
- Descargas solo con OK, archivo por archivo, guardadas fuera del repo con su hash y antivirus (Decisión 46).

## 4. Pendientes reales

**Del dueño**

1. Abrir el PR de `anatomy/a13-a24-base` hacia `main` (si todavía no aparece abierto), revisarlo y hacer el merge. El cuerpo
   listo para pegar está en `C:\DEV\Assets\PR_anatomy_a13-a24-base_body.md`.
2. Tolerancias del ajuste de assets (A19 / A20 / A22 dan la dispersión medida).
3. Aprobar o no el contrato del manifiesto de assets F0 (Decisión 61, PROPUESTO).
4. Opcional: escribir al licenciante de BodyParts3D para cerrar la discrepancia con las cabeceras CC BY-SA 2.1 JP de los OBJ
   (hoy declarada en `NOTICE`, Decisión 76).
5. `feature/audio-p0`: sigue "como está"; si se mergea, renumerar su decisión a la siguiente libre.
   El historial no se reescribe salvo pedido explícito: el `LICENSE` anterior sigue en commits viejos y en `main` hasta el merge.

**Anatomía** (cada cambio de datos canónicos necesita el OK del dueño y una Decisión)

6. Pivote de la mandíbula en la articulación temporomandibular.
7. Altura del hombro y base del cuello (ANSUR cervicale queda 35–45 mm arriba).
8. Costillas con fuente poblacional; curvas de la columna con una referencia Cobb que permita uso comercial.
9. Mallas reales para reemplazar los proxies de `assets/anatomy/proxies/` (A25).

**De otros hilos**

10. Variante F del pie (talón→bola, ANSUR II): con el hilo de animación, junto con el contacto del pie (A29).

**Sin verificar**: UPBGE no se corrió en estos cambios; el CI de GitHub no se pudo ver.

**Cerrado, no reabrir sin motivo**: manos y pies NO se mueven (A29); licencias de publicación y del código (Decisiones 76, 77).
`LICENSE` lleva solo el nombre del dueño; el dato personal anterior ya no está en el árbol de la rama (Decisión 77).
