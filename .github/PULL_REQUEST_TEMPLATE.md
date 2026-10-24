## Summary

<!-- What changes and why. Link the phase/spec (e.g. C6, docs/audit/...). -->

## Checklist

- [ ] `python scripts/test.py` passes locally
- [ ] `python scripts/lint.py` passes (ruff + no `bpy` outside `infrastructure/` / `runtime/`)
- [ ] No anatomical/historical value was invented: new numbers carry provenance (`PROVEN`/`DERIVED`) or are marked `UNKNOWN`/`PLACEHOLDER`
- [ ] Coordinate system documented for any new geometry (canonical = Z-up, -Y forward, metres)
- [ ] Canonical data (`src/character_engine/data/anatomy/*.json`) unchanged, or the change is justified in `docs/`
- [ ] Evidence/decision recorded in `docs/` when the change closes a phase or alters a contract
