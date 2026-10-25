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

## 3.1 D1-2 plan — "maqueta de pelea en Workbench" with reference sheets (PREPARED, not implemented)

**Reference folder (outside the repository) — owner's choice 2026-10-24:** `C:\DEV\Assets\` (current sheets in
`C:\DEV\Assets\Imagenes Para Libertadores, Bocetar y dibujar\`, 6 AI sheets registered in the matrix
REFERENCE-IMAGES; the levita sheet `…5_19AM.png` has back/front/side views). The scene reads files in place, never
copies or modifies them. Optional naming for new files (the existing names are kept as they are)
`<subject>_<view>_<source>_<nn>.png`, e.g. (originally proposed under `C:\DEV\Referencias\`):

```
C:\DEV\Referencias\granadero\granadero_front_ai_01.png
C:\DEV\Referencias\granadero\granadero_side_ai_01.png
C:\DEV\Referencias\caballo\caballo-criollo_side_ai_01.png
C:\DEV\Referencias\items\sable_side_ai_01.png
C:\DEV\Referencias\laminas\estudio-paisano-1810_sheet_ai_01.png
```

`<view>` = front / side / back / three-quarter / sheet; `<source>` = ai / pd (public domain) / own (owner's drawing or
photo). Each file gets a register entry (SHA-256, origin, licence/generator, status) per REFERENCE-IMAGES.

**Scene (Blender 3.6, Workbench, headless-buildable):**
1. Two canonical skeletons (1.80 m) facing each other at a configurable distance, sabre placeholders on the hand
   socket, full-body Workbench camera preset.
2. Reference image planes (front/side) scaled so the drawn figure height matches 1.80 m (scale = ESTIMATE),
   placed behind/next to each skeleton; the sheet as a board for item references.
3. Item proxies (boxes/cylinders) sized from the sheet → all sizes ESTIMATE/ASSUMED.
4. One strike keyed by hand; collision check sabre proxy ↔ bone proxies; Workbench renders front and side.

**Item → rig/asset map:**

| Item on the sheet | Target in the rig / assets | State |
|-------------------|----------------------------|-------|
| sable de granadero | `SOCKET-sabre_hip.L` (carried), `SOCKET-hand_grip.R` (in hand) | sockets exist; sabre = PLACEHOLDER box |
| cuchillo verijero / facón | new socket at the waist (e.g. on SACRUM / COXAL) | not defined |
| faja, cinturón | clothing asset bound to pelvis/lumbar | no clothing system |
| botas de potro | clothing asset on TIBIA/TALUS/feet | none |
| espuelas | small socket on the heel (CALCANEUS) | not defined |
| lazo, maneador, rebenque | hand socket / saddle socket | not defined |
| sombrero / morrión | socket on CRANIUM / FRONTAL | not defined; headwear UNVERIFIED |
| casaca / levita | clothing asset on the torso and arms | none; colours UNVERIFIED |
| montura gaucha | saddle socket on the horse | horse has no skeleton |
| caballo criollo | `horse_adult` template | **NO DATA** (no equine skeleton) — image plane only |
| tero, perro cimarrón | environment / `dog_adult` template | **NO DATA** |

### 3.2 D1-2 — first version DONE (2026-10-25)

Script `runtime/blender/ce_fight_mockup.py` (Blender 3.6, headless, reproducible):

```
blender -b --factory-startup --python runtime/blender/ce_fight_mockup.py -- --anim <UAL1_Standard.glb> --reference <levita sheet .png>
```

* Two canonical 1.80 m skeletons (`CE_Fighter_A`, `CE_Fighter_B`), each with the block dummy + 17 collision
  capsules; spacing **1.6 m (ESTIMATE)**, B turned to face A.
* A plays `Sword_Idle`, B plays `Sword_Attack` — Quaternius UAL1 (CC0) clips retargeted through `quaternius_ual`.
* PLACEHOLDER sabre (0.90 × 0.035 m box) in the right fist. Its blade axis runs through the grip channel
  (METACARPAL_5 → METACARPAL_2) — **ASSUMED, mock-up only**.
* Reference: the owner's levita sheet (`…5_19AM.png`, front/back/side) as an image plane beside the fighters
  (height 1.4 m, ESTIMATE).
* Output: Workbench renders `builds/renders/D1-2_fight_mockup_f###.png`, report `D1-2_fight_mockup.json`
  (closest attacker-sabre to defender-body distance per frame), scene `builds/tests/D1-2_fight_mockup.blend`.
* First run (frames 0, 9, 14, 18, 27, 36): closest sabre-to-body distance 1.195 / 1.481 / 1.187 / 1.132 /
  **0.646** / 1.186 m. There is no contact at 1.6 m spacing; the spacing is a script parameter.

Findings:
* `SOCKET-hand_grip.R` (CINE-GR-001 step 1, ASSUMED) points along the fingers. A sabre held in a fist runs
  through the grip channel instead, so the socket axis needs correcting. **Proposed** for the owner's approval:
  socket direction along METACARPAL_5 → METACARPAL_2. The domain contract was not changed.
* In frame 18 the blade angle looks unnatural (wrist rotation of the clip on the canonical hand). To review once
  the socket axis is decided.
* Import robustness: rigs whose left side is not at +X are now turned 180° automatically (parent empty). The
  Quaternius files did not need it; the headless test covers a source that faces +Y.

### 3.3 D1-2 — second run with the corrected socket (Decision 48), 2026-10-25

The sabre now uses the domain `SOCKET-hand_grip.R` (blade through the fist); the mock-up-only blade was removed.
Contact metric: signed distance from the blade centre line (40 samples) to the defender's collision capsules
(**negative = penetration**); the first run measured vertex to vertex, which cannot see a blade inside a capsule.

| Spacing (ESTIMATE) | f0 | f6 | f9 | f12 | f14 | f16 | f18 | f21 | f24 | f27 | f30 | f36 |
|--------------------|----|----|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| 1.6 m | 1.576 | 1.876 | 1.530 | 1.204 | 1.224 | 1.200 | 1.128 | 0.104 | 0.074 | 1.210 | 1.561 | 1.565 |
| 1.2 m | 1.180 | 1.512 | 1.203 | 0.835 | 0.859 | 0.825 | 0.753 | 0.071 | **−0.008 (contact, forearm.L)** | 0.828 | 1.164 | 1.169 |

Renders: `builds/renders/D1-2_1.6m/`, `builds/renders/D1-2_1.2m/` (12 frames each); scenes
`builds/tests/D1-2_fight_mockup_1.6m.blend`, `…_1.2m.blend`; logs `logs/20261025T041512Z_fight_mockup.log`,
`logs/20261025T041533Z_fight_mockup.log`.
Frame 18 review: the blade now points down, which is the clip's wind-up (wrist dropped before the thrust), no longer
the socket error; whether it looks natural depends on the clip.

### 3.4 Contact → wound (owner approval 2026-10-25, card "Contacto a heridas")

On the first frame with contact (signed distance ≤ 0), the mock-up creates the wound with the **same domain code**
used to build the Godot gameplay table. `blade_contact_to_wound` maps the contact to an INCISION, then
`assess_wound` evaluates it. The bone is the one nearest to the contact point **in the current pose**. A
colour-coded marker is parented to that bone, and a close-up is rendered with X-ray so the marker shows inside the
proxy.

Wound generated at 1.2 m (`logs/20261025T043634Z_fight_mockup.log`, renders `builds/renders/D1-2_1.2m_wound/`):

| Field | Value | Basis |
|-------|-------|-------|
| frame / defender | 24 / CE_Fighter_A | clip `Sword_Attack` (Quaternius UAL1, CC0), spacing 1.2 m ESTIMATE |
| bone / region | RADIUS_L (0.054 m from the contact point) / forearm | nearest posed canonical bone |
| type / depth | incision / 8.2 mm | blade centre line inside the block-dummy capsule (envelope radius ESTIMATE) |
| width | 35 mm | PLACEHOLDER sabre width |
| energy | none | UNKNOWN: not used by the incision assessment; no cited model |
| result | skin + fat breached, severity 2, lethality 0.009, bleeding 0.2, no fracture | `assess_wound`, tissue thicknesses ESTIMATE |
| provenance / seed | ESTIMATE / none (no randomness) | identical SHA-256 `747e9595…f260d3d` in 3 consecutive runs |

**What a model with a cited basis would need:**
1. Measured tissue thicknesses per region (skin, fat, muscle) instead of the per-region ESTIMATEs, e.g. from
   anthropometric / imaging literature.
2. A cited cutting/penetration model: force or energy needed to cut skin, muscle and bone with a sabre edge, and
   blade geometry (edge angle, sharpness).
3. Real sabre data (length, mass, centre of balance) and a measured strike speed. That gives the impact energy
   now left UNKNOWN.
4. A body mesh instead of the envelope capsules, so penetration is measured against a real surface.
5. A cited injury-severity scale for incisions (e.g. an AIS-type classification) to replace the current severity
   rules.

## 4. What Mariano must provide or decide first

1. Base mesh origin: artist-made (by you, from your drawings) or generated (MPFB2/other) — and licence policy
   (CC0/CC BY only, or share-alike allowed).
2. Uniform and sabre references: your drawings/notebook pages and/or bibliography to search and cite.
3. Engagement answers Q10–Q14 (what changes, distance bands/sectors, first scenario).
4. First offline experiment (Q9), e.g. sabre cut/impact on the forearm or the torso.
5. Armed moves for the first fight (which sabre strikes/guards; on foot or mounted — horse needs data).
6. Baked reaction format preference (bone animation vs morph targets) — or leave it to a small comparison test.
