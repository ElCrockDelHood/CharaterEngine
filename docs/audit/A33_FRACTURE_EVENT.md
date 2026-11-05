# A33 — Bone fragments of a fractured blow

Status: ASSUMED, additive and opt-in (Decision 80). Code: `domain/physics/fracture_event.py`; tests:
`tests/unit/test_fracture_event.py`; samples: `scripts/fracture_events_demo.py`. Spanish: `A33_FRACTURE_EVENT.es.md`.
Why: the owner sees bone hits as blurred or sliding away; bone should break like glass, in fragments. `strike_model.py` decides
*whether* a shell breaks; this module says *how it comes apart*, as data the Blender and Godot threads can draw. Wounds,
`strike_model.py`, the gameplay table and every earlier result are unchanged. (Planned as A18; that number is BodyParts3D.)

**No published fragment size, count or speed was used.** Fragmentation theory (Mott, Grady) is the frame for a power law in
energy; none of its numbers were read or used, and none of these constants is fitted to data. The output is a plausible
drawing, not a prediction of how a real bone breaks.

## Model

1. **Pattern by region:** skull `spiderweb` (many shards radiating from the impact); thorax `transverse_ribs` (few long pieces
   across the body, driven inward); upper arm, forearm, thigh, leg `butterfly` (one wedge plus large pieces along the bone); neck,
   abdomen, pelvis, hand, foot `small_pieces`.
2. **Mobilised mass:** bone density (catalog, 1900 kg/m³) × patch area × shell thickness × mobile fraction. Patch radius =
   factor × contact radius, no wider than the struck half of the bone (π × outer radius). The fragment masses add up to it exactly.
3. **Excess energy:** skull `E_diss − 23 J` (mid of its energy criterion); elsewhere `E_diss − F_mid² / 2k`, the energy already
   spent when the linear-spring force reached the midpoint of the region's range.
4. **Count:** `n = clamp(round(a · (E_excess / 50 J) ** 0.6), 3, cap)`.
5. **Sizes:** Weibull weights with the pattern's shape, rescaled to the mobilised mass.
6. **Speeds:** 10 % of the excess energy becomes fragment kinetic energy, shared by mass × a random factor 0.5–1.5; no fragment
   exceeds 2 × the blow's speed, so the reported kinetic energy can be below that share. Inner fragments (under the contact
   patch) leave in a 20° cone around the inward normal (input for secondary injury); outer ones scatter radially with an inward bias.
7. **Determinism:** the seed defaults to a 48-bit hash of segment and striker numbers (it stays exact in JSON parsers that read
   numbers as doubles).

## Constants

| Constant | Value | Range | Provenance |
|---|---|---|---|
| Patch factor (patch radius / contact radius) | 2.0 | 1.5–3 | ASSUMED |
| Mobile fraction of the patch | 0.6 | 0.4–0.9 | ASSUMED |
| Reference energy | 50 J | — | ASSUMED |
| Count exponent | 0.6 | 0.4–0.8 | ASSUMED (power-law form from the Mott / Grady frame, no number from it) |
| Count limits | 3–24 | — | 24: hardware budget (GeForce 740M + i3) |
| Fragment kinetic share | 0.10 | 0.05–0.15 | ASSUMED |
| Speed limit | 2 × blow speed | — | DERIVED (elastic limit for a light body) |
| Inner cone half angle | 20° | 10–35° | ASSUMED |
| Spin (angular speed × size / speed) | 0.2–1.0 | — | ASSUMED |
| Bone density | 1900 kg/m³ | 1800–2000 | catalog, ESTIMATE |

| Pattern | a (n at 50 J) | Cap | Weibull shape | Aspect | Outer inward bias |
|---|---|---|---|---|---|
| spiderweb | 10 | 24 | 1.6 | 1.8 | 0.3 |
| transverse_ribs | 4 | 8 | 2.0 | 3.0 | 0.8 |
| butterfly | 3 | 6 | 1.0 | 2.0 | 0.4 |
| small_pieces | 6 | 12 | 1.4 | 1.2 | 0.5 |

All pattern values ASSUMED.

## JSON schema `ce-fracture/1` (fixed key order)

```json
{
  "schema": "ce-fracture/1",
  "segment": "thorax", "region": "thorax", "bone": "THORACIC_6",
  "fractured": true, "pattern": "transverse_ribs", "seed": 123456789,
  "impact_point_m": [x, y, z],
  "frame": {"x": [..], "y": [..], "z": [..]},
  "patch_radius_m": 0.09, "shell_thickness_m": 0.009,
  "patch_mass_kg": 0.46, "excess_energy_j": 80.5, "fragment_kinetic_j": 8.05,
  "provenance": "ASSUMED",
  "fragments": [
    {"id": 0, "kind": "piece", "inner": true, "size_m": 0.09, "aspect": 3.0, "mass_kg": 0.15,
     "position_m": [x, y, z], "velocity_m_s": [x, y, z],
     "angular_speed_rad_s": 12.0, "spin_axis": [x, y, z]}
  ]
}
```

`frame` is in world coordinates (canonical Z-up, metres): `x` lateral, `y` along the segment, `z` inward along the strike.
`position_m` (offset from the impact point), `velocity_m_s` and `spin_axis` are in that local frame. `kind` is `wedge` or `piece`;
`inner` marks a fragment that starts under the contact patch. `size_m` is the lateral size of a plate-like piece of the shell's
thickness; `aspect` is length / width. When `fractured` is false, `fragments` is empty and the masses and energies are 0.

## Sample events (`python scripts/fracture_events_demo.py`)

| Segment | Striker | m (kg) | v (m/s) | F_peak (N) | Fractured | Pattern | Excess J | Fragments | Mass (g) | Largest (mm) | Fastest (m/s) | Fragment KE (J) | File |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| head | jab | 2.1 | 7.5 | 2917 | no | spiderweb | 0.0 | 0 | 0 | 0 | 0.0 | 0.00 | builds/fracture_events/head_jab.json |
| head | straight | 3.2 | 7.5 | 3339 | no | spiderweb | 0.0 | 0 | 0 | 0 | 0.0 | 0.00 | builds/fracture_events/head_straight.json |
| head | front_kick | 3.7 | 9.0 | 4187 | no | spiderweb | 0.0 | 0 | 0 | 0 | 0.0 | 0.00 | builds/fracture_events/head_front_kick.json |
| thorax | jab | 2.1 | 7.5 | 4037 | yes | transverse_ribs | 16.9 | 3 | 261 | 82 | 3.6 | 1.69 | builds/fracture_events/thorax_jab.json |
| thorax | front_kick | 3.7 | 9.0 | 6055 | yes | transverse_ribs | 80.5 | 5 | 464 | 85 | 7.0 | 8.05 | builds/fracture_events/thorax_front_kick.json |
| thigh.L | front_kick | 3.7 | 9.0 | 7457 | yes | butterfly | 70.7 | 4 | 168 | 51 | 10.2 | 7.07 | builds/fracture_events/thigh.L_front_kick.json |
| head | heavy_blow | 8.0 | 12.0 | 6739 | yes | spiderweb | 204.0 | 23 | 149 | 36 | 19.4 | 20.40 | builds/fracture_events/head_heavy_blow.json |

`builds/` holds generated files; the JSONs are not committed. Rerun the script to get them.

## What this says, and what it does not

* **No gameplay move breaks the skull**: at the midpoint of its ASSUMED force range (5 kN) head blows stay below it (the highest
  tested here, a front kick, gives 4187 N). So `spiderweb` only appears with the heavy test blow (8 kg at 12 m/s, not a move).
* **Even a jab breaks the thorax** (4037 N against a 3300 N midpoint), the same result as A15, whose thorax range is weakly sourced.
  The module draws what `strike_model.py` decides; it does not correct it.
* The patch is a circle or a band on a capsule, not on a real bone; `THORACIC_6` is the weight bone of the thorax block, while the
  fragments stand for ribs.
* On a solid core (limbs) the thickness is the core radius, so the patch mass overstates a half-cylinder by up to about 2 ×.

## Limits

No spalling outward, no crack growth in time, no fragment collisions, no drag in tissue, no bone anisotropy, no secondary injury
model yet (inner fragments are only its input), and no rendering here: Blender and Godot belong to other threads.
