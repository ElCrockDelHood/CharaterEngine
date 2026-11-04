# Audit index (A07 – A24)

One line per audit: what it decided or measured, and the decision that recorded it. Older audits (A01 – A06,
C1 – C6) are listed in `docs/reorientation/DECISION_LOG.md`. Spanish copies (`.es.md`) exist where noted.

| Audit | Topic | Decision | Status |
|-------|-------|----------|--------|
| A07 | Stature retarget to 1.80 m, Drillis & Contini joint heights | 15 | FINAL |
| A08 | Osteometry drives mesh extents, tissues, T-pose | 16 | FINAL |
| A09 | Mirror X (left = +X); material samples 1 and 2 (`.es.md`) | 33 | FINAL |
| A10 | Hand layout; body strike (`.es.md`) | 35 | FINAL (layout PLACEHOLDER proportions) |
| A11 | Radius lateral to ulna; hand re-anchor | 36 | FINAL (separation PLACEHOLDER) |
| A12 | Godot performance on the GT 740M | — | measured |
| A13 | Foot layout from sourced length and atlas topology | 54 | FINAL |
| A14 | Effective mass of a strike (`.es.md`) | 58 | opt-in, values reversible |
| A15 | Strike model, force-based fracture (`.es.md`) | 58 amendment | opt-in |
| A16 | Head kinematics, concussion, knockdown (`.es.md`) | 59 | opt-in |
| A17 | Per-move striker records (`.es.md`) | 60 | opt-in |
| — | Source verification of A14–A16 (`VERIFICACION_FUENTES_A14_A16.es.md`, 2026-10-31) | — | report |
| A18 | BodyParts3D bone mapping to the 206 canonical bones (199 / 206) | 62 | internal use |
| A19 | F2 femur fit in Blender 3.6 | 63 | measured, tolerances PENDING |
| A20 | F2 long bones L + R | 64 | measured, tolerances PENDING |
| A21 | Fibula lateral to the tibia | 65 | FINAL (offset PLACEHOLDER) |
| A22 | Whole skeleton vs BodyParts3D by regions | 66 | measured, tolerances PENDING |
| A23 | Hip joint centres 180.2 mm apart | 67 | FINAL (value ESTIMATE) |
| A24 | Shoulder girdle: shoulder centres 406.8 mm, clavicle SC → AC, scapula AC → AI | 68 | FINAL (values ESTIMATE; clavicle re-parent pending) |

Related proposals (`docs/architecture/`): `ASSET_FITTING_PROPOSAL.md` (F0 – F6), `FEMUR_ANCHOR_LANDMARKS_PROPOSAL.md`,
`PELVIS_LANDMARKS_PROPOSAL.md`, `PELVIS_HIP_CENTERS_PROPOSAL.md` (applied as A23), `SHOULDER_GIRDLE_PROPOSAL.md`
(applied as A24).
