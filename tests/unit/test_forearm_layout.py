"""Finding A11: in the anatomical position (palms −Y) the radius is lateral to the ulna.

Left = +X (Decision 17), so RADIUS_L has the larger x and RADIUS_R the smaller (more negative) x;
the two forearm bones lie side by side in X, not one in front of the other in Y.
"""

import json
import math

import pytest

from character_engine.domain.character.templates import default_canonical_json


@pytest.fixture(scope="module")
def B():
    return {b["canonical_name"]: b for b in json.loads(default_canonical_json().read_text(encoding="utf-8"))["bones"]}


@pytest.mark.parametrize("side,lateral", [("L", 1), ("R", -1)])
def test_radius_is_lateral_to_ulna(B, side, lateral):
    for end in ("head", "tail"):
        r, u = B[f"RADIUS_{side}"][end], B[f"ULNA_{side}"][end]
        assert lateral * (r["x"] - u["x"]) > 0.02, f"{side} {end}: radius must be lateral (thumb side)"
        assert abs(r["y"] - u["y"]) < 1e-6, f"{side} {end}: radius/ulna must not be split antero-posteriorly"


@pytest.mark.parametrize("side", ["L", "R"])
def test_forearm_lengths_and_heights_kept(B, side):
    for n in (f"RADIUS_{side}", f"ULNA_{side}"):
        h, t = B[n]["head"], B[n]["tail"]
        assert math.dist((h["x"], h["y"], h["z"]), (t["x"], t["y"], t["z"])) == pytest.approx(0.2409, abs=1e-4)
        assert (h["z"], t["z"]) == pytest.approx((1.1139, 0.873), abs=1e-4)    # elbow / wrist landmarks
