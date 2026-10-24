---
name: run-tests
description: Run and triage the Character Engine pytest suite (domain, export, backend) with the project venv. Use when the user asks to run tests, check failures, verify a fix, or before finishing any code change.
---

# Run Tests

## Quick start

```bash
# venv lives OUTSIDE the repo (see scripts/bootstrap.py); on Windows/Git Bash:
PY=../.ce-venv/Scripts/python.exe        # or .venv/bin/python on Linux/macOS
$PY scripts/test.py                      # full suite (~570 tests, ~40 s)
$PY scripts/test.py --domain             # anatomy + unit + integration + export
$PY scripts/test.py --backend            # C1–C6 backend (in-memory SQLite, ~15 s)
$PY -m pytest tests/backend/test_c6_authorization.py -q -x   # one file, stop on first failure
```

`tests/conftest.py` sets `CHARACTER_ENGINE_ENV=test` and `sys.path`; no `PYTHONPATH` needed.

## Triage workflow

1. Run the smallest failing scope with `-x -q --tb=short`.
2. Classify the failure:
   - **Contract test** (`tests/anatomy`, C-phase tests): the code is wrong, not the test.
     Read the matching `docs/audit/*` before changing the assertion.
   - **Environment**: `ModuleNotFoundError: character_engine` → venv not created or not
     using `$PY`; `No Python at ...` → run `python scripts/bootstrap.py --recreate`.
   - **Slow backend** (> 60 s): `CHARACTER_ENGINE_ENV` is not `test` (Argon2 production params).
3. Fix, add a regression test next to the failing one, re-run the scope, then the full suite.
4. Finish with `$PY scripts/lint.py` (ruff + `bpy` architecture guard).

## Expected baseline

`tests/anatomy + unit + integration` 282 · `tests/export` 23 · `tests/backend` 261 → **566 passed, 0 failed**.
If the count drops, tests were deleted or skipped — investigate before accepting.
