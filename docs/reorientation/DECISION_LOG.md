# CHARACTER ENGINE - DECISION LOG

**Document**: DECISION_LOG.md  
**Date**: 2026-09-02  
**Status**: POST-REORIENTATION AUDIT  
**Purpose**: Record all architectural and design decisions made during reorientation

---

## 1. FUNDAMENTAL DECISIONS

### 1.1 Source of Truth Decision

**Decision**: The source of truth is NOT Blender

**Rationale**: Blender is a production tool, not a data management system. The canonical source must be DATA + SCHEMAS + PARAMETERS + RELATIONSHIPS + PROVENANCE.

**Impact**: All architectural decisions must prioritize data management over Blender dependency.

**Date**: 2026-09-02
**Status**: FINAL

---

### 1.2 Architecture Direction Decision

**Decision**: Change from SKELETON-FIRST to MESH-FIRST architecture

**Rationale**: The target production flow requires DATA → ANATOMY → MORPHOLOGY → MESH → SKELETON, not SKELETON → BLENDER.

**Impact**: Requires complete architectural reorientation and new mesh infrastructure.

**Date**: 2026-09-02
**Status**: FINAL

---

### 1.3 Backend Priority Decision

**Decision**: Backend foundation is P0-P1 priority, higher than mesh infrastructure

**Rationale**: Without backend foundation (identity, events, rewards, security, assets), the production workflow (Blender → Backend → UPBGE) cannot function.

**Impact**: Backend foundation must be implemented before or in parallel with mesh infrastructure.

**Date**: 2026-09-02
**Status**: FINAL

---

## 2. DOMAIN LAYER DECISIONS

### 2.1 Anatomical Domain Decision

**Decision**: Keep existing `domain/anatomy/` as canonical anatomical domain

**Rationale**: The anatomical domain is well-implemented with 262 passing tests, frozen dataclasses, and A0.5 provenance enforcement.

**Impact**: No changes to anatomical domain required, only refactoring for provenance integration.

**Date**: 2026-09-02
**Status**: FINAL

---

### 2.2 Coordinate System Decision

**Decision**: Maintain Z-UP, right-handed coordinate system

**Rationale**: Z-UP is the established standard, consistent with Blender and UPBGE.

**Impact**: All new components must use Z-UP coordinate system.

**Date**: 2026-09-02
**Status**: FINAL

---

### 2.3 Provenance System Decision

**Decision**: Use A0.5 provenance system (PROVEN, DERIVED, ESTIMATE, ASSUMED, PLACEHOLDER, UNKNOWN)

**Rationale**: A0.5 implemented strict provenance enforcement with ReconstructionEligibilityValidator, which is critical for preventing placeholder data contamination.

**Impact**: All new components must use A0.5 provenance system. PLACEHOLDER/ASSUMED/UNKNOWN cannot enter canonical reconstruction.

**Date**: 2026-09-02
**Status**: FINAL

---

## 3. BACKEND DECISIONS

### 3.1 Identity Separation Decision

**Decision**: Separate USER, ACCOUNT, IDENTITY, SESSION, DEVICE, API CLIENT as distinct concepts

**Rationale**: Mixing these concepts creates architectural confusion and security vulnerabilities.

**Impact**: Backend must implement separate models with clear relationships.

**Date**: 2026-09-02
**Status**: FINAL

---

### 3.2 Event System Decision

**Decision**: Implement event-driven architecture with server-generated sequence numbers

**Rationale**: Server-generated sequences prevent client manipulation and ensure event ordering.

**Impact**: Event system must include server_sequence, integrity_hash, previous_hash, idempotency_key.

**Date**: 2026-09-02
**Status**: FINAL

---

### 3.3 Reward System Decision

**Decision**: Implement configurable reward system (not hardcoded)

**Rationale**: Hardcoded rewards are inflexible and difficult to maintain. Configurable rewards allow easy modification.

**Impact**: Reward definitions must be data/configuration, not code.

**Date**: 2026-09-02
**Status**: FINAL

---

### 3.4 First Reward Decision

**Decision**: First reward is FIRST_USER ("Eres el Primer Usuario")

**Rationale**: Provides immediate user engagement and validates the reward system.

**Impact**: Reward system must support this specific reward.

**Date**: 2026-09-02
**Status**: FINAL

---

## 4. MESH DECISIONS

### 4.1 Mesh Domain Model Decision

**Decision**: Create first-class HumanMesh domain model, independent from Blender

**Rationale**: Domain must not depend on bpy. Mesh must be a domain concept, not a Blender concept.

**Impact**: Must implement HumanMesh, MeshVertex, MeshEdge, MeshFace, SurfaceRegion, MeshTopology in domain layer.

**Date**: 2026-09-02
**Status**: FINAL

---

### 4.2 Mesh Generation Decision

**Decision**: Do NOT invent anatomical geometry. Build contracts to receive geometry from specialists.

**Rationale**: The Blender team will be responsible for 3D production. Engineering should focus on contracts and infrastructure.

**Impact**: Mesh infrastructure must be designed to receive geometry from Blender team, not generate it.

**Date**: 2026-09-02
**Status**: FINAL

---

## 5. SECURITY DECISIONS

### 5.1 Security Architecture Decision

**Decision**: Implement layered security: INTERNET → TLS → REVERSE PROXY → RATE LIMITING → AUTHENTICATION → AUTHORIZATION → API → SERVICES → DATABASE

**Rationale**: Defense-in-depth strategy provides comprehensive security.

**Impact**: Must implement each security layer with appropriate middleware.

**Date**: 2026-09-02
**Status**: FINAL

---

### 5.2 Error Handling Decision

**Decision**: Never expose stack traces, database errors, API keys, tokens, secrets, filesystem paths, or infrastructure information

**Rationale**: Information disclosure is a security vulnerability.

**Impact**: All error handling must use safe, generic error messages.

**Date**: 2026-09-02
**Status**: FINAL

---

## 6. DATA DECISIONS

### 6.1 Reference Data Decision

**Decision**: Mark all current reference data as PLACEHOLDER, require real data acquisition

**Rationale**: Current reference data is 100% placeholder with ASSUMPTION provenance. This violates A0.5 rules.

**Impact**: Must acquire real reference data (NHANES, WHO_BMI, ISB, FORENSIC) before production.

**Date**: 2026-09-02
**Status**: FINAL

---

### 6.2 Anatomical Data Decision

**Decision**: Keep 206-bone JSON as structurally valid but anatomically incomplete

**Rationale**: The JSON structure is valid but contains anatomical issues (incorrect height, insufficient spine curvature, etc.).

**Impact**: Must acquire real osteometric data to correct anatomical issues.

**Date**: 2026-09-02
**Status**: FINAL

---

## 7. HISTORICAL CHARACTER DECISIONS

### 7.1 Historical Character Approach Decision

**Decision**: Historical/social categories must NOT become rigid biological presets

**Rationale**: A woman must not be "male model + modifier". Must have complete anatomical model.

**Impact**: Must implement separate anatomical models for different demographics.

**Date**: 2026-09-02
**Status**: FINAL

---

### 7.2 Identity Separation Decision

**Decision**: Separate IDENTITY, ANATOMY, MORPHOLOGY, GENEALOGY, HISTORICAL CONTEXT, CULTURAL CONTEXT, CLOTHING, EQUIPMENT, BEHAVIOR

**Rationale**: Mixing these concepts creates architectural confusion and data integrity issues.

**Impact**: Must implement separate models for each concept with clear relationships.

**Date**: 2026-09-02
**Status**: FINAL

---

## 8. CONSOLIDATION DECISIONS

### 8.1 Skeleton Consolidation Decision

**Decision**: Consolidate all skeleton implementations to `domain/anatomy/osteology/`

**Rationale**: Three different skeleton implementations exist (anatomy/, skeleton/, domain/anatomy/osteology/). This creates confusion and maintenance burden.

**Impact**: Deprecate `anatomy/` and `skeleton/` directories, use `domain/anatomy/osteology/` as canonical.

**Date**: 2026-09-02
**Status**: FINAL

---

### 8.2 Parameter Consolidation Decision

**Decision**: Consolidate all parameter systems to `domain/anatomy/parameters/`

**Rationale**: Four different parameter systems exist. Consolidation reduces duplication and maintenance burden.

**Impact**: Deprecate `anatomy/measurements.py`, use `domain/anatomy/parameters/` as canonical.

**Date**: 2026-09-02
**Status**: FINAL

---

## 9. IMPLEMENTATION DECISIONS

### 9.1 Incremental Migration Decision

**Decision**: Migrate incrementally without breaking existing functionality

**Rationale**: Big-bang migration is high-risk. Incremental migration with testing at each step is safer.

**Impact**: Must implement new components alongside existing ones, then gradually migrate.

**Date**: 2026-09-02
**Status**: FINAL

---

### 9.2 Parallel Implementation Decision

**Decision**: Implement backend and mesh infrastructure in parallel where possible

**Rationale**: Backend and mesh infrastructure are largely independent. Parallel implementation reduces timeline.

**Impact**: Phase 1 (backend) and Phase 2 (mesh) can proceed in parallel.

**Date**: 2026-09-02
**Status**: FINAL

---

## 10. VALIDATION DECISIONS

### 10.1 End-to-End Test Decision

**Decision**: First end-to-end test must validate: Create user → Generate USER_REGISTERED → Server assigns sequence=1 → Reward engine detects FIRST_USER → Generate reward grant → Generate audit trail

**Rationale**: This test validates the entire backend foundation workflow.

**Impact**: Must implement this test before considering backend foundation complete.

**Date**: 2026-09-02
**Status**: FINAL

---

## 11. NO-BUNKER DECISION

### 11.1 Separation Decision

**Decision**: CHARACTER ENGINE is independent of BÚNKER. Do not mix architecture, models, databases, events, trading, finance, or risk management.

**Rationale**: Domain mixing creates architectural confusion and maintenance burden.

**Impact**: Must keep CHARACTER ENGINE strictly independent.

**Date**: 2026-09-02
**Status**: FINAL

---

## 12. DATA INVENTION RULE DECISION

### 12.1 Critical Rule Decision

**Decision**: NEVER fill a scientific/anatomical/historical gap with an invented number just to make the system work

**Rationale**: Invented data undermines evidence-grade reconstruction and creates technical debt.

**Impact**: If information is missing, use UNKNOWN, PLACEHOLDER, or REFERENCE_DATA_REQUIRED.

**Date**: 2026-09-02
**Status**: FINAL

---

## 13. SUCCESS CRITERIA DECISION

### 13.1 Success Definition Decision

**Decision**: Work is complete when ARCHITECTURE + DATA + SECURITY + EVENTS + PROVENANCE + ASSETS + VALIDATION + EVIDENCE are coherently connected and demonstrable

**Rationale**: Success is not defined by compilation, tests passing, or file count. Success is defined by architectural coherence and validation.

**Impact**: Must prioritize architectural correctness over feature count.

**Date**: 2026-09-02
**Status**: FINAL

---

## 15. CANONICAL STATURE RETARGET DECISION

### 15.1 Base Stature and Proportion Source

**Decision**: The canonical skeleton `human_adult_206.json` is retargeted from the 3.08 m placeholder
scale to a **base stature of 1.80 m**, using the segment-length / joint-height ratios of
Drillis & Contini (1966) as reproduced in Winter (2009) Fig. 4.1 (`source_id = DRILLIS_CONTINI_1966`).

**Rationale**: 3.08 m was a documented anatomical failure (A02). 1.80 m is a project design parameter
(`USER_INPUT`), not a population statistic. Drillis & Contini is the most widely used published
proportionality set and is self-consistent (shoulder − upper arm = elbow, etc.).

**Method**: `scripts/retarget_stature.py` — three monotonic piecewise-linear Z maps (axial / arm / leg)
through the sourced landmarks; uniform XY scale to the biacromial breadth 0.259H. Topology unchanged.
Report: `docs/audit/A07_STATURE_RETARGET_REPORT.json`. Audit: `docs/audit/A07_STATURE_RETARGET_180.md`.

**Provenance**: ratios PROVEN; landmark heights DERIVED; every interpolated bone position ESTIMATE;
XY scale ESTIMATE. This does **not** violate Decision 12: no number was invented, and non-sourced
positions are labelled ESTIMATE, not upgraded.

**Impact**: `tests/anatomy` fixtures that encode the 3.08 m baseline stay as a *known-bad* regression
fixture. Godot/UPBGE validators check orientation, not stature. Future data (ISB joint centres,
osteometric tables) may refine individual bones without changing this decision.

**Date**: 2026-09-29
**Status**: FINAL (stature value revisable by the project owner; method fixed)

---

## 16. OSTEOMETRY DRIVES MESH EXTENTS, NOT JOINTS

**Decision**: Long-bone lengths from forensic regressions (Trotter 1970 / Trotter & Gleser,
`references/osteometry.json`) size **bone meshes** (proxies or fitted assets) in the Blender addon.
They never move joint centres of `human_adult_206.json`, which stay governed by Decision 15.

**Rationale**: the regressions describe *maximum length on an osteometric board* (with epiphyses),
a different measurement from joint-centre distance; mixing them would silently corrupt the retarget.

**Provenance**: male-white regressions PROVEN (verified in three secondary sources); derived lengths
DERIVED; midshaft diameters ESTIMATE; female white and female Black long-bone regressions PROVEN
(Trotter & Gleser 1952:495, A08 update); child segment ratios PLACEHOLDER; male Black Trotter 1970
not mixed with 1952. Audit: `docs/audit/A08_OSTEOMETRY_TISSUES_TPOSE.md`.

**Date**: 2026-09-29 · **Status**: FINAL

---

## 17. LEFT/RIGHT LABELLING VERSUS −Y FORWARD (OPEN)

**Finding**: with Z-up, right-handed axes and the character facing **−Y**, the anatomical right
is `forward × up = (0,−1,0) × (0,0,1) = (−1,0,0)`, i.e. **−X**. The canonical data places every
`*_R` bone at **+X** (`HUMERUS_R.head.x = +0.2331`) and `domain/anatomy/coordinate_system.py`
documents "+X = right". Either the character actually faces +Y, or the labels are mirrored.
Blender's convention (character faces −Y, `.L` at +X) agrees with the geometric reading; glTF/Godot
preserve the mirror (`(x, z, −y)` keeps X).

**Decision**: **not** silently flipped. Exporters, addon and runtimes keep the current labels; the
rule `.cursor/rules/coordinate-system.mdc` states the discrepancy. Resolution (flip X in data + tests,
or redefine forward as +Y) requires the project owner's call and an A02-style forensic pass, because
it touches every landmark, muscle attachment and hitbox side.

**Impact until resolved**: mirror-symmetric content is unaffected; side-specific gameplay (a
right-hand jab reaching the opponent's left jaw) is consistent *within* the engine but may be
mirrored relative to a photo reference.

**Date**: 2026-09-29 · **Status**: OPEN

---

## 18. TISSUE / WOUND MODEL IS AN ESTIMATE-GRADE GAMEPLAY LAYER

**Decision**: `domain/tissue` and `domain/trauma` (layer thicknesses, AIS-like severity 1–6, regional
lethality caps, `REFERENCE_BLUNT_ENERGY_J = 400`, health costs) are **gameplay/simulation
abstractions** with `provenance = ESTIMATE`. They are not clinical models and must not be upgraded
without a sourced literature pass. Muscle *attachment topology* (origin/insertion bones) is textbook
anatomy; muscle geometry is PLACEHOLDER (spindle proxies).

**Date**: 2026-09-29 · **Status**: FINAL (values revisable with sources)

---

## 19. RUNTIMES CONSUME GENERATED DATA; UPBGE EMBEDS PYTHON

**Decision**: Godot never imports the Python domain. The gameplay table
(`runtime/godot/addons/character_engine/data/gameplay_shenmue.json`) is generated by
`scripts/export_gameplay_data.py` and checked for staleness by pytest; the GDScript combat port must
replay the reference fights identically (verified: 7/7). UPBGE, whose runtime *is* Python, embeds
`character_engine.domain.gameplay` directly through `runtime/upbge/components/ce_combat.py`.

**Known engine limit recorded**: UPBGE 0.50 crashes (`EXCEPTION_ACCESS_VIOLATION`) when registering
Python components or logic bricks in background mode and when starting the embedded game from an app
timer; the UPBGE suite therefore runs in UI mode and uses `blenderplayer.exe` for the game smoke.

**Date**: 2026-09-29 · **Status**: FINAL

---

## 14. SUMMARY

### 14.1 Decision Summary

**Total Decisions**: 19
**Final Decisions**: 18
**Open Decisions**: 1 (Decision 17, left/right labelling vs −Y forward)
**Reversible Decisions**: 2 (base stature value; tissue/wound estimate values)
**Critical Decisions**: 6 (Source of Truth, Architecture Direction, Backend Priority, Provenance System, Mesh Generation, Data Invention Rule)

### 14.2 Decision Impact

**Architecture**: Complete reorientation from skeleton-first to mesh-first
**Backend**: Complete new implementation required
**Mesh**: Complete new implementation required
**Data**: Real reference data acquisition required
**Security**: Complete new implementation required
**Timeline**: 12-16 weeks estimated

### 14.3 Decision Principles

All decisions are based on:
- Production requirements (Blender → Backend → UPBGE workflow)
- Evidence-grade reconstruction (no invented data)
- Architectural correctness (source of truth is data, not Blender)
- Security (defense-in-depth, no information disclosure)
- Maintainability (consolidation, clear separation of concerns)