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

Update 2026-10-24 22:51 UTC — owner clarification of "engagement" (verbatim in the draft §10): "entrecruzamiento o
cruzamiento de combate, aproximaciones … es como reacciona la cinematografía de movimiento según proximidad a enemigo
o NPC … ataques frontales cambia toda la cinematografía ligeramente". Interpretation (to be confirmed): adaptive
movement cinematography — slight, continuous changes of camera/motion parameters driven by proximity, attack
direction and combat state; presets authored in Blender, selected/blended deterministically in Godot (L1). Phase E6
may become the core (flagged, not reordered). Open questions 10–14 in the draft §10.

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

## Row REFERENCE-IMAGES — DRAFT (owner, 2026-10-24 23:08 UTC)

Owner (verbatim): "1ero podriamos hacer pruebas con referencias de imagenes gratis de internet que sean seguras tengo
algunas generadas con AI. en este caso tenemos tambien items y caballo asociado."

| ID | Requirement (owner's words) | Notes | Status |
|----|-----------------------------|-------|--------|
| **REFERENCE-IMAGES** | First tests with free, safe internet images and the owner's AI-generated images (items and horse included) | **Rule PROPOSED for the owner's approval:** AI-generated or free internet images are **REFERENCE ONLY** (blocking, silhouette, approximate proportions, item design). Each one is registered (file, SHA-256, origin, licence or generator terms — for AI: generator/date/prompt if known — and status). They are **never** a source of anatomical or historical facts (those need cited published sources) and are **not** included in a sold product unless the licence is verified. Measurements taken from them are ESTIMATE/ASSUMED. Owner rule (Decision 46): references must bring **no legal and no malware problems** | PENDING |

**First registered reference (outside the repository, not copied):**

| Field | Value |
|-------|-------|
| File | `Generated Image September 03 2026 - 3_31AM 1.png` (sent by the owner in the project thread) |
| SHA-256 | `a71a90987862ab6a664a3b91d8f6b7544b09ea292bb59b30514ac1125935545a` |
| Size | 1408 × 768 px, 2 395 800 bytes |
| Title on the sheet | "Estudio antropológico y del reino animal: el paisano criollo, soldado y gaucho (1810)" |
| Provenance | USER_INPUT + AI_GENERATED (generator, date and prompt not recorded) |
| Content | face; hands with mate; gaucho hat with cockade; Granadero a Caballo levita/casaca with red collar and cuffs; faja; cuchillo verijero / facón; sabre de granadero; botas de potro; espuelas; maneador; lazo; rebenque; montura gaucha; caballo criollo saddled (side view); tero; perro cimarrón |
| Known issues | garbled text (AI artefacts); mismatched labels ("Montura Gaucha" points at a jacket); date 1810 on the sheet (regiment created 1812 — to be cited); hat/uniform combination and colours **UNVERIFIED** |
| Use allowed | blocking, silhouettes, item list, approximate proportions (ESTIMATE) |

**Reference folder (owner, 2026-10-24 23:33 UTC):** `C:\DEV\Assets\Imagenes Para Libertadores, Bocetar y dibujar\`
(outside the repository; read-only for Claude). Inventory — all 1408 × 768 px PNG, provenance USER_INPUT +
AI_GENERATED (generator/prompt not recorded), historical details **UNVERIFIED**, garbled text in places:

| File | Bytes | SHA-256 | Content (as drawn) |
|------|-------|---------|--------------------|
| `Generated Image September 03, 2026 - 3_31AM (1).png` | 2 395 800 | `a71a9098…935545a` | the sheet above (paisano criollo, soldado y gaucho; caballo criollo, tero, perro) |
| `Generated Image September 03, 2026 - 3_31AM (2).png` | 2 572 419 | `84b76a71…1cd37` | mujer criolla — paisana, granadera, gaucha; items (mate, lazo, rebenque, sable, carabina), caballo criollo, perro, tero, vizcacha |
| `Generated Image September 03, 2026 - 3_31AM (3).png` | 2 439 894 | `47588811…eb6a6b` | San Martín — equipment and campaign fauna (uniform, epaulettes, sable corvo, bicornio, montura, pistolas de arzón, catalejo, mule, condor, guanaco) |
| `Generated Image September 03, 2026 - 3_31AM.png` | 2 571 228 | `ba27a743…341b` | Ejército Libertador — ethnic groups and fauna (several figures, llama, vicuña, mule, condor) |
| `Generated Image September 03, 2026 - 3_44AM.png` | 2 516 448 | `5b711365…913b` | San Martín — tailoring (levita, bicornio, chaleco, faja, camisa/corbatín, boots) |
| `Generated Image September 03, 2026 - 5_19AM.png` | 2 463 579 | `bcea5ef7…7e04` | levita de Granadero a Caballo — **back, front and side views**, collar, cuff, epaulette, grenade button, lining |

Full hashes: run `Get-FileHash -Algorithm SHA256` on the folder (values above truncated for readability).

---

## Rows STORYBOARD-TO-SHOT / LOCOMOTION-STANDALONE — DRAFT (owner, 2026-10-24 23:33 UTC)

Owner (verbatim): "C:\DEV\Assets lo guarde ahi, claro mi trabajo es dejar todo lo mejor posible, siguiendo el guion de
la historia las tomas que quiero privilegiar contando la historias. toda la experiencia cinematografica del guion sale de
mis bocetos, despues buscamos un modelo de boceto que te quede bien para anotar movimientos de camara y detalles de la
escena para intentar recrearlas, elegir escenario con todos sus elementos, ese es nuestro ejemplo, que nuestro
character no solo pelee sino que camine bien que tenga buenos momentos de standalone."

| ID | Requirement (owner's words) | Notes | Status |
|----|-----------------------------|-------|--------|
| **STORYBOARD-TO-SHOT** | "toda la experiencia cinematografica del guion sale de mis bocetos … un modelo de boceto … para anotar movimientos de camara y detalles de la escena para intentar recrearlas, elegir escenario con todos sus elementos" | The script (guion) and the shots the owner wants to privilege drive the cinematography; each sketch is annotated so the shot can be recreated in Blender. Shot-list and set schemas below are **PROPOSED** | PENDING |
| **LOCOMOTION-STANDALONE** | "que nuestro character no solo pelee sino que camine bien que tenga buenos momentos de standalone" | Today: rig with IK legs and foot roll, mocap retarget; no walk cycle, no idle/standalone animations. Realistic walking speeds need cited sources (REALISM-UNITS) | PENDING |

**Shot-list schema — PROPOSED (one record per sketch/shot):**

| Field | Meaning |
|-------|---------|
| `shot_id` | e.g. `SC01-SH03` (scene, shot) |
| `sketch_file` | path + SHA-256 of the owner's sketch (scan/photo) |
| `scene` / `location` | scene name and escenario id |
| `shot_size` | framing: extreme wide / wide / full / medium / close-up / detail |
| `camera_move` | static / pan / tilt / dolly / truck / crane / handheld / follow, with direction |
| `duration_s` | planned duration |
| `subject_action` | who does what (characters, animals, items) |
| `lens_mm` / `fov_deg` | ESTIMATE from the sketch |
| `engagement` | proximity / direction cues if it is a fight (draft engagement §10) |
| `notes` | lighting, mood, sound, transitions |
| `provenance` | USER_INPUT (owner sketch); any AI or internet reference listed with its register entry |

**Set / escenario element list — PROPOSED:** `set_id`, `location`, `period`, `terrain` (size m, slope), `structures`
(e.g. rancho, tents), `props` (with sockets/assets), `animals`, `extras` (count, roles), `lighting`/`time_of_day`,
`weather`, `references` (register entries), `provenance`.

Open questions: (1) is the written guion available, and where? (2) which scene is the pilot? (3) sketch format —
paper scans, tablet drawings, storyboard panels? (4) what exactly are the "standalone moments" (idle, walking, mounting,
drinking mate…)? (5) what must the walk satisfy (speeds, gait, terrain) — realistic values need cited sources.

---

## Rows MUSIC-DRIVEN-SHOTS / MUSIC-PRODUCTION — DRAFT (owner, 2026-10-25 00:13–00:29 UTC)

Owner (verbatim, 00:13): "no son la base de la serie, las escenas y momentos todos los que mencionaste. quiero hacer
tomas, con chamame y folklore en 3 tiempos y luego mezclar las lineas, usando un mix de folcklores mios y famosos de
argentina de mercedez sosa charly gracia." (00:29): "los temas los puedo tocar yo y grabar, mas los mios y tambien ya
pensar en un super estilo lo mas folcklorico rokero de argentina, los maestros, tambien puedo tocar Chamameces , todo
con syntesmezclados con techno y trance."
(Clarifies the pilot: the base is the scenes and moments listed in `PILOT-SAN-LORENZO.md`, not the video lesson notes.)

| ID | Requirement (owner's words) | Notes | Status |
|----|-----------------------------|-------|--------|
| **MUSIC-DRIVEN-SHOTS** | "tomas, con chamame y folklore en 3 tiempos y luego mezclar las lineas" | Shots cut to the music; famous Argentine folklore (Mercedes Sosa, Charly García) as **style inspiration**. Per-shot music fields added to `PILOT-SAN-LORENZO-SHOTLIST.md` (cue, work owner, BPM, metre 3/4 or 6/8, start/end bar, cut beat, musical line). Mixing 3/4–6/8 folklore with 4/4 techno/trance implies tempo/metre changes per section | PENDING |
| **MUSIC-PRODUCTION** | "los temas los puedo tocar yo y grabar, mas los mios … super estilo lo mas folcklorico rokero de argentina … Chamameces, todo con syntes mezclados con techno y trance" | Owner performs and records; own songs plus covers; style: Argentine folk-rock + chamamé + synths, techno, trance. Music in products follows **Decision 47** | PENDING |

**Author profile (owner, 2026-10-25):** audiovisual programmer, visual artist, musician, composer and producer
— **2.5exp ("2.5 experience") is the owner's personal production company** (owner, 2026-10-25: "2.5exp es mi productora personal").

---

## Row PILOT-SAN-LORENZO — DRAFT (owner, 2026-10-24 23:41–23:44 UTC)

Owner: "voy a tomar este video para el guion y ya lo tenemos" (https://www.youtube.com/watch?v=j6slbLEUA3c,
"San Martín y la Batalla de San Lorenzo", EducaciónSantaFe) and "El piloto es una mezcla de momeno de entrenamiento,
con previos a la batalla con cotidianos de la epoca y entrenamiento y de la batalla". Draft structure (acts A–F,
facts to verify, empty shot list, sets): `docs/product/PILOT-SAN-LORENZO.md`. **Piloto D1:** mezcla de entrenamiento, previos a la batalla con cotidianos de la época, y la batalla de San Lorenzo (3-feb-1813, fecha a citar). Shot list template with blocks A) cotidiano, B) entrenamiento, C) batalla, the narrative timeline (SIN VERIFICAR) and the pilot's engine needs (march, mounting, weapon drill, standalone): `docs/product/PILOT-SAN-LORENZO-SHOTLIST.md`. The video is a **research reference**
(standard licence assumed, not verified); the script and sketches are the owner's. Status: **PENDING**.

---

## Row DELIVERABLE-1 — Granaderos fight (first deliverable) — DRAFT

Owner choice 2026-10-24: "Pelea de Granaderos" is the **first deliverable**. Full draft (goal, inventory,
PROPOSED steps D1-0…D1-8, owner decisions): `docs/product/DELIVERABLE-1-GRANADEROS-FIGHT.md`.

| Column | State | Status |
|--------|-------|--------|
| **REUSABLE** | combat L1 (Python + GDScript), wounds, sockets + placeholder sabre, Workbench preset, solver benchmark, Godot arena, mocap retarget | IMPLEMENTED |
| **BLOCKED BY** | uniform source; base-mesh decision; sabre source; realistic reach/speed sources; engagement Q10–Q14; first experiment (Q9); baked format; material parameters; armed-move spec | PENDING |
| **ACCEPTANCE** | per step, PROPOSED only (draft §3) | PENDING |

---

## Rows BLOCK-DUMMY / MESH-NORMALIZER — owner request 2026-10-25 01:17–01:21 UTC

Owner (verbatim): "1ro me gustaria ver un muñeco mesh compuesto por bloques centrales que van a simular de musculos o
podemos hacerlos para las coliciones … poder normalizar el tamaño la escala de todo en el mesh." and "no tengo ninguna
malla, me gustaria que las hagas o que las bajes".

| ID | Implementation | Test / evidence | Status |
|----|----------------|-----------------|--------|
| **BLOCK-DUMMY** (P1) | `domain/rigging/block_dummy.py` (17 segments: head, neck, thorax, abdomen, pelvis, upper arm, forearm, hand, thigh, leg, foot ×2; capsule between averaged joints; radius = per-region envelope radius, ESTIMATE, scaled with stature — single source shared with the skin envelope) + addon `build_block_dummy`, operator *Block dummy (blocks + collision)*: one skinned mesh, every vertex 100 % on one bone, plus 17 collision capsules parented to their bones (COLLISION modifier) | `tests/unit/test_block_dummy.py` (7); Blender 3.6 headless: 1 666 vertices 100 % weighted, HUMERUS_L 60° → capsule 0.159 m / block 0.158 m; render `builds/renders/blender_block_dummy.png` | IMPLEMENTED |
| **MESH-NORMALIZER** (P2) | `domain/assets/normalize.py` (declared source up/forward → canonical Z-up / −Y forward, proper rotation, scale to target height, feet on z = 0, centred in X/Y; ESTIMATE) + addon `normalize_mesh`, operator *Normalize mesh scale* | `tests/unit/test_normalize.py` (10); Blender 3.6 headless: Y-up 180-unit box → z [0, 1.750] m, centred | IMPLEMENTED |

**First approved download (owner approval 2026-10-25, Decision 46 procedure):**

| Field | Value |
|-------|-------|
| File | `Farm Animals Animated by Quaternius.zip` — 6 963 285 bytes (page: 6.6 MB) |
| Origin | https://quaternius.itch.io/lowpoly-animated-animals (itch.io free download; file served from itch.io's own storage mirror) |
| Licence (read on the page) | "Creative Commons Zero v1.0 Universal" (CC0) |
| SHA-256 | `b4bc5f209368cafc21962934e7d676cf1cfb1f746a363086cd9f45c4385db70e` |
| Stored | `C:\DEV\Assets\descargas\quaternius_farm_animals\` (outside the repository) |
| Windows Defender | zip and extracted folder: **no threats found** |
| Extracted | only FBX / OBJ / MTL / GIF (22 files); the 7 third-party `.blend` files were **not** extracted or opened; no executables in the archive |
| Content (Blender 3.6 FBX import) | Cow, **Horse**, Zebra (39 bones; Idle, Walk, WalkSlow, Run, Jump, Death) · Llama, Pig, Pug, Sheep (35 bones; Idle, Jump); 283–679 vertices each (low-poly) |
| Test | Horse scaled to 1.60 m total height (**PLACEHOLDER**, same value as the `horse_adult` template), Walk and Run rendered in Workbench next to a 1.80 m reference: `builds/renders/quaternius_horse_walk.png`, `…_run.png` |
| Finding | the FBX actions also animate the armature **object** (location, rotation, scale), so a rigged import must be scaled through a parent (empty); `normalize_mesh` only handles plain meshes — a rig-aware variant is pending |
| Use allowed | tests, blocking, animation reference; **not** anatomy (low-poly, no source); status ACQUIRED (test asset) |

Observations: the trunk segments are shorter than their diameter on the canonical spine, so thorax/abdomen/pelvis
are spheres; the feet are tiny spheres because the canonical foot bones lie almost vertical near the ground (known
open item on foot layout). No rigid-body set-up yet (collision capsules work for cloth, soft body and particles).

---

## Rows REALISM-UNITS / PRODUCT-VISION-GRANADEROS — DRAFT (owner, 2026-10-24 22:57 UTC)

Owner (verbatim): "quiero que todo ocurra a distancias y con velocidades y movimientos realistas, tengo que realizar
granaderos en cosas cotidianas, a caballo, realizar las tomas ponerlos a luchar, pense en hacer un juego de los padres
de la patria san martin y todos los demas tipo AOE2DE."

| ID | Requirement (owner's words) | Notes / current state | Status |
|----|-----------------------------|------------------------|--------|
| **REALISM-UNITS** | "que todo ocurra a distancias y con velocidades y movimientos realistas" | Canonical units are already metric (metres, Z-up). Every speed / gait / reach value — human walk/run, horse gaits (walk, trot, canter, gallop), cavalry charge distances, weapon reach — needs a **cited source** or an ESTIMATE mark, never invented; sources **NOT_ACQUIRED**. Today the combat reach/energy values are gameplay constants without source | PENDING (DATA REQUIRED) |
| **PRODUCT-VISION-GRANADEROS** | "granaderos en cosas cotidianas, a caballo, realizar las tomas ponerlos a luchar, … un juego de los padres de la patria san martin y todos los demas tipo AOE2DE" | Recorded as the owner's **vision/idea**, not a committed requirement. Ties to open items: Granaderos uniform needs a cited historical source (CINE-GR-001); `horse_adult` template has **NO DATA**; animal skeletons pending (ANATOMY-MESH). Neutral note: an RTS (Age of Empires II DE style) differs from the current Shenmue-style fight engagement — many units, top-down camera, different performance demands on the GT 740M; the engine is general and each manifestation is sold separately (MANIFESTATION-LEVELS). No priority is reordered | PENDING |

Acceptance criteria: **not specified**. Open questions: (1) first deliverable — everyday-life cinematic, horseback
cinematic, fight shots or an RTS prototype? (2) Is the RTS a later manifestation or the flagship? (3) Historical
scope — period, figures, units? (4) Expected unit counts and camera for the RTS? (5) Where do historical references
come from — the owner's drawings/documentation, published sources, or both?

---

## Rows WORKBENCH-LAYOUT / MATERIAL-SWATCHES — DRAFT (owner, 2026-10-24 21:49 UTC)

Owner (verbatim): "estaria bueno poder maquetar muy bien bocetar, pulir bien en worckbrech. y ademas si puedo tener
pequeñas muestar de los materiales que van en cada caso."

| ID | Requirement (owner's words) | Notes / current state | Status |
|----|-----------------------------|------------------------|--------|
| **WORKBENCH-LAYOUT** | "maquetar muy bien bocetar, pulir bien en worckbrech" | Layout/mock-up, sketching and polishing in Blender **Workbench** (no shaders/textures, per the original scope), with collisions visible. Today: full-body Workbench preset (CINE-GR-001 step 1) and Experiment 0 key frames (collisions visible, `docs/audit/EXPERIMENT-0-RESULTS-2026-10-24.md`) | PARTIAL |
| **MATERIAL-SWATCHES** | "pequeñas muestras de los materiales que van en cada caso" | Claude's interpretation, **to be confirmed**: a swatch = a small standard object (sphere/cube) per material shown in Workbench using viewport display colour / MatCap / cavity only, plus a data card with the material's mechanical parameters (density, Young's modulus, …), each with a cited source or ESTIMATE, tied to the measurement-systems library (Decision 45 clarification). Today: no material data in the repository | PENDING |

Acceptance criteria: **not specified**. Open questions: which materials first (bone, muscle, skin, cloth, wood,
metal, glass…)? Are swatches separate renders or part of each experiment's output? What must a polished Workbench
layout contain?

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
Confirmed by the owner as **Decision 45** (2026-10-24 21:19 UTC).
Clarification (owner, verbatim, 21:27 UTC): "En realidad Creo que son Bibliotecas de sistemas de medidas y de experimentos que nos da esa exprecion representativa, quiebres, movimientos de acuerdo a la gravedad, el viento, etc." — Claude's interpretation (to be confirmed): libraries of measurement systems and reproducible experiments (gravity, wind, impact, drop, breaking) feed the baked reactions; each with SHA-256 ID and provenance; material parameters cited or ESTIMATE. Open questions 6–9 in the engagement draft §9.1.
