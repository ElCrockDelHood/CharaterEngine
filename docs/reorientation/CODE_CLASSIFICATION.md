# CHARACTER ENGINE - CODE CLASSIFICATION

**Document**: CODE_CLASSIFICATION.md  
**Date**: 2026-09-02  
**Status**: POST-REORIENTATION AUDIT  
**Purpose**: Classification of all existing code components

---

## CLASSIFICATION CATEGORIES

Each component is classified as:
- **KEEP**: Keep as-is, production-ready
- **REFACTOR**: Keep but needs refactoring
- **MOVE**: Move to different location
- **MERGE**: Merge with another component
- **DEPRECATE**: Mark as deprecated, remove later
- **DELETE**: Safe to delete immediately
- **REPLACE**: Replace with new implementation
- **UNKNOWN**: Status unclear, needs investigation

---

## 1. DOMAIN LAYER CLASSIFICATION

### 1.1 Anatomy Domain

#### KEEP (Production-Ready)
- `domain/anatomy/coordinate_system.py` - KEEP (well-implemented, 45 tests)
- `domain/anatomy/landmarks/landmark.py` - KEEP (well-implemented, 24 tests)
- `domain/anatomy/joints/joint_center.py` - KEEP (well-implemented, 21 tests)
- `domain/anatomy/parameters/parameter.py` - KEEP (well-implemented, 27 tests)
- `domain/anatomy/proportions/calculator.py` - KEEP (well-implemented, 26 tests)
- `domain/anatomy/reference/source.py` - KEEP (A0.5 implemented, well-designed)
- `domain/anatomy/reference/eligibility.py` - KEEP (A0.5 implemented, 20 tests)
- `domain/anatomy/reference/reference_manager.py` - REFACTOR (needs integration with source.py)
- `domain/anatomy/validation/anatomical_validator.py` - KEEP (well-implemented, 27 tests)
- `domain/anatomy/validation/result.py` - KEEP (well-implemented)
- `domain/anatomy/osteology/bone.py` - KEEP (well-implemented, 27 tests)
- `domain/anatomy/osteology/skeleton.py` - KEEP (well-implemented)
- `domain/anatomy/osteology/builder.py` - KEEP (well-implemented)
- `domain/anatomy/osteology/validator.py` - KEEP (well-implemented)
- `domain/anatomy/osteology/constants.py` - KEEP (well-implemented)
- `domain/anatomy/osteology/transform.py` - KEEP (well-implemented)
- `domain/anatomy/osteology/exceptions.py` - KEEP (well-implemented)

#### KEEP (Designed, Not Populated)
- `domain/anatomy/hands/model.py` - KEEP (structure good, needs real data)
- `domain/anatomy/feet/model.py` - KEEP (structure good, needs real data)
- `domain/anatomy/spine/model.py` - KEEP (structure good, needs real data)

#### REFACTOR (Needs Integration)
- `domain/anatomy/reconstruction/parameter_normalizer.py` - REFACTOR (needs A0.5 provenance integration)
- `domain/anatomy/reconstruction/proportion_calculator.py` - REFACTOR (needs reference data)
- `domain/anatomy/reconstruction/landmark_positioner.py` - REFACTOR (needs real reference data)
- `domain/anatomy/reconstruction/bone_generator.py` - REFACTOR (needs real reference data)
- `domain/anatomy/reconstruction/pipeline.py` - REFACTOR (needs provenance enforcement)
- `domain/anatomy/reconstruction/integration.py` - REFACTOR (needs architecture update)

#### KEEP (Templates)
- `domain/anatomy/templates/human.py` - KEEP (template system)

---

## 2. INFRASTRUCTURE LAYER CLASSIFICATION

### 2.1 Blender Infrastructure

#### KEEP (Production-Ready)
- `infrastructure/blender/importer.py` - KEEP (skeleton import works)
- `infrastructure/blender/state_auditor.py` - KEEP (comprehensive validation)
- `infrastructure/blender/visual_inspector.py` - KEEP (mesh inspection works)
- `infrastructure/blender/inspector.py` - KEEP (general inspector)

#### KEEP (Scene - Empty Files, Keep Structure)
- `blender/scene/builder.py` - KEEP (structure exists, needs implementation)
- `blender/scene/camera.py` - KEEP (structure exists, needs implementation)
- `blender/scene/cleanup.py` - KEEP (structure exists, needs implementation)
- `blender/scene/collections.py` - KEEP (structure exists, needs implementation)
- `blender/scene/lighting.py` - KEEP (structure exists, needs implementation)
- `blender/scene/save.py` - KEEP (structure exists, needs implementation)
- `blender/scene/units.py` - KEEP (structure exists, needs implementation)
- `blender/scene/validator.py` - KEEP (structure exists, needs implementation)

---

## 3. CORE LAYER CLASSIFICATION

### 3.1 Core Components

#### EMPTY (Critical - Needs Implementation)
- `core/application.py` - REPLACE (0 bytes, needs backend application)
- `core/events.py` - REPLACE (0 bytes, needs event system)

#### KEEP (Implemented)
- `core/bootstrap.py` - KEEP (exists)
- `core/context.py` - KEEP (exists)
- `core/pipeline.py` - KEEP (exists)
- `core/runtime.py` - KEEP (exists)

---

## 4. DATA LAYER CLASSIFICATION

### 4.1 Canonical Data

#### KEEP (With Issues)
- `data/anatomy/human_adult_206.json` - KEEP (structurally valid, anatomically incomplete)
- `data/anatomy/human_adult_206_backup.json` - KEEP (backup)

#### KEEP (Reference Data)
- `data/anatomy/references/source_registry.json` - KEEP (registry structure good, needs real data)
- `data/anatomy/references/anthropometry.json` - KEEP (needs real data)
- `data/anatomy/references/biomechanics.json` - KEEP (needs real data)

---

## 5. DEPRECATED LAYER CLASSIFICATION

### 5.1 Old Anatomy Directory

#### DEPRECATE (Pre-Domain Architecture)
- `anatomy/__init__.py` - DEPRECATE (old anatomy package)
- `anatomy/female.py` - DEPRECATE (old model)
- `anatomy/human.py` - DEPRECATE (old model)
- `anatomy/male.py` - DEPRECATE (old model)
- `anatomy/measurements.py` - DEPRECATE (old parameter system)
- `anatomy/proportions.py` - DEPRECATE (old proportion system)

---

## 6. DUPLICATED LAYER CLASSIFICATION

### 6.1 Duplicated Skeleton Implementations

#### DEPRECATE (Consolidate to Domain)
- `skeleton/` - DEPRECATE (use domain/anatomy/osteology/)
- `anatomy/` - DEPRECATE (use domain/anatomy/)

---

## 7. EMPTY LAYER CLASSIFICATION

### 7.1 Empty Files (26 files)

#### REPLACE (Needs Implementation)
- `types/mesh.py` - REPLACE (0 bytes, needs mesh domain model)
- `export/blend.py` - REPLACE (0 bytes, needs export implementation)
- `export/fbx.py` - REPLACE (0 bytes, needs export implementation)
- `export/gltf.py` - REPLACE (0 bytes, needs export implementation)
- `export/usd.py` - REPLACE (0 bytes, needs export implementation)
- `rig/builder.py` - REPLACE (0 bytes, needs rigging implementation)
- `rig/constraints.py` - REPLACE (0 bytes, needs rigging implementation)
- `rig/controls.py` - REPLACE (0 bytes, needs rigging implementation)
- `rig/drivers.py` - REPLACE (0 bytes, needs rigging implementation)
- `simulation/muscles.py` - REPLACE (0 bytes, needs simulation implementation)
- `simulation/physics.py` - REPLACE (0 bytes, needs simulation implementation)
- `simulation/skin.py` - REPLACE (0 bytes, needs simulation implementation)
- `simulation/cloth.py` - REPLACE (0 bytes, needs simulation implementation)
- `simulation/fat.py` - REPLACE (0 bytes, needs simulation implementation)

---

## 8. MATH LAYER CLASSIFICATION

### 8.1 Math Infrastructure

#### KEEP (Production-Ready)
- `math/algebra/vector3.py` - KEEP (well-implemented)
- `math/algebra/quaternion.py` - KEEP (well-implemented)
- `math/algebra/matrix4.py` - KEEP (well-implemented)

---

## 9. SCHEMA LAYER CLASSIFICATION

### 9.1 Schema

#### KEEP (Production-Ready)
- `schema/skeleton_v1.schema.json` - KEEP (well-implemented, pattern for asset package)

---

## 10. DTO LAYER CLASSIFICATION

### 10.1 Data Transfer Objects

#### KEEP (Implemented)
- `dto/skeleton_dto.py` - KEEP (skeleton DTO works)

---

## 11. SERIALIZATION LAYER CLASSIFICATION

### 11.1 Serialization

#### KEEP (Implemented)
- `serialization/skeleton_serializer.py` - KEEP (skeleton serialization works)

---

## 12. LOADER LAYER CLASSIFICATION

### 12.1 Loader

#### KEEP (Implemented)
- `loader/json_loader.py` - KEEP (JSON loader works)

---

## 13. EXPORT LAYER CLASSIFICATION

### 13.1 Export

#### REPLACE (All Empty)
- `export/blend.py` - REPLACE (0 bytes)
- `export/fbx.py` - REPLACE (0 bytes)
- `export/gltf.py` - REPLACE (0 bytes)
- `export/usd.py` - REPLACE (0 bytes)

---

## 14. VALIDATION LAYER CLASSIFICATION

### 14.1 Validation

#### KEEP (Implemented)
- `validation/` - KEEP (validation system exists)

---

## 15. TEST LAYER CLASSIFICATION

### 15.1 Tests

#### KEEP (All Passing)
- `tests/anatomy/` - KEEP (262 tests, all passing)
- `tests/integration/` - KEEP (12 tests, all passing)
- `tests/test_export.py` - KEEP (exists)
- `tests/test_rig.py` - KEEP (exists)
- `tests/test_scene.py` - KEEP (exists)
- `tests/unit/test_osteology.py` - KEEP (exists)
- `tests/units/test_skeleton.py` - KEEP (exists)

---

## 16. SUMMARY

### 16.1 Classification Summary

**KEEP**: 47 components (production-ready or good structure)
**REFACTOR**: 6 components (needs integration/update)
**REPLACE**: 14 components (empty files, needs implementation)
**DEPRECATE**: 8 components (old/duplicated architecture)
**DELETE**: 0 components (safe to delete immediately)
**MERGE**: 0 components
**MOVE**: 0 components
**UNKNOWN**: 0 components

### 16.2 Critical Actions

**Immediate (P0-P1)**:
1. Implement backend components (REPLACE core/application.py, core/events.py)
2. Implement mesh domain model (REPLACE types/mesh.py)
3. Refactor reconstruction for A0.5 provenance integration
4. Acquire real reference data (keep structure, populate with real data)

**Short-term (P2-P3)**:
1. Implement export infrastructure (REPLACE export/*.py)
2. Implement rigging infrastructure (REPLACE rig/*.py)
3. Implement simulation infrastructure (REPLACE simulation/*.py)
4. Implement Blender scene components (implement blender/scene/*.py)

**Long-term (P4+)**:
1. Deprecate old anatomy directory
2. Consolidate duplicated skeleton implementations
3. Complete mesh generation pipeline
4. Complete musculoskeletal system