# A27 — Vertebral heights from BodyParts3D (variant B, ESTIMATE)

**Date:** 2026-11-05 · **Status:** APPLIED (owner, card "B y luego tórax, con Busscher", 01:38) · **Decision 72** ·
**Proposal:** `docs/architecture/CERVICAL_SPACING_PROPOSAL.md` · **Script:** `scripts/fix_spine_heights.py` ·
**Report:** `A27_SPINE_HEIGHTS_REPORT.json` · **Tests:** `tests/unit/test_spine_heights.py`

## Change

C1–L5 and the sacrum take the z of their BodyParts3D namesake (body mid-height, stature map ×1.0468). Below T1 a shift
fades in up to +23.3 mm at the sacrum, so the BP3D hip height meets the canonical hip. Stub ends are midpoints, so the
chain is contiguous. The coccyx keeps its length and hangs from the new sacrum tail (DERIVED; absent from BP3D). x and
the y curve of Decision 71 are unchanged.

| Span / point | Before | After |
|--------------|--------|-------|
| C1–C7 | 30 mm | 112 mm |
| T1–T12 | 146 mm | 306 mm |
| C1 head (head pivot) | 1.552 m | 1.628 m (under `OCCIPITAL` 1.633 m) |
| L4 head | 1.233 m | 1.123 m |
| Sacrum tail / coccyx tail | 1.051 / 0.986 m | 1.010 / 0.977 m |

**Unchanged:** stature (`FRONTAL` tail 1.80 m), hips (`FEMUR.head` 0.954 m), shoulders (`HUMERUS.head` 1.4724 m),
`STERNUM`, ribs, skull. `SPINE_VERTEBRAL_HEIGHTS` is registered in `source_registry.json`. Fingerprints (LF):
`human_adult_206.json` → `57083dd0…2b8f`; `source_registry.json` → `e4786f68…4ca8`.

## Contrast with a published source (not a source of canonical values)

Busscher I. et al. (2010), "Comparative anatomical dimensions of the complete human and porcine spine", *Eur Spine J*
19: 1104–1114, PMC2900026. Read online and checked against the article. **Licence: CC BY-NC (non-commercial)**, so its
values are cited as a contrast, not copied as tables and not used as canonical data.

| Quantity | Busscher 2010 (human) | Canonical now | Note |
|----------|----------------------|---------------|------|
| Total C3 → L5 (central body heights + discs) | 569.4 ± 17.7 mm | 539.6 mm | was 362 mm; −5 %, 1.7 SD. The source's subjects are 175–192 cm (coordinator's reading; not re-verified), so a 1.80 m skeleton is expected to be a little shorter |
| Sagittal angle, cervical C3–C7 | 20.1 ± 10.0° | 24.5° (tangents, Decision 71) | within 1 SD; **different definitions**: end-plate angles vs centroid tangents |
| Thoracic T1–T12 | 34.5 ± 12.8° | 42.2° | within 1 SD; same caveat |
| Lumbar L1–L5 | 29.2 ± 7.6° | 24.3° | within 1 SD; same caveat |

The BodyParts3D *body* bounding heights used here run larger than Busscher's central heights (e.g. T6 body 34.8 mm vs
~18 mm): the anterior-40 % slice catches tilt and rim. Only mid-heights (spacing) enter the data, so this does not
reach the canonical z, but the vertebral *size* of a mesh must not be read from these stubs.

## Behaviour (measured before committing)

| Gate | Result |
|------|--------|
| Gameplay table | in sync |
| Godot | 60/60; **every replay identical** |
| Blender | 40/40; T-pose PASS; IK rest deviation 13.6 mm (unchanged); game rig IK rest error 0.0019 mm |
| Clips | re-exported and re-baked: directions of `spine_02`, `head` and the arm-chain probes change; timings unchanged; parity worst 0.0006° |
| `strike_physics.json` | regenerated and compared: only the commit stamp differs (not committed). The proposal's warning was excessive |
| Proxies | regenerated (latissimus dorsi attaches to the sacrum) |
| pytest / lint | 1246 passed; clean |

Tests changed, with the reason:

- `test_body_strike`: a strike at the neck now lands on the **neck**, not the thorax block. The exception was removed.
- `test_collision::test_default_body_is_unchanged`: tolerance 0.1 → 0.5 %. The thorax capsule's tilt reduces the normal
  energy by 0.27 % in the opt-in layered model.
- `test_spine_curve`: new C1 / L5 z.

## Re-measured A22

Spine centroid → segment median **79.1 → 16.8 mm**; extent / length 4.77 → 1.79; axis angle 24.2° → 28.8° (longer stubs
expose the per-vertebra tilt the stubs do not model). Other regions and the global RMS (29.7 mm) are unchanged.

## Open

The base of the neck stays uncertain: ANSUR II cervicale (skin) is 1.557 m, while BP3D and the canonical C7 sit about
35–45 mm lower. C7 was kept.
