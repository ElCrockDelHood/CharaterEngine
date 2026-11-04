# A24 — Shoulder girdle: shoulder joint centres 406.8 mm apart, clavicle SC → AC, scapula AC → AI (variant A)

**Date:** 2026-11-04 · **Status:** APPLIED (owner: "todos los contratos y todo lo que sea necesario", then "elijo A")
· values **ESTIMATE** · **Decision 68** · topology (clavicle re-parent) **not** applied, separate step
**Proposal:** `docs/architecture/SHOULDER_GIRDLE_PROPOSAL.md` · **Script:** `scripts/fix_shoulder_girdle.py` ·
**Report:** `A24_SHOULDER_GIRDLE_REPORT.json` · **Tests:** `tests/unit/test_shoulder_girdle.py`

## Change (left; right mirrored in x)

| Bone | Before head → tail | After head → tail | Provenance |
|------|--------------------|-------------------|------------|
| `HUMERUS_L` | (0.2331, 0, 1.4724) → (0.2331, 0, 1.1566) | (**0.2034**, 0, 1.4724) → unchanged | ANSUR II biacromial 421.1 mm × BP3D GH / acromion 0.966 → spacing 406.8 mm, ESTIMATE |
| `CLAVICLE_L` | (0.1665, −0.0666, 1.5156) → (0.1998, −0.0666, 1.5084) | SC (0.0220, −0.0586, 1.4810) → AC (0.1862, 0.0037, 1.5101) | ISB landmarks (Wu 2005), BP3D offsets × 1.0358, ESTIMATE |
| `SCAPULA_L` | (0.2331, 0, 1.5012) → (0.2331, 0, 1.4796) | AC → AI (0.1349, 0.0718, 1.3359) | same |

Elbows, forearms, hands and the hierarchy are unchanged (`CLAVICLE_*` still hangs from `ROOT_SKELETON`). The humerus
is now 5.37° off vertical (elbow lateral to the shoulder, as in BP3D) and 0.3172 m long (was 0.3158).
`SHOULDER_JOINT_CENTRE_SPACING` and `SHOULDER_GIRDLE_LANDMARKS` are registered in `source_registry.json` (pending
a population source). The Drillis & Contini biacromial ratio (0.259 H) is unchanged and stays the biacromial value.

Fingerprints (LF): `human_adult_206.json` `c2d6341a…e7ca` → `823c5241…4209`; `source_registry.json`
`be8f1f96…1ae1` → `96a7b9a6…f5ffa3`.

## T-pose (code change, `domain/anatomy/pose/tpose.py`)

`apply_tpose` used to rotate the arm by a fixed 90°, which assumes a vertical humerus. It now:

1. subtracts the humerus's rest abduction, so the humerus ends exactly horizontal;
2. straightens the elbow by that same angle, so the posed arm is a straight chain, as a T / A pose should be.

A vertical humerus gives rest = 0, i.e. the original behaviour bit for bit.

Before the elbow was straightened, Blender's "IK at rest" check measured 25.9 mm (limit 20). The bent chain then
lay in the plane of the pole after pronation. Refining the addon's pole-angle search did not change it, so that
attempt was reverted and **the addon is unchanged**. With the straight chain it measures 13.6 mm (was 11.8).

Two tests compared T-pose coordinates at 1e-9 m / exact float equality. The T-pose rounds bone ends to 1 µm by
design (`tpose._d`), so those two checks now use 1e-6 m and float-noise tolerance:
`test_equipment_sockets.py::test_socket_keeps_its_offset_relative_to_the_parent_in_tpose` and
`test_hand_poses.py::test_point_keeps_the_index_straight`.

## Behaviour

| Area | Result |
|------|--------|
| Gameplay table | `export_gameplay_data.py --check`: in sync |
| Godot replays (souls, arena, autoplay) | identical to Python and to the pre-A24 run |
| T-pose (Godot check) | elbow → radius delta 0.3585 → 0.3599 m (longer humerus) |
| Posed hand / weapon displacement checks | 0.502 → 0.504 m, 0.520 → 0.521 m, 0.703 → 0.704 m (all PASS) |
| `souls_clips.json` / `.glb`, `human_game_v1_body.glb`, `skeleton_serialized.json` | regenerated / re-baked; only the arm-chain directions change in the clips; Godot parity worst 0.0001° |
| Blender addon | 40/40, IK rest deviation 13.6 mm; addon code unchanged |

## Re-measured (BodyParts3D, internal use; `C:\DEV\Assets\BodyParts3D_4.0\out\a24\`)

- **A22:** global RMS 40.8 → **29.7 mm**. Shoulder residual 67.0 → **39.8 mm**; knee 21 → 17 mm; hip 11.6 → 10.9 mm.
  Shoulder girdle region, centroid → segment median: 107.8 → **27.9 mm** (`CLAVICLE_L` 99.2 → 11.3, `SCAPULA_L`
  116.8 → 44.6). Arm 29.0 → 26.6 mm. Other regions within ±3.5 mm. 0 joints moved.
- **A20:** humerus L/R length vs Trotter +2.00 / +2.15 % → +2.45 / +2.60 %; RMS 3.12 / 2.91 mm. The other long
  bones are unchanged.

## Not done (separate steps)

The clavicle re-parent `ROOT_SKELETON` → `STERNUM` is a topology change (still 208 nodes; CE-GAME-v1 already hangs
`clavicle_*` from `spine_03`); it needs its own Decision. Not done either: the shoulder height (Drillis 0.818 H
kept; BP3D puts GH 27–29 mm below the acromion) and a population source for the girdle landmarks.
