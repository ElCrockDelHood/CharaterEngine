# CE-MASTER-REQUIREMENTS-MATRIX

**Owner:** Mariano Martin Galli · **Started:** 2026-10-24 · **Status:** DRAFT (row 1 of N)
**Gate:** CE-Q4 UNBLOCKED 2026-10-24 (Decision 41) · **Pipeline:** production line in Blender, gameplay runtime in Godot (Decision 42)
**Source of the method:** "Product Defined Complete — Cinematografías" (T13–T14) and "Tareas para el
Despliegue" (CINE-SM/GR/H, P1–P15). Chain: PRODUCT → CINEMATOGRAPHY → REQUIREMENT → MANIFOLD →
DOMAIN MODEL → IMPLEMENTATION → TEST → EVIDENCE (Toyota: CTQ, quality gate, jidoka, poka-yoke, kaizen).

**Cell status:** `IMPLEMENTED` = code exists *and* a test proves it · `PARTIAL` = some of it exists ·
`SPECIFIED` = written requirement, no code · `PENDING` = needs a decision or source first ·
`DATA REQUIRED` = cannot be done without a cited source (Decision 12).

**Runtime gating (all rows, Decision 40):** Godot 4 is the primary runtime and the only one that gates a
row's RUNTIME / TEST / ACCEPTANCE cells; UPBGE checks are optional and informative (non-blocking).

**Performance baseline (all rows):** this PC — ASUS N56VB, i3-3120M 2c/4t, 16 GB, GeForce GT 740M 2 GB
(driver 388.73) / Intel HD 4000 — Blender **3.6.23** (reference, Decision 20), viewport/render **Workbench**.

---

## Row CINE-GR-001 — Granadero en reposo

| Column | Requirement | Current state (2026-10-24) | Status |
|--------|-------------|----------------------------|--------|
| **ID** | CINE-GR-001 | — | SPECIFIED |
| **PRODUCT** | Libertadores / Proyecto ALPHA — Ejército de los Andes; acceptance test **P2 Granadero** | product docs only | SPECIFIED |
| **SCENARIO** | Granadero de pie en reposo, cuerpo completo, fondo neutro (sin entorno histórico todavía) | — | SPECIFIED |
| **CHARACTER** | Granadero a Caballo (1812–1826), varón adulto; individual (no NPC genérico) but row 1 uses the base template | `human_male_adult` 1.80 m (USER_INPUT stature, Drillis & Contini proportions PROVEN), 206 bones / 208 nodes, left = +X (Decision 17) | PARTIAL |
| **ACTION** | Static: posición de firmes/descanso militar (weight on both feet, arms at sides, head up) | Only `anatomical`, `tpose`, `apose` poses exist (`domain/anatomy/pose/tpose.py`); no military rest pose, no pose library | PENDING (pose definition needs an owner-approved reference: drill manual / iconography) |
| **CAMERA** | Full-body, eye level ≈ 1.5 m, ~35–50 mm equivalent, whole figure + base in frame; Workbench render | Step 1: operator *Cinematic preset: full body, Workbench* — front camera 50 mm framed from the armature bounds, 1920×1080; headless test: 208/208 bones in frame, no foreign occluder | IMPLEMENTED (eye-level/lens values not yet owner-approved) |
| **ANATOMICAL RESOLUTION** | Full body readable at distance: proportions, posture, limb segmentation; no face/hand close-up required | Canonical skeleton with sourced joint heights; hands A10 and forearm A11 fixed (intra-hand proportions PLACEHOLDER) | PARTIAL |
| **SKELETAL REQUIREMENTS** | 206/208 contract, correct sides, joints at sourced heights, rest pose clean | Implemented and tested (pytest 747; addon headless 20/20 Blender 3.6; Godot 21/21) | IMPLEMENTED |
| **MUSCLE REQUIREMENTS** | Silhouette-level volumes under the uniform (no deformation visible) | 50 bilateral spindle proxies, attachment topology PROVEN, geometry PLACEHOLDER (`domain/tissue/muscles.py`, addon *Tissues*) | PARTIAL |
| **SOFT-TISSUE REQUIREMENTS** | Fat/skin envelope giving a believable body volume under clothing | Skin = skin-modifier envelope from per-region radii (ESTIMATE), proxy only | PARTIAL |
| **MESH REQUIREMENTS** | **Parametric base body mesh** (male), clean topology, weighted to the 208-bone armature, stature-driven | **Does not exist** (no `HumanMesh` domain model; Decision 1.2 "mesh-first" never implemented) | PENDING |
| **DEFORMATION REQUIREMENTS** | None visible in static rest (bind pose only); weights must not tear at shoulders/hips in the rest pose | Proxies 100 % weighted per bone; no skinning of a real mesh | PENDING (depends on mesh) |
| **PHYSICS** | None for a static shot | — | N/A |
| **COLLISION** | Boots on ground plane (z = 0), sabre and scabbard not intersecting the body | Skeleton ground check (Godot gating; UPBGE optional); step 1: placeholder sabre AABB clear of all 192 bone-proxy AABBs (test). No boots, no body mesh to collide with yet | PARTIAL |
| **CLOTHING** | Uniforme de Granaderos: casaca, pantalón, correajes, morrión/kepí — modelled as separate assets bound to the body | **No clothing system / assets**; historical design needs a cited source | DATA REQUIRED |
| **EQUIPMENT** | **Sable** (with scabbard) attached to a **socket** (hip/hand), boots (botas de montar), belts | Step 1: sockets `SOCKET-sabre_hip.L` (COXAL_L) and `SOCKET-hand_grip.R` (METACARPAL_3_R) as domain data (ASSUMED placement) built as MCH bones; **PLACEHOLDER** sabre box parented to the hip socket; tests: follow parent in T-pose and anatomical pose (Δ < 1e-7). No modelled sabre, scabbard, belts or boots | PARTIAL |
| **ENVIRONMENT** | Neutral studio: ground plane + 3-point light; historical environment out of scope for row 1 | Step 1: floor plane + key/fill/rim lights created by the preset (Workbench ignores scene lights; they are for later EEVEE/Cycles) | PARTIAL |
| **RUNTIME** | Production only (Blender authoring/render); optional glTF export for Godot preview | Canonical GLB export (byte-reproducible) + scene GLB from the addon | PARTIAL |
| **PERFORMANCE** | Workbench render ≤ 30 s at 1920×1080 on the baseline PC; viewport ≥ 15 fps with the character | Step 1: Workbench 1920×1080 render **2.38 s** (skeleton proxies + sabre, Blender 3.6.23 background, 2026-10-24). Viewport fps not measured | PARTIAL |
| **MANIFOLD** | M01 Anatomical, M02 Morphological, M03 Skeletal, M07 Surface, M09 Identity, M10 Historical, M11 Clothing, M12 Equipment, M20 Cinematic | M03 implemented; M01 partial; others not started | PARTIAL |
| **DEPENDENCIES** | Base mesh (M07) → skinning → clothing (M11) & equipment sockets (M12) → military pose → camera/scene template | — | SPECIFIED |
| **TEST** | Headless Blender 3.6 test that builds the scene and asserts: 208 bones, mesh bound, boots at z≈0, sabre parented to socket, no body–equipment intersection, camera framing contains the whole figure, render produced | Step 1 scene checks in `runtime/blender/ce_addon_headless_test.py` (24/24 on Blender 3.6): framing, occlusion, socket follow, sabre clearance, render time. Mesh/boots checks pending | PARTIAL |
| **ACCEPTANCE CRITERIA** | All TEST checks pass; render image reviewed and accepted by the owner (Jidoka: any failed check stops the row) | — | SPECIFIED |
| **EVIDENCE** | Rendered PNG + JSON report in `builds/` (ignored) and a versioned summary in `docs/audit/` | Step 1: `builds/renders/<engine>_CINE-GR-001_fullbody.png` + addon report JSON (ignored); summary in DECISION_LOG §37 | PARTIAL |
| **PRIORITY** | P1 (first cinematic row; unlocks P2 Granadero acceptance test) | — | SPECIFIED |

### Minimum gaps to satisfy CINE-GR-001

1. **Parametric base body mesh** (male, stature-driven) bound to the canonical armature — the largest
   gap; needs a decision on origin (artist-made base vs. generated) per Decision 4.2 ("do not invent
   anatomical geometry; receive geometry from specialists").
2. **Military rest pose** ("firmes/descanso") as a sourced pose definition next to `tpose`/`apose`.
3. **Uniform** (Granaderos a Caballo) — requires a cited historical source before modelling.
4. **Boots** (riding boots) as a separate clothing asset.
5. **Sabre + scabbard with a socket** on the rig (hip carry; hand grip later for CINE-03).
6. **Workbench camera/scene template** (full-body framing, neutral light, ground plane) and a headless
   render test with a performance measurement on the baseline PC.

### Step 1 — DONE 2026-10-24 (commit b74327c): scene template + equipment sockets

All acceptance criteria (a)–(f) below passed on Blender 3.6.23; see DECISION_LOG §37.

### (original proposal) "CINE-GR-001 / step 1: scene template + equipment socket"

Scope deliberately avoids anything that needs new anatomical or historical data:

- Add to the Blender addon (Blender 3.6) a **"Cinematic preset: full body, Workbench"** operator that
  creates ground plane, 3-point light and a camera framing the whole armature (bounds-based), and a
  headless render to `builds/renders/`.
- Add **equipment sockets** to `domain/rigging` as named, data-only attachment points
  (`SOCKET-sabre_hip.L`, `SOCKET-hand_grip.R`) parented to canonical bones, built as `MCH-` bones by the
  addon; place a **placeholder box** for the sabre (explicitly labelled PLACEHOLDER) to prove the
  attachment and collision checks.
- **Acceptance criteria:** headless test in Blender 3.6 passes: camera frustum contains all 208 bone
  heads/tails; sockets exist and follow their parents in T-pose and anatomical pose; placeholder sabre
  does not intersect the skeleton proxies; Workbench render produced in ≤ 30 s at 1920×1080 on the
  baseline PC (time logged); pytest and ruff stay green; no change to canonical data.
- Out of scope (need owner decisions / sources first): base mesh, uniform, boots, military pose.

---

## Row ENGAGEMENT-001 — Fight engagement system (Godot runtime) — DRAFT

Owner definition (verbatim) and the full inventory are in `docs/product/ENGAGEMENT-SYSTEM-DRAFT-v0.md`.
Only the owner's words and code facts are filled in. Owner answer 1 (verbatim in draft §4): integrate the 8 points; Claude's interpretation awaiting confirmation = every option of Q1–Q8 in scope. Layering L1/L2/L3 (draft §6) and phasing E0–E8 (draft §7) are PROPOSED; open questions in draft §8.

| Column | Requirement | Current state (2026-10-24) | Status |
|--------|-------------|----------------------------|--------|
| **ID** | ENGAGEMENT-001 | — | SPECIFIED |
| **DEFINITION** | "sistema de enfrentamiento determinado … interacciones entre las cápsulas de colisiones" (owner, verbatim in the draft §1) | — | PARTIAL (definition only) |
| **RUNTIME** | Godot (Decision 42 clarification) | Deterministic 60 Hz frame-data combat (Python domain + GDScript port), arena playable windowed | PARTIAL |
| **DETERMINISM** | Owner: "determinado"; Q4 a and b both selected → tension T-1; PROPOSED: L1 bit-identical, L2 may vary, L3 baked manifest identical (draft §6) | 7 reference fights replay identically Python ↔ Godot | PARTIAL |
| **COLLISION CAPSULES** | Capsule–capsule interactions (owner); body reacts physically, complex result refined into the manifestation (owner answer 1, draft §4); determinism vs physics open (T-1) | None in domain/Godot; hit = root-distance ≤ reach; per-bone hit spheres are data only | PENDING |
| **CONFRONTATION PHASES** | Open (Q1) | Nearest-opponent targeting only | PENDING |
| **COMBAT SYSTEMS** | "sistemas de combate elaborados" — which ones open (Q8) | 8 moves, guard, throws, cancels, knockdown, wounds | PENDING |
| **STYLES** | Open (Q5) | shenmue implemented; souls_like / beat_em_up planned | PENDING |
| **BLENDER → GODOT DATA** | Canonical files only (Decision 42); content open (Q6) | GLB skeleton + gameplay JSON from the Python domain | PENDING |
| **TEST / ACCEPTANCE** | Not specified (no invented criteria) | — | PENDING |
| **PRIORITY** | Not set by the owner | — | PENDING |

Update 2026-10-24: the three-layer design L1/L2/L3 is **CONFIRMED** by the owner (Decision 44). The other
open questions of the draft §8 remain open.

Update 2026-10-24 21:16 UTC: open question 3 **ANSWERED** by the owner (verbatim in the draft §9) — L2 physics
runs **offline in Blender**; manifestations are extracted as meshes, retouched/joined in Blender for cinematics;
the game reacts by state and collision point with baked reactions (interpretation CONFIRMED by the owner, Decision 45; keying,
baked format, performance and offline tool OPEN — draft §9).

---

## Rows ANATOMY / RIG / TISSUE / TREATMENTS / FK — DRAFT (owner request, Decision 44)

Owner request (verbatim in DECISION_LOG §44): real skeleton meshes of different sizes for "nuestros personajes"
and "nuestros animales", rigged "a cada parte, a la cara", "que quede perfecto, así vamos a poder simular las
heridas"; a mesh of all muscles, tendons and fasciae; special treatment of hands, of head and face, then of the
general body, each with its IK; FK extracted from the simulations as results.

| ID | Requirement (owner's words) | Current state in the repo (2026-10-24) | Status |
|----|-----------------------------|----------------------------------------|--------|
| **ANATOMY-MESH** | "modelos de esqueletos meshes reales de diferentes medidas" — humans ("nuestros personajes") and animals ("nuestros animales") | Bones are drawn as **cone proxies** (`build_bone_meshes`); the addon can fit a real per-bone mesh from `assets/anatomy/meshes/<BONE>.glb/.obj/.ply` but the folder holds only a README (**no real meshes**). Stature scaling exists (osteometry table). Animals: `horse_adult`, `dog_adult` templates marked **NO DATA YET** (no skeleton). Species list: **UNKNOWN** | PENDING (DATA REQUIRED) |
| **RIG-PARTS** | Rig "a cada parte, a la cara, etc." — "que quede perfecto" | 208-bone deform armature + control rig: IK arms, legs, clavicle follow; spline spine and neck; equipment sockets. **No finger rig controls, no face rig** (no jaw/eyes/facial controls, no shape keys). "Perfecto" is **not testable**: measurable criteria needed from the owner | PARTIAL |
| **MUSCLE-FASCIA-MESH** | "un mesh de todos músculos, tendones, fascias" | 50 bilateral **spindle proxies** (attachment topology PROVEN, geometry PLACEHOLDER/ESTIMATE) with tendon ends; fat/fascia only as **per-region thickness ESTIMATES** in the tissue-layer model; **no fascia mesh** | PENDING (DATA REQUIRED) |
| **TREAT-HANDS** | Special treatment of hands, with IK | Hands rebuilt (A10, intra-hand proportions PLACEHOLDER); arm IK ends at the wrist; **no finger IK/FK controls** | PARTIAL |
| **TREAT-HEAD-FACE** | Special treatment of head and face, with IK | Skull bones only (CRANIUM container, FRONTAL, PARIETAL, TEMPORAL, MANDIBLE…); neck spline; **no face rig, no facial mesh** | PENDING |
| **TREAT-BODY** | General body treatment, with IK | Limb IK + spline spine/neck exist (see RIG-PARTS) | PARTIAL |
| **FK-FROM-SIM** | "los FK los vamos a extraer de las simulaciones como resultados" (FK not hand-authored) | Mocap retarget to FK exists (`import_mocap`, `retarget_mocap`); **no simulation → FK extraction** (fits L2/L3 of Decision 44) | PENDING |
| **WOUNDS (context)** | "así vamos a poder simular las heridas" | Today: wound = point + type + depth/width/energy → `assess_wound` over **region tissue-thickness ESTIMATES** → severity/lethality/bleeding/fracture + colour marker on the nearest bone. No mesh is cut or deformed | PARTIAL |

Acceptance criteria for all rows: **not specified** (no invented criteria; the owner defines them).

### Provenance rule for every mesh (reminder, Decisions 4.2 and 12)

* Never invent anatomical data or geometry. A mesh enters the repository only with a **cited source and
  licence** registered in `src/character_engine/data/anatomy/references/source_registry.json`, status
  `NOT_ACQUIRED` until it is downloaded **and** approved by the owner.
* Sizes obtained by scaling or fitting a sourced mesh are `ESTIMATE`/`DERIVED`, never `PROVEN`.
* **Licence compatibility is a decision for the owner**: share-alike licences (CC BY-SA) oblige derived
  assets to be shared under the same licence; non-commercial licences may conflict with the product.

### Candidate sources found (research only — nothing downloaded, nothing registered yet)

| Source | Content (as reported) | Licence (as reported, to verify on the official page) |
|--------|-----------------------|--------------------------------------------------------|
| BodyParts3D 4.0 (DBCLS, Japan) | Adult male reference anatomy, ~2,234 OBJ meshes (bones, muscles, organs) | Older releases CC BY-SA 2.1 JP; a third-party notice says the current database licence is CC BY 4.0 — **unverified** |
| Z-Anatomy (Blender template) | Skeleton, muscles, ligaments, insertions, vessels, nerves, organs; derived from BodyParts3D; Blender 2.8+/3.x | CC BY-SA 4.0 (share-alike). Fascia/tendon coverage **unconfirmed** |
| MakeHuman / MPFB2 (Blender add-on) | Parametric human base mesh (hm08) of any size, auto-rig incl. Rigify | Assets CC0, code GPLv3; face rig coverage **unconfirmed** |
| Univ. of Edinburgh R(D)SVS (Open.Ed, Sketchfab) | CT-derived animal skeletons and skulls incl. a horse | "openly licensed" — exact licence per model **unverified** |
| LSU / JoVE 62276 | CT-based whole-body rigged horse skeleton (research) | Release and licence **unknown** |

---

## Rows PHOTO-TO-3D / WORK-SIGNING — DRAFT (owner idea, recorded only, 2026-10-24)

Owner message (verbatim): "tal vez puedo crear algún tipo de programa para crear meshes, tengo mucha
documentación porque trabaje mucho tiempo en una empresa audiovisual para un modelista resolviendo sistemas
audiovisuales de simulación. para poder agregarle algun sistema que me permita crear NTFS Hashes Id con la
manifestacion, como ir firmando la obra. estuve documentanco muchas cosas que tal vez sirven. le doy fotos y me
da el 3D". The owner chose **"only record the idea"**: no research, installs, downloads or code.

| ID | Requirement (owner's words) | Notes / current state | Status |
|----|-----------------------------|------------------------|--------|
| **PHOTO-TO-3D** | "algún tipo de programa para crear meshes … le doy fotos y me da el 3D" | Photos give the **surface only** (no muscles, tendons, fasciae). Any scan the owner makes is provenance **USER_INPUT** (own data, no third-party licence). A mesh generator must start from **measured data** — no invented geometry (Decision 4.2). Today: the addon can fit a real per-bone mesh from `assets/anatomy/meshes/` (empty) | PENDING |
| **WORK-SIGNING** | "crear NTFS Hashes Id con la manifestacion, como ir firmando la obra" | Term **UNCONFIRMED** ("NTFS" = NFT? or other — not answered). Proposed, **non-binding**: content ID = SHA-256 of each mesh / manifest (exports are already byte-reproducible) + provenance record signed with the owner's key (Ed25519), optionally C2PA later; NFT only later and only with explicit owner authorization. No technology is added until the full flow is validated (dossier rule) | PENDING |
| **OWNER-DOCS (context)** | "tengo mucha documentación … estuve documentando muchas cosas que tal vez sirven" | Extensive documentation from the owner's audiovisual-simulation work may be shared. Location **UNKNOWN**; confidentiality status **UNKNOWN** | PENDING |

**Clarification (owner, verbatim, 2026-10-24 20:46 UTC)** — applies to WORK-SIGNING and OWNER-DOCS:
"es porque soy ilustrador y tengo todo el proyecto escrito a mano y se dibujar muy bien. , la verdadera obra de
arte es ese documento fisico. estaria bueno si hago todo, le saco fotos lo publico y lo vendo."
Claude's interpretation, **to be confirmed by the owner**: the hand-written, hand-drawn physical project
document is the primary artwork (and the main owner-authored source, USER_INPUT); the hash ID / signed
manifestation is meant to authenticate the work and tie photographs of the physical document to the digital
outputs (drawing → model → simulation → manifestation); the owner may publish and sell the result. Design
content from the drawings (uniform, poses, characters) is owner design, not measured anatomical data.

Acceptance criteria: **not specified**. Open questions: (1) "NTFS" — NFT or something else? (2) where is the
documentation and what may be used (confidentiality)? (3) photogrammetry on the owner's hardware — not
researched (owner did not request it). (4) What exactly is sold: the physical document, photos/prints, the
digital manifestations, the game/film, or a combination? — **ANSWERED** (owner, verbatim, 2026-10-24 20:59 UTC):
"yo vendo todas, pero esto es un engine gral, cada uno puede sacar diferentes manifestaciones segun el nivel en
simulaciones y Artistico Tecnico en cada Manifestacion Final, cada cosa la vendo por separado, asi que todo o que
es audio visual me conviene crear el programa para dibujar y crear meshes que luego yo los retoco o agrego AI que
me ayuden, algo bien ligero." → every output is sold **separately** (physical notebook, photos/prints, digital
manifestations, game, film). (5) Licensing of third-party sources in anything sold:
share-alike sources (CC BY-SA, e.g. Z-Anatomy, older BodyParts3D) could constrain a commercial product — an
owner decision (not legal advice).

---

## Rows MANIFESTATION-LEVELS / MESH-AUTHORING-TOOL — DRAFT (owner, 2026-10-24 20:59 UTC)

| ID | Requirement (owner's words) | Notes / current state | Status |
|----|-----------------------------|------------------------|--------|
| **MANIFESTATION-LEVELS** | "esto es un engine gral, cada uno puede sacar diferentes manifestaciones segun el nivel en simulaciones y Artistico Tecnico en cada Manifestacion Final, cada cosa la vendo por separado" | Character Engine is a **general engine**; each Final Manifestation is defined by a *simulation level* and an *artistic-technical level*, and is sold separately. Relates to the confirmed L1/L2/L3 layers (Decision 44). Definition of the levels **UNKNOWN** | PENDING |
| **MESH-AUTHORING-TOOL** | "crear el programa para dibujar y crear meshes que luego yo los retoco o agrego AI que me ayuden, algo bien ligero" | Lightweight draw → mesh program; meshes retouched by the owner. Hardware constraint: GT 740M 2 GB, OpenGL 3.3, driver 388.73; Blender 3.6 reference. Implementation form **UNDECIDED** — candidates, listed neutrally: **(A)** a mode inside the existing Blender 3.6 addon (no new technology); **(B)** a standalone lightweight app (new dependencies/technology — needs justification per the dossier). **AI assistance is out of scope** until the owner decides (licence, cost, hardware) | PENDING |

Acceptance criteria: **not specified**. Open questions — MANIFESTATION-LEVELS: how many levels per axis? What
differs between levels (simulation fidelity, mesh resolution, rig detail, render quality, runtime target)? Is the
level part of each manifestation's signed ID? — MESH-AUTHORING-TOOL: form A or B? Input = drawing directly in
the tool, scanned drawings, or both? Which assets first (bodies, clothing, equipment, animals)?

---

## Row PHYSICS-BACKENDS — DRAFT (owner, 2026-10-24 21:04 UTC)

Owner (verbatim): "Que con Blender y Godot podes usar libreias Jolt PBD XPBD FEM Bullet, asi poder simular
colisiones de materiales". Verification evidence: `docs/audit/PHYSICS-BACKENDS-VERIFICATION-2026-10-24.md`
(read-only probes on the baseline PC).

| Item | Verified fact | Unverified |
|------|---------------|------------|
| Godot 4.7.2 | `physics/3d/physics_engine` options `DEFAULT, Jolt Physics, GodotPhysics3D, Dummy`; 33 `physics/jolt_physics_3d/*` settings; `SoftBody3D` exists; no Bullet; `runtime/godot` = `DEFAULT` | what `DEFAULT` maps to for this project; Jolt soft-body support in practice; cross-run determinism of Jolt in this build |
| Blender 3.6.23 | Bullet built in (`build_options.bullet=True`): rigid body world; cloth, soft body, collision, fluid, particles, dynamic paint, geometry-nodes simulation; numpy 1.23.5 (no scipy); **no XPBD or FEM** | determinism of baked simulations across machines; Blender 4.2 (not installed) |
| XPBD / PBD | not present anywhere (would be own code) | — |
| FEM | not built into either tool | — |
| Repository | no physics or mechanical-material code/data | — |

Per-layer candidates — **PROPOSED**, engine choice per layer **PENDING** the owner's decision (engagement open
question 3: where does L2 physics run):

| Layer (Decision 44) | Candidates |
|---------------------|------------|
| L1 deterministic combat | own logic + own capsules (Python domain + GDScript port, as today) |
| L2 physical reaction (recorded) | own XPBD (deterministic by design) · Bullet/cloth/soft body/geometry nodes in Blender (offline, baked) · Jolt or GodotPhysics3D in Godot (real time, determinism unverified) · FEM offline only (new technology) |
| L3 polish + bake | Blender (bake to a canonical file played back by Godot) |

Rules: no new technology before a validated full flow (dossier); mechanical material parameters (density, Young's
modulus, Poisson ratio, damping, fracture thresholds) need cited sources or ESTIMATE/PLACEHOLDER marking
(Decision 12). Acceptance criteria: **not specified**. Status: **PENDING**.

Update 2026-10-24 21:16 UTC (owner, engagement question 3 answered — draft §9): **L2 = offline in Blender**
(owner decision). With this design, runtime physics (Jolt / GodotPhysics3D) is **not needed for L2**; kept in
the table as a note, not removed. The offline tool inside Blender (Bullet, cloth, soft body, particles, geometry
nodes, own XPBD, FEM) is still **PENDING**. Godot 4.7.2 scene importers verified: glTF, `.blend`, FBX; no Alembic.
