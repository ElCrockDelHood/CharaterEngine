# A0.4 Implementation Baseline

**Sprint:** A0.4 - Anatomical Foundation Engineering  
**Date:** 2026-08-13  
**Status:** IMPLEMENTATION BASELINE CREATED  
**Purpose:** Reconcile existing A0 documentation with repository state and create implementation plan

---

## Executive Summary

This baseline reconciles the comprehensive A0.3 analysis with the current repository state to create a concrete implementation plan for Sprint A0.4. The analysis reveals that the repository has a solid structural foundation but lacks the anatomical reconstruction infrastructure required for deterministic anatomical skeleton generation.

**Key Finding:** The repository architecture is sound and suitable for extension. No major conflicts exist between A0.3 requirements and existing architecture. The implementation can proceed with targeted additions rather than wholesale redesign.

---

## Current Architecture Used

### Existing Pipeline (PRESERVED)
```
human_adult_206.json (canonical)
    ↓
JsonLoader.load_to_dto()
    ↓
AssetDTO + SkeletonDTO
    ↓
SkeletonBuilder.build() [domain/anatomy/osteology/builder.py]
    ↓
Skeleton (domain model)
    ↓
SkeletonValidator.validate()
    ↓
SkeletonSerializer.serialize()
    ↓
skeleton_serialized.json (builds/exports/)
    ↓
BlenderImporter.import_from_skeleton()
    ↓
validation.blend (builds/tests/)
    ↓
StateAuditor.validate()
```

### Current Domain Structure
```
src/character_engine/domain/anatomy/
├── osteology/
│   ├── bone.py              # Bone domain model (functional)
│   ├── builder.py           # SkeletonBuilder (functional)
│   ├── constants.py         # Osteology constants
│   ├── exceptions.py        # Domain exceptions
│   ├── skeleton.py          # Skeleton domain model
│   ├── transform.py         # Transform model
│   └── validator.py         # Skeleton validator
└── templates/
    ├── human.py             # Human template loader
    └── __init__.py
```

### Existing Math Infrastructure
```
src/character_engine/math/algebra/
├── vector3.py              # Vector3 class (functional)
├── quaternion.py           # Quaternion class (functional)
└── matrix4.py             # Matrix4 class (functional)
```

### Existing Validation Infrastructure
```
src/character_engine/validation/
├── result.py              # ValidationResult (functional)
└── validator.py           # General validator (functional)
```

### Coordinate System (CURRENT STATE)
- **Up axis:** Z (verified from data)
- **Handedness:** Right-handed (verified from data)
- **Units:** Meters (verified from data)
- **Origin:** Foot midline ground (Z=0)
- **Lateral axis:** X (positive direction unknown)
- **Forward axis:** UNDEFINED (needs definition)

---

## A0.3 Requirements Mapped to Repository Files

### A0.3: Anatomical Parameter Inventory
**Requirement:** 70+ anatomical parameters with provenance  
**Repository Status:** NO EXISTING IMPLEMENTATION  
**Implementation Location:** `src/character_engine/domain/anatomy/parameters/`  
**Decision:** Create new parameter module structure

### A0.3: Landmark Model
**Requirement:** 50+ anatomical landmarks with coordinates  
**Repository Status:** NO EXISTING IMPLEMENTATION  
**Implementation Location:** `src/character_engine/domain/anatomy/landmarks/`  
**Decision:** Create new landmark module structure

### A0.3: Proportion Model
**Requirement:** Anthropometric proportion relationships  
**Repository Status:** EMPTY FILES EXIST (`src/character_engine/anatomy/proportions.py`)  
**Implementation Location:** `src/character_engine/domain/anatomy/proportions/`  
**Decision:** Use existing location but replace with proper implementation

### A0.3: Joint Center Model
**Requirement:** 6 major joint centers with biomechanical data  
**Repository Status:** NO EXISTING IMPLEMENTATION  
**Implementation Location:** `src/character_engine/domain/anatomy/joints/`  
**Decision:** Create new joint center module structure

### A0.3: Spine Model
**Requirement:** Parameterized spine with natural curvatures  
**Repository Status:** NO EXISTING IMPLEMENTATION  
**Implementation Location:** `src/character_engine/domain/anatomy/spine/`  
**Decision:** Create new spine module structure

### A0.3: Hand Model
**Requirement:** 27-bone hand structure per hand  
**Repository Status:** NO EXISTING IMPLEMENTATION  
**Implementation Location:** `src/character_engine/domain/anatomy/hands/`  
**Decision:** Create new hand module structure

### A0.3: Foot Model
**Requirement:** 26-bone foot structure per foot  
**Repository Status:** NO EXISTING IMPLEMENTATION  
**Implementation Location:** `src/character_engine/domain/anatomy/feet/`  
**Decision:** Create new foot module structure

### A0.3: Coordinate System Verification
**Requirement:** Formal coordinate system contract  
**Repository Status:** PARTIALLY DEFINED (Z-up, right-handed, meters)  
**Implementation Location:** `src/character_engine/domain/anatomy/coordinate_system.py`  
**Decision:** Extend existing partial definition to full contract

### A0.3: Reconstruction Architecture
**Requirement:** 12-stage reconstruction pipeline  
**Repository Status:** EXISTING PIPELINE STRUCTURAL (different stages)  
**Implementation Location:** `src/character_engine/domain/anatomy/reconstruction/`  
**Decision:** Create reconstruction layer that integrates with existing pipeline

### A0.3: Test Specification Review
**Requirement:** 52 anatomical validation tests  
**Repository Status:** EXISTING STRUCTURAL TESTS (16 currently testable)  
**Implementation Location:** `tests/anatomy/`  
**Decision:** Create new anatomical test suite separate from structural tests

### A0.3: Reference Data Requirements
**Requirement:** Comprehensive reference data system  
**Repository Status:** NO EXISTING IMPLEMENTATION  
**Implementation Location:** `src/character_engine/domain/anatomy/reference/`  
**Decision:** Create new reference data module structure

---

## Conflicts Discovered

### NO MAJOR CONFLICTS IDENTIFIED

**Minor Conflicts Resolved:**

1. **Empty anatomy modules:** The repository has empty/stub files in `src/character_engine/anatomy/` (proportions.py, etc.)
   - **Resolution:** These appear to be abandoned placeholders. A0.4 will implement proper anatomy modules in `domain/anatomy/` and these can be removed or updated post-A0.4.

2. **Duplicate builder investigation:** A0.1 identified potential duplicate builders
   - **Resolution:** Confirmed that `skeleton/builder.py` is empty (0 bytes) and `domain/anatomy/osteology/builder.py` is functional. No actual duplication exists.

3. **Math module location:** Vector3/Quaternion exist in `math/algebra/` 
   - **Resolution:** This is correct location. A0.4 will use existing math infrastructure.

4. **Coordinate system partial definition:** Forward axis undefined
   - **Resolution:** A0.4 will define complete coordinate system contract based on current Z-up convention.

---

## Decisions Made

### Architectural Decisions

1. **PRESERVE EXISTING PIPELINE:** Do not modify existing JSON → Skeleton → Blender pipeline
2. **ADD RECONSTRUCTION LAYER:** Create new reconstruction layer that feeds into existing pipeline
3. **DOMAIN SEPARATION:** Keep anatomical reconstruction separate from Blender infrastructure
4. **INCREMENTAL IMPLEMENTATION:** Implement in logical checkpoints as specified in A0.4
5. **NO MODIFICATION TO CANONICAL JSON:** Preserve `human_adult_206.json` as A0.2 baseline

### Module Structure Decisions

1. **New anatomy domain structure:** Create organized subdirectories under `domain/anatomy/`
2. **Reference data separation:** Keep reference data in dedicated module
3. **Test separation:** Create anatomical tests separate from structural tests
4. **Documentation structure:** Create anatomy documentation under `docs/anatomy/`

### Implementation Approach Decisions

1. **Pure Python math:** Use existing Vector3/Quaternion, no bpy in core calculations
2. **Deterministic algorithms:** No random values, no external state dependencies
3. **Provenance tracking:** Every value must have traceable source
4. **Test-driven development:** Implement tests alongside components
5. **Incremental validation:** Test at each checkpoint

---

## Implementation Plan

### Phase 1: Foundation (A04-01 to A04-03)
**Goal:** Establish coordinate system, reference data, and parameter models

**A04-01: Coordinate System**
- Create `docs/anatomy/COORDINATE_SYSTEM.md`
- Create `src/character_engine/domain/anatomy/coordinate_system.py`
- Implement coordinate system contract
- Add coordinate system tests
- Define forward axis (recommend NEGATIVE_Y_FORWARD)
- Define rotation conventions

**A04-02: Reference Data**
- Create `docs/anatomy/REFERENCE_DATA.md`
- Create `src/character_engine/domain/anatomy/reference/` module
- Implement reference data model (source, dataset, value)
- Create reference data file structure
- Add reference data tests
- Leave actual reference data acquisition for later (mark as UNKNOWN/ASSUMED)

**A04-03: Parameter Model**
- Create `src/character_engine/domain/anatomy/parameters/` module
- Implement anatomical parameter model
- Add parameter status tracking (DIRECT_REFERENCE, DERIVED, ASSUMED, UNKNOWN)
- Add parameter tests
- Create parameter validation framework

### Phase 2: Core Anatomical Models (A04-04 to A04-06)
**Goal:** Implement landmark, proportion, and joint center models

**A04-04: Landmark Model**
- Create `src/character_engine/domain/anatomy/landmarks/` module
- Implement landmark domain model
- Add bilateral support (MIDLINE, LEFT, RIGHT)
- Implement mirror/symmetry utilities
- Add landmark tests

**A04-05: Proportion Engine**
- Create `src/character_engine/domain/anatomy/proportions/` module
- Implement proportion calculator
- Add derivation tracking
- Implement proportion formulas based on A0.3 model
- Add proportion tests

**A04-06: Joint Center Model**
- Create `src/character_engine/domain/anatomy/joints/` module
- Implement joint center model for 6 major joints
- Distinguish joint center from bone endpoint
- Add joint center tests
- Create `docs/anatomy/JOINT_CENTERS.md`

### Phase 3: Specialized Anatomical Models (A04-07)
**Goal:** Implement spine, hand, and foot parameterization foundations

**A04-07: Spine/Hand/Foot Foundation**
- Create `src/character_engine/domain/anatomy/spine/` module
- Implement spine parameterization model
- Create `src/character_engine/domain/anatomy/hands/` module
- Implement hand parameterization model
- Create `src/character_engine/domain/anatomy/feet/` module
- Implement foot parameterization model
- Add validation for uniform anatomy detection
- Add specialized anatomical tests

### Phase 4: Validation and Integration (A04-08 to A04-10)
**Goal:** Implement validation framework, tests, and documentation

**A04-08: Anatomical Validation**
- Create `src/character_engine/domain/anatomy/validation/` module
- Implement anatomical validation framework
- Extend existing ValidationResult if needed
- Add PHASE 1 anatomical tests (BS-01 to AP-05)
- Add coordinate system tests
- Implement tolerance definitions

**A04-09: Tests**
- Create test fixtures (A0.2 baseline, synthetic valid)
- Implement highest-priority anatomical tests
- Add determinism test
- Add property/invariant tests
- Verify tests detect known A0.2 failures

**A04-10: Documentation**
- Create `docs/anatomy/RECONSTRUCTION_PIPELINE.md`
- Create `docs/audit/A04_OPEN_QUESTIONS.md`
- Update architecture documentation
- Create implementation guides
- Document data flow

---

## Files to Create

### Documentation Files
1. `docs/anatomy/COORDINATE_SYSTEM.md`
2. `docs/anatomy/REFERENCE_DATA.md`
3. `docs/anatomy/JOINT_CENTERS.md`
4. `docs/anatomy/RECONSTRUCTION_PIPELINE.md`
5. `docs/audit/A04_OPEN_QUESTIONS.md`
6. `docs/audit/A04_ANATOMICAL_FOUNDATION_REPORT.md`

### Source Files
1. `src/character_engine/domain/anatomy/coordinate_system.py`
2. `src/character_engine/domain/anatomy/reference/__init__.py`
3. `src/character_engine/domain/anatomy/reference/source.py`
4. `src/character_engine/domain/anatomy/reference/dataset.py`
5. `src/character_engine/domain/anatomy/reference/value.py`
6. `src/character_engine/domain/anatomy/parameters/__init__.py`
7. `src/character_engine/domain/anatomy/parameters/parameter.py`
8. `src/character_engine/domain/anatomy/parameters/set.py`
9. `src/character_engine/domain/anatomy/landmarks/__init__.py`
10. `src/character_engine/domain/anatomy/landmarks/landmark.py`
11. `src/character_engine/domain/anatomy/landmarks/symmetry.py`
12. `src/character_engine/domain/anatomy/proportions/__init__.py`
13. `src/character_engine/domain/anatomy/proportions/calculator.py`
14. `src/character_engine/domain/anatomy/joints/__init__.py`
15. `src/character_engine/domain/anatomy/joints/joint_center.py`
16. `src/character_engine/domain/anatomy/spine/__init__.py`
17. `src/character_engine/domain/anatomy/spine/model.py`
18. `src/character_engine/domain/anatomy/hands/__init__.py`
19. `src/character_engine/domain/anatomy/hands/model.py`
20. `src/character_engine/domain/anatomy/feet/__init__.py`
21. `src/character_engine/domain/anatomy/feet/model.py`
22. `src/character_engine/domain/anatomy/validation/__init__.py`
23. `src/character_engine/domain/anatomy/validation/anatomical_validator.py`
24. `src/character_engine/domain/anatomy/validation/result.py`

### Test Files
1. `tests/anatomy/__init__.py`
2. `tests/anatomy/test_coordinate_system.py`
3. `tests/anatomy/test_reference_data.py`
4. `tests/anatomy/test_parameters.py`
5. `tests/anatomy/test_landmarks.py`
6. `tests/anatomy/test_proportions.py`
7. `tests/anatomy/test_joint_centers.py`
8. `tests/anatomy/test_spine.py`
9. `tests/anatomy/test_hands.py`
10. `tests/anatomy/test_feet.py`
11. `tests/anatomy/test_anatomical_validation.py`
12. `tests/anatomy/test_determinism.py`
13. `tests/anatomy/fixtures/` (test fixtures directory)

### Data Files
1. `src/character_engine/data/anatomy/reference/` (directory)
2. `src/character_engine/data/anatomy/reference/sources.json`
3. `src/character_engine/data/anatomy/reference/anthropometry.json`
4. `src/character_engine/data/anatomy/reference/osteometry.json`
5. `src/character_engine/data/anatomy/reference/joint_centers.json`

---

## Files to Modify

### Minimal Modifications Required
1. `src/character_engine/domain/anatomy/__init__.py` - Add new module exports
2. `src/character_engine/validation/result.py` - Extend if needed for anatomical validation
3. `.gitignore` - Add temporary/experimental build directories

### No Modifications To
- `src/character_engine/data/anatomy/human_adult_206.json` - PROTECTED
- `src/character_engine/domain/anatomy/osteology/` - PRESERVE EXISTING FUNCTIONALITY
- `src/character_engine/infrastructure/blender/` - PRESERVE EXISTING FUNCTIONALITY
- `src/character_engine/loader/` - PRESERVE EXISTING FUNCTIONALITY
- `src/character_engine/serialization/` - PRESERVE EXISTING FUNCTIONALITY
- Existing test files - PRESERVE EXISTING FUNCTIONALITY

---

## Files Explicitly Protected from Modification

### PROTECTED FILES (DO NOT MODIFY)
1. `src/character_engine/data/anatomy/human_adult_206.json` - Canonical anatomy (A0.2 baseline)
2. `src/character_engine/data/anatomy/human_adult_206_backup.json` - Backup
3. `src/character_engine/domain/anatomy/osteology/bone.py` - Functional bone model
4. `src/character_engine/domain/anatomy/osteology/builder.py` - Functional skeleton builder
5. `src/character_engine/domain/anatomy/osteology/skeleton.py` - Functional skeleton model
6. `src/character_engine/domain/anatomy/osteology/validator.py` - Functional validator
7. `src/character_engine/infrastructure/blender/importer.py` - Functional importer
8. `src/character_engine/infrastructure/blender/state_auditor.py` - Functional auditor
9. `src/character_engine/loader/json_loader.py` - Functional loader
10. `src/character_engine/serialization/skeleton_serializer.py` - Functional serializer
11. All existing test files in `tests/unit/` and `tests/integration/`
12. All existing scripts in `scripts/`

### EMPTY/STUB FILES (LEAVE AS-IS FOR NOW)
1. `src/character_engine/anatomy/__init__.py` - Empty
2. `src/character_engine/anatomy/proportions.py` - Empty
3. `src/character_engine/anatomy/human.py` - Stub
4. `src/character_engine/anatomy/female.py` - Stub
5. `src/character_engine/anatomy/male.py` - Stub
6. `src/character_engine/anatomy/measurements.py` - Stub
7. `src/character_engine/skeleton/builder.py` - Empty (0 bytes)

---

## Integration Strategy

### Reconstruction API Integration Point
The new reconstruction layer will integrate with the existing pipeline at the DTO level:

```
Reference Data
    ↓
Parameter Set
    ↓
Landmark Generator
    ↓
Joint Center Generator
    ↓
Bone Geometry Generator
    ↓
[INTEGRATION POINT]
    ↓
Existing SkeletonBuilder (preserved)
    ↓
Existing Skeleton (preserved)
    ↓
Existing Validation (preserved)
    ↓
Existing Serialization (preserved)
    ↓
Existing Blender Import (preserved)
```

### Data Flow Integration
The reconstruction layer will generate bone specifications that are compatible with the existing SkeletonBuilder input format. This ensures seamless integration without modifying existing components.

---

## Risk Assessment

### LOW RISKS
- **Architecture conflicts:** None identified
- **Module duplication:** Resolved (no actual duplication)
- **Integration complexity:** Low (clear integration point defined)

### MEDIUM RISKS
- **Reference data availability:** Critical but can be marked as UNKNOWN/ASSUMED initially
- **Coordinate system definition:** Forward axis needs definition but can be resolved
- **Test coverage:** Extensive new tests required but approach is clear

### MITIGATION STRATEGIES
- **Reference data:** Use UNKNOWN/ASSUMED status until real data acquired
- **Coordinate system:** Define based on existing Z-up convention with clear documentation
- **Test coverage:** Implement incrementally with each component

---

## Success Criteria

### A0.4 Complete When:
- [ ] All planned modules created and functional
- [ ] All coordinate system tests pass
- [ ] All reference data model tests pass
- [ ] All parameter model tests pass
- [ ] All landmark model tests pass
- [ ] All proportion engine tests pass
- [ ] All joint center model tests pass
- [ ] All specialized anatomical model tests pass
- [ ] Anatomical validation framework functional
- [ ] PHASE 1 anatomical tests detect known A0.2 failures
- [ ] Determinism test passes
- [ ] Existing structural tests still pass
- [ ] No bpy imports in core anatomical calculation layers
- [ ] All documentation complete
- [ ] A0.4 report generated

---

## Next Steps

**Immediate Action:** Begin A04-01 (Coordinate System Contract) as specified in the A0.4 requirements.

**Sequence:** Follow the implementation plan phases sequentially, testing at each checkpoint.

**Validation:** Run existing tests after each phase to ensure no regression.

**Documentation:** Update this baseline as decisions evolve during implementation.

---

**BASELINE STATUS:** COMPLETE  
**READY FOR IMPLEMENTATION:** YES  
**BLOCKING ISSUES:** NONE  
**RECOMMENDATION:** PROCEED WITH A04-01
