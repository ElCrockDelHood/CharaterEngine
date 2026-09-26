# CHARACTER ENGINE - MIGRATION PLAN

**Document**: MIGRATION_PLAN.md  
**Date**: 2026-09-02  
**Status**: POST-REORIENTATION AUDIT  
**Purpose**: Implementation roadmap for migrating from legacy to target architecture

---

## 1. MIGRATION STRATEGY

### 1.1 Migration Principles

**No Breaking Changes**: Migrate incrementally without breaking existing functionality

**Parallel Implementation**: Build new components alongside existing ones

**Gradual Migration**: Migrate components incrementally with testing at each step

**Validation**: Validate each migration step before proceeding

**Rollback**: Maintain rollback capability at each step

---

## 2. MIGRATION PHASES

### 2.1 Phase 1: Backend Foundation (P0-P1 Priority)

**Timeline**: 2-3 weeks

**Objective**: Implement critical backend infrastructure

#### Step 1.1: Directory Structure
- Create `backend/` directory structure
- Create subdirectories: `identity/`, `events/`, `rewards/`, `security/`, `assets/`, `api/`, `database/`
- Update `__init__.py` files

#### Step 1.2: Identity System
- Implement User model
- Implement Account model
- Implement Identity model
- Implement Session model
- Implement Device model
- Implement API Client model
- Define relationships
- Add unit tests
- Add integration tests

#### Step 1.3: Event System
- Implement Event model (event_id, event_type, actor_id, timestamp, server_sequence, payload, source, schema_version, integrity_hash, previous_hash, idempotency_key)
- Implement event ingestion pipeline
- Implement server sequence generation
- Implement integrity verification
- Implement idempotency enforcement
- Implement first event: USER_REGISTERED
- Add unit tests
- Add integration tests

#### Step 1.4: Reward System
- Implement Reward definitions (configurable, not hardcoded)
- Implement eligibility engine
- Implement reward ledger
- Implement grant tracking
- Implement first reward: FIRST_USER
- Add unit tests
- Add integration tests

#### Step 1.5: Security Infrastructure
- Implement authentication middleware
- Implement authorization middleware
- Implement rate limiting
- Implement input validation
- Implement audit logging
- Add security tests

#### Step 1.6: Asset Registry
- Implement asset registration
- Implement version tracking
- Implement provenance tracking
- Implement evidence tracking
- Add unit tests
- Add integration tests

#### Step 1.7: API Layer
- Implement API layer
- Implement request/response models
- Implement error handling
- Implement API security
- Add API tests

#### Step 1.8: Database
- Implement database models
- Implement migrations
- Implement ORM integration
- Add database tests

**Validation**: End-to-end test (create user → event → reward → audit)

---

### 2.2 Phase 2: Mesh Infrastructure (P2 Priority)

**Timeline**: 2-3 weeks

**Objective**: Implement mesh domain model and generation

#### Step 2.1: Mesh Domain Model
- Create `domain/mesh/` directory
- Implement HumanMesh domain model
- Implement MeshVertex
- Implement MeshEdge
- Implement MeshFace
- Implement SurfaceRegion
- Implement AnatomicalRegion
- Implement MeshTopology
- Implement MeshCoordinateSystem
- Add unit tests

#### Step 2.2: Mesh Generation
- Implement MeshGenerator
- Implement TopologyGenerator
- Implement ParametricDeformation
- Implement SurfaceLandmarks
- Add unit tests
- Add integration tests

#### Step 2.3: Mesh Validation
- Implement MeshValidation
- Implement TopologyValidation
- Implement SymmetryValidation
- Add unit tests
- Add integration tests

#### Step 2.4: Mesh-Skeleton Relationship
- Implement mesh-to-skeleton fitting algorithm
- Implement joint region detection
- Implement surface-to-joint mapping
- Implement constraint system
- Add unit tests
- Add integration tests

**Validation**: Mesh generation → skeleton fitting → validation

---

### 2.3 Phase 3: Consolidation (P3 Priority)

**Timeline**: 1-2 weeks

**Objective**: Remove duplicated and deprecated components

#### Step 3.1: Deprecation Marking
- Add deprecation notices to `anatomy/` directory
- Add deprecation notices to `skeleton/` directory
- Add deprecation notices to `anatomy/measurements.py`
- Add deprecation notices to `anatomy/proportions.py`
- Add deprecation warnings at runtime
- Update documentation

#### Step 3.2: Import Migration
- Update all imports to canonical implementations
- Update test imports
- Update application code imports
- Verify tests pass
- Fix broken functionality

#### Step 3.3: Component Removal
- Remove `anatomy/` directory
- Remove `skeleton/` directory
- Update `__init__.py` files
- Run full test suite
- Verify no broken imports

**Validation**: Clean codebase, all tests pass

---

### 2.4 Phase 4: Integration (P4 Priority)

**Timeline**: 2-3 weeks

**Objective**: Integrate new components with existing system

#### Step 4.1: Reconstruction Pipeline Refactor
- Refactor reconstruction pipeline for A0.5 provenance integration
- Integrate ReconstructionEligibilityValidator
- Replace hardcoded constants with reference-backed values
- Add provenance validation gates
- Add unit tests
- Add integration tests

#### Step 4.2: Reference Data Acquisition
- Acquire real reference data (NHANES, WHO_BMI, ISB, FORENSIC)
- Populate reference data files
- Validate reference data quality
- Update source registry
- Add validation tests

#### Step 4.3: Blender Integration Extension
- Implement mesh import
- Implement mesh export
- Implement material system integration
- Implement Blender scene components
- Add integration tests

#### Step 4.4: Export/Import Infrastructure
- Implement asset package system
- Implement export pipelines
- Implement import validation
- Implement package verification
- Add unit tests
- Add integration tests

**Validation**: Full pipeline integration test

---

## 3. MIGRATION ORDER

### 3.1 Critical Path

**Critical Order**:
1. Backend foundation (enables user/events/rewards/security/assets)
2. Mesh infrastructure (enables mesh-first architecture)
3. Consolidation (removes technical debt)
4. Integration (connects new with existing)

**Dependencies**:
- Backend foundation must come before events/rewards/security/assets
- Mesh infrastructure can proceed in parallel with backend
- Consolidation must come after integration testing
- Integration must come after backend and mesh are stable

---

## 4. MIGRATION VALIDATION

### 4.1 Validation Criteria

**Phase 1 Validation**:
- End-to-end test: Create user → event → reward → audit
- Idempotency test: Repeat same request → no duplicates
- Security test: Modify sequence from client → reject
- Access test: Access reward of another user → 403

**Phase 2 Validation**:
- Mesh generation test: Generate mesh from parameters
- Mesh validation test: Validate mesh topology
- Fitting test: Fit skeleton to mesh
- Integration test: Mesh → skeleton → validation

**Phase 3 Validation**:
- Import test: All imports work with canonical implementations
- Test test: All tests pass with canonical implementations
- Clean test: No broken imports after removal

**Phase 4 Validation**:
- Pipeline test: Full reconstruction pipeline with provenance enforcement
- Data test: Real reference data integration
- Blender test: Mesh import/export works
- Export test: Asset package generation works

---

## 5. RISK MITIGATION

### 5.1 Backend Foundation Risks

**Risk**: Building backend from scratch is complex

**Mitigation**:
- Start with minimal viable backend
- Use proven patterns (event sourcing, CQRS)
- Implement incrementally with testing
- Keep existing system functional

### 5.2 Mesh Infrastructure Risks

**Risk**: Mesh generation is complex and requires expertise

**Mitigation**:
- Design domain model first
- Implement basic mesh operations first
- Use existing math infrastructure (Vector3, Quaternion, Matrix4)
- Coordinate with Blender team for asset production

### 5.3 Consolidation Risks

**Risk**: Breaking imports or functionality

**Mitigation**:
- Comprehensive import analysis before removal
- Step-by-step import updates
- Test after each update
- Keep deprecated files during migration

### 5.4 Integration Risks

**Risk**: Integration breaks existing functionality

**Mitigation**:
- Parallel implementation
- Extensive testing
- Gradual rollout
- Rollback capability

---

## 6. SUCCESS CRITERIA

### 6.1 Phase Success Criteria

**Phase 1 Success**:
- End-to-end test passes
- All backend tests pass
- Security tests pass
- Integration tests pass

**Phase 2 Success**:
- Mesh domain model implemented
- Mesh generation works
- Mesh validation works
- Mesh-skeleton fitting works

**Phase 3 Success**:
- Deprecated components removed
- Codebase is clean
- All tests pass
- No broken imports

**Phase 4 Success**:
- Reconstruction pipeline refactored
- A0.5 provenance enforced
- Real reference data integrated
- Blender integration extended
- Export/import implemented

---

## 7. TIMELINE SUMMARY

### 7.1 Overall Timeline

**Phase 1 (Backend Foundation)**: 2-3 weeks
**Phase 2 (Mesh Infrastructure)**: 2-3 weeks
**Phase 3 (Consolidation)**: 1-2 weeks
**Phase 4 (Integration)**: 2-3 weeks

**Total Estimated Timeline**: 7-11 weeks

---

## 8. NEXT STEPS

### 8.1 Immediate Actions

1. Create `backend/` directory structure
2. Implement User model
3. Implement Event model
4. Implement first event: USER_REGISTERED
5. Implement first reward: FIRST_USER
6. Implement security middleware
7. End-to-end validation test

### 8.2 Parallel Actions

1. Design mesh domain model
2. Implement mesh domain model (can proceed in parallel with backend)
3. Design parametric body model
4. Implement parametric body model (can proceed in parallel with backend)

---

## 9. SUMMARY

### 9.1 Migration Summary

**Total Phases**: 4
**Total Estimated Timeline**: 7-11 weeks
**Critical Path**: Backend → Mesh → Consolidation → Integration
**Risk Level**: MEDIUM-HIGH (significant new implementation required)

### 9.2 Migration Strategy

**Approach**: Incremental migration with parallel implementation
**Validation**: Comprehensive testing at each phase
**Rollback**: Maintain rollback capability
**Success**: Full validation at each phase before proceeding