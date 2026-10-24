---
name: audit-phase-closure
description: Close or audit a project phase (A0x anatomy audits, C1-C6 backend phases) by reconciling code, tests and docs/audit contracts, and recording evidence. Use when the user asks to close a phase, write an audit, reconcile a contract, or check if an implementation matches its spec.
disable-model-invocation: true
---

# Audit / Phase Closure

The repo treats `docs/audit/` and `docs/reorientation/` as the source of truth. A phase is
closed only when code, tests and documents agree.

## Workflow

```
- [ ] 1. Read the contract: docs/audit/<PHASE>_*CONTRACT*.md or *_SPEC*.md
- [ ] 2. List every requirement ID (e.g. C6-01 … C6-NN) in a scratch table
- [ ] 3. For each ID find: implementing symbol (file:line) + test(s) asserting it
- [ ] 4. Run the phase tests; record counts (passed/failed/skipped)
- [ ] 5. Gaps → either implement + test, or mark OPEN with a reason (never silently drop)
- [ ] 6. Write docs/audit/<PHASE>_RECONCILIATION.md (template below)
- [ ] 7. Update docs/reorientation/PHASE_C_EVIDENCE.md (or the anatomy equivalent)
        and DECISION_LOG.md for any contract deviation
- [ ] 8. Update docs/19_Changelog.md
```

## Reconciliation template

```markdown
# <PHASE> — Reconciliation

**Date**: YYYY-MM-DD · **Tests**: N passed / 0 failed · **Status**: CLOSED | OPEN

| Req | Requirement | Implementation | Test | Status |
|-----|-------------|----------------|------|--------|
| C6-01 | Deterministic 7-step decision | backend/authorization/authorization_service.py:decide | test_c6_authorization.py::test_decision_order | ✅ |

## Deviations
- <ID>: what differs, why, decision reference

## Open items
- <ID>: reason, owner, follow-up
```

## Anatomy-specific checks

- Node counts 208/206, unique names, acyclic hierarchy, single root, Z-up frame.
- Every new number has a `ProvenanceState`; `UNKNOWN` is acceptable, invented is not.
- Regenerate reports only with the scripts already in `scripts/` (`acceptance_gate.py`);
  do not hand-edit `docs/audit/*.json`.
