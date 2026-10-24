# Deliverable 1 — Granaderos fight (DRAFT)

**Status:** DRAFT — nothing here is decided; steps and acceptance criteria are **PROPOSED**.
**Owner choice (2026-10-24):** "Pelea de Granaderos" is the first deliverable (decision card, after the owner's
message of 22:57 UTC).
**Matrix row:** DELIVERABLE-1 in `docs/product/CE-MASTER-REQUIREMENTS-MATRIX.md`.

## 1. Goal (owner's words)

* "quiero que todo ocurra a distancias y con velocidades y movimientos realistas, tengo que realizar granaderos en
  cosas cotidianas, a caballo, realizar las tomas ponerlos a luchar" (22:57 UTC) — this deliverable covers the
  **fight shots (tomas)** of Granaderos.
* Engagement = "como reacciona la cinematografía de movimiento según proximidad a enemigo o NPC … ataques frontales
  cambia toda la cinematografía ligeramente" (draft engagement §10).
* Simulation offline in Blender, gameplay runtime in Godot (Decision 45); production line in Blender (Decision 42).

## 2. Inventory

### Reusable today

| Piece | Where | State |
|-------|-------|-------|
| Deterministic combat L1 (60 Hz, 8 moves, guard/throw, wounds) | `domain/gameplay/combat.py` + `ce_shenmue_combat.gd` | IMPLEMENTED, replays identical Python ↔ Godot |
| Wound assessment + markers on bones | `domain/trauma`, addon `apply_wound`, Godot `add_wound_marker` | IMPLEMENTED (tissue thicknesses ESTIMATE) |
| Canonical skeleton 208 nodes, rig (IK arms/legs, spline spine/neck) | data + addon | IMPLEMENTED |
| Equipment sockets + PLACEHOLDER sabre (0.90 × 0.035 m box) | `domain/rigging/sockets.py`, addon | IMPLEMENTED (placement ASSUMED) |
| Workbench full-body preset (camera, lights, floor) | addon `setup_fullbody_workbench` | IMPLEMENTED |
| Solver benchmark (Bullet, cloth, soft body, particles, geonodes, fluid) | `scripts/solver_benchmark.py` | IMPLEMENTED, results in `docs/audit/EXPERIMENT-0-RESULTS-2026-10-24.md` |
| Godot arena (two fighters, HUD, autoplay, windowed on the GT 740M) | `runtime/godot/arena_play.tscn` | IMPLEMENTED (bone proxies only) |
| Mocap import/retarget to the canonical rig | addon `import_mocap`, `retarget_mocap` | IMPLEMENTED |

### Missing or blocked

| Item | Blocked by |
|------|-----------|
| Granaderos uniform (casaca, morrión, correajes, botas) | **cited historical source** (Decision 12) + owner's drawings |
| Base body mesh | owner decision **artist-made vs generated** (Decision 4.2; MESH-AUTHORING-TOOL form A/B) |
| Real sabre (dimensions, mass, curvature) | **cited source** |
| Realistic reach / speed / timing values for strikes and footwork | **cited sources** (REALISM-UNITS) |
| Engagement cinematography (what changes with proximity/direction) | owner answers **Q10–Q14** (engagement draft §10) |
| First offline experiment (e.g. sabre impact on a body region) | owner choice (Q9) |
| Baked reaction format (glTF morph targets / bone animation; Godot has no Alembic) | owner decision |
| Material parameters (bone, muscle, skin, cloth, steel) | **cited sources** or ESTIMATE marks (MATERIAL-SWATCHES) |
| Sabre moves (current move set is unarmed, Shenmue-style) | spec of armed moves (owner) |

## 3. Smallest testable steps (dependency order) — PROPOSED

| # | Step | Depends on | PROPOSED acceptance criterion | Owner |
|---|------|------------|-------------------------------|-------|
| D1-0 | Answer the decisions in §4 | — | answers recorded in DECISION_LOG | Mariano |
| D1-1 | Source register: sabre, gaits/speeds, strike reach, uniform references listed as NOT_ACQUIRED with citations | D1-0 | `source_registry.json` entries pass the existing registry tests; no value used before approval | Claude (search) + Mariano (approve) |
| D1-2 | Two-fighter Workbench fight layout in Blender: two canonical skeletons + placeholder sabres, camera from the full-body preset, one strike keyed by hand | — | headless Blender 3.6 test: both rigs present, sabre on hand socket, render produced, collisions visible (sabre proxy vs bone proxies) | Claude |
| D1-3 | Engagement camera v0 in Blender: camera parameters as a function of distance and attack direction for the scenario chosen in Q14 | D1-0 (Q10–Q14) | deterministic: same inputs → same camera keys (hash); renders for 3 distances × 2 directions | Claude |
| D1-4 | First offline experiment (Q9), e.g. sabre impact on a body region with Bullet/soft body, recorded as an experiment (conditions → measurements → expression → SHA-256) | D1-0, D1-1 | experiment JSON validates; key frame shows the collision; all values ESTIMATE or cited | Claude |
| D1-5 | Bake the experiment result into the chosen format and play it in the Godot arena when the matching hit happens | D1-4, baked-format decision | Godot headless test: reaction plays on the scripted hit; replay identical | Claude |
| D1-6 | Replace gameplay reach/speed constants with sourced values for sabre moves | D1-1, armed-move spec | reference fights updated; Python ↔ Godot replay identical; provenance per value | Claude |
| D1-7 | Base mesh + uniform on the fighters | mesh decision, uniform source, owner drawings | mesh bound to the 208-bone rig; no tearing in rest pose (CINE-GR-001 criteria) | Mariano (art) + Claude (pipeline) |
| D1-8 | Fight shot (toma) render in Workbench, reviewed by the owner | D1-2…D1-7 | owner accepts the render (Jidoka: any failed check stops the row) | Mariano |

## 4. What Mariano must provide or decide first

1. Base mesh origin: artist-made (by you, from your drawings) or generated (MPFB2/other) — and licence policy
   (CC0/CC BY only, or share-alike allowed).
2. Uniform and sabre references: your drawings/notebook pages and/or bibliography to search and cite.
3. Engagement answers Q10–Q14 (what changes, distance bands/sectors, first scenario).
4. First offline experiment (Q9), e.g. sabre cut/impact on the forearm or the torso.
5. Armed moves for the first fight (which sabre strikes/guards; on foot or mounted — horse needs data).
6. Baked reaction format preference (bone animation vs morph targets) — or leave it to a small comparison test.
