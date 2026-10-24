# CE-MASTER-REQUIREMENTS-MATRIX

**Owner:** Mariano Martin Galli · **Started:** 2026-10-24 · **Status:** DRAFT (row 1 of N)
**Source of the method:** "Product Defined Complete — Cinematografías" (T13–T14) and "Tareas para el
Despliegue" (CINE-SM/GR/H, P1–P15). Chain: PRODUCT → CINEMATOGRAPHY → REQUIREMENT → MANIFOLD →
DOMAIN MODEL → IMPLEMENTATION → TEST → EVIDENCE (Toyota: CTQ, quality gate, jidoka, poka-yoke, kaizen).

**Cell status:** `IMPLEMENTED` = code exists *and* a test proves it · `PARTIAL` = some of it exists ·
`SPECIFIED` = written requirement, no code · `PENDING` = needs a decision or source first ·
`DATA REQUIRED` = cannot be done without a cited source (Decision 12).

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
| **CAMERA** | Full-body, eye level ≈ 1.5 m, ~35–50 mm equivalent, whole figure + base in frame; Workbench render | No camera/scene template for production (only the UPBGE arena camera in `runtime_upbge.py`) | SPECIFIED |
| **ANATOMICAL RESOLUTION** | Full body readable at distance: proportions, posture, limb segmentation; no face/hand close-up required | Canonical skeleton with sourced joint heights; hands A10 and forearm A11 fixed (intra-hand proportions PLACEHOLDER) | PARTIAL |
| **SKELETAL REQUIREMENTS** | 206/208 contract, correct sides, joints at sourced heights, rest pose clean | Implemented and tested (pytest 747; addon headless 20/20 Blender 3.6; Godot 21/21) | IMPLEMENTED |
| **MUSCLE REQUIREMENTS** | Silhouette-level volumes under the uniform (no deformation visible) | 50 bilateral spindle proxies, attachment topology PROVEN, geometry PLACEHOLDER (`domain/tissue/muscles.py`, addon *Tissues*) | PARTIAL |
| **SOFT-TISSUE REQUIREMENTS** | Fat/skin envelope giving a believable body volume under clothing | Skin = skin-modifier envelope from per-region radii (ESTIMATE), proxy only | PARTIAL |
| **MESH REQUIREMENTS** | **Parametric base body mesh** (male), clean topology, weighted to the 208-bone armature, stature-driven | **Does not exist** (no `HumanMesh` domain model; Decision 1.2 "mesh-first" never implemented) | PENDING |
| **DEFORMATION REQUIREMENTS** | None visible in static rest (bind pose only); weights must not tear at shoulders/hips in the rest pose | Proxies 100 % weighted per bone; no skinning of a real mesh | PENDING (depends on mesh) |
| **PHYSICS** | None for a static shot | — | N/A |
| **COLLISION** | Boots on ground plane (z = 0), sabre and scabbard not intersecting the body | Ground check exists for the skeleton (Godot/UPBGE validators); no body/equipment collision | PARTIAL |
| **CLOTHING** | Uniforme de Granaderos: casaca, pantalón, correajes, morrión/kepí — modelled as separate assets bound to the body | **No clothing system / assets**; historical design needs a cited source | DATA REQUIRED |
| **EQUIPMENT** | **Sable** (with scabbard) attached to a **socket** (hip/hand), boots (botas de montar), belts | **No equipment model, no sockets** in rig or domain | PENDING |
| **ENVIRONMENT** | Neutral studio: ground plane + 3-point light; historical environment out of scope for row 1 | — | SPECIFIED |
| **RUNTIME** | Production only (Blender authoring/render); optional glTF export for Godot preview | Canonical GLB export (byte-reproducible) + scene GLB from the addon | PARTIAL |
| **PERFORMANCE** | Workbench render ≤ 30 s at 1920×1080 on the baseline PC; viewport ≥ 15 fps with the character | Not measured | PENDING |
| **MANIFOLD** | M01 Anatomical, M02 Morphological, M03 Skeletal, M07 Surface, M09 Identity, M10 Historical, M11 Clothing, M12 Equipment, M20 Cinematic | M03 implemented; M01 partial; others not started | PARTIAL |
| **DEPENDENCIES** | Base mesh (M07) → skinning → clothing (M11) & equipment sockets (M12) → military pose → camera/scene template | — | SPECIFIED |
| **TEST** | Headless Blender 3.6 test that builds the scene and asserts: 208 bones, mesh bound, boots at z≈0, sabre parented to socket, no body–equipment intersection, camera framing contains the whole figure, render produced | Skeleton-level tests exist; scene-level test does not | PENDING |
| **ACCEPTANCE CRITERIA** | All TEST checks pass; render image reviewed and accepted by the owner (Jidoka: any failed check stops the row) | — | SPECIFIED |
| **EVIDENCE** | Rendered PNG + JSON report in `builds/` (ignored) and a versioned summary in `docs/audit/` | — | PENDING |
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

### Proposed next minimal task — "CINE-GR-001 / step 1: scene template + equipment socket"

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
