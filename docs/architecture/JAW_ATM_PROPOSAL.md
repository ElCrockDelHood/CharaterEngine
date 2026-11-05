# Proposal A32 — jaw pivot at the temporomandibular joint (not applied)

**Status:** PROPOSAL, measured in a throw-away working copy (reverted; canonical data and fingerprints unchanged) ·
**Date:** 2026-11-05 · applying it needs the owner's OK and **Decision 78** · Related: A18, A22, A30, Decisions 52, 74, 76;
`RIG-GAME-001_SPEC.md` (which already says `jaw` = "canonical MANDIBLE head = TMJ").

## Finding

`MANDIBLE` is a vertical stub on the midline: head (0, 0, 1.566), the chin at the PROVEN 0.87 H; tail (0, 0, 1.5994). The
game `jaw` bone copies it, so the jaw opens about the chin. At the current 25° limit the chin does not move at all, and
the stub's tail moves 14.5 mm. It is also the worst bone in the skull region of A22: 64.7 mm, against a median of 6.4 mm.

## Recommendation: variant A

| `MANDIBLE` | Today | Proposed | Provenance |
|------------|-------|----------|------------|
| `head` | (0, 0, 1.566) chin | **(0, −0.0168, 1.6539)** TMJ axis, midline | ESTIMATE, BodyParts3D, one subject |
| `tail` | (0, 0, 1.5994) | **(0, −0.0914, 1.566)** chin | z PROVEN (0.87 H, kept); y ESTIMATE, BodyParts3D |

The bone becomes 115.3 mm long (33.4 mm today), running forward and down 49.7° below horizontal (BodyParts3D: 48.4°).
**No node is added and no parent changes:** still 208 canonical nodes, `MANDIBLE` under `CRANIUM`, 66 bones in CE-GAME-v1,
`jaw` under `head`. `game_rig.py` needs no change, because `jaw` already runs from `MANDIBLE` head to tail. The data comes into
line with what the rig spec already says.

## Measurements

BodyParts3D `FJ3289` (A18), scaled ×1.0468 as in A30, with the offset to the canonical frame calibrated on the 20 skull bones
applied in A30 and mapped here: y +82.25 mm (spread 4.02 mm), z +81.76 mm (spread 4.62 mm). Check: the menton comes out at
1.5699 m, against the 1.570 m recorded in A30. Vertex-extreme rules; mesh resolution about ±5 mm; one subject (1.72 m).

| Landmark | Rule | x, y, z (mm) |
|----------|------|--------------|
| Condyle L / R | centroid of the top 10 mm of the posterior ramus | ±46.0, −16.9, 1653.9 (mirror mean) |
| Condyle top | highest posterior vertex | ±45.9, −16.7, 1658.3 |
| TMJ axis | midpoint of the condyles | 0.1, −16.8, 1653.9 |
| Menton | lowest midline vertex | 6.4, −91.4, 1569.9 |
| Pogonion | most anterior midline vertex | −2.7, −99.7, 1592.6 |
| Anterior alveolar top | highest anterior midline vertex | −0.5, −97.8, 1597.1 |
| Gonion L / R | largest (y − z) | ±41.2, −24.6, 1600.4 (mirror mean) |

Derived: intercondylar distance 92.0 mm; condylar head 17.5 × 12–13 mm (mediolateral × anterior-posterior); the axis between
the condyles is square to the midline (0.16° about Z, 0.07° about Y), so the rig's lateral axis through a midline point
matches it. A single midline pivot is therefore enough.

**Ramus and body stay in the mesh, not in the skeleton:** ramus (condyle → gonion) 54–55 mm, body (gonion → menton) 82–87 mm.
The side difference comes from the menton vertex lying 6.4 mm off the midline. One straight bone cannot represent the angle
between them. For mesh fitting they are landmarks, and the F2 fit per bone already handles that.

### Contrast (not sources of the proposed values)

| Check | Value | Reading |
|-------|-------|---------|
| ANSUR II tragion → top of head, men 1.75–1.85 m, n = 1814 | ratio 0.0736, 132.4 mm at 1.80 m (p5–p95 of the raw measure 122–142 mm) | tragion at z ≈ 1.668 m on the skin; the proposed TMJ centre is 14 mm below it and the condyle top 9 mm below. Plausible, not a proof: ANSUR gives no bone landmark for the joint and no y position |
| ANSUR II menton → sellion | 123.6 ± 6.2 mm | from the kept chin, sellion ≈ 1.690 m; PROVEN eye height 1.685 m. The chin height is consistent |
| ANSUR II head length | 201.0 ± 6.6 mm | BodyParts3D 204.5 mm (A30): the same subject scale is reasonable for y |
| Keeping the chin PROVEN | TMJ → chin 87.9 mm in z | BodyParts3D 84.0 mm: 3.9 mm taller than the subject, because the chin stays at 1.566 m and the TMJ stays in the skull's frame |

*Anatomía Clínica* (Pró) is not used for any number. A qualitative check of the joint description is pending.

## Mouth opening

| Source | Finding |
|--------|---------|
| Posselt, "Hinge opening axis of the mandible", *Acta Odontologica Scandinavica* ([PDF](https://medicaljournalssweden.se/actaodontologica/article/download/35790/40886/93098)) | about 20 mm between the incisors without anterior gliding of the condyles |
| Abushouk et al. 2025, *Open Dent J* 19:e18742106392815 (CC BY 4.0), n = 277, Sudanese students aged 18–25 | maximum opening: men 56.33 ± 6.77, women 50.62 ± 5.19 mm |
| Study of Nepalese bachelor-level students ([PDF](https://nepjol.info/index.php/mjmms/article/download/53510/40075/158408)) | maximum opening: men 48.69 ± 6.92, women 46.51 ± 6.24 mm |

Populations differ and neither opening study is the ANSUR population, so these are ranges to check against, not values to fix.

Geometry of a pure rotation about the proposed pivot. The mesh has no teeth, so the moved point is the anterior alveolar top
(98.9 mm from the pivot), not the incisal edge:

| Rotation | Alveolar point moves | Chin moves | Reading |
|----------|----------------------|------------|---------|
| 11.6° | 20 mm | 23 mm | hinge phase (Posselt) |
| **25° (current limit, ASSUMED)** | **42.8 mm** | **49.9 mm** | below both studies' male means |
| 29.7° | 50.6 mm | 59 mm | |
| 33.1° | 56.3 mm | 66 mm | |

The real joint rotates and then translates forward. A fixed pivot does not model that translation. Beyond the hinge phase the angle
is only an approximation of the opening, and a larger angle without translation pushes the condyle into impossible positions
for close-up work.

**Recommendation: keep `JAW_OPEN_MAX_DEG` at 25° and ASSUMED in this step.** With the new pivot it gives a believable opening,
and changing the limit would change the face contract for no visible gain until a head mesh exists. Condylar translation
belongs to the face or cinematic work.

## Variants

| Variant | What | Verdict |
|---------|------|---------|
| **A** | Head at the TMJ, tail at the chin, as above | **Recommended; measured below** |
| A′ | As A, with the TMJ lowered 3.9 mm so the BodyParts3D distance to the chin is kept | Not measured. It would separate the joint from the skull bones placed in A30, which share its frame. No clear gain |
| B | Canonical bone unchanged; only the game `jaw` gets a pivot from a constant | Rejected: the canonical bone stays wrong, the 64.7 mm stays, and rig and canonical data disagree |
| C | Two bones, `CONDYLE_L` and `CONDYLE_R` | Rejected: breaks the 208-node contract, and the axis measurement shows one midline pivot is enough |
| D | Head at the TMJ, tail straight below at y = 0 | Rejected: the chin would stay 91 mm behind its measured position |

## Trial of variant A (throw-away, reverted)

| Gate | Result |
|------|--------|
| Gameplay table | in sync |
| Godot | 60/60; replays unchanged. One detail differs: `CEBreathing` sternum movement 0.0016 → 0.0017 m, still PASS. Cause not investigated; `MANDIBLE` is not an input of that modifier that I know of, so a timing effect is possible |
| Blender | 40/40; IK rest 13.6 mm; game rig IK rest 0.0019 mm; canonical bones driven, rest error 0.0553 mm |
| Clips | re-exported and re-baked; no field changes |
| Proxies | 67 files in sync |
| pytest | 1273 passed, 2 failed, both expected: the fingerprint of `human_adult_206.json`, and `test_skull_positions.py::test_vertex_and_mandible_unchanged`, which pins the old values on purpose |
| A22 | `MANDIBLE` centroid → segment **64.7 → 8.3 mm**, axis angle 2.7°; skull maximum 64.7 → 9.3 mm; skull median 6.4 mm unchanged; global RMS 29.74 mm unchanged; 0 joints moved |

Not measured: lint (no code in the trial), UPBGE, a visual render, and the opening on a real head (no head mesh exists yet).

## Impact

- **Stature retarget:** `stature_retarget.py` takes the chin as `min(head z, tail z)`, so it now reads the tail. The chin stays
  at 0.87 H.
- **Rig and clips:** `jaw` gets its correct rest pose and the same 66 bones. Face reference rotations are about the head's lateral axis and
  do not depend on the pivot's position. `souls_clips` does not probe `jaw`.
- **Body and dummy:** `human_game_v1_body.glb` needs a re-bake with the new rest pose. The block dummy's head segment uses `CERVICAL_1` and `FRONTAL`, not `MANDIBLE`.
- **Strikes to the jaw:** hitboxes are radii per bone, not positions, and the strike tables depend on the bone name. `MANDIBLE` keeps its radius (0.06 m), its
  tissues and its impact results, which is why the gameplay table stays in sync.
- **Mesh fitting:** F2 can fit the mandible against a real segment.

## If approved (Decision 78, audit `docs/audit/A32_JAW_ATM.md`)

1. `scripts/fix_jaw_atm.py`: deterministic and idempotent, with the fixed table above; refuses `_backup`; writes a report.
2. Update the `human_adult_206.json` fingerprint in the same commit (Decision 52). The backup fixture is not touched.
3. Update `test_vertex_and_mandible_unchanged` with a stated reason, and add `tests/unit/test_jaw_atm.py`: chin z = 0.87 H, head at the TMJ, tail
   below and ahead of the head, node count unchanged, chin moves down on opening, script idempotent.
4. Add the provenance note to `source_registry.json` and update its fingerprint if the owner wants the data gap recorded there.
5. Re-export clips and re-bake body and clips. Run pytest, lint, Blender, Godot, the replay comparison and A22.
6. Add the new citations to `NOTICE`, and update `HANDOFF` and the index.

## What the owner decides

1. Apply variant A, or not.
2. Keep the 25° limit (recommended), or raise it to about 30° (51 mm), knowing that the condyle does not translate.
