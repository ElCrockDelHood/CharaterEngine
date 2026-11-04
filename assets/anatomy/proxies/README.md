# Anatomy PROXY pieces (A25)

Script-generated placeholder geometry for structures that have **no real mesh** in BodyParts3D (A18, A22, IS-A tree).
It is regenerated, never edited by hand:

```bash
python scripts/build_anatomy_proxies.py            # write
python scripts/build_anatomy_proxies.py --check    # verify (also a pytest test)
```

| Pieces | Layer | Provenance | Built from |
|--------|-------|------------|------------|
| latissimus dorsi, rectus abdominis, tibialis anterior, peroneus group (L/R) | muscle | ESTIMATE | `MUSCLES` catalogue origin / insertion / radius / tendon fraction; spindle |
| knee ACL, PCL, MCL, LCL; ankle ATFL, deltoid; shoulder coracoclavicular, coracoacromial, glenohumeral (L/R) | ligament | PLACEHOLDER | canonical bone points + offsets (knee half-width ESTIMATE from A20, everything else PLACEHOLDER); band |
| coccyx; malleus, incus, stapes (L/R) | bone | PLACEHOLDER | ellipsoid on the canonical segment |

Each `*.obj` (metres, canonical frame: Z-up, −Y forward, left = +X) has a `*.manifest.json` that passes
`domain/assets/manifest.validate_manifest` (contract PROPOSED, Decision 61). `INDEX.json` lists all 33 pieces. The
licence is project-generated: no third-party geometry. Replace a piece with a sourced mesh, plus its own manifest,
when one exists. The canonical skeleton and the rig are only read, never changed.
