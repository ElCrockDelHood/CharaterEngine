# Anatomy test fixtures — frozen legacy baselines

These fixtures are **frozen on purpose**. They encode known-bad historical states so that the
validators keep proving they detect them. Do not "fix", migrate, rename or move them.

| Fixture | What it is | Why it stays |
|---------|------------|--------------|
| `fixtures.py` → `create_a02_baseline_parameter_set()`, `run_a02_baseline_validation()` | A02 baseline with a total height of **3.08 m** (and the values derived from it) | Known-bad regression fixture: the validation tests must report the 3.08 m failure (Decision 15). |
| `src/character_engine/data/anatomy/human_adult_206_backup.json` | Pre-A07 skeleton in the old **Y-up** frame (top of skull at y ≈ 1.9 m) with the old left/right labels — not the 3.08 m placeholder | Frozen audit fixture; never migrated by `mirror_canonical_x.py`, `rebuild_hand_layout.py` or `fix_forearm_layout.py` (Decisions 15, 33). Its SHA-256 is pinned by `tests/anatomy/test_contract_fingerprint.py` (Decision 52). |

The current canonical skeleton is `human_adult_206.json` (1.80 m, left = +X); see
`docs/reorientation/DECISION_LOG.md` Decisions 15, 33, 35, 36. `create_synthetic_valid_parameter_set()`
and `create_minimal_landmark_set()` in `fixtures.py` are synthetic valid inputs, not legacy data.
