"""Topology of hands, feet and spine in the canonical skeleton (no data is changed here).

Bone counts and chains are textbook anatomy (PROVEN topology): 27 bones per hand (8 carpals,
5 metacarpals, 14 phalanges), 26 per foot (7 tarsals, 5 metatarsals, 14 phalanges), 7 + 12 + 5
vertebrae + sacrum + coccyx. Left is +X (Decision 33 / D-13). Hand parents and carpal rows follow
A10 (Decision 35); `tests/unit/test_hand_layout.py` already covers metacarpal / phalanx parents and
wrist distances, so they are not repeated here.

Known data defects are recorded as strict xfail: they must be fixed in the data (with the owner's
OK and a DECISION_LOG entry), never by editing these expectations.
"""

import json

import pytest

from character_engine.domain.anatomy.coordinate_system import LateralSide
from character_engine.domain.anatomy.feet import (
    FootBoneType,
    FootModelBuilder,
    create_unknown_foot_bone,
)
from character_engine.domain.anatomy.hands import (
    HandBoneType,
    HandModelBuilder,
    create_unknown_hand_bone,
)
from character_engine.domain.anatomy.spine import SpineRegion
from character_engine.domain.character.templates import default_canonical_json

SIDES = ("L", "R")
PROXIMAL_CARPALS = ("SCAPHOID", "LUNATE", "TRIQUETRUM")          # lateral -> medial
DISTAL_CARPALS = ("TRAPEZIUM", "TRAPEZOID", "CAPITATE", "HAMATE")  # lateral -> medial
TARSALS = ("TALUS", "CALCANEUS", "NAVICULAR", "CUBOID",
           "CUNEIFORM_MEDIAL", "CUNEIFORM_INTERMEDIATE", "CUNEIFORM_LATERAL")
# Atlas articulations: talus on the tibia (talocrural), calcaneus / navicular on the talus, cuboid on the
# calcaneus, cuneiforms on the navicular, MT1-3 on the cuneiforms, MT4-5 on the cuboid.
FOOT_PARENTS = {
    "TALUS": "TIBIA", "CALCANEUS": "TALUS", "NAVICULAR": "TALUS", "CUBOID": "CALCANEUS",
    "CUNEIFORM_MEDIAL": "NAVICULAR", "CUNEIFORM_INTERMEDIATE": "NAVICULAR", "CUNEIFORM_LATERAL": "NAVICULAR",
    "METATARSAL_1": "CUNEIFORM_MEDIAL", "METATARSAL_2": "CUNEIFORM_INTERMEDIATE",
    "METATARSAL_3": "CUNEIFORM_LATERAL", "METATARSAL_4": "CUBOID", "METATARSAL_5": "CUBOID",
}
SPINE = ([f"CERVICAL_{i}" for i in range(1, 8)] + [f"THORACIC_{i}" for i in range(1, 13)]
         + [f"LUMBAR_{i}" for i in range(1, 6)] + ["SACRUM", "COCCYX"])
SPINE_REGION = {"CERVICAL": SpineRegion.CERVICAL, "THORACIC": SpineRegion.THORACIC,
                "LUMBAR": SpineRegion.LUMBAR, "SACRUM": SpineRegion.SACRUM, "COCCYX": SpineRegion.COCCYX}


@pytest.fixture(scope="module")
def data():
    return json.loads(default_canonical_json().read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def B(data):
    return {b["canonical_name"]: b for b in data["bones"]}


def _phalanges(prefix, side):
    return [f"{prefix}_{s}_{r}_{side}" for r in range(1, 6) for s in ("PROXIMAL", "INTERMEDIATE", "DISTAL")
            if not (r == 1 and s == "INTERMEDIATE")]


def _hand(side):
    carpals = [f"{c}_{side}" for c in PROXIMAL_CARPALS + ("PISIFORM",) + DISTAL_CARPALS]
    return carpals, [f"METACARPAL_{r}_{side}" for r in range(1, 6)], _phalanges("PHALANX", side)


def _foot(side):
    return ([f"{t}_{side}" for t in TARSALS], [f"METATARSAL_{r}_{side}" for r in range(1, 6)],
            _phalanges("TOE_PHALANX", side))


def _subtree(B, root):
    children = {}
    for n, b in B.items():
        children.setdefault(b["parent"], []).append(n)
    out, stack = set(), list(children.get(root, []))
    while stack:
        n = stack.pop()
        out.add(n)
        stack += children.get(n, [])
    return out


def _side(side):
    return LateralSide.LEFT if side == "L" else LateralSide.RIGHT


def _swap(name):
    return name[:-2] + ("_R" if name.endswith("_L") else "_L") if name[-2:] in ("_L", "_R") else name


# --- hands -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("side", SIDES)
def test_hand_is_the_27_bone_subtree_of_the_radius(B, side):
    carpals, metacarpals, phalanges = _hand(side)
    assert (len(carpals), len(metacarpals), len(phalanges)) == (8, 5, 14)
    assert _subtree(B, f"RADIUS_{side}") == set(carpals + metacarpals + phalanges)
    assert not _subtree(B, f"ULNA_{side}")                 # the ulna does not articulate with the carpus (A10)

    builder = HandModelBuilder(f"canonical_{side}", "1", _side(side))
    for kind, names in ((HandBoneType.CARPAL, carpals), (HandBoneType.METACARPAL, metacarpals)):
        for i, n in enumerate(names):
            builder.add_bone(create_unknown_hand_bone(n, kind, _side(side), i))
    for i, n in enumerate(phalanges):
        kind = {"PROXIMAL": HandBoneType.PROXIMAL_PHALANX, "INTERMEDIATE": HandBoneType.INTERMEDIATE_PHALANX,
                "DISTAL": HandBoneType.DISTAL_PHALANX}[n.split("_")[1]]
        builder.add_bone(create_unknown_hand_bone(n, kind, _side(side), i))
    assert builder.build().has_complete_structure()


@pytest.mark.parametrize("side,lateral", [("L", 1), ("R", -1)])
def test_carpal_rows_follow_the_atlas(B, side, lateral):
    for c in PROXIMAL_CARPALS + ("PISIFORM",) + DISTAL_CARPALS:
        assert B[f"{c}_{side}"]["parent"] == f"RADIUS_{side}"            # wrist anchor (A10)
    for row in (PROXIMAL_CARPALS, DISTAL_CARPALS):
        xs = [lateral * B[f"{c}_{side}"]["head"]["x"] for c in row]
        assert xs == sorted(xs, reverse=True), f"{row} not ordered lateral -> medial"
    assert min(B[f"{c}_{side}"]["head"]["z"] for c in PROXIMAL_CARPALS) > \
        max(B[f"{c}_{side}"]["head"]["z"] for c in DISTAL_CARPALS)      # proximal row above the distal row
    pisi, tri = B[f"PISIFORM_{side}"]["head"], B[f"TRIQUETRUM_{side}"]["head"]
    assert pisi["x"] == tri["x"] and pisi["z"] == tri["z"] and pisi["y"] < tri["y"]   # palmar on the triquetrum


# --- feet ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("side", SIDES)
def test_foot_is_the_26_bone_subtree_of_the_tibia(B, side):
    tarsals, metatarsals, phalanges = _foot(side)
    assert (len(tarsals), len(metatarsals), len(phalanges)) == (7, 5, 14)
    assert _subtree(B, f"TIBIA_{side}") == set(tarsals + metatarsals + phalanges)
    assert not _subtree(B, f"FIBULA_{side}")

    builder = FootModelBuilder(f"canonical_{side}", "1", _side(side))
    for kind, names in ((FootBoneType.TARSAL, tarsals), (FootBoneType.METATARSAL, metatarsals)):
        for i, n in enumerate(names):
            builder.add_bone(create_unknown_foot_bone(n, kind, _side(side), i))
    for i, n in enumerate(phalanges):
        kind = {"PROXIMAL": FootBoneType.PROXIMAL_PHALANX, "INTERMEDIATE": FootBoneType.INTERMEDIATE_PHALANX,
                "DISTAL": FootBoneType.DISTAL_PHALANX}[n.split("_")[2]]
        builder.add_bone(create_unknown_foot_bone(n, kind, _side(side), i))
    assert builder.build().has_complete_structure()


@pytest.mark.parametrize("side", SIDES)
def test_toe_chains_follow_the_atlas(B, side):
    for ray in range(2, 6):
        assert B[f"TOE_PHALANX_INTERMEDIATE_{ray}_{side}"]["parent"] == f"TOE_PHALANX_PROXIMAL_{ray}_{side}"
        assert B[f"TOE_PHALANX_DISTAL_{ray}_{side}"]["parent"] == f"TOE_PHALANX_INTERMEDIATE_{ray}_{side}"
    assert B[f"TOE_PHALANX_DISTAL_1_{side}"]["parent"] == f"TOE_PHALANX_PROXIMAL_1_{side}"   # hallux: 2 phalanges
    for n in _foot(side)[2]:
        parent = B[n]["parent"]
        if parent.startswith("TOE_PHALANX"):
            assert B[n]["head"] == B[parent]["tail"], f"{n} not continuous with {parent}"


@pytest.mark.xfail(strict=True, reason="data defect: every tarsal, metatarsal and proximal toe phalanx is "
                   "parented to TIBIA_* (no tarsal / tarsometatarsal / metatarsophalangeal chain)")
@pytest.mark.parametrize("side", SIDES)
def test_tarsal_and_metatarsal_parents_follow_the_atlas(B, side):
    wrong = {f"{bone}_{side}": B[f"{bone}_{side}"]["parent"] for bone, parent in FOOT_PARENTS.items()
             if B[f"{bone}_{side}"]["parent"] != f"{parent}_{side}"}
    wrong.update({f"TOE_PHALANX_PROXIMAL_{r}_{side}": B[f"TOE_PHALANX_PROXIMAL_{r}_{side}"]["parent"]
                  for r in range(1, 6)
                  if B[f"TOE_PHALANX_PROXIMAL_{r}_{side}"]["parent"] != f"METATARSAL_{r}_{side}"})
    assert not wrong, f"parents off the atlas: {wrong}"


# --- spine -----------------------------------------------------------------------------------------

def test_spine_segments_and_hierarchy(B):
    assert B["CERVICAL_1"]["parent"] == "CRANIUM"                       # atlas carries the skull container
    for upper, lower in zip(SPINE, SPINE[1:]):
        assert B[lower]["parent"] == upper
    counts = {}
    for n in SPINE:
        counts[SPINE_REGION[n.split("_")[0]]] = counts.get(SPINE_REGION[n.split("_")[0]], 0) + 1
    assert counts == {SpineRegion.CERVICAL: 7, SpineRegion.THORACIC: 12, SpineRegion.LUMBAR: 5,
                      SpineRegion.SACRUM: 1, SpineRegion.COCCYX: 1}
    assert not any(n.startswith(("CERVICAL_", "THORACIC_", "LUMBAR_")) for n in B if n not in SPINE)


def test_spine_is_midline_and_descends(B):
    zs = []
    for n in SPINE:
        for end in ("head", "tail"):
            assert B[n][end]["x"] == 0, f"{n}.{end} off the midline"
            zs.append(B[n][end]["z"])
    assert all(a >= b for a, b in zip(zs, zs[1:])), "vertebrae must stack from the skull down"


def test_ribs_and_pelvis_hang_from_their_segments(B):
    for side in SIDES:
        for k in range(1, 13):
            assert B[f"RIB_{k:02d}_{side}"]["parent"] == f"THORACIC_{k}"
        assert B[f"COXAL_{side}"]["parent"] == "SACRUM"


# --- whole skeleton --------------------------------------------------------------------------------

def test_left_and_right_mirror_each_other(B):
    for n, b in B.items():
        if not n.endswith("_L"):
            continue
        r = B[_swap(n)]
        assert r["parent"] == _swap(b["parent"]), n
        for end in ("head", "tail"):
            assert r[end]["x"] == pytest.approx(-b[end]["x"], abs=1e-6), n          # left = +X (Decision 33)
            assert (r[end]["y"], r[end]["z"]) == pytest.approx((b[end]["y"], b[end]["z"]), abs=1e-6), n
    assert {n for n in B if n.endswith("_R")} == {_swap(n) for n in B if n.endswith("_L")}


def test_single_common_root_without_cycles(data, B):
    containers = {c["canonical_name"]: c["parent"] for c in data["containers"]}
    assert [n for n, p in containers.items() if p is None] == ["ROOT_SKELETON"]
    parents = {**containers, **{n: b["parent"] for n, b in B.items()}}
    assert len(parents) == 208
    for n in parents:
        seen, cur = set(), n
        while parents[cur] is not None:
            assert cur not in seen, f"cycle through {n}"
            seen.add(cur)
            cur = parents[cur]
            assert cur in parents, f"{n} reaches unknown parent {cur}"
        assert cur == "ROOT_SKELETON"
