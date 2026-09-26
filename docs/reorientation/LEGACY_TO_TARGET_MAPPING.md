# CHARACTER ENGINE - LEGACY TO TARGET MAPPING

**Document**: LEGACY_TO_TARGET_MAPPING.md  
**Date**: 2026-09-02  
**Status**: POST-REORIENTATION AUDIT  
**Purpose**: Map legacy architecture to target architecture

---

## 1. ARCHITECTURE MAPPING

### 1.1 Production Flow Mapping

#### Legacy Architecture
```
REFERENCE DATA
    ↓
ANTHROPOMETRIC MODEL
    ↓
ANATOMICAL LANDMARK MODEL
    ↓
SKELETAL FITTING
    ↓
206-BONE ANATOMICAL SKELETON
    ↓
[NO MESH]
    ↓
[NO DEFORMATION RIG]
    ↓
[NO MUSCLE SYSTEM]
```

#### Target Architecture
```
DATA
    ↓
ANATOMY
    ↓
MORPHOLOGY
    ↓
MESH
    ↓
TISSUES
    ↓
MUSCULOSKELETAL
    ↓
DEFORMATION
    ↓
RIG
    ↓
PHYSICS
    ↓
BEHAVIOR
    ↓
HISTORICAL / IDENTITY
    ↓
CLOTHING
    ↓
EQUIPMENT
    ↓
RUNTIME
    ↓
CINEMATIC
```

#### Mapping Strategy
- **KEEP**: Data → Anatomy (existing)
- **ADD**: Morphology → Mesh → Tissues → Musculoskeletal → Deformation → Rig → Physics → Behavior
- **ADD PARALLEL**: User → Events → Rewards → Security → Assets → Provenance → Validation → Evidence

---

## 2. COMPONENT MAPPING

### 2.1 Skeleton Mapping

#### Legacy
- Location: Multiple directories (anatomy/, skeleton/, domain/anatomy/osteology/)
- Status: Duplicated across 3 locations
- Function: 206-bone skeleton reconstruction

#### Target
- Location: `domain/anatomy/osteology/` (canonical)
- Status: PRODUCTION-READY
- Function: 206-bone skeleton reconstruction
- Integration: Mesh → Skeleton fitting (NEW)

#### Migration Action
- **CONSOLIDATE**: Keep `domain/anatomy/osteology/` as canonical
- **DEPRECATE**: `anatomy/` and `skeleton/` directories
- **ADD**: Mesh → Skeleton relationship module

---

## 3. PARAMETER SYSTEM MAPPING

### 3.1 Parameter Mapping

#### Legacy
- Location: Multiple directories (anatomy/measurements.py, anatomy/proportions.py, domain/anatomy/parameters/, domain/anatomy/proportions/)
- Status: Duplicated across 4 locations
- Function: Anatomical parameter management

#### Target
- Location: `domain/anatomy/parameters/` (canonical)
- Location: `domain/anatomy/proportions/` (canonical)
- Status: PRODUCTION-READY
- Function: Anatomical parameter management
- Integration: Parametric body model (NEW)

#### Migration Action
- **CONSOLIDATE**: Keep `domain/anatomy/parameters/` and `domain/anatomy/proportions/` as canonical
- **DEPRECATE**: `anatomy/measurements.py` and `anatomy/proportions.py`
- **ADD**: Parametric body model with dependency graph

---

## 4. REFERENCE DATA MAPPING

### 4.1 Reference Data Mapping

#### Legacy
- Location: `domain/anatomy/reference/`
- Status: PRODUCTION-READY (A0.5 implemented)
- Function: Reference data management with provenance enforcement
- Data Status: 100% placeholder, all sources NOT_ACQUIRED

#### Target
- Location: `domain/anatomy/reference/` (canonical)
- Status: PRODUCTION-READY
- Function: Reference data management with provenance enforcement
- Data Status: NEEDS REAL DATA

#### Migration Action
- **KEEP**: `domain/anatomy/reference/` architecture
- **POPULATE**: Acquire real reference data (NHANES, WHO_BMI, ISB, FORENSIC)
- **INTEGRATE**: Apply A0.5 provenance enforcement to reconstruction pipeline

---

## 5. MESH INFRASTRUCTURE MAPPING

### 5.1 Mesh Mapping

#### Legacy
- Location: `types/mesh.py` (0 bytes)
- Status: MISSING
- Function: None

#### Target
- Location: `domain/mesh/` (NEW)
- Status: DESIGNED, NOT IMPLEMENTED
- Function: HumanMesh domain model, mesh generation, mesh validation
- Components: HumanMesh, MeshVertex, MeshEdge, MeshFace, SurfaceRegion, MeshTopology

#### Migration Action
- **CREATE**: New `domain/mesh/` directory
- **IMPLEMENT**: HumanMesh domain model
- **IMPLEMENT**: Mesh generation pipeline
- **IMPLEMENT**: Mesh validation system
- **IMPLEMENT**: Mesh → Skeleton relationship

---

## 6. BACKEND INFRASTRUCTURE MAPPING

### 6.1 Backend Mapping

#### Legacy
- Location: DOES NOT EXIST
- Status: MISSING
- Function: None

#### Target
- Location: `backend/` (NEW)
- Status: DESIGNED, NOT IMPLEMENTED
- Function: User/Identity, Events, Rewards, Security, Assets, API, Database
- Components: User, Account, Identity, Session, Event, Reward, Security, Asset, API, Database

#### Migration Action
- **CREATE**: New `backend/` directory
- **IMPLEMENT**: User/Identity system
- **IMPLEMENT**: Event system
- **IMPLEMENT**: Reward system
- **IMPLEMENT**: Security infrastructure
- **IMPLEMENT**: Asset registry
- **IMPLEMENT**: API layer
- **IMPLEMENT**: Database models

---

## 7. EVENT SYSTEM MAPPING

### 7.1 Event Mapping

#### Legacy
- Location: `core/events.py` (0 bytes)
- Status: MISSING
- Function: None

#### Target
- Location: `backend/events/` (NEW)
- Status: DESIGNED, NOT IMPLEMENTED
- Function: Event model, event ingestion, server sequence, integrity verification, idempotency
- First Event: USER_REGISTERED

#### Migration Action
- **REPLACE**: `core/events.py` with backend event system
- **IMPLEMENT**: Event model with server sequence
- **IMPLEMENT**: Event ingestion pipeline
- **IMPLEMENT**: Integrity verification
- **IMPLEMENT**: Idempotency enforcement

---

## 8. IDENTITY SYSTEM MAPPING

### 8.1 Identity Mapping

#### Legacy
- Location: DOES NOT EXIST
- Status: MISSING
- Function: None

#### Target
- Location: `backend/identity/` (NEW)
- Status: DESIGNED, NOT IMPLEMENTED
- Function: User, Account, Identity, Session, Device, API Client
- Separation: Clear separation between concepts

#### Migration Action
- **CREATE**: New `backend/identity/` directory
- **IMPLEMENT**: User model
- **IMPLEMENT**: Account model
- **IMPLEMENT**: Identity model
- **IMPLEMENT**: Session model
- **IMPLEMENT**: Relationship definitions

---

## 9. REWARD SYSTEM MAPPING

### 9.1 Reward Mapping

#### Legacy
- Location: DOES NOT EXIST
- Status: MISSING
- Function: None

#### Target
- Location: `backend/rewards/` (NEW)
- Status: DESIGNED, NOT IMPLEMENTED
- Function: Reward definitions, eligibility engine, reward ledger
- First Reward: FIRST_USER

#### Migration Action
- **CREATE**: New `backend/rewards/` directory
- **IMPLEMENT**: Reward definitions (configurable, not hardcoded)
- **IMPLEMENT**: Eligibility engine
- **IMPLEMENT**: Reward ledger
- **IMPLEMENT**: Grant tracking

---

## 10. SECURITY MAPPING

### 10.1 Security Mapping

#### Legacy
- Location: DOES NOT EXIST
- Status: MISSING
- Function: None

#### Target
- Location: `backend/security/` (NEW)
- Status: DESIGNED, NOT IMPLEMENTED
- Function: Authentication, authorization, rate limiting, input validation, audit logging

#### Migration Action
- **CREATE**: New `backend/security/` directory
- **IMPLEMENT**: Authentication middleware
- **IMPLEMENT**: Authorization middleware
- **IMPLEMENT**: Rate limiting
- **IMPLEMENT**: Input validation
- **IMPLEMENT**: Audit logging

---

## 11. ASSET REGISTRY MAPPING

### 11.1 Asset Registry Mapping

#### Legacy
- Location: DOES NOT EXIST
- Status: MISSING
- Function: None

#### Target
- Location: `backend/assets/` (NEW)
- Status: DESIGNED, NOT IMPLEMENTED
- Function: Asset registration, version tracking, provenance tracking, evidence tracking

#### Migration Action
- **CREATE**: New `backend/assets/` directory
- **IMPLEMENT**: Asset registration
- **IMPLEMENT**: Version tracking
- **IMPLEMENT**: Provenance tracking
- **IMPLEMENT**: Evidence tracking

---

## 12. BLENDER INTEGRATION MAPPING

### 12.1 Blender Integration Mapping

#### Legacy
- Location: `infrastructure/blender/`
- Status: PARTIAL (skeleton import only)
- Function: Skeleton import, state validation

#### Target
- Location: `infrastructure/blender/` (canonical)
- Status: KEEP + EXTEND
- Function: Skeleton import, mesh import/export, state validation, material integration

#### Migration Action
- **KEEP**: Existing skeleton import
- **ADD**: Mesh import
- **ADD**: Mesh export
- **ADD**: Material system integration
- **IMPLEMENT**: Blender scene components (currently empty)

---

## 13. VALIDATION MAPPING

### 13.1 Validation Mapping

#### Legacy
- Location: `domain/anatomy/validation/`
- Status: PRODUCTION-READY
- Function: Anatomical validation (13 test families)

#### Target
- Location: `domain/anatomy/validation/` (canonical)
- Location: `backend/validation/` (NEW)
- Status: KEEP + EXTEND
- Function: Anatomical validation + mesh validation + backend validation

#### Migration Action
- **KEEP**: Existing anatomical validation
- **ADD**: Mesh validation system
- **ADD**: Backend validation system
- **ADD**: Asset package validation

---

## 14. EXPORT/IMPORT MAPPING

### 14.1 Export/Import Mapping

#### Legacy
- Location: `export/` (all files 0 bytes)
- Status: MISSING
- Function: None

#### Target
- Location: `backend/export/` (NEW)
- Status: DESIGNED, NOT IMPLEMENTED
- Function: Asset package export/import, format conversion (BLEND, FBX, GLTF, USD)

#### Migration Action
- **MOVE**: `export/` to `backend/export/`
- **IMPLEMENT**: Asset package system
- **IMPLEMENT**: Export pipelines
- **IMPLEMENT**: Import validation
- **IMPLEMENT**: Package verification

---

## 15. SCHEMA MAPPING

### 15.1 Schema Mapping

#### Legacy
- Location: `schema/skeleton_v1.schema.json`
- Status: PRODUCTION-READY
- Function: Skeleton schema

#### Target
- Location: `backend/schemas/` (NEW)
- Status: DESIGNED, NOT IMPLEMENTED
- Function: Asset package schema, event schema, user schema, reward schema

#### Migration Action
- **MOVE**: `schema/` to `backend/schemas/`
- **KEEP**: Existing skeleton schema
- **ADD**: Asset package schema
- **ADD**: Event schema
- **ADD**: User schema
- **ADD**: Reward schema

---

## 16. MIGRATION PRIORITY

### 16.1 Phase 1: Backend Foundation (P0-P1)

1. **CREATE** `backend/` directory structure
2. **IMPLEMENT** User/Identity system
3. **IMPLEMENT** Event system
4. **IMPLEMENT** Reward system
5. **IMPLEMENT** Security infrastructure
6. **IMPLEMENT** Asset registry
7. **IMPLEMENT** API layer
8. **IMPLEMENT** Database models

### 16.2 Phase 2: Mesh Infrastructure (P2)

1. **CREATE** `domain/mesh/` directory
2. **IMPLEMENT** HumanMesh domain model
3. **IMPLEMENT** Mesh generation pipeline
4. **IMPLEMENT** Mesh validation system
5. **IMPLEMENT** Mesh → Skeleton relationship

### 16.3 Phase 3: Consolidation (P3)

1. **DEPRECATE** `anatomy/` directory
2. **DEPRECATE** `skeleton/` directory
3. **CONSOLIDATE** skeleton to `domain/anatomy/osteology/`
4. **CONSOLIDATE** parameters to `domain/anatomy/parameters/`
5. **CONSOLIDATE** proportions to `domain/anatomy/proportions/`

### 16.4 Phase 4: Integration (P4)

1. **REFACTOR** reconstruction pipeline for A0.5 provenance
2. **INTEGRATE** mesh with skeleton
3. **IMPLEMENT** export/import infrastructure
4. **IMPLEMENT** Blender scene components

---

## 17. SUMMARY

### 17.1 Mapping Summary

**KEEP (No Change)**: 27 components
**ADD (New Components)**: 35 components
**MOVE (Relocate)**: 3 components
**REPLACE (Reimplement)**: 14 components
**DEPRECATE (Mark as Deprecated)**: 8 components
**DELETE (Remove)**: 0 components

### 17.2 Critical Paths

**Backend Foundation**: NEW (critical for production)
**Mesh Infrastructure**: NEW (critical for mesh-first architecture)
**Consolidation**: Remove duplication (technical debt)
**Integration**: Connect legacy to target architecture

### 17.3 Risk Assessment

**LOW RISK**: Keep existing anatomical domain (strong foundation)
**MEDIUM RISK**: Consolidate duplicated systems (needs careful testing)
**HIGH RISK**: Backend foundation from scratch (critical but necessary)
**HIGH RISK**: Mesh infrastructure from scratch (critical but necessary)