"""Decision 89: quality tolerances in force (first batch, ESTIMATE), their judges and today's measurements.

Committed measurements (A20, A22, the face contract) are judged here on every run. Measurements that live in
``builds/`` (batch retarget, Blender headless, Godot perf) need Blender, Godot, the mocap library or the GT 740M:
their tests skip with the reason when the report is not on this machine. A known failure is an ``xfail(strict=True)``
with its measured value, never a relaxed limit: when it gets fixed the test turns red and asks for the update.
"""

import json
import sys
from pathlib import Path

import pytest

from character_engine.domain.animation import leg_quality as lq
from character_engine.domain.quality import tolerances as tq
from character_engine.domain.rigging.face import ARKIT_52, GAME_FACE_SHAPES

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import quality_report as qr  # noqa: E402

A20 = ROOT / "docs" / "audit" / "A20_F2_LONG_BONES_FIT.json"
A22 = ROOT / "docs" / "audit" / "A22_SKELETON_REGIONS_FIT.json"


def _json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _report(key):
    p = qr.DEFAULTS[key]
    if not p.exists():
        pytest.skip(f"{p.relative_to(ROOT)} not on this machine (needs the engine run named in its tolerance)")
    return _json(p)


# --- the table: exactly the approved batch, with the approved limits ---------------------------------------------

APPROVED = {("AN-1", "all"): {"rms_mm": 4.0}, ("AN-3", "all"): {"mean_mm": 2.5, "p95_mm": 6.0},
            ("MO-2", "game"): {"abs_m": 0.01}, ("MO-2", "cinema"): {"abs_m": 0.003},
            ("MO-3", "game"): {"median_deg": 5.0, "p90_deg": 10.0}, ("MO-3", "cinema"): {"median_deg": 3.0, "p90_deg": 6.0},
            ("RG-1", "all"): {"max_mm": 0.1}, ("RG-6", "game"): {"max_shapes": 20}, ("RG-6", "cinema"): {"shapes": 52},
            ("PF-1", "game"): {"mean_ms": 16.7, "p95_ms": 20.0}, ("PF-4", "cinema"): {"seconds": 30.0}}


def test_table_is_the_approved_first_batch():
    assert {(t.id, t.profile): t.limit for t in tq.TOLERANCES} == APPROVED
    assert set(tq.IN_FORCE) == {t.id for t in tq.TOLERANCES} and len(tq.IN_FORCE) == 8
    assert all(t.provenance == "ESTIMATE" for t in tq.TOLERANCES)
    assert {t.id for t in tq.TOLERANCES if t.level == "Q0"} == {"PF-1", "PF-4"}


def test_doc_lists_every_tolerance_in_force():
    doc = (ROOT / "docs" / "architecture" / "QUALITY_TOLERANCES.md").read_text(encoding="utf-8")
    for tid in tq.IN_FORCE:
        assert f"| {tid} |" in doc, tid
    assert "Decision 89" in doc


# --- judges at their limits ---------------------------------------------------------------------------------------

def test_an1_limit_is_inclusive():
    assert tq.judge_an1([{"bone": "X", "side": "L", "rms_mm": 4.0}]).status == tq.PASS
    v = tq.judge_an1([{"bone": "X", "side": "L", "rms_mm": 4.001}])
    assert v.status == tq.FAIL and v.measured["over"] == ["X_L 4.00"]
    assert tq.judge_an1(None).status == tq.NOT_MEASURED


def test_an3_needs_both_mean_and_p95():
    assert tq.judge_an3({"P": {"mean_mm": 2.5, "p95_mm": 6.0}}).status == tq.PASS
    assert tq.judge_an3({"P": {"mean_mm": 2.6, "p95_mm": 1.0}}).status == tq.FAIL
    assert tq.judge_an3({"P": {"mean_mm": 1.0, "p95_mm": 6.1}}).status == tq.FAIL


def _clip(cat, sole, knee_med=1.0, knee_p90=2.0):
    return {"library": "lib", "clip": "c", "category": cat,
            "legs": {"rm": {"sole_median_m": sole, "knee_median_deg": knee_med, "knee_p90_deg": knee_p90}}}


def test_mo2_by_profile_and_jumps_excluded():
    assert tq.judge_mo2([_clip("idle", -0.008)], "game").status == tq.PASS
    assert tq.judge_mo2([_clip("idle", -0.008)], "cinema").status == tq.FAIL
    assert tq.judge_mo2([_clip("jump", -0.11), _clip("idle", 0.001)], "cinema").status == tq.PASS
    assert tq.judge_mo2([_clip("swim", -1.4), _clip("idle", 0.001)], "cinema").status == tq.PASS   # no ground
    assert tq.judge_mo2([], "game").status == tq.NOT_MEASURED


def test_mo3_by_profile():
    assert tq.judge_mo3([_clip("idle", 0, 4.0, 9.0)], "game").status == tq.PASS
    assert tq.judge_mo3([_clip("idle", 0, 4.0, 9.0)], "cinema").status == tq.FAIL
    assert tq.judge_mo3([_clip("idle", 0, 1.0, 10.5)], "game").status == tq.FAIL


def test_rg1_pf1_pf4_limits_and_missing_inputs():
    assert tq.judge_rg1(0.1).status == tq.PASS and tq.judge_rg1(0.11).status == tq.FAIL
    assert tq.judge_rg1(None).status == tq.NOT_MEASURED
    assert tq.judge_pf1("GeForce GT 740M", {"avg_ms": 16.7, "p95_ms": 20.0}).status == tq.PASS
    assert tq.judge_pf1("GeForce GT 740M", {"avg_ms": 10.0, "p95_ms": 21.0}).status == tq.FAIL
    assert tq.judge_pf1("GeForce RTX 4060", {"avg_ms": 1.0, "p95_ms": 1.0}).status == tq.NOT_MEASURED  # not Q0 hardware
    assert tq.judge_pf4(30.0).status == tq.PASS and tq.judge_pf4(30.5).status == tq.FAIL


# --- leg metrics (MO-2 / MO-3 inputs) -----------------------------------------------------------------------------

def _legs(knee_y_src, knee_y_dst, toe_z, side_offset=0.0, frames=1):
    """One frame and the rest pose of both legs. Rest legs are straight; ``side_offset`` puts the target knee that far
    to the side of its hip-ankle line in rest *and* in the frame (a fixed rig difference, like the canonical 13.5 mm)."""
    rest_s, rest_t, src, dst = {"pelvis": (0, 0, 0.95)}, {}, {"pelvis": (0, 0, 0.93)}, {}
    for side, x in (("L", 0.1), ("R", -0.1)):
        s, o = side.lower(), (side_offset if side == "L" else -side_offset)
        for pts, ky in ((rest_s, 0.0), (src, knee_y_src)):
            pts.update({f"thigh_{s}": (x, 0, 0.9), f"thigh_{s}.tail": (x, ky, 0.45), f"thigh_{s}.x": (x + 0.1, 0, 0.9),
                        f"calf_{s}": (x, ky, 0.45), f"foot_{s}": (x, 0, 0.08),
                        f"ball_{s}": (x, -0.1, 0.0), f"ball_{s}.tail": (x, -0.15, 0.0)})
        for pts, ky, tz in ((rest_t, 0.0, 0.0), (dst, knee_y_dst, toe_z)):
            pts.update({f"FEMUR_{side}": (x, 0, 0.95), f"FEMUR_{side}.tail": (x + o, ky, 0.5),
                        f"FEMUR_{side}.x": (x + 0.1, 0, 0.95), f"TIBIA_{side}": (x + o, ky, 0.46),
                        f"TALUS_{side}": (x, 0, 0.07), f"CALCANEUS_{side}": (x, 0.05, tz),
                        f"TOE_PHALANX_PROXIMAL_3_{side}": (x, -0.1, tz), f"TOE_PHALANX_PROXIMAL_3_{side}.tail": (x, -0.15, tz)})
    return [src] * frames, [dst] * frames, rest_s, rest_t


def test_leg_metrics_on_a_known_pose():
    src, dst, rs, rt = _legs(-0.15, -0.15, -0.006, frames=12)    # 12 still frames: 11 with a speed, 2 feet
    rec = lq.clip_legs(src, dst, rs, rt)
    assert rec["sole_median_m"] == pytest.approx(-0.006) and rec["stance_samples"] == 22
    assert rec["knee_median_deg"] == pytest.approx(0.0, abs=1e-6) and rec["knee_samples"] == 24
    src, dst, rs, rt = _legs(-0.15, 0.15, 0.0)                     # target knee bends backwards
    assert lq.clip_legs(src, dst, rs, rt)["knee_median_deg"] == pytest.approx(180.0)


def test_knee_hinge_axis_and_minimum_bend():
    """Decision 89 amendment 2: the hinge axis (thigh x shin) is judged only past a 15 deg source bend."""
    assert lq.MIN_FLEXION_DEG == 15.0
    src, dst, _, _ = _legs(-0.15, 0.0, 0.0)                        # source bent about 37 deg, target leg straight
    errors, excluded = lq.knee_errors(src, dst)
    assert errors == [90.0, 90.0] and excluded == 0
    src, dst, _, _ = _legs(-0.15, -0.15, 0.0)                      # same bend: axes agree
    errors, _ = lq.knee_errors(src, dst)
    assert max(errors) == pytest.approx(0.0, abs=1e-6)


def test_stance_means_support():
    """Decision 89 amendment 3: a moving foot, a lying body or too few frames give no MO-2 value."""
    src, dst, rs, rt = _legs(-0.15, -0.15, -0.006, frames=12)
    moving = [{k: ((v[0], v[1] + 0.02 * i, v[2]) if k.startswith(("foot", "ball")) else v) for k, v in f.items()}
              for i, f in enumerate(src)]                          # 0.6 m/s at 30 fps: sliding, not a support
    assert lq.clip_legs(moving, dst, rs, rt)["sole_median_m"] is None
    lying = [{**f, "pelvis": (0, 0, 0.30)} for f in src]           # pelvis 0.65 m below rest
    assert lq.clip_legs(lying, dst, rs, rt)["sole_median_m"] is None
    src, dst, rs, rt = _legs(-0.15, -0.15, -0.006, frames=5)       # 8 support frames < 10
    assert lq.clip_legs(src, dst, rs, rt)["sole_median_m"] is None


def test_straight_source_leg_carries_no_knee_direction():
    src, dst, rs, rt = _legs(-0.05, -0.05, 0.0)                    # about 12.6 deg of bend: under the 15 deg minimum
    rec = lq.clip_legs(src, dst, rs, rt)
    assert rec["knee_samples"] == 0 and rec["knee_excluded_frames"] == 2


# --- today's measurements -----------------------------------------------------------------------------------------

def test_an1_long_bone_fit_passes():
    v = tq.judge_an1(qr.an1_rows(_json(A20)))
    assert v.status == tq.PASS and v.measured["bone_sides"] == 12, v.measured


def test_an3_passes_with_its_one_documented_exception():
    """Decision 89 amendment 3: INFERIOR_NASAL_CONCHA is a documented exception (BodyParts3D subject), shown in the
    verdict; any other pair over the limit still fails."""
    v = tq.judge_an3(qr.an3_pairs(_json(A22)))
    assert v.status == tq.PASS and v.measured["pairs"] == 83, v.measured["over"]
    assert set(v.measured["exceptions"]) == {"INFERIOR_NASAL_CONCHA"} and "exceptions applied" in v.detail


def test_an3_exception_evidence_still_matches():
    """The exception holds only while the pair measures what was recorded; a fix or a new reference turns this red."""
    e = next(x for x in tq.EXCEPTIONS if x.id == "AN-3" and x.item == "INFERIOR_NASAL_CONCHA")
    pair = qr.an3_pairs(_json(A22))["INFERIOR_NASAL_CONCHA"]
    assert {k: round(pair[k], 2) for k, _ in e.evidence} == dict(e.evidence)


def test_an3_exception_does_not_carry_to_another_reference():
    v = tq.judge_an3({"INFERIOR_NASAL_CONCHA": {"mean_mm": 2.43, "p95_mm": 8.15}}, reference="another atlas")
    assert v.status == tq.FAIL and not v.measured["exceptions"]


def test_rg6_face_contract_counts():
    assert tq.judge_rg6(len(GAME_FACE_SHAPES), "game").status == tq.PASS
    assert tq.judge_rg6(len(ARKIT_52), "cinema").status == tq.PASS


@pytest.mark.skip(reason="RG-6 asset part: no head mesh with ARKit blend shapes exists yet (Decision 89)")
def test_rg6_on_a_head_mesh():
    pass


def test_rg1_and_pf4_from_the_blender_report():
    rg1, pf4 = qr.blender_checks(_report("blender"))
    assert tq.judge_rg1(rg1).status == tq.PASS, rg1
    assert tq.judge_pf4(pf4).status == tq.PASS, pf4


def test_pf1_from_the_godot_perf_report():
    adapter, arena = qr.perf_arena(_report("perf"))
    v = tq.judge_pf1(adapter, arena)
    if v.status == tq.NOT_MEASURED:
        pytest.skip(v.detail)
    assert v.status == tq.PASS, v.measured


def test_mo2_sole_height_from_the_retarget_report():
    clips = _report("retarget")["clips"]
    assert tq.judge_mo2(clips, "game").status == tq.PASS and tq.judge_mo2(clips, "cinema").status == tq.PASS


TUCKED = {"ual2/NinjaJump_Idle_Loop", "ual2/NinjaJump_Start"}   # knee bent about 155 deg in the air


@pytest.mark.xfail(strict=True, reason="MO-3 fails today on 2 of 84 clips (batch retarget 2026-11-26), knee bent "
                                       "about 155 deg in the air where rotations are copied without grounding: "
                                       "NinjaJump_Idle_Loop median 6.8 / p90 7.5 deg, NinjaJump_Start 6.7 / 7.2; "
                                       "Decision 89 amendment 3. Limits unchanged.")
def test_mo3_knee_direction_from_the_retarget_report():
    clips = _report("retarget")["clips"]
    assert tq.judge_mo3(clips, "game").status == tq.PASS and tq.judge_mo3(clips, "cinema").status == tq.PASS


def test_mo3_fails_only_on_the_recorded_tucked_clips():
    """Not an xfail: a knee failure outside the two recorded clips turns this red (landings fixed, amendment 3)."""
    clips = _report("retarget")["clips"]
    for profile in ("game", "cinema"):
        assert set(tq.judge_mo3(clips, profile).measured.get("over", {})) <= TUCKED, profile
