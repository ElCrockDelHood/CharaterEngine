"""Finding A10: the hand hangs from the wrist (anatomical position) with atlas topology.

Sourced constraints only: wrist = RADIUS tail, fingertips at 0.377·H (Drillis & Contini);
carpal rows / metacarpal articulations are textbook topology. Intra-hand proportions are
PLACEHOLDER (see docs/audit/A10_HAND_LAYOUT.md) and are deliberately not asserted here.
"""

import json

import pytest

from character_engine.domain.anatomy.pose import apply_pose
from character_engine.domain.character.templates import default_canonical_json

H = 1.80
MC_PARENT = {1: "TRAPEZIUM", 2: "TRAPEZOID", 3: "CAPITATE", 4: "HAMATE", 5: "HAMATE"}
CARPALS = ("SCAPHOID", "LUNATE", "TRIQUETRUM", "PISIFORM", "TRAPEZIUM", "TRAPEZOID", "CAPITATE", "HAMATE")


@pytest.fixture(scope="module")
def B():
    return {b["canonical_name"]: b for b in json.loads(default_canonical_json().read_text(encoding="utf-8"))["bones"]}


def _hand(side):
    names = [f"{c}_{side}" for c in CARPALS] + [f"METACARPAL_{r}_{side}" for r in range(1, 6)]
    names += [f"PHALANX_{s}_{r}_{side}" for r in range(1, 6) for s in ("PROXIMAL", "INTERMEDIATE", "DISTAL")
              if not (r == 1 and s == "INTERMEDIATE")]
    return names


@pytest.mark.parametrize("side", ["L", "R"])
def test_hand_is_attached_to_the_wrist(B, side):
    wrist = B[f"RADIUS_{side}"]["tail"]
    for n in _hand(side):
        for end in ("head", "tail"):
            p = B[n][end]
            dist = ((p["x"] - wrist["x"]) ** 2 + (p["y"] - wrist["y"]) ** 2 + (p["z"] - wrist["z"]) ** 2) ** 0.5
            # 0.108 H wrist→fingertip (Drillis & Contini) + lateral spread of the outer rays
            assert dist <= 0.115 * H, f"{n}.{end} is {dist:.3f} m from the wrist"
            assert p["z"] <= wrist["z"] + 1e-9, f"{n}.{end} above the wrist"


@pytest.mark.parametrize("side", ["L", "R"])
def test_fingertips_at_sourced_height(B, side):
    tips = [B[f"PHALANX_DISTAL_{r}_{side}"]["tail"]["z"] for r in range(2, 6)]
    assert min(tips) == pytest.approx(0.377 * H, abs=1e-4)          # Drillis & Contini fingertip


@pytest.mark.parametrize("side", ["L", "R"])
def test_hand_parents_follow_atlas_topology(B, side):
    for ray, carpal in MC_PARENT.items():
        assert B[f"METACARPAL_{ray}_{side}"]["parent"] == f"{carpal}_{side}"
        assert B[f"PHALANX_PROXIMAL_{ray}_{side}"]["parent"] == f"METACARPAL_{ray}_{side}"
    for ray in range(2, 6):
        assert B[f"PHALANX_INTERMEDIATE_{ray}_{side}"]["parent"] == f"PHALANX_PROXIMAL_{ray}_{side}"
        assert B[f"PHALANX_DISTAL_{ray}_{side}"]["parent"] == f"PHALANX_INTERMEDIATE_{ray}_{side}"
    assert B[f"PHALANX_DISTAL_1_{side}"]["parent"] == f"PHALANX_PROXIMAL_1_{side}"


@pytest.mark.parametrize("side,lateral", [("L", 1), ("R", -1)])
def test_thumb_is_lateral_and_fingers_point_down(B, side, lateral):
    assert lateral * (B[f"METACARPAL_1_{side}"]["head"]["x"] - B[f"METACARPAL_5_{side}"]["head"]["x"]) > 0
    for r in range(1, 6):
        mc = B[f"METACARPAL_{r}_{side}"]
        assert mc["tail"]["z"] < mc["head"]["z"]
        assert B[f"PHALANX_PROXIMAL_{r}_{side}"]["head"] == mc["tail"]      # joints are continuous


def test_tpose_hand_stays_with_the_forearm():
    bones = json.loads(default_canonical_json().read_text(encoding="utf-8"))["bones"]
    P = {b["canonical_name"]: b for b in apply_pose(bones, "tpose")}
    for side, sign in (("L", 1), ("R", -1)):
        wrist = P[f"RADIUS_{side}"]["tail"]
        tip = P[f"PHALANX_DISTAL_3_{side}"]["tail"]
        assert sign * (tip["x"] - wrist["x"]) > 0.15                      # hand continues the arm
        assert abs(tip["z"] - wrist["z"]) < 0.05
