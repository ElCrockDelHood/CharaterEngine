# Proposal A27 — vertebral heights: cervical spacing and the whole spine (NOT applied)

**Status:** PROPOSAL, measured in throw-away working copies (reverted; canonical data and fingerprints unchanged) ·
**Date:** 2026-11-05 · needs the owner's OK and a numbered Decision · Related: A22, A26 / Decision 71 (AP curve).

## Finding: it is not only the neck

Heights of the BodyParts3D vertebral bodies, mapped to the canonical stature (skin bottom…top → 0…1.80 m, ×1.0468;
one subject, ESTIMATE), against the canonical segments (mid-bone z, metres):

| Vertebra | BP3D | Canonical | Canonical − BP3D (mm) |
|----------|------|-----------|-----------------------|
| C1 | 1.623 | 1.549 | **−73** |
| C4 | 1.571 | 1.536 | −34 |
| C7 | 1.525 | 1.524 | −1 |
| T1 | 1.508 | 1.506 | −2 |
| T4 | 1.445 | 1.491 | +46 |
| T8 | 1.330 | 1.463 | **+133** |
| T12 | 1.210 | 1.374 | **+164** |
| L1 | 1.178 | 1.297 | +119 |
| L3 | 1.119 | 1.246 | +126 |
| L5 | 1.055 | 1.194 | **+139** |
| Sacrum | 1.019 | 1.084 | +64 |

- **Spans:** C1–C7 canonical 30 mm vs ~98 mm between body mids in BP3D; T1–T12 146 mm vs ~298 mm; L1–L5 130 mm vs
  ~123 mm. The canonical stubs are 4–5 mm tall from C1 to T7; real vertebrae are 15–50 mm.
- C7 and T1 already agree, so the shoulders are in the right place. The neck is too short *upwards* and the trunk is
  compressed *downwards*: everything from T4 to L5 sits 5–16 cm too high.
- **Discs** (BP3D, thickness along the minor axis, scaled): C 6.7–11.0, T 9.1–12.8, L 12.3–17.5 mm. The canonical
  skeleton has no disc nodes; in these variants the disc is simply the midpoint boundary between two stubs.

**Controls (ANSUR II, men 1.75–1.85 m, skin landmarks at 1.80 m):**

- Iliocristale 1.091 m: the iliac crest is at the L4 level by the usual palpation rule (qualitative). BP3D L4 is
  1.087 m ✓; canonical L4 is 1.220 m ✗.
- Suprasternale 1.476 m: BP3D 1.469, canonical 1.487 (both within ~10 mm).
- Cervicale (C7 spinous tip, skin) 1.557 m: BP3D's most posterior C7 vertex gives 1.514 and canonical C7 is 1.521.
  **Both are ~35–45 mm low.** That is the largest uncertainty at the neck base; it is not resolved here. C7 is kept.

**Sources:** Pró, *Anatomía Clínica* ch. 2 (qualitative only). A citable per-vertebra source exists and is free to
read online: Busscher I. et al. (2010), "Comparative anatomical dimensions of the complete human and porcine spine",
*Eur Spine J* 19:1104–1114, PMC2900026 (CT of 6 human spines, 16 dimensions per vertebra, including body height and
disc ratios). **Not downloaded and not read in full**: it awaits the owner's OK, and its licence must be read first. It
could replace the BP3D body heights or serve as a control.

## Variants (x unchanged; the y curve of Decision 71 kept)

| | A — cervical only | B — whole spine (recommended) |
|---|---|---|
| Moves | C1–C7 head z (C7 tail fixed) | C1–L5, sacrum, coccyx |
| Fixed | T1 and below; stature (skull unchanged, `FRONTAL` tail 1.80 m); shoulders; hips | T1 and above as in A; hips (`FEMUR.head` 0.954 m); stature; shoulders |
| Rule | Stub ends at the midpoints between BP3D body mids | Same; below T1 a shift fades in linearly to +23.3 mm at the sacrum, so BP3D's hip height (0.931) meets the canonical 0.954 |
| Neck | `neck_01` 30 → 107 mm; `head` pivot (C1 head) 1.552 → 1.628 m, still under `OCCIPITAL` 1.633 | same |
| Provenance | ESTIMATE (one subject); ±45 mm at the neck base (cervicale control) | ESTIMATE; L4 vs iliocristale within ~17 mm |

## Measured impact (working copy, reverted)

| Gate | A | B |
|------|---|---|
| Gameplay table | in sync | in sync |
| Godot | 60/60, replays identical | 60/60, replays identical |
| Blender | 40/40, IK rest 13.6 mm, T-pose OK | 40/40, IK rest 13.6 mm, T-pose OK |
| Clips | only `head` directions | `head`, `spine_02` and the arm-chain probes; timings unchanged; parity worst 0.0006° |
| pytest failures to resolve | fingerprint; `test_spine_curve` (asserts today's C1 z); `test_body_strike` neck (see below) | the same, plus `test_anatomy_proxies` (regenerate: latissimus attaches to the sacrum), `test_collision::test_default_body_is_unchanged` (thorax energy 120.81 vs 121.13 J, −0.27 %, over its 0.1 % tolerance) and `test_spine_is_midline_and_descends` (the trial did not lower the coccyx; **must move with the sacrum**) |
| A22 spine, centroid → segment median | 79.1 → 75.8 mm | 79.1 → **16.8 mm** (axis angle 24.2° → 28.8°) |

- `test_body_strike::…except_the_neck`: it documents that a strike at the neck used to land on the thorax block. With
  a real neck the strike lands on the **neck**. This is an improvement; the test's expectation would change.
- Variant B also changes the opt-in strike physics slightly (body capsules follow the spine); `strike_physics.json`
  must be regenerated and compared.
- `skeleton_serialized.json`, `human_game_v1_body.glb`, `souls_clips` regenerated; Decision + fingerprint.

## Recommendation

**Variant B**, by a deterministic script, with the coccyx lowered with the sacrum and each test above resolved. It
removes the largest remaining error of A22 (79 → 17 mm) without touching stature, hips, shoulders, gameplay or replays.
Variant A alone would leave T8–L5 up to 16 cm too high, and the ribs (next proposal) hang from those vertebrae.
