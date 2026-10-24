"""T-pose transform, stature retarget core and character templates."""

import math

import pytest

from character_engine.domain.anatomy.pose import POSES, apply_pose, apply_tpose, arm_subtree
from character_engine.domain.anatomy.proportions.stature_retarget import (
    DRILLIS_CONTINI_RATIOS,
    PiecewiseLinear,
    measure_landmarks,
    retarget_stature,
)
from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.character import (
    TEMPLATES,
    CharacterParameters,
    Species,
    build_character_bones,
    get_template,
    load_canonical_bones,
)


@pytest.fixture(scope="module")
def canonical():
    bones, _ = load_canonical_bones()
    return bones


def _index(bones):
    return {b["canonical_name"]: b for b in bones}


def _length(b):
    return math.dist((b["head"]["x"], b["head"]["y"], b["head"]["z"]), (b["tail"]["x"], b["tail"]["y"], b["tail"]["z"]))


# ---------------------------------------------------------------- T-pose ----------------

def test_tpose_arms_horizontal_and_lateral(canonical):
    posed = _index(apply_tpose(canonical))
    for side, sign in (("L", 1.0), ("R", -1.0)):   # left = +X (Decision 17)
        hum = posed[f"HUMERUS_{side}"]
        assert hum["tail"]["z"] == pytest.approx(hum["head"]["z"], abs=1e-3), "humerus must be horizontal"
        assert sign * (hum["tail"]["x"] - hum["head"]["x"]) > 0.25, "arm must point laterally (+X left, -X right)"
        rad = posed[f"RADIUS_{side}"]
        assert sign * (rad["tail"]["x"] - rad["head"]["x"]) > 0.2
        fingertip = posed[f"PHALANX_DISTAL_3_{side}"]["tail"]
        assert sign * fingertip["x"] > abs(hum["head"]["x"]) + 0.5


def test_tpose_preserves_bone_lengths_and_non_arm_bones(canonical):
    before, after = _index(canonical), _index(apply_tpose(canonical))
    arm = arm_subtree(canonical, "L") | arm_subtree(canonical, "R")
    for name, b in before.items():
        assert _length(after[name]) == pytest.approx(_length(b), abs=2e-4), name
        if name not in arm:
            assert after[name]["head"] == b["head"] and after[name]["tail"] == b["tail"], name


def test_tpose_is_rigid_per_arm(canonical):
    """Distances between any two joints inside the same arm are preserved."""
    before, after = _index(canonical), _index(apply_tpose(canonical))
    a, b = before["HUMERUS_L"]["head"], before["PHALANX_DISTAL_2_L"]["tail"]
    a2, b2 = after["HUMERUS_L"]["head"], after["PHALANX_DISTAL_2_L"]["tail"]
    d = math.dist((a["x"], a["y"], a["z"]), (b["x"], b["y"], b["z"]))
    d2 = math.dist((a2["x"], a2["y"], a2["z"]), (b2["x"], b2["y"], b2["z"]))
    assert d2 == pytest.approx(d, abs=1e-3)


def test_apply_pose_names(canonical):
    assert set(POSES) >= {"anatomical", "tpose", "apose"}
    assert apply_pose(canonical, "anatomical") == canonical
    apose = _index(apply_pose(canonical, "apose"))
    tpose = _index(apply_pose(canonical, "tpose"))
    assert apose["HUMERUS_R"]["tail"]["z"] < tpose["HUMERUS_R"]["tail"]["z"]
    with pytest.raises(ValueError):
        apply_pose(canonical, "handstand")


# ---------------------------------------------------------------- retarget --------------

def test_piecewise_linear_hits_anchors_and_extrapolates():
    f = PiecewiseLinear([(0.0, 0.0), (1.0, 2.0), (2.0, 3.0)])
    assert f(0.0) == 0.0 and f(1.0) == 2.0 and f(2.0) == 3.0
    assert f(0.5) == pytest.approx(1.0) and f(1.5) == pytest.approx(2.5)
    assert f(3.0) == pytest.approx(4.0)
    with pytest.raises(ValueError):
        PiecewiseLinear([(0.0, 0.0), (1.0, 0.0)])


def test_canonical_is_at_180_landmarks(canonical):
    lm = measure_landmarks(canonical)
    assert lm["vertex"] == pytest.approx(1.80, abs=1e-3)
    for key in ("shoulder", "hip", "knee", "ankle", "wrist", "elbow"):
        assert lm[key] == pytest.approx(DRILLIS_CONTINI_RATIOS[key] * 1.80, abs=2e-3), key


def test_retarget_reaches_target_landmarks(canonical):
    bones, report = retarget_stature(canonical, 1.65)
    lm = measure_landmarks(bones)
    for key, ratio in DRILLIS_CONTINI_RATIOS.items():
        assert lm[key] == pytest.approx(ratio * 1.65, abs=2e-3), key
    assert report["source_id"] == "DRILLIS_CONTINI_1966"
    assert len(bones) == len(canonical)
    with pytest.raises(ValueError):
        retarget_stature(canonical, 0.0)


# ---------------------------------------------------------------- templates -------------

def test_templates_have_explicit_provenance():
    for tid, t in TEMPLATES.items():
        assert t.template_id == tid
        assert isinstance(t.stature_provenance, ProvenanceState)
        assert isinstance(t.proportion_provenance, ProvenanceState)
        assert t.notes, tid
        if t.proportion_provenance in (ProvenanceState.PLACEHOLDER, ProvenanceState.UNKNOWN):
            assert "PLACEHOLDER" in t.notes or "No canonical" in t.notes, tid


def test_animal_templates_are_disabled_and_refuse_to_build():
    horse = get_template("horse_adult")
    assert not horse.available and horse.params.species == Species.HORSE
    assert horse.proportion_provenance == ProvenanceState.UNKNOWN
    with pytest.raises(NotImplementedError):
        build_character_bones(horse.params)


def test_elderly_uses_trotter_gleser_ageing_correction():
    elderly = get_template("human_male_elderly_75y")
    assert elderly.params.stature_m == pytest.approx(1.80 - 0.0006 * 45, abs=1e-4)
    assert elderly.stature_provenance == ProvenanceState.DERIVED


@pytest.mark.parametrize("tid", ["human_male_adult", "human_female_adult", "human_child_5y", "human_child_10y"])
def test_build_human_templates_in_tpose(tid, canonical):
    t = get_template(tid)
    bones, report = build_character_bones(t.params, canonical_bones=canonical)
    top = max(max(b["head"]["z"], b["tail"]["z"]) for b in bones)
    ground = min(min(b["head"]["z"], b["tail"]["z"]) for b in bones)
    assert top == pytest.approx(t.params.stature_m, abs=2e-3)
    assert ground == pytest.approx(0.0, abs=2e-3)
    assert report["pose"] == "tpose" and report["stature_m"] == t.params.stature_m
    hum = _index(bones)["HUMERUS_R"]
    assert hum["tail"]["z"] == pytest.approx(hum["head"]["z"], abs=1e-3)


def test_parameters_with_override():
    p = CharacterParameters(stature_m=1.80).with_(stature_m=1.70, pose="anatomical")
    assert p.stature_m == 1.70 and p.pose == "anatomical"
    with pytest.raises(KeyError):
        get_template("elf")
