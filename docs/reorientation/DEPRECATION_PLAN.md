# CHARACTER ENGINE - DEPRECATION PLAN

**Document**: DEPRECATION_PLAN.md  
**Date**: 2026-09-02  
**Status**: POST-REORIENTATION AUDIT  
**Purpose**: Plan for deprecating obsolete and duplicated components

---

## 1. DEPRECATION PRINCIPLES

### 1.1 Deprecation Rules

**NEVER delete code without**:
1. Explaining why
2. Verifying it's not used
3. Documenting the deprecation
4. Providing migration path
5. Testing the deprecation

**Deprecation States**:
- **DEPRECATED**: Marked as deprecated, still functional
- **OBSOLETE**: No longer recommended, will be removed
- **REMOVED**: Deleted from codebase

**Deprecation Timeline**:
- Phase 1: Mark as DEPRECATED (immediate)
- Phase 2: Mark as OBSOLETE (after migration)
- Phase 3: REMOVE (after verification)

---

## 2. DEPRECATED COMPONENTS

### 2.1 Old Anatomy Directory

#### Component: `src/character_engine/anatomy/`

**Status**: DEPRECATED (Phase 1)

**Reason**: Pre-domain architecture, replaced by `domain/anatomy/`

**Components**:
- `anatomy/__init__.py`
- `anatomy/female.py`
- `anatomy/human.py`
- `anatomy/male.py`
- `anatomy/measurements.py`
- `anatomy/proportions.py`

**Migration Path**:
- Female/Male/Human models → `domain/anatomy/templates/human.py`
- Measurements → `domain/anatomy/parameters/parameter.py`
- Proportions → `domain/anatomy/proportions/calculator.py`

**Verification Required**:
- Check for imports in test files
- Check for imports in application code
- Verify no external dependencies

**Timeline**:
- Phase 1: Mark DEPRECATED (immediate)
- Phase 2: Mark OBSOLETE (after consolidation)
- Phase 3: REMOVE (after verification)

---

### 2.2 Duplicated Skeleton Implementations

#### Component: `src/character_engine/skeleton/`

**Status**: DEPRECATED (Phase 1)

**Reason**: Duplicated, canonical implementation in `domain/anatomy/osteology/`

**Migration Path**:
- All skeleton operations → `domain/anatomy/osteology/skeleton.py`

**Verification Required**:
- Check for imports in test files
- Check for imports in application code
- Verify test coverage for canonical implementation

**Timeline**:
- Phase 1: Mark DEPRECATED (immediate)
- Phase 2: Mark OBSOLETE (after consolidation)
- Phase 3: REMOVE (after verification)

---

### 2.3 Duplicated Parameter Systems

#### Component: `src/character_engine/anatomy/measurements.py`

**Status**: DEPRECATED (Phase 1)

**Reason**: Duplicated, canonical implementation in `domain/anatomy/parameters/`

**Migration Path**:
- All parameter operations → `domain/anatomy/parameters/parameter.py`

**Verification Required**:
- Check for imports in test files
- Check for imports in application code
- Verify canonical implementation has equivalent functionality

**Timeline**:
- Phase 1: Mark DEPRECATED (immediate)
- Phase 2: Mark OBSOLETE (after consolidation)
- Phase 3: REMOVE (after verification)

---

### 2.4 Duplicated Proportion Systems

#### Component: `src/character_engine/anatomy/proportions.py`

**Status**: DEPRECATED (Phase 1)

**Reason**: Duplicated, canonical implementation in `domain/anatomy/proportions/`

**Migration Path**:
- All proportion operations → `domain/anatomy/proportions/calculator.py`

**Verification Required**:
- Check for imports in test files
- Check for imports in application code
- Verify canonical implementation has equivalent functionality

**Timeline**:
- Phase 1: Mark DEPRECATED (immediate)
- Phase 2: Mark OBSOLETE (after consolidation)
- Phase 3: REMOVE (after verification)

---

## 3. DEPRECATION PROCESS

### 3.1 Deprecation Marking

**Action**: Add deprecation notice to all deprecated files

**Template**:
```python
"""
DEPRECATED - This module is deprecated and will be removed in a future version.

Migration: Use domain/anatomy/[target] instead
Deprecated: 2026-09-02
Deprecated by: MASTER_REORIENTATION_AUDIT
Migration guide: docs/reorientation/LEGACY_TO_TARGET_MAPPING.md
"""
```

**Implementation**:
1. Add deprecation notice to top of each deprecated file
2. Add `@deprecated` decorator to functions/classes if available
3. Update documentation
4. Add deprecation warnings at runtime

---

### 3.2 Deprecation Verification

**Step 1: Import Analysis**
```bash
# Find all imports of deprecated components
grep -r "from character_engine.anatomy" src/
grep -r "from character_engine.skeleton" src/
grep -r "from character_engine.anatomy.measurements" src/
grep -r "from character_engine.anatomy.proportions" src/
```

**Step 2: Test Analysis**
```bash
# Find all test imports
grep -r "from character_engine.anatomy" tests/
grep -r "from character_engine.skeleton" tests/
```

**Step 3: Update Imports**
- Replace deprecated imports with canonical imports
- Update test files
- Update documentation
- Update examples

**Step 4: Test Verification**
- Run all tests with deprecated imports
- Run all tests with canonical imports
- Verify test results are identical

---

### 3.3 Deprecation Removal

**Preconditions**:
1. All imports updated to canonical implementations
2. All tests pass with canonical implementations
3. Documentation updated
4. Migration guide published

**Removal Process**:
1. Remove deprecated files
2. Remove deprecated directory structures
3. Update imports in __init__.py files
4. Run full test suite
5. Verify no broken imports
6. Commit removal with clear message

---

## 4. DEPRECATION TIMELINE

### 4.1 Phase 1: Marking (Immediate)

**Actions**:
- Add deprecation notices to all deprecated files
- Add deprecation warnings at runtime
- Update documentation
- Publish migration guide

**Components**:
- `src/character_engine/anatomy/` (entire directory)
- `src/character_engine/skeleton/` (entire directory)

**Timeline**: 1-2 days

---

### 4.2 Phase 2: Migration (Short-term)

**Actions**:
- Update all imports to canonical implementations
- Update all tests to use canonical implementations
- Verify test coverage
- Fix any broken functionality

**Timeline**: 3-5 days

---

### 4.3 Phase 3: Removal (After Verification)

**Actions**:
- Remove deprecated files
- Remove deprecated directory structures
- Update __init__.py files
- Run full test suite
- Verify no broken imports

**Timeline**: 1-2 days

---

## 5. RISK MITIGATION

### 5.1 Import Risks

**Risk**: Breaking imports in test files or application code

**Mitigation**:
- Comprehensive import analysis before removal
- Step-by-step import updates
- Test after each import update
- Keep deprecated files during migration

### 5.2 Functionality Risks

**Risk**: Canonical implementation missing functionality

**Mitigation**:
- Feature comparison between deprecated and canonical
- Add missing functionality to canonical before removal
- Comprehensive testing before removal

### 5.3 Test Risks

**Risk**: Tests fail after import updates

**Mitigation**:
- Run tests after each import update
- Fix broken tests immediately
- Ensure test coverage for canonical implementation

---

## 6. DEPRECATION LOG

### 6.1 Deprecation Log Template

**Entry Template**:
```markdown
## [Component Name]

**Date**: YYYY-MM-DD
**Deprecation Phase**: Phase 1
**Reason**: [Reason for deprecation]
**Migration Path**: [Canonical component]
**Status**: DEPRECATED / OBSOLETE / REMOVED
**Verification**: [Verification status]
**Removed Date**: YYYY-MM-DD (if removed)
```

### 6.2 Deprecation Log Entries

## src/character_engine/anatomy/

**Date**: 2026-09-02
**Deprecation Phase**: Phase 1
**Reason**: Pre-domain architecture, replaced by domain/anatomy/
**Migration Path**: domain/anatomy/
**Status**: DEPRECATED
**Verification**: PENDING
**Removed Date**: TBD

## src/character_engine/skeleton/

**Date**: 2026-09-02
**Deprecation Phase**: Phase 1
**Reason**: Duplicated, canonical in domain/anatomy/osteology/
**Migration Path**: domain/anatomy/osteology/
**Status**: DEPRECATED
**Verification**: PENDING
**Removed Date**: TBD

## src/character_engine/anatomy/measurements.py

**Date**: 2026-09-02
**Deprecation Phase**: Phase 1
**Reason**: Duplicated, canonical in domain/anatomy/parameters/
**Migration Path**: domain/anatomy/parameters/parameter.py
**Status**: DEPRECATED
**Verification**: PENDING
**Removed Date**: TBD

## src/character_engine/anatomy/proportions.py

**Date**: 2026-09-02
**Deprecation Phase**: Phase 1
**Reason**: Duplicated, canonical in domain/anatomy/proportions/
**Migration Path**: domain/anatomy/proportions/calculator.py
**Status**: DEPRECATED
**Verification**: PENDING
**Removed Date**: TBD

---

## 7. SUCCESS CRITERIA

### 7.1 Deprecation Success

**Phase 1 Success**:
- All deprecated components marked
- Deprecation notices added
- Migration guide published
- No breaking changes

**Phase 2 Success**:
- All imports updated to canonical implementations
- All tests pass with canonical implementations
- No broken functionality
- Documentation updated

**Phase 3 Success**:
- All deprecated files removed
- All deprecated directory structures removed
- Full test suite passes
- No broken imports
- Clean codebase

---

## 8. ROLLBACK PLAN

### 8.1 Rollback Triggers

**Rollback if**:
- Tests fail after import updates
- Canonical implementation missing critical functionality
- Breaking changes detected
- Timeline exceeds estimates significantly

### 8.2 Rollback Process

**Immediate Rollback**:
1. Revert import updates
2. Restore deprecated components
3. Re-run tests
4. Investigate failure
5. Fix issues
6. Resume deprecation

---

## 9. SUMMARY

### 9.1 Deprecation Summary

**Total Components to Deprecate**: 4 (directory-level)
**Total Files to Deprecate**: ~10
**Estimated Timeline**: 5-9 days
**Risk Level**: MEDIUM

### 9.2 Next Steps

1. Add deprecation notices (Phase 1)
2. Perform import analysis
3. Update imports (Phase 2)
4. Verify tests
5. Remove deprecated components (Phase 3)
6. Verify clean codebase