# CHARACTER ENGINE - TARGET ARCHITECTURE

**Document**: TARGET_ARCHITECTURE.md  
**Date**: 2026-09-02  
**Status**: DEFINITIVE ARCHITECTURE  
**Purpose**: Define the target architecture for CHARACTER ENGINE production system

---

## 1. DEFINITIVE PRODUCT DEFINITION

CHARACTER ENGINE is a production and runtime system for realistic and reusable human characters targeting:

- Cinematography
- Video games
- Simulation
- Animation
- Interaction
- Historical character representation (José de San Martín, Granaderos, etc.)
- Wound/Transformation simulation
- Crowd systems
- UPBGE integration

---

## 2. DEFINITIVE ARCHITECTURE DIRECTION

### 2.1 Source of Truth

**PRINCIPLE**: The source of truth is NOT Blender.

**SOURCE OF TRUTH**: DATA + SCHEMAS + PARAMETERS + RELATIONSHIPS + PROVENANCE

**Blender Role**: Producer, visualizer, generator, validator, exporter (NOT source of truth)

**Domain Independence**: The domain layer MUST NOT depend on bpy

---

## 2.2 Layered Architecture

```
DOMAIN
    ↓
APPLICATION
    ↓
DATA
    ↓
INFRASTRUCTURE
    ↓
BLENDER
    ↓
RUNTIME
    ↓
BACKEND
```

---

## 3. PRODUCTION FLOW

### 3.1 Target Production Pipeline

```
BLENDER TEAM
    ↓
MASTER ASSET
    ↓
BLENDER VALIDATION
    ↓
EXPORT PACKAGE
    ↓
BACKEND REGISTRATION
    ↓
ASSET VERSION
    ↓
VALIDATION
    ↓
EVIDENCE
    ↓
UPBGE IMPORT
    ↓
RUNTIME VALIDATION
    ↓
RELEASE
```

### 3.2 Data Flow Pipeline

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

### 3.3 Parallel Backend Pipeline

```
USER
    ↓
EVENTS
    ↓
REWARDS
    ↓
SECURITY
    ↓
ASSETS
    ↓
PROVENANCE
    ↓
VALIDATION
    ↓
EVIDENCE
```

---

## 4. SYSTEM COMPONENTS

### 4.1 Complete System Architecture

#### A. DATA
- Reference data management
- Provenance tracking
- Schema validation
- Data integrity

#### B. DOMAIN
- Anatomical domain (existing)
- Morphological domain (NEW)
- Mesh domain (NEW)
- Tissue domain (NEW)
- Musculoskeletal domain (NEW)
- Deformation domain (NEW)
- Behavior domain (NEW)
- Historical domain (NEW)

#### C. ANATOMY
- 206-bone skeleton (existing)
- Coordinate system (existing)
- Landmarks (existing)
- Proportions (existing)
- Reference data (existing, A0.5)

#### D. MORPHOLOGY (NEW)
- Parametric body model
- Global parameters
- Segment parameters
- Regional parameters
- Shape parameters
- Dependency graph

#### E. MESH (NEW)
- HumanMesh domain model
- MeshVertex, MeshEdge, MeshFace
- SurfaceRegion, AnatomicalRegion
- MeshTopology
- MeshCoordinateSystem
- MeshGenerator
- MeshValidation

#### F. TISSUES (NEW)
- Tissue models
- Soft tissue simulation
- Skin deformation
- Fat distribution

#### G. MUSCULOSKELETAL (NEW)
- Muscle models
- Tendon models
- Connective tissue
- Muscle attachment regions

#### H. DEFORMATION (NEW)
- Deformation rig
- Skin deformation
- Blend shapes
- Morph targets

#### I. RIG (NEW)
- Rig builder
- Constraints
- Controls
- Drivers

#### J. PHYSICS (NEW)
- Physics simulation
- Collision detection
- Soft body physics

#### K. CLOTHING (NEW)
- Clothing models
- Clothing simulation
- Attachment systems

#### L. EQUIPMENT (NEW)
- Equipment models
- Weapon systems
- Mount systems (horses)

#### M. BEHAVIOR (NEW)
- Behavior trees
- State machines
- AI behaviors

#### N. DAMAGE / WOUNDS (NEW)
- Wound models
- Damage simulation
- Transformation effects

#### O. TRANSFORMATION (NEW)
- Age transformation
- Body modification
- Historical transformation

#### P. ENVIRONMENT (NEW)
- Environment models
- Climate effects
- Terrain interaction

#### Q. INTERACTION (NEW)
- Interaction systems
- Combat systems
- Social interaction

#### R. CROWD (NEW)
- Crowd simulation
- Crowd behavior
- Multitude systems

#### S. CINEMATIC (NEW)
- Cinematic sequences
- Camera systems
- Scene management

#### T. RUNTIME (NEW)
- UPBGE integration
- Runtime validation
- Performance optimization

#### U. BACKEND (NEW - CRITICAL)
- User/Identity system
- Event system
- Reward system
- Security infrastructure
- Asset registry
- API layer
- Database

#### V. SECURITY (NEW - CRITICAL)
- Authentication
- Authorization
- Rate limiting
- Input validation
- Audit logging
- Secrets management

#### W. EVENTS (NEW - CRITICAL)
- Event model
- Event ingestion
- Server sequence generation
- Integrity verification
- Idempotency

#### X. EVIDENCE / VALIDATION (NEW - CRITICAL)
- Evidence tracking
- Validation pipelines
- Audit trails
- Provenance enforcement

#### Y. EXPORT / IMPORT (NEW)
- Asset package system
- Export pipelines
- Import validation
- Package verification

---

## 5. MANIFOLDS

### 5.1 Manifold Definitions

The system must support the following manifolds:

#### M01 Anatomical
- 206-bone skeleton
- Joint centers
- Landmarks
- Proportions

#### M02 Morphological
- Body parameters
- Shape parameters
- Dependency relationships

#### M03 Skeletal
- Bone hierarchy
- Joint relationships
- Coordinate transforms

#### M04 Joint / Kinematic
- Joint centers
- Joint axes
- Range of motion

#### M05 Musculoskeletal
- Muscles
- Tendons
- Connective tissue

#### M06 Soft-Tissue
- Skin
- Fat
- Soft tissue deformation

#### M07 Surface
- Mesh geometry
- Surface regions
- Topology

#### M08 Deformation
- Blend shapes
- Morph targets
- Skin weights

#### M09 Identity
- Character identity
- Historical identity
- Cultural identity

#### M10 Historical
- Historical parameters
- Population characteristics
- Era-specific data

#### M11 Clothing
- Clothing models
- Attachment systems
- Clothing physics

#### M12 Equipment
- Weapons
- Tools
- Mount systems

#### M13 Behavioral
- Behavior trees
- State machines
- AI systems

#### M14 Physical-State
- Health
- Stamina
- Injury state

#### M15 Damage / Wound
- Wound models
- Damage simulation
- Healing systems

#### M16 Transformation
- Age transformation
- Body modification
- Magical effects

#### M17 Environmental
- Climate effects
- Terrain
- Weather

#### M18 Interaction
- Combat
- Social
- Environmental

#### M19 Crowd
- Crowd simulation
- Multitude systems
- Group behavior

#### M20 Cinematic
- Sequences
- Camera
- Scene management

#### M21 Runtime
- UPBGE integration
- Performance
- Optimization

---

## 6. BACKEND ARCHITECTURE

### 6.1 Backend Components (P0-P1 Priority)

#### B0.1 Configuration
- Application configuration
- Environment configuration
- Feature flags

#### B0.2 Database Foundation
- Database models
- Migrations
- ORM integration
- Connection management

#### B0.3 User
- User model
- User profile
- User preferences

#### B0.4 Account
- Account model
- Account types
- Account status

#### B0.5 Identity
- Identity model
- Identity verification
- Identity federation

#### B0.6 Session
- Session model
- Session management
- Session security

#### B0.7 Authentication
- Authentication mechanisms
- Token management
- Password management

#### B0.8 Authorization
- Role-based access control
- Permission system
- Policy enforcement

#### B0.9 Event Model
- Event schema
- Event types
- Event metadata

#### B0.10 Event Ingestion
- Event receivers
- Event processors
- Event routing

#### B0.11 Event Integrity
- Integrity verification
- Hash validation
- Chain validation

#### B0.12 Idempotency
- Idempotency keys
- Duplicate detection
- Idempotency enforcement

#### B0.13 Reward Definitions
- Reward models
- Reward types
- Reward conditions

#### B0.14 Reward Eligibility
- Eligibility engine
- Condition evaluation
- Qualification tracking

#### B0.15 Reward Ledger
- Grant tracking
- Reward history
- Ledger integrity

#### B0.16 Audit Trail
- Audit logging
- Audit storage
- Audit querying

#### B0.17 Security Middleware
- Authentication middleware
- Authorization middleware
- Rate limiting middleware

#### B0.18 Rate Limiting
- Rate limiting algorithms
- Quota management
- Abuse prevention

#### B0.19 Input Validation
- Request validation
- Schema validation
- Type validation

#### B0.20 Asset Registry
- Asset registration
- Asset metadata
- Asset versioning

#### B0.21 Asset Versions
- Version tracking
- Version comparison
- Version rollback

#### B0.22 Provenance
- Provenance tracking
- Provenance validation
- Provenance enforcement

#### B0.23 Evidence
- Evidence tracking
- Evidence validation
- Evidence storage

#### B0.24 API
- API layer
- Request/response models
- Error handling

#### B0.25 Integration Tests
- Backend integration tests
- End-to-end tests
- Performance tests

#### B0.26 Security Tests
- Authentication tests
- Authorization tests
- Penetration tests

---

## 7. IDENTITY ARCHITECTURE

### 7.1 Identity Separation

**PRINCIPLE**: Do not mix concepts.

**Separate Components**:
- USER
- ACCOUNT
- IDENTITY
- SESSION
- DEVICE
- API CLIENT

**Relationships**:
- One Identity can have multiple Accounts
- One Account can have multiple Users
- One User can have multiple Sessions
- One Session can have multiple Devices
- One Device can have multiple API Clients

---

## 8. EVENT SYSTEM ARCHITECTURE

### 8.1 Event Model

**First Fundamental Event**: USER_REGISTERED

**Event Structure**:
- event_id
- event_type
- actor_id
- timestamp
- server_sequence
- payload
- source
- schema_version
- integrity_hash
- previous_hash
- idempotency_key

**Critical Rule**: The sequence MUST be generated by the server. The client CANNOT determine it.

---

## 9. REWARD SYSTEM ARCHITECTURE

### 9.1 Reward Flow

```
USER_REGISTERED
    ↓
SERVER SEQUENCE
    ↓
ELIGIBILITY
    ↓
REWARD ENGINE
    ↓
REWARD GRANT
    ↓
AUDIT EVENT
```

### 9.2 First Reward

**Reward**: FIRST_USER

**Concept**: "Eres el Primer Usuario"

**Implementation**: Configurable, NOT hardcoded

### 9.3 Reward Ledger

**Fields**:
- grant_id
- user_id
- reward_id
- qualification_event_id
- granted_at
- status
- metadata

**States**:
- PENDING
- GRANTED
- REVOKED
- EXPIRED
- REJECTED

### 9.4 Idempotency

**Critical Rule**: The same operation repeated CANNOT produce:
- Multiple users
- Multiple events
- Multiple rewards

---

## 10. SECURITY ARCHITECTURE

### 10.1 Security Layers

```
INTERNET
 ↓
TLS
 ↓
REVERSE PROXY / GATEWAY
 ↓
RATE LIMITING
 ↓
AUTHENTICATION
 ↓
AUTHORIZATION
 ↓
API
 ↓
SERVICES
 ↓
DATABASE
```

### 10.2 Security Requirements

**Implement or Prepare**:
- Input validation
- Request size limits
- Authentication
- Authorization
- Session control
- Rate limiting
- Audit logging
- Secrets management
- Safe errors
- Integrity validation
- Ownership checks
- Access control
- Replay protection
- Idempotency
- Abuse prevention

**Never Expose**:
- Stack traces
- Database errors
- API keys
- Tokens
- Secrets
- Filesystem paths
- Infrastructure information

---

## 11. PROVENANCE ARCHITECTURE

### 11.1 Provenance States

**States**:
- PROVEN
- DERIVED
- ESTIMATE
- ASSUMED
- PLACEHOLDER
- UNKNOWN
- USER_INPUT

**Critical Rule**: Never convert ASSUMED, PLACEHOLDER, or UNKNOWN to canonical truth.

**PROVEN Definition**: PROVEN means there exists a traceable and documented source, NOT absolute biological truth.

**Track When Appropriate**:
- Source
- Dataset
- Population
- Method
- Units
- Uncertainty
- Provenance
- Transformation
- Derivation chain

---

## 12. ANATOMY ARCHITECTURE

### 12.1 Existing 206-Bone Structure

**Status**: EXISTING (208 nodes = 206 bones + CRANIUM + ROOT_SKELETON)

**Do Not Modify Arbitrarily**

**Known Issues** (from A02/A03 audits):
- Incorrect height
- Insufficient spine curvature
- Joint gaps
- Incorrect proportions
- Uniform lengths
- Simplified hands/feet
- Incorrect orientations

**Action**: Keep as debt/historical knowledge, do NOT automatically convert to new data

---

## 13. MESH ARCHITECTURE

### 13.1 Mesh Requirements

**Required Architecture**:
- HumanMesh (first-class domain concept)
- MeshVertex, MeshEdge, MeshFace
- SurfaceRegion, AnatomicalRegion
- MeshTopology
- MeshCoordinateSystem
- MeshGenerator
- MeshValidation
- Skeleton-Mesh relationship
- Blender mesh integration

**Critical Rule**: Do NOT invent anatomical geometry. Build contracts to receive geometry from specialists.

---

## 14. MUSCULOSKELETAL ARCHITECTURE

### 14.1 Musculoskeletal System

**Required Integration**:
- BONE → JOINT → MUSCLE → TENDON → CONNECTIVE TISSUE → SOFT TISSUE → SKIN

**Relationship with Rig**:
- RIG → DEFORMATION → PHYSICS → MOTION

**Critical Rule**: Do NOT implement fictional simulations to appear to have progress.

---

## 15. HISTORICAL CHARACTERS

### 15.1 Historical Character Support

**Required Support**:
- José de San Martín
- Granaderos
- Historical context characters

**Population Support**:
- Mestizos
- Afrodescendants
- Mulatos
- Criollos
- Españoles
- Pueblos indígenas
- Men
- Women
- Heroínas
- Different ages
- Different bodies
- Different physical states

**Critical Rule**: Historical/social categories must NOT become rigid biological presets.

**Separate**:
- IDENTITY
- ANATOMY
- MORPHOLOGY
- GENEALOGY
- HISTORICAL CONTEXT
- CULTURAL CONTEXT
- CLOTHING
- EQUIPMENT
- BEHAVIOR

**Critical Rule**: A woman must NOT be "male model + modifier". Must have complete anatomical model.

---

## 16. CABALLO SUPPORT

### 16.1 Horse Architecture

**Required for Granaderos context**:
- CHARACTER + ANIMAL + EQUIPMENT + RIDER + MOUNT + INTERACTION

**Implementation**: Design architecture now, implement content later when requested.

---

## 17. CINEMATOGRAPHY ARCHITECTURE

### 17.1 Cinematic Scenarios

**Example Scenarios**:
- CINE-SM-001: Retrato / rostro de San Martín
- CINE-SM-002: San Martín montado
- CINE-GR-001: Granadero descansando
- CINE-GR-002: Granadero caminando
- CINE-GR-003: Marcha militar
- CINE-GR-004: Carga de caballería
- CINE-GR-005: Combate
- CINE-GR-006: Herida
- CINE-H-001: Heroína histórica

**Additional Requirements**:
- Multitudes
- Ejército
- Combate
- Interacción
- Ambiente histórico

---

## 18. COORDINATE SYSTEM ARCHITECTURE

### 18.1 Coordinate System

**Maintain**: Z-UP

**Document Explicitly**:
- Units
- Axes
- Handedness
- Origin
- World coordinates
- Local coordinates
- Bone coordinates
- Mesh coordinates
- Runtime coordinates
- Blender coordinates
- UPBGE coordinates
- Transformations between systems

**Critical Rule**: Do NOT assume equivalence between systems without validation.

---

## 19. BLENDER / UPBGE ARCHITECTURE

### 19.1 Responsibilities

**BLENDER**:
- Production
- Modeling
- Rigging
- Materials
- Animation
- Validation
- Export

**BACKEND**:
- Identity
- Assets
- Versions
- Metadata
- Events
- Provenance
- Security
- Validation records
- Evidence
- Registry

**UPBGE**:
- Runtime
- Interaction
- Gameplay
- Simulation
- Execution

**Critical Rule**: UPBGE must consume an approved version. Must NOT silently modify the master asset.

---

## 20. GIT / TRAZABILIDAD ARCHITECTURE

### 20.1 Traceability Requirements

**Register**:
- Decisions
- Architecture
- Audits
- Migrations
- Reconstructions
- Schema changes
- API changes
- Data changes
- Validations
- Design decisions

**Critical Rule**: Do NOT delete useful history. If Git is not available, document the blockage.

**Critical Rule**: Do NOT execute destructive Git operations without explicit authorization.

---

## 21. DATA INVENTION RULE

### 21.1 CRITICAL RULE

**NEVER fill a scientific/anatomical/historical gap with an invented number just to make the system work.**

**If information is missing**:
- Use UNKNOWN
- Use PLACEHOLDER
- Use REFERENCE_DATA_REQUIRED

**Never present** an ASSUMPTION as PROVEN.

---

## 22. NO BUNKER MIXING

### 22.1 Separation Principle

**CHARACTER ENGINE is independent of BÚNKER.**

**Do NOT mix**:
- Architecture
- Models
- Databases
- Events
- Trading
- Finances
- Risk management

**Reuse**: Engineering philosophy is acceptable, but do NOT mix domains.

---

## 23. IMPLEMENTATION PRIORITY

### 23.1 Correct Order

**P0**: Repository truth
**P1**: Architecture reconciliation
**P2**: Backend foundation
**P3**: Identity / Auth / Authorization
**P4**: Event system
**P5**: Rewards
**P6**: Security
**P7**: Asset registry
**P8**: Asset versioning
**P9**: Provenance
**P10**: Evidence / Validation
**P11**: Blender asset ingestion
**P12**: UPBGE runtime contract
**P13**: Anatomical/Mesh data integration
**P14**: Advanced manifolds

**Critical Rule**: Do NOT attempt to implement everything simultaneously.

---

## 24. END-TO-END TEST

### 24.1 First End-to-End Test

**System must demonstrate**:
1. Create user
2. Generate USER_REGISTERED
3. Server assigns sequence=1
4. Reward engine detects FIRST_USER
5. Generate reward grant
6. Generate audit trail
7. Repeat same request with same idempotency key
8. No duplicates created
9. Attempt to modify sequence from client
10. Must be rejected
11. Create 10 identical requests
12. Must exist only: 1 user, 1 event, 1 reward
13. Manipulate historical event
14. Integrity verification must detect it
15. Attempt to access reward of another user
16. Must produce 403

---

## 25. SUCCESS CRITERIA

### 25.1 Success Definition

**Work is NOT complete when**:
- It compiles
- Basic tests pass
- Files exist
- API exists
- Database exists
- Skeleton exists

**Work IS complete when**:
- ARCHITECTURE
- DATA
- SECURITY
- EVENTS
- PROVENANCE
- ASSETS
- VALIDATION
- EVIDENCE

are coherently connected and demonstrable.

---

## 26. ARCHITECTURE STATUS

### 26.1 Current vs Target

**Current Architecture**: SKELETON → BLENDER  
**Target Architecture**: DATA → ANATOMY → MORPHOLOGY → MESH → SKELETON

**Current Backend**: MISSING  
**Target Backend**: FULLY IMPLEMENTED

**Current Mesh**: MISSING  
**Target Mesh**: FULLY IMPLEMENTED

**Current Events**: MISSING  
**Target Events**: FULLY IMPLEMENTED

**Current Security**: MISSING  
**Target Security**: FULLY IMPLEMENTED

---

## 27. CONCLUSION

### 27.1 Architecture Summary

**Principles**:
- CORRECTNESS
- TRACEABILITY
- DETERMINISM
- SECURITY
- REPRODUCIBILITY
- VALIDATION
- MODULARITY
- EXTENSIBILITY

**Before**:
- Quantity of files
- Quantity of features
- Quantity of code

**After**:
- Architectural correctness
- Data integrity
- Security
- Traceability
- Validation

**Objective**: Build CHARACTER ENGINE correctly.