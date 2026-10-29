"""Finding A13 (Decision 54): the foot stands on the ground and points forward, with atlas topology.

Sourced constraints only: ankle = TIBIA tail (0.039·H), heel -> longest toe tip = 0.152·H and the
ray span from the foot breadth 0.055·H (Drillis & Contini). The 3 : 5 : 3 segment split, ray
spacing, heel offset and arch profile are PLACEHOLDER / ESTIMATE (docs/audit/A13_FOOT_LAYOUT.md) and
are deliberately not asserted here beyond what follows from the sourced values. Parents are covered
by `tests/unit/test_extremity_spine_topology.py`.
"""

import json

import pytest

from character_engine.domain.character.templates import default_canonical_json

H = 1.80
TARSALS = ("TALUS", "CALCANEUS", "NAVICULAR", "CUBOID",
           "CUNEIFORM_MEDIAL", "CUNEIFORM_INTERMEDIATE", "CUNEIFORM_LATERAL")
CUNEIFORM = {1: "CUNEIFORM_MEDIAL", 2: "CUNEIFORM_INTERMEDIATE", 3: "CUNEIFORM_LATERAL"}


@pytest.fixture(scope="module")
def B():
    return {b["canonical_name"]: b for b in json.loads(default_canonical_json().read_text(encoding="utf-8"))["bones"]}


def _foot(side):
    names = [f"{t}_{side}" for t in TARSALS] + [f"METATARSAL_{r}_{side}" for r in range(1, 6)]
    names += [f"TOE_PHALANX_{s}_{r}_{side}" for r in range(1, 6) for s in ("PROXIMAL", "INTERMEDIATE", "DISTAL")
              if not (r == 1 and s == "INTERMEDIATE")]
    return names


def _points(B, side):
    return [B[n][end] for n in _foot(side) for end in ("head", "tail")]


@pytest.mark.parametrize("side", ["L", "R"])
def test_talus_sits_on_the_ankle(B, side):
    assert B[f"TALUS_{side}"]["head"] == B[f"TIBIA_{side}"]["tail"]
    assert B[f"TIBIA_{side}"]["tail"]["z"] == pytest.approx(0.039 * H, abs=1e-4)     # Drillis & Contini ankle


@pytest.mark.parametrize("side", ["L", "R"])
def test_sole_on_the_ground_and_foot_below_the_ankle(B, side):
    ankle_z = B[f"TIBIA_{side}"]["tail"]["z"]
    zs = [p["z"] for p in _points(B, side)]
    assert min(zs) == 0.0
    assert max(zs) <= ankle_z
    for r in range(1, 6):                                       # heel, metatarsal heads and toes on the sole
        assert B[f"METATARSAL_{r}_{side}"]["tail"]["z"] == 0.0
    assert B[f"CALCANEUS_{side}"]["head"]["z"] == 0.0


@pytest.mark.parametrize("side", ["L", "R"])
def test_foot_points_forward_with_sourced_length(B, side):
    ankle_y = B[f"TIBIA_{side}"]["tail"]["y"]
    heel_y = B[f"CALCANEUS_{side}"]["head"]["y"]
    tips = [B[f"TOE_PHALANX_DISTAL_{r}_{side}"]["tail"]["y"] for r in range(2, 6)]
    assert heel_y > ankle_y > max(tips)                          # heel behind the ankle, toes in front (−Y)
    assert heel_y - min(tips) == pytest.approx(0.152 * H, abs=1e-4)
    for n in _foot(side):                                        # every bone points forward or down, never back
        assert B[n]["tail"]["y"] <= B[n]["head"]["y"] + 1e-9, n


@pytest.mark.parametrize("side,lateral", [("L", 1), ("R", -1)])
def test_rays_spread_medial_to_lateral_within_the_breadth(B, side, lateral):
    xs = [lateral * B[f"METATARSAL_{r}_{side}"]["head"]["x"] for r in range(1, 6)]
    assert xs == sorted(xs)                                      # hallux medial, little toe lateral
    assert xs[-1] - xs[0] < 0.055 * H                            # rays inside the sourced foot breadth
    for n in _foot(side):
        assert lateral * B[n]["head"]["x"] > 0, n                # left foot on +X (Decision 33)


@pytest.mark.parametrize("side", ["L", "R"])
def test_joints_are_continuous(B, side):
    s = side
    assert B[f"TALUS_{s}"]["tail"] == B[f"NAVICULAR_{s}"]["head"]
    assert B[f"CALCANEUS_{s}"]["tail"] == B[f"CUBOID_{s}"]["head"]
    for r, cun in CUNEIFORM.items():
        assert B[f"{cun}_{s}"]["tail"] == B[f"METATARSAL_{r}_{s}"]["head"]
    for r in range(1, 6):
        assert B[f"TOE_PHALANX_PROXIMAL_{r}_{s}"]["head"] == B[f"METATARSAL_{r}_{s}"]["tail"]
