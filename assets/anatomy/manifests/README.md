# Asset manifests (contract PROPOSED, not approved)

One JSON manifest per mesh asset file (bone, muscle, tendon, fascia, fat, skin), as described in §3 of
`docs/architecture/ASSET_FITTING_PROPOSAL.md`. The validator is
`src/character_engine/domain/assets/manifest.py` (`validate_manifest`, phase F0). It rejects a manifest
when the licence, author or origin was not read, the hash is missing or malformed, a `canonical_bone` is not
one of the 208 canonical nodes, a rigid part has fewer than 3 non-collinear anchors, or a muscle attachment
does not match the `MUSCLES` catalogue.

This folder holds **no assets yet**. Every download needs the owner's OK, file by file (Decision 46).

Not part of the canonical fingerprint: `tests/anatomy/test_contract_fingerprint.py` covers only
`src/character_engine/data/anatomy/` (Decision 52). A manifest records the SHA-256 of its own asset file
instead.
