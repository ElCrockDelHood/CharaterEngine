# Proposal A26b — spine curvature, thorax and skull (NOT applied)

**Status:** spine applied (Decisions 71, 72), thorax applied (Decision 73, `THORAX_PROPOSAL.md`); skull still PROPOSAL · **Date:** 2026-11-04 · needs the
owner's OK, a source per region and numbered Decisions · Related: A22 (spine 86 mm, thorax 122 mm, skull 52 mm
median centroid → segment distance), A24.

Measurements: BodyParts3D PART-OF meshes (internal use, Decision 62), raw frame (mm, Z-up, −Y front), scaled ×1.0269
(A22 global similarity after A24) where stated. ANSUR II men 1.75–1.85 m (n = 1814, public release) as control.
Every value below is **ESTIMATE** (one subject) unless it says otherwise.

## 1. Spine

**Canonical today:** 24 vertebrae are short vertical stubs on a straight line x = y = 0. Each is as tall as its own
segment (cervical 4.3 mm, thoracic 5–23 mm, lumbar 25.9 mm), with z from Drillis & Contini. There is no lordosis
and no kyphosis.

**BodyParts3D:** vertebral body centroid, taken as the anterior 40 % of each vertebra by y (rule ESTIMATE):

| Measure | Value |
|---------|-------|
| Cervical curve (tangent C2–C3 vs C6–C7) | 24.5° lordosis |
| Thoracic curve (tangent T1–T2 vs T11–T12) | 42.2° kyphosis |
| Lumbar curve (tangent L1–L2 vs L4–L5) | 24.3° lordosis |
| AP offset from the straight C1 → sacrum line (scaled) | C4 −4.7 mm, **T7 +29.8 mm** (posterior), **L3 −27.8 mm** (anterior) |
| C1 → sacrum body length (scaled) | 588 mm |
| Vertebral height (scaled, whole bone with processes) | C4 28.3, T6 61.3, L3 43.2 mm |

These are **not Cobb angles**. Cobb is measured between endplates (T4–T12 kyphosis, L1–S1 lordosis); the tangents
here use body centroids, so they are only a shape descriptor. Reference ranges for Cobb angles need a cited source
(radiographic normative study or the owner's *Anatomía Clínica*, Pró). **None is copied from memory.**

**ANSUR II control** (skin landmarks, men 1.75–1.85 m, as ratio × 1.80 m): cervicale (C7 spinous tip) 1556.7 mm
(0.8648 ± 0.0063 H), suprasternale 1476.3 mm, iliocristale 1090.9 mm, sitting height 937.1 mm. Canonical C7 body
1.5257–1.5214 m, i.e. 30 mm below the skin landmark, as expected for body vs spinous tip. The canonical vertical
spacing is therefore plausible; the problem is the missing curve.

**Variant A (recommended):** keep every vertebra's z (Drillis heights) and the sacrum / C1 positions; give each body
the BP3D AP offset (×1.0269) from the straight C1 → sacrum line, and orient each stub along the local tangent.
Lengths stay. Variant B: also take the vertebral heights from BP3D (moves z, larger change).

**Impact (to measure before applying, as A23 / A24):** CE-GAME-v1 `spine_01..03`, `neck`, `head` are derived from
vertebra joints, so the game rig, the baked clips and possibly the Godot replays change. Also affected: breathing,
block dummy torso segments and the spine IK / spline chain. Stop condition: any gameplay or replay change gets
reported before committing.

## 2. Thorax

| Bone | Canonical | BodyParts3D (raw; chord ×1.0269) |
|------|-----------|-----------------------------------|
| `STERNUM` | 46.8 mm vertical stub, y −0.0666 | 166 mm tall (manubrium + body + xiphoid), 170 mm scaled, y −214 … −131 |
| `RIB_01_L` | 37 mm horizontal stub at y = 0 | posterior head → anterior end chord 90 mm, descending |
| `RIB_03_L` | 43 mm | 166 mm |
| `RIB_06_L` | 53 mm | 214 mm, lateral reach 133 mm |
| `RIB_09_L` | 63 mm | 164 mm |
| `RIB_12_L` | 74 mm | 60 mm (floating rib) |

**Proposed (Variant A):** `STERNUM` head = incisura jugularis (kept), tail = xiphoid tip (length from BP3D ×1.0269,
ESTIMATE). Each rib head = its costovertebral joint, next to its thoracic vertebra (after the spine variant). Each rib
tail = its anterior end (costochondral junction): a chord, because the canonical bone is a straight segment. The
real curve would be a proxy mesh. Depends on the spine proposal (the rib heads hang on the vertebrae), so thorax goes
after spine.

## 3. Skull

Canonical skull bones are vertical stubs (e.g. `FRONTAL` 33 mm at z 1.77–1.80, `MANDIBLE` z 1.566–1.599 at y = 0).
The BP3D centroids sit lower and more anterior (frontal −137 mm y, mandible −133 mm y). Note: the canonical head
top z 1.80 m equals the stature, as it must. The skull matters little for gameplay (single `head` game bone).
**Proposal:** place each skull bone's segment through its BP3D centroid with a principal axis (ESTIMATE), keeping the
vertex at 1.80 m; low priority, after spine and thorax.

## Order and what each needs

1. Clavicle re-parent (`CLAVICLE_REPARENT_PROPOSAL.md`): ready, owner's OK.
2. Spine Variant A: owner's OK plus a source for reference curvature (or accept BP3D as ESTIMATE as for A23 / A24).
3. Thorax: after the spine.
4. Skull: last.
