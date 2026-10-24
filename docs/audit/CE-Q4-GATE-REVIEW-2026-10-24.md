# CE-Q4 Gate Review (Fase E) — 2026-10-24

**Type:** read-only review (no code, data or commits) · **Reviewer:** Claude, on the owner's PC
**Repo state reviewed:** `main` 8884a19 (local, 2 commits ahead of `origin/main` 7f66647), clean tree
**Inputs:** R21 §3, §8, §9, §10; R13 §8.1; R10 §4.3–§7.3; DECISION_LOG §17, §20–§37; code in
`math/algebra/`, `domain/anatomy/osteology/transform.py`, `domain/rigging/`; test suite.
**Status vocabulary (dossier §0):** ESPECIFICADO · IMPLEMENTADO · REPORTADO COMO FUNCIONAL ·
VERIFICADO INDEPENDIENTEMENTE (re-run today by this review) · PENDIENTE · BLOQUEADO.

## 1. What CE-Q4 is (as documented)

No file defines CE-Q4's own scope. It appears only as the **exit gate of S2-D1** (quaternion /
transform / kinematics contracts CE-Q1…CE-Q3). Entry criteria used here:

* R21 §8 Phase 5: architecture review approved, all P0 and P1 items resolved, full test suite
  passing, test coverage adequate, documentation complete, human approval.
* R13 §8.1.2 (additional CE-Q4 blockers): S2-D1 closed; **integrator authorised** (requires
  executed convergence tests); frame convention resolved.

## 2. Evidence executed today by this review

| Check | Result |
|-------|--------|
| `pytest` full suite | **753 passed**, 0 failed |
| Coverage (math + transform + sockets) | quaternion 97 %, transform 94 %, sockets 90 %, vector3 94 %, matrix4 100 % — total 95 % |
| QI-003 probe | `Quaternion(1,2,3,4) * inverse()` = (1,0,0,0); `(2,0,0,0)⁻¹` = (0.5,0,0,0) |
| Q-008 probe | `Quaternion.zero().inverse()` → `DegenerateQuaternionError` |
| TI-004 / TC-005 probe (500 random uniform-scale TRS) | max ‖M·M⁻¹ − I‖ = 1.8e-15; max ‖compose − M₁M₂‖ = 1.1e-14 |
| TR-001 probe | non-uniform scale in `inverse()` → `NonUniformScaleError` |
| Q-010 probe | slerp t=0.25: d₁+d₂ = d₁₂ = 0.398675; nlerp(0.5) = π about X |
| Q-005 probe | q₀ = 90° Z, ω_world = (1,0,0): matches R_x·q₀ (0.0), not q₀·R_x (0.70) |
| R10 convergence, case 1 (fixed axis Z, ω = π/2, T = 1 s) | E_ang = 3.2e-3, 8.1e-4, 2.0e-4, 5.0e-5 for dt = 0.1…0.0125; **ratio ≈ 4.0 (order 2)**; E_norm ≤ 1.1e-16 |
| Convergence, case 2 (variable axis ω(t) = (sin t, cos t, 0.5), ref dt = 1e-5) | E_ang = 4.35e-2 … 5.43e-3; **ratio 2.00 (order 1)** |
| Git | clean; `origin/main` = 7f66647; local 8884a19 (+2: CINE-GR-001 step 1) |

## 3. Blocker-by-blocker (R21 §9 + R13 §8.1.2 + R21 §10)

| ID | Item | Spec | Impl. | Evidence | Status (this review) |
|----|------|------|-------|----------|----------------------|
| RG-001 | Repository integrity (5 815 staged files) | R20-B | 028c803 (venv removed, work consolidated), pushed | old copy/backup verified file-by-file against `origin/main` before deletion; tree clean | **VERIFICADO INDEPENDIENTEMENTE** — owner acceptance PENDIENTE |
| RG-002 | Unauthorised R19 production edits | R19 scope gate | committed in 028c803, then superseded by D-01…D-08 commits | same files now covered by today's tests | **VERIFICADO** (superseded) — owner acceptance PENDIENTE |
| QI-003 | `Quaternion.inverse()` ÷‖q‖ | Decision 21 | 31a8271 | tests + probe | **VERIFICADO INDEPENDIENTEMENTE** |
| QI-004 / Q-008 / Q-007 | zero quaternion, tolerances | Decision 22 | 0861ac5 | tests + probe | **VERIFICADO INDEPENDIENTEMENTE** |
| TI-004 / TI-006 / TI-007 | `Transform.inverse()` | Decisions 23, 25 | 35c4a4f | seeded tests + 500-case probe | **VERIFICADO INDEPENDIENTEMENTE** (uniform scale ⇒ always representable) |
| TC-003 / TC-004 / TC-005 / TC-006 | `compose()` exactness, shear | Decisions 24, 25 | 35c4a4f | idem | **VERIFICADO INDEPENDIENTEMENTE** |
| TR-001 | TRS vs general matrix | Decision 25 | 35c4a4f | `NonUniformScaleError` probe | **VERIFICADO** (TRS uniform; Affine deferred until needed) |
| Q-005 / Q-006 | angular-velocity frame | Decision 26 | 982bc0e | test + probe | **VERIFICADO INDEPENDIENTEMENTE** |
| Q-009 / NP-002 / Q-010 | double cover, SLERP shortest path | Decisions 28, 34 | cd28727 | tests (fail on old code) + probe | **VERIFICADO INDEPENDIENTEMENTE** |
| NP-001 | radians in domain | Decision 27 | dacca51 (docs) | legacy degree params listed, not migrated | **IMPLEMENTADO (doc)**; code migration PENDIENTE (non-blocking, legacy interfaces) |
| NP-004 / NP-005 | dimensional validation / unit conversion | Decisions 30, 31 | 82995a1 (docs) | decision = defer / single `UnitConverter` path | **ESPECIFICADO** (decided) — R21 Phase 3 asks "defined and approved": satisfied as a recorded owner decision |
| NP-003 / NP-006 | Point3, semantic types | Decisions 29, 32 | — | deferred | **ESPECIFICADO (diferido)** |
| RG-003 | test evidence for corrections | — | today's tests | 753 passed, 95 % coverage of the math | **VERIFICADO INDEPENDIENTEMENTE** |
| R13 "Integrator authorised" (R10 #10) | executed convergence tests | R10 §4.3–4.4 (designed) | **not in the suite** | executed in memory today (§2) | **PENDIENTE** — see finding F-1 |
| R10 #11 Tolerance values | measured via convergence | R10 | — | measured today (§2), not recorded | **PENDIENTE** (record + test) |
| R10 #9 Distance metric naming | `geodesic_distance` doc | R10 | — | docstring says "geodesic on S³" but returns 2·acos‖q₁·q₂‖ (rotation angle on SO(3)) | **PENDIENTE** (P2, doc only) |
| Phase 4 "engine interoperability verified" | Blender / UPBGE / Godot | Decision 20 | addon + runtimes | Blender 3.6 24/24, Blender 4.2 20/20, Godot 4.7.2 21/21 today; **UPBGE 0.50 suite last run 2026-09-29 on another machine** | Blender/Godot **VERIFICADO**; UPBGE **REPORTADO COMO FUNCIONAL** only |
| RG-004 | architecture review approval | R21 Phase 4 | this document | — | **PENDIENTE** (owner) |
| RG-005 | CE-Q4 release | R21 Phase 5 | — | — | **BLOQUEADO** at review time → **UNBLOCKED 2026-10-24** (owner, Decision 41; see §6) |

## 4. Findings

* **F-1 (new, CONFIRMED by execution):** R10's acceptance criterion for convergence case 1
  ("|r_angular − 2| < 0.1", first order) is **wrong for a fixed axis**: explicit Euler + renormalisation
  on a constant-axis rotation only shortens the step angle (2·atan(ω·dt/2) instead of ω·dt), an O(dt³)
  local error, so the global error is **second order** (measured ratio 3.99–4.00). With a variable axis
  the method is first order as expected (ratio 2.00). The integrator is correct; the R10 criterion must
  be corrected (case 1: order ≥ 1, observed 2; case 2: |r − 2| < 0.1) before writing the tests.
* **F-2:** the convergence tests designed in R10 were never added to the suite; today's measurement is
  evidence but not a regression guard.
* **F-3:** `integrate_quaternion_angular_velocity` sign-continuity branch (quaternion.py:505) is never
  reached by the tests (expected: without canonicalisation consecutive Euler steps stay in one
  hemisphere). Harmless guard; documented, not a defect.
* **F-4:** `geodesic_distance` naming/docstring (R10 #9) still mislabels the SO(3) rotation angle as the
  S³ geodesic.
* **F-5:** UPBGE 0.50 interoperability has no evidence on this machine (needs a window; the owner can
  run `python scripts/engine_tests.py upbge`).

## 5. Proposed verdict

**CE-Q4: NOT YET UNBLOCKED — conditionally unblockable.** All P0 mathematical and repository blockers of
R21 §9 are resolved and independently verified. CE-Q4 can be unblocked once these minimal items close:

1. **Owner acceptance** of RG-001 / RG-002 (repository consolidated in 028c803; copies verified) and of
   this review (RG-004).
2. **Integrator authorisation (R13 / R10 #10–#11):** add the two convergence tests to the suite with the
   corrected criterion (case 1: order ≥ 1, observed 2; case 2: |r − 2| < 0.1; E_norm < 1e-12), record
   the measured tolerances in DECISION_LOG; owner approves the R10 criterion correction (F-1).
3. **UPBGE 0.50 suite** run once on this PC (UI mode) to verify the Phase 4 interoperability criterion,
   or an explicit owner waiver.

Non-blocking follow-ups: F-4 docstring; NP-001 legacy degree parameters; F-3 branch coverage.

**Estimated size:** item 2 is one test file + a DECISION_LOG entry (no production code); item 3 is a
run, not a change.

## 6. Status update — 2026-10-24 (after owner decision)

| Item | Status |
|------|--------|
| Verdict of this review | **APPROVED by the owner** (RG-004) |
| RG-001 / RG-002 | **ACCEPTED by the owner** |
| Integrator authorisation (R13; R10 #10–#11) + F-1 | **DONE**: Decision 38 corrects the R10 criterion; `tests/math/test_quaternion_convergence.py` (commit 4dfa99c) — case 1 order ≥ 1 (observed 2.0), norm error < 1e-12; case 2 \|r − 2\| < 0.1; measured tolerances recorded. pytest 755 passed, ruff and architecture guard clean |
| UPBGE 0.50 suite (Phase 4 interoperability) | Run by the owner on this PC: **26/27 PASS** (UPBGE 0.50 / Blender 5.0.1, Python 3.11.13). Only failure: blenderplayer autoplay smoke — NVIDIA 388.73 cannot compile UPBGE EEVEE shaders (C1317), crash 0xC0000005, reproduced with the pre-change `.blend` and without CE code: **environmental**. **DISPENSED by the owner** (Decision 39). Combat inside UPBGE and CINE-GR-001 checks verified |
| F-3, F-4, NP-001 legacy degrees | open, non-blocking |
| Runtime gating (Decision 40) | **Godot 4 is the only runtime that gates CE-Q4** and later phases: Godot 4.7.2 suite 21/21 (headless). UPBGE is OPTIONAL and non-blocking (code and tests kept; 26/27 informative). Follow-up: verify Godot windowed play on the GT 740M (Compatibility renderer already configured) |
| **RG-005 (CE-Q4)** | **UNBLOCKED — explicit owner approval, 2026-10-24 (Decision 41).** Conditions: Godot gate 21/21 (Decision 40), UPBGE optional, blenderplayer waived (Decision 39), integrator convergence (Decision 38), suite green. |
