# A24 proposal — shoulder girdle: shoulder joint centres, clavicle, scapula

**Status:** positions APPLIED as variant A (Decision 68, `docs/audit/A24_SHOULDER_GIRDLE.md`); topology step pending. Originally: PROPOSAL (positions approved by the owner via the coordinator, "todos los contratos y todo lo que sea
necesario"; the clavicle re-parent is a separate topology step, reported before it is applied) · **Date:**
2026-11-04 · Related: A22 (shoulder residual 68 mm), A23 / Decision 67 (same method for the hips).

## Finding

The canonical shoulder joint centres (`HUMERUS_L/R.head`, x ±0.2331) are **466.2 mm** apart. That is the **biacromial**
breadth (0.259 H, Drillis & Contini 1966) used as if it were the gleno-humeral (GH) joint spacing. Biacromial is
measured between the acromion tips, over the skin, so it is wider than the joint centres. The clavicle is a 34 mm
stub at x 0.1665–0.1998, and `SCAPULA_*` is a 22 mm vertical stub sitting on the shoulder joint. In BodyParts3D
both bones lie ~10 cm more medial (A22).

## Landmarks (ISB: Wu et al. 2005, *J Biomech* 38: 981–992, part II, shoulder)

`IJ` (incisura jugularis), `SC` (sternoclavicular joint), `AC` (acromioclavicular joint), `AA` (angulus acromialis),
`TS` (trigonum spinae), `AI` (angulus inferior), `GH` (gleno-humeral rotation centre). Measured on BodyParts3D (left;
mm relative to IJ, scaled ×1.0358 to the canonical frame; x lateral, y +posterior, z up; extraction rules ESTIMATE):

| Landmark | Rule on the mesh | x | y | z |
|----------|------------------|---|---|---|
| SC | most medial vertex of the clavicle | 22.0 | 8.0 | −5.8 |
| AC | most lateral vertex of the clavicle | 162.4 | 68.9 | 27.8 |
| AA | most lateral vertex of the scapula | 185.7 | 83.6 | 20.3 |
| TS | most medial vertex, upper 35 % of the scapula | 72.4 | 131.1 | −27.6 |
| AI | lowest vertex of the scapula | 111.1 | 137.0 | −146.4 |
| GH | humeral head sphere (A20 rule) | 179.6 | 65.2 | −9.9 |

BP3D ratio GH spacing / bone acromion spacing = 321.6 / 332.9 = **0.966**. GH lies 27–29 mm below the acromion.

## Width: three sources disagree

| Source | Biacromial | GH spacing implied (× 0.966) |
|--------|------------|-------------------------------|
| Drillis & Contini 0.259 H (canonical, PROVEN as biacromial) | 466.2 mm | 450 mm |
| **ANSUR II men 1.75–1.85 m** (n = 1814, public release; skin) | **421.1 ± 16.8 mm** (p5 394, p95 448), 0.2349 H | **406.8 mm** |
| BodyParts3D (one subject, 1.72 m, bone) | 344.8 mm (scaled) | 333.1 mm (measured directly) |

**Proposed:** GH spacing **406.8 mm** → `HUMERUS_L/R.head` x = **±0.2034** (now ±0.2331). ANSUR II is the largest
sample at the canonical stature. The BP3D ratio turns a biacromial breadth into a joint spacing. Label: **ESTIMATE**
(population mean × single-subject ratio). Uncertainty: ±16 mm (1 SD ANSUR) plus the ratio error (±2 %). It is
slightly too wide, because ANSUR measures over the skin at the acromion; the skin thickness is not modelled. The
Drillis ratio is not changed: it remains the biacromial value.

## Positions (variant A, recommended: arm chain unchanged)

Only the shoulder girdle and the humeral heads move. Elbows, forearms and hands keep their positions, so the
humerus tilts 5.4° (elbow lateral to the shoulder). BP3D shows the same thing in the anatomical pose. Reference
point: canonical `STERNUM.head` = IJ (0, −0.0666, 1.4868). Offsets are BP3D × 1.0358 (DERIVED from one subject,
ESTIMATE).

| Bone | head (left; right mirrored in x) | tail | Rule |
|------|------------------------------------|------|------|
| `HUMERUS_L` | (0.2034, 0.0, 1.4724) | unchanged (0.2331, 0.0, 1.1566) | x from the width above; y and z unchanged (Drillis shoulder height) |
| `CLAVICLE_L` | SC = IJ + (0.0220, 0.0080, −0.0058) = (0.0220, −0.0586, 1.4810) | AC = GH + (AC − GH) = (0.1862, 0.0037, 1.5101) | SC fixed to the sternum; AC keeps its BP3D position relative to GH |
| `SCAPULA_L` | AC (= clavicle tail) | AI = GH + (AI − GH) = (0.1349, 0.0718, 1.3359) | head at the joint with the clavicle, tail at the inferior angle |

Variant B (not recommended): also translate the whole arm 29.7 mm medially. Hands and strike positions would
move, so gameplay would change.

Consequence: the clavicle becomes 178 mm long, against 157 mm in BP3D (BP3D is narrow-shouldered; the
difference comes from the ANSUR width).

## What changes (variant A)

| Area | Expected change |
|------|-----------------|
| Canonical data | 2 × (HUMERUS head x, CLAVICLE head/tail, SCAPULA head/tail) via `scripts/fix_shoulder_girdle.py`; `SHOULDER_JOINT_CENTRE_SPACING` and `SHOULDER_GIRDLE_LANDMARKS` registered in `source_registry.json` |
| Fingerprints | `human_adult_206.json`, `source_registry.json`, new Decision |
| Game rig | `clavicle_*` (SC → GH) and `upperarm_*` start move; re-bake `human_game_v1_body.glb` and `souls_clips` |
| Block dummy / sockets | no shoulder segment reads these bones (to be confirmed by tests) |
| Gameplay / replays | hands at rest unchanged; arm rotations pivot at the new shoulder, so animated hand positions may shift. **Any replay or gameplay-table change stops the commit** |
| Tissue proxies | DELTOID, TRAPEZIUS, BICEPS and TRICEPS attachments on the clavicle / scapula move (visual) |

## Topology (separate step, not applied with the positions)

`CLAVICLE_*` hangs from `ROOT_SKELETON`. Anatomically the clavicle articulates with the sternum (SC joint), so the
right parent is `STERNUM` (the manubrium). Re-parenting keeps 208 nodes and does not touch CE-GAME-v1
(`clavicle_*` already hangs from `spine_03` there). It does change the canonical hierarchy (contract invariant 4
holds: acyclic, single root), so it will be reported before it is applied.
