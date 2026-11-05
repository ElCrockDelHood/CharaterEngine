# Proposal A28 — thorax: sternum and ribs (NOT applied)

**Status:** PROPOSAL, measured in a throw-away working copy (reverted; canonical data and fingerprints unchanged) ·
**Date:** 2026-11-05 · needs the owner's OK and a numbered Decision · depends on `CERVICAL_SPACING_PROPOSAL.md`
(variant B) · Related: A22, A24, A26.

## Finding

`STERNUM` is a 46.8 mm vertical stub; the 24 ribs are horizontal stubs of 37–74 mm at y = 0, starting at x 0.07–0.15 m
(not at the spine) and *growing* in length downwards. Real ribs start at their vertebra, run back and around, and
end at the front, lower than they start. A22: thorax centroid → segment median 123 mm, axis angle 38°.

## Landmarks (BodyParts3D, left; scaled ×1.0468 to the stature; ESTIMATE, one subject)

**Sternum:** incisura jugularis (highest vertex) → xiphoid tip (lowest vertex): Δ (y −71.5, z −168.8) mm, length
183.7 mm (x taken as 0, midline). Height check: BP3D IJ 1.469 m, ANSUR suprasternale 1.476 m, canonical 1.487 m.

**Ribs** (relative to the body centroid of their own thoracic vertebra, mm; x lateral, y +posterior, z up). Head = most
medial vertex of the posterior 40 % (costovertebral end). Tail = most anterior vertex (costochondral end).

| Rib | Head x, y, z | Tail x, y, z | Chord |
|-----|--------------|--------------|-------|
| 1 | 17, −6, −3 | 59, −62, −52 | 85 |
| 2 | 16, −3, 2 | 50, −106, −75 | 134 |
| 3 | 13, 2, 7 | 52, −130, −82 | 163 |
| 4 | 14, −3, 6 | 61, −152, −90 | 183 |
| 5 | 22, 6, 0 | 83, −163, −103 | 208 |
| 6 | 14, 2, 6 | 94, −163, −107 | 215 |
| 7 | 20, 10, 16 | 112, −150, −109 | 223 |
| 8 | 21, 14, 10 | 122, −125, −109 | 209 |
| 9 | 27, 17, 2 | 127, −93, −111 | 187 |
| 10 | 30, 22, −1 | 126, −70, −108 | 170 |
| 11 | 24, 23, 2 | 110, −38, −103 | 148 |
| 12 | 32, 27, −10 | 23, 4, 0 | 27 (**rule artefact**) |

Rib 12: this mesh's most anterior vertex is not the free end. An earlier rule gave a 60 mm chord. It needs its own rule
(the tip along the bone's principal axis) before being applied. Costal cartilages are not part of the bone; the chord
ends at the bony end. A straight segment is only the chord of a curved bone: the visible curve belongs to the mesh
or a proxy, not to the skeleton.

## Variants

| | A (recommended) | B |
|---|---|---|
| Sternum | head (IJ) fixed, tail = IJ + (0, −71.5, −168.8) mm | stub stays |
| Ribs | head / tail = own vertebra centroid + table above, mirrored in x | only the sternum changes |

**SC joint (A24):** `CLAVICLE` head = IJ + offset, and the sternum head does **not** move, so SC, the clavicle, the
scapula and the shoulders are unchanged. Decision 70's parent is unaffected.

## Measured impact (variant A on today's spine; working copy, reverted)

| Gate | Result |
|------|--------|
| Gameplay table | in sync |
| Godot | 60/60; replays identical (the `RIB_08_L`, `RIB_10_L` and `STERNUM` hit targets use bone names and tables) |
| Blender | 40/40, IK rest 13.6 mm, T-pose OK |
| Clips | no field changes (ribs and sternum are only *covered* by `spine_03`) |
| pytest failures to resolve | fingerprint; `test_anatomy_proxies` (regenerate: rectus abdominis attaches to the sternum tail) |
| A22 thorax | centroid → segment median 123.2 → 94.7 mm; axis angle 38.2° → **5.1°** |

The axis angle shows that the directions become right. The 95 mm that remains comes from the rib heads hanging on the
compressed thoracic spine (T8–T12 up to 16 cm too high), so it should fall further once A27 variant B is applied.
Expected, not measured together.

Also to check when applying: the breathing drivers (`CTRL-breath` moves sternum + ribs, Blender; `ce_breathing.gd`),
`PERONEUS`-style tissue proxies with attachments on ribs (`EXTERNAL_OBLIQUE` on `RIB_08`), the proxy ligaments
(none on the ribs) and the `rectus abdominis` proxy.

## Uncertainty

One subject (BP3D, 1.72 m, internal use). Vertex-extreme rules: ±5 mm (mesh resolution). Rib positions inherit the
vertebra's uncertainty. No population source for rib geometry is registered yet: label **ESTIMATE**.

## Recommendation

**Apply after A27 variant B, variant A here**, with a dedicated rib-12 rule. No gameplay or replay change was measured,
and the thorax stops being schematic.
