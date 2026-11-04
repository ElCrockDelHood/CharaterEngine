# A25 — PROXY geometry for anatomy missing from BodyParts3D

**Date:** 2026-11-04 · **Status:** DONE (proxies, replaceable) · **Decision 69** · owner: "lo que nos falta, ¿lo podés
modelar?" · **Module:** `domain/assets/proxies.py` · **Script:** `scripts/build_anatomy_proxies.py` ·
**Output:** `assets/anatomy/proxies/` · **Tests:** `tests/unit/test_anatomy_proxies.py`

## Why

BodyParts3D 4.0 (PART-OF and IS-A trees, A18 and the 2026-11-04 IS-A download) has no mesh for: latissimus dorsi,
rectus abdominis, tibialis anterior, the peroneus group, the major joint ligaments (its 16 ligaments are laryngeal
and ocular), the coccyx and the ear ossicles. The fitting pipeline (F0–F2) and the weight-paint work need *some*
geometry in place, clearly labelled, until a sourced mesh exists. Decision 4.2 (do not invent geometry) is respected
by **labelling**: nothing here claims to be anatomy data.

## What was generated (33 pieces, 432 KB, deterministic)

| Group | Pieces | Shape | Provenance |
|-------|--------|-------|------------|
| Muscles | latissimus dorsi, rectus abdominis, tibialis anterior, peroneus group × L/R | spindle origin → insertion, tendon ends at 0.25 × radius (PLACEHOLDER ratio) | **ESTIMATE**: `MUSCLES` catalogue attachments, radius, tendon fraction |
| Ligaments | knee ACL, PCL, MCL, LCL; ankle ATFL, deltoid; shoulder coracoclavicular, coracoacromial, glenohumeral × L/R | band, radius 4 mm / 6 mm | **PLACEHOLDER**: bone points + offsets; only the knee half-width (41.7 mm) is ESTIMATE (BP3D epicondyles, A20) |
| Bones | coccyx; malleus, incus, stapes × L/R | ellipsoid on the canonical segment, radius 0.35 × length | **PLACEHOLDER** |

Every OBJ has an asset manifest (Decision 61, contract PROPOSED): layer, canonical bone, side, 3 anchors
(origin, insertion, equator), the muscle attachment checked against `MUSCLES`, the file's SHA-256 and a
project-generated licence. All 33 manifests validate. The manifest's layer list gains **`ligament`**: the contract
is still PROPOSED, and ligaments are not tendons.

## Checks

The committed files equal a fresh build (byte for byte). Every shape is closed with outward winding (signed
volume > 0), starts and ends exactly on its attachment points (1e-6 m), and L/R pieces mirror in x. Canonical data,
fingerprints and rig are untouched: the builder only reads `human_adult_206.json`.

## Replace later

Each piece is meant to be replaced by a sourced mesh with its own manifest. Candidate sources:

- muscles: Z-Anatomy (CC BY-SA, share-alike), or the owner's own modelling;
- ligaments: atlas definitions (e.g. *Anatomía Clínica*, Pró) for the attachment points;
- coccyx and ossicles: another open dataset.

Any download needs the owner's OK (Decision 46).
