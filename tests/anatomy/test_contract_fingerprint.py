"""Contract fingerprint of the canonical anatomy data (Decision 52).

The canonical skeleton and its reference tables may only change with the project owner's
approval and a numbered entry in ``docs/reorientation/DECISION_LOG.md``. This test pins the
SHA-256 of each file so that an unapproved edit (a script run by mistake, a formatter, a merge)
fails loudly instead of silently moving bones.

Line endings are normalised (CRLF -> LF) before hashing, so the fingerprint is the same on a
Windows checkout and on Linux. To update a fingerprint after an approved change, record the
decision first, then replace the hash and the decision reference below.
"""

import hashlib
from pathlib import Path

import pytest

ANATOMY_DIR = Path(__file__).resolve().parents[2] / "src" / "character_engine" / "data" / "anatomy"

# {path relative to data/anatomy: (sha256 of LF-normalised bytes, decisions that approved this state)}
CONTRACT_FINGERPRINTS = {
    "human_adult_206.json": (
        "83025e87bc1b87bfda480d36728d225e8810c4c3676c6b46a1c178342b06c5a9",
        "Decisions 15 (1.80 m retarget), 33 (D-13 mirror X), 35 (A10 hand), 36 (A11 radius lateral), 54 (A13 foot), "
        "65 (A21 fibula lateral), 67 (A23 hip centres), 68 (A24 shoulder girdle), 70 (clavicle parent)",
    ),
    "human_adult_206_backup.json": (
        "4bda0b92e23f88bb0871b2d1fb2c7b64701fb538197a26a71f3e351fcbfbf3ff",
        "Decision 33 (frozen pre-retarget audit fixture, keeps the old labels)",
    ),
    "references/anthropometry.json": (
        "0ec140dacc4c0f174db9bd49a8fd49e8fffc1142c9e9e518ae0aff53812b4219",
        "Decision 15 (Drillis & Contini 1966 ratios, base stature 1.80 m)",
    ),
    "references/biomechanics.json": (
        "1c1134f9f10846bf32b07c71f20297c37c11a323f9cafb80383d12f02563a61c",
        "Decision 12 (PLACEHOLDER baseline, pending ISB joint-centre source)",
    ),
    "references/osteometry.json": (
        "4fe6fe34bd2971efad42fb8463e06ef7ec8a0aee291bfe1ed241f6ed3afc851f",
        "Decision 16 (Trotter 1970 / Trotter & Gleser 1952 regressions)",
    ),
    "references/source_registry.json": (
        "96a7b9a634922c5bbf17f5e173b01e08655e2f9b1afe966d88da127accf5ffa3",
        "Decisions 15, 16, 35, 36, 54, 65, 67, 68 (sources and pending data requirements)",
    ),
}


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@pytest.mark.parametrize("relative", sorted(CONTRACT_FINGERPRINTS))
def test_canonical_data_matches_approved_fingerprint(relative):
    expected, decision = CONTRACT_FINGERPRINTS[relative]
    actual = _fingerprint(ANATOMY_DIR / relative)
    assert actual == expected, (
        f"{relative} changed (sha256 {actual}, approved {expected} by {decision}). "
        "Canonical anatomy data is a contract: a change requires the project owner's OK and a new "
        "numbered entry in docs/reorientation/DECISION_LOG.md before this fingerprint is updated."
    )


def test_every_reference_table_is_fingerprinted():
    present = {f"references/{p.name}" for p in (ANATOMY_DIR / "references").glob("*.json")}
    pinned = {k for k in CONTRACT_FINGERPRINTS if k.startswith("references/")}
    assert present == pinned, (
        f"Unpinned or missing reference tables: {sorted(present ^ pinned)}. Adding or removing a "
        "reference table requires the project owner's OK and a DECISION_LOG entry."
    )
