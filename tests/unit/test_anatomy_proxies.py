"""PROXY anatomy pieces (A25): in sync, deterministic, valid manifests, closed outward shapes on canonical points."""

import hashlib
import json
import math
from pathlib import Path

import pytest

from character_engine.domain.assets.manifest import validate_manifest
from character_engine.domain.assets.proxies import SPECS, build, resolve
from character_engine.domain.character.templates import load_canonical_bones

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "anatomy" / "proxies"


@pytest.fixture(scope="module")
def joints():
    bones, _ = load_canonical_bones()
    return {b["canonical_name"]: (tuple(b["head"].values()), tuple(b["tail"].values())) for b in bones}


@pytest.fixture(scope="module")
def files(joints):
    return build(joints)


@pytest.fixture(scope="module")
def nodes():
    bones, containers = load_canonical_bones()
    return [b["canonical_name"] for b in bones + containers]


def _obj(data: bytes):
    v, f = [], []
    for line in data.decode("utf-8").splitlines():
        if line.startswith("v "):
            v.append(tuple(float(x) for x in line.split()[1:]))
        elif line.startswith("f "):
            f.append(tuple(int(x) - 1 for x in line.split()[1:]))
    return v, f


def test_committed_proxies_are_in_sync(files):
    assert sorted(p.name for p in OUT.glob("*") if p.name != "README.md") == sorted(files)
    for name, data in files.items():
        assert (OUT / name).read_bytes() == data, f"{name} stale: run scripts/build_anatomy_proxies.py"


def test_build_is_deterministic(joints, files):
    assert build(joints) == files


def test_expected_pieces_and_labels(files):
    idx = json.loads(files["INDEX.json"])["pieces"]
    assert len(idx) == 33
    by = {p["asset_id"]: p for p in idx}
    for m in ("latissimus_dorsi", "rectus_abdominis", "tibialis_anterior", "peroneus_group"):
        assert by[f"proxy_{m}_l"]["provenance"] == "ESTIMATE" and by[f"proxy_{m}_r"]["layer"] == "muscle"
    for k in ("knee_acl", "knee_pcl", "knee_mcl", "knee_lcl", "ankle_atfl", "ankle_deltoid",
              "shoulder_coracoclavicular", "shoulder_coracoacromial", "shoulder_glenohumeral"):
        assert by[f"proxy_{k}_l"]["layer"] == "ligament" and by[f"proxy_{k}_l"]["provenance"] == "PLACEHOLDER"
    assert by["proxy_coccyx"]["side"] == "midline" and by["proxy_coccyx"]["provenance"] == "PLACEHOLDER"
    for o in ("malleus", "incus", "stapes"):
        assert by[f"proxy_{o}_r"]["layer"] == "bone"


def test_every_manifest_validates_and_hashes_its_file(files, nodes):
    manifests = [n for n in files if n.endswith(".manifest.json")]
    assert len(manifests) == 33
    for n in manifests:
        m = json.loads(files[n])
        report = validate_manifest(m, nodes)
        assert report.ok, (n, report.codes())
        assert hashlib.sha256(files[m["file"]]).hexdigest() == m["sha256"]
        assert m["licence"].startswith("Character Engine project-generated")


def test_shapes_are_closed_outward_and_on_their_attachments(files, joints):
    for spec in SPECS:
        for side in (("L", "R") if spec.bilateral else (None,)):
            aid = spec.asset_id + (f"_{side.lower()}" if side else "")
            v, f = _obj(files[f"{aid}.obj"])
            assert all(math.isfinite(c) for p in v for c in p)
            vol = sum(sum(a * b for a, b in zip(v[i], (v[j][1] * v[k][2] - v[j][2] * v[k][1],
                                                       v[j][2] * v[k][0] - v[j][0] * v[k][2],
                                                       v[j][0] * v[k][1] - v[j][1] * v[k][0]))) for i, j, k in f) / 6
            assert vol > 0, f"{aid}: inward winding"
            a, b = resolve(spec.origin, joints, side), resolve(spec.insertion, joints, side)
            assert v[0] == pytest.approx(a, abs=1e-6) and v[-1] == pytest.approx(b, abs=1e-6)


def test_left_right_mirror(files):
    for n in files:
        if n.endswith("_l.obj"):
            vl, _ = _obj(files[n])
            vr, _ = _obj(files[n.replace("_l.obj", "_r.obj")])
            assert vr[0] == pytest.approx((-vl[0][0], vl[0][1], vl[0][2]), abs=1e-6)
