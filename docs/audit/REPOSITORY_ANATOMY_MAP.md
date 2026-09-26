# Repository Anatomy Map

**Discovery Sprint A0.1**  
**Date:** 2026-08-12  
**Status:** DISCOVERY ONLY - NO MODIFICATIONS

---

## Project root

**Path:** `C:\DEV\Proyectos\CharacterEngine`

**Main directories:**
- `.ai/` - AI agent configuration and prompts
- `.engine/` - Engine rules and architecture documentation
- `.github/` - GitHub workflow templates
- `assets/` - Project assets
- `builds/` - Build outputs and exports
- `cache/` - Temporary cache
- `config/` - Configuration files
- `docs/` - Documentation
- `logs/` - Log files
- `references/` - Reference materials
- `scripts/` - Utility scripts
- `src/` - Source code
- `temp/` - Temporary files
- `tests/` - Test suite

---

## Relevant directories

### Anatomy-related source structure
```
src/
├── character_engine/
│   ├── data/
│   │   └── anatomy/
│   │       ├── human_adult_206.json          # Canonical anatomy definition
│   │       └── human_adult_206_backup.json   # Backup of canonical anatomy
│   ├── domain/
│   │   └── anatomy/
│   │       ├── osteology/
│   │       │   ├── bone.py                  # Bone domain model
│   │       │   ├── builder.py               # Skeleton builder
│   │       │   ├── constants.py             # Osteology constants
│   │       │   ├── exceptions.py            # Domain exceptions
│   │       │   ├── skeleton.py              # Skeleton domain model
│   │       │   ├── validator.py             # Skeleton validator
│   │       │   └── __init__.py
│   │       └── templates/
│   │           ├── human.py                 # Human template loader
│   │           └── __init__.py
│   ├── dto/
│   │   ├── skeleton_dto.py                  # Skeleton data transfer object
│   │   └── __init__.py
│   ├── infrastructure/
│   │   └── blender/
│   │       ├── importer.py                  # Blender importer
│   │       ├── inspector.py                 # Blender inspector
│   │       ├── state_auditor.py             # State auditor for validation
│   │       ├── visual_inspector.py          # Visual inspector
│   │       └── __init__.py
│   ├── loader/
│   │   ├── json_loader.py                   # JSON loader
│   │   └── __init__.py
│   ├── pipeline/
│   │   ├── pipeline.py                      # Main pipeline orchestrator
│   │   └── __init__.py
│   ├── schema/
│   │   ├── skeleton_schema_v1.py            # Schema definition
│   │   ├── skeleton_v1.schema.json          # JSON schema
│   │   └── __init__.py
│   ├── serialization/
│   │   ├── skeleton_serializer.py           # Skeleton serializer
│   │   └── __init__.py
│   ├── skeleton/
│   │   ├── bones.py                          # Bone utilities
│   │   ├── builder.py                       # Skeleton builder (alternative)
│   │   ├── constraints.py                   # Bone constraints
│   │   ├── hierarchy.py                     # Hierarchy utilities
│   │   └── validation.py                    # Validation utilities
│   ├── validation/
│   │   ├── result.py                        # Validation result
│   │   ├── validator.py                     # General validator
│   │   └── __init__.py
│   └── types/
│       ├── bone.py                          # Bone type
│       ├── joint.py                         # Joint type
│       ├── material.py                      # Material type
│       ├── mesh.py                          # Mesh type
│       ├── muscle.py                        # Muscle type
│       ├── scene.py                         # Scene type
│       └── transform.py                     # Transform type
```

### Generator structure
```
src/generators/
├── materials/
├── muscles/
├── physics/
├── rig/
├── scene/
├── skeleton/
└── skin/
```

---

## Anatomy files

### Canonical anatomy data
- **File:** `src/character_engine/data/anatomy/human_adult_206.json`
- **Purpose:** Canonical definition of human adult skeleton with 206 bones
- **Structure:** 
  - `bones`: Array of 206 bone definitions with canonical_name, name, parent, head, tail
  - `containers`: Array of 2 container bones (ROOT_SKELETON, CRANIUM)
- **Coordinate system:** Currently Z-up (feet at Z=0)
- **Backup:** `src/character_engine/data/anatomy/human_adult_206_backup.json`

### Bone organization
The 206 bones are organized into anatomical groups:
1. **Cranium and Face (22)** - Neurocranium (8) + Viscerocranium (14)
2. **Ear bones (6)** - Malleus, Incus, Stapes (left/right)
3. **Hyoid (1)**
4. **Vertebral column (26)** - Cervical (7) + Thoracic (12) + Lumbar (5) + Sacrum + Coccyx
5. **Thoracic cage (25)** - Sternum + 24 ribs
6. **Upper limbs (64)** - Shoulder girdle (4) + Arms/forearms (6) + Carpals (16) + Metacarpals (10) + Phalanges (28)
7. **Lower limbs + Pelvic girdle (62)** - Coxal (2) + Femur (2) + Patella (2) + Tibia/Fibula (4) + Tarsals (14) + Metatarsals (10) + Phalanges (28)

### Container bones
- **ROOT_SKELETON** - Root container for entire skeleton
- **CRANIUM** - Container for cranial bones, child of ROOT_SKELETON

---

## Blender files

### Validation blend file
- **File:** `builds/tests/validation.blend`
- **Size:** 1,129,760 bytes (~1.1 MB)
- **Last modified:** 2026-08-12 05:42:01
- **Purpose:** Output of headless Blender validation pipeline
- **Contents:** Armature named "Human Skeleton" with 208 bones (206 anatomical + 2 containers)

### No other .blend files found in repository

---

## Generation pipeline

### Current pipeline flow
```
human_adult_206.json (canonical)
    ↓
JsonLoader.load_to_dto()
    ↓
AssetDTO + SkeletonDTO
    ↓
SkeletonBuilder.build()
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

### Pipeline components

#### 1. JSON Loading
- **Script:** `src/character_engine/loader/json_loader.py`
- **Function:** Loads canonical JSON, validates schema, creates DTOs
- **Output:** AssetDTO + SkeletonDTO

#### 2. Skeleton Construction
- **Script:** `src/character_engine/domain/anatomy/osteology/builder.py`
- **Function:** Builds Skeleton domain model from DTO/spec
- **Output:** Skeleton domain object

#### 3. Validation
- **Script:** `src/character_engine/domain/anatomy/osteology/validator.py`
- **Function:** Validates skeleton integrity, hierarchy, geometry
- **Output:** ValidationResult

#### 4. Serialization
- **Script:** `src/character_engine/serialization/skeleton_serializer.py`
- **Function:** Serializes Skeleton back to JSON format
- **Output:** skeleton_serialized.json

#### 5. Blender Import
- **Script:** `src/character_engine/infrastructure/blender/importer.py`
- **Function:** Imports Skeleton to Blender as Armature
- **Method:** Two-step process (create all bones, then assign parents/geometry)
- **Output:** Blender Armature object

#### 6. State Validation
- **Script:** `src/character_engine/infrastructure/blender/state_auditor.py`
- **Function:** Validates Blender state matches Skeleton
- **Output:** Status report with diff analysis

### Pipeline orchestrator
- **Script:** `src/character_engine/pipeline/pipeline.py`
- **Function:** Coordinates all pipeline stages
- **Current scope:** JSON → Skeleton → Serialization (Blender import done separately)

---

## Validation pipeline

### Headless validation script
- **Script:** `scripts/validate_blender_headless.py`
- **Purpose:** Complete validation pipeline execution within Blender
- **Execution:** 
  1. Load JSON
  2. Build Skeleton
  3. Validate Skeleton
  4. Import to Blender
  5. Verify bone count (208)
  6. Save validation.blend
  7. Run State Auditor
  8. Report status

### Validation components
- **SkeletonValidator:** Domain-level validation (hierarchy, geometry, naming)
- **StateAuditor:** Blender state validation (bone count, parent relationships, geometry)
- **Acceptance Gate:** `scripts/acceptance_gate.py` - Final acceptance criteria

### Validation criteria
- Bone count: exactly 206 anatomical bones
- Total nodes: 208 (206 bones + 2 containers)
- Container presence: ROOT_SKELETON and CRANIUM must exist
- Hierarchy integrity: No cycles, valid parent references
- Geometry validity: Non-zero bone lengths (except containers)
- Round-trip preservation: JSON → Skeleton → JSON must preserve data

---

## Existing tests

### Unit tests
- **File:** `tests/unit/test_osteology.py`
- **Coverage:**
  - Bone creation, geometry, immutability, serialization
  - Skeleton operations (add, remove, hierarchy)
  - Builder functionality
  - HumanTemplate loading and validation
  - Architecture constraints (no bpy imports, no rigging dependencies)

### Integration tests
- **File:** `tests/integration/test_b8_contract.py`
- **Coverage:**
  - JSON loading and schema validation
  - DTO to Skeleton reconstruction
  - Asset data preservation
  - Bone count validation (206)

- **File:** `tests/integration/test_b8_pipeline.py`
- **Coverage:**
  - Pipeline execution (all stages)
  - Skeleton validation within pipeline
  - Round-trip preservation
  - Output file generation

- **File:** `tests/integration/test_b8_roundtrip.py`
- **Coverage:**
  - Complete round-trip (JSON → Skeleton → JSON → Skeleton)
  - Order preservation
  - Schema validation of serialized output
  - Exhaustive bone-by-bone comparison

### Additional test files (mostly empty)
- `tests/test_export.py`
- `tests/test_rig.py`
- `tests/test_scene.py`
- `tests/units/test_skeleton.py`

---

## Existing scripts

### Generation scripts
- **`scripts/generate_human_template.py`**
  - Generates canonical 206-bone JSON
  - Organizes bones by anatomical groups
  - Creates container bones
  - Outputs to `src/character_engine/data/anatomy/human_adult_206.json`

### Validation scripts
- **`scripts/validate_blender_headless.py`**
  - Complete headless validation pipeline
  - Generates validation.blend
  - Runs State Auditor
  - Reports PASS/FAIL status

- **`scripts/acceptance_gate.py`**
  - Final acceptance criteria validation
  - Checks bone counts, containers, hierarchy
  - Reports acceptance status

### Utility scripts
- **`transform_json_to_zup.py`**
  - Transforms human_adult_206.json from Y-up to Z-up
  - Ensures feet at Z=0
  - Creates backup before transformation

- **`validar_blender_headless.ps1`**
  - PowerShell wrapper for headless validation
  - Calls Blender with validation script

---

## 206/208 architecture references

### 206 (anatomical bones)
**Usage throughout codebase:**
- Canonical bone count in `human_adult_206.json`
- Expected bone count in tests (`test_b8_contract.py`, `test_b8_pipeline.py`)
- Validation criteria in `acceptance_gate.py`
- Generation target in `generate_human_template.py`
- Serialization verification in `test_b8_roundtrip.py`

**Significance:** Represents the standard adult human skeleton bone count

### 208 (total nodes)
**Usage throughout codebase:**
- Total node count = 206 bones + 2 containers
- Validation in `test_b8_contract.py`, `test_b8_pipeline.py`
- Blender import verification in `validate_blender_headless.py`
- Acceptance criteria in `acceptance_gate.py`

**Significance:** Complete hierarchy including container bones

### ROOT_SKELETON
**Usage:**
- Root container for entire skeleton hierarchy
- Parent of CERVICAL_1 and SACRUM
- Parent of CRANIUM container
- Referenced in `inspector.py` as container marker
- Validated in `acceptance_gate.py`

**Purpose:** Logical root for skeleton, separate from anatomical bones

### CRANIUM
**Usage:**
- Container for cranial bones (22 bones parent to CRANIUM)
- Child of ROOT_SKELETON
- Referenced in `inspector.py` as container marker
- Validated in `acceptance_gate.py`

**Purpose:** Logical grouping for skull bones

### Human Skeleton
**Usage:**
- Asset name in serialization
- Armature name in Blender
- Asset DTO name field
- Default name in SkeletonSerializer

**Purpose:** Human-readable name for the skeleton asset

---

## Current unknowns

### Architecture
- **Purpose of duplicate skeleton builders:** Both `domain/anatomy/osteology/builder.py` and `skeleton/builder.py` exist
- **Relationship between domain and skeleton modules:** Unclear separation of concerns
- **Intended use of `src/generators/` directories:** All currently empty
- **Coordinate system evolution:** Evidence of Y-up → Z-up transformation, but current standard unclear

### Blender integration
- **State Auditor completeness:** Full validation coverage unclear
- **Blender version requirements:** Current use of 3.6.23, but minimum version unknown
- **Headless limitations:** What Blender features are unavailable in headless mode
- **Import method rationale:** Two-step import process (create then assign) reasoning unclear

### Data model
- **Metadata schema:** Structure and purpose of bone/skeleton metadata undefined
- **Transform representation:** Current Vector3 implementation, quaternion/matrix support unclear
- **Joint types:** `types/joint.py` exists but relationship to bones undefined
- **Material/mesh integration:** Purpose in anatomy system unclear

### Testing
- **Empty test files:** `test_export.py`, `test_rig.py`, `test_scene.py`, `test_skeleton.py` are placeholders
- **Integration test coverage:** Missing tests for Blender import, State Auditor
- **Performance testing:** No benchmarks for large skeleton operations

### Pipeline
- **Error handling:** Pipeline failure modes and recovery strategies undefined
- **Incremental updates:** Support for partial skeleton updates unclear
- **Version management:** Schema evolution and backward compatibility strategy unclear

---

## Risks

### Architecture risks
- **Module duplication:** Multiple builder/validator implementations may lead to inconsistency
- **Unclear boundaries:** Domain vs. infrastructure separation may be violated
- **Empty generator modules:** May indicate incomplete architecture or abandoned features

### Data integrity risks
- **Coordinate system ambiguity:** Mixed Y-up/Z-up history may cause transformation errors
- **Single source of truth:** Only one canonical JSON, no versioning strategy
- **Manual generation:** `generate_human_template.py` is manual, error-prone for updates

### Integration risks
- **Blender version dependency:** Tight coupling to Blender 3.6.23 may break with updates
- **Headless limitations:** Unknown constraints may limit validation completeness
- **Round-trip failures:** Current tests may not catch all serialization edge cases

### Testing risks
- **Incomplete coverage:** Missing integration tests for Blender workflow
- **Empty test files:** May indicate untested critical paths
- **Validation gaps:** State Auditor may not catch all Blender state inconsistencies

### Process risks
- **No CI/CD evidence:** No automation for validation pipeline
- **Manual validation steps:** Headless validation requires manual execution
- **Backup strategy:** Only single backup file, no version history

---

## Recommended next audit

### Priority 1: Architecture clarification
1. **Module mapping:** Create clear responsibility matrix for all skeleton-related modules
2. **Builder consolidation:** Determine if duplicate builders should be merged or have distinct purposes
3. **Generator strategy:** Define purpose and implementation plan for empty generator modules

### Priority 2: Blender integration validation
1. **State Auditor coverage:** Audit validation completeness against all Skeleton invariants
2. **Headless capability test:** Document exact limitations of headless Blender mode
3. **Import process analysis:** Document rationale for two-step import and potential alternatives

### Priority 3: Data model standardization
1. **Coordinate system policy:** Define and enforce single coordinate system standard
2. **Metadata schema:** Define structure and validation rules for metadata fields
3. **Version strategy:** Implement schema versioning and backward compatibility plan

### Priority 4: Test coverage expansion
1. **Blender integration tests:** Add comprehensive tests for import and State Auditor
2. **Error path testing:** Add tests for failure modes and error handling
3. **Performance baseline:** Establish benchmarks for skeleton operations

### Priority 5: Pipeline automation
1. **CI/CD integration:** Automate validation pipeline execution
2. **Incremental update support:** Design and test partial skeleton update workflow
3. **Backup strategy:** Implement versioned backup system for canonical anatomy

---

**DISCOVERY STATUS:** COMPLETE  
**MODIFICATIONS:** NONE (as per sprint requirements)  
**NEXT ACTION:** Review findings and define Sprint A0.2 scope based on identified risks and priorities