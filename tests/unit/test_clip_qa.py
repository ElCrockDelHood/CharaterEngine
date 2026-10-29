"""Clip QA (domain/animation/clip_qa.py): contact, sliding, penetration, loop seam, root vs. stance speed."""

import math

import pytest

from character_engine.domain.animation import clip_qa as qa

DT = 1.0 / 30.0
REST = {"heel": (0.1, 0.03, 0.0), "toe": (0.1, -0.2, 0.0)}
FEET = {"L": ("heel", "toe")}


def gait(n: int, body_speed: float, stance_speed: float, lift: float = 0.1, offset_z: float = 0.0):
    """One foot over ``n`` frames: first half planted (moving back at ``stance_speed`` relative to the world
    origin), second half swinging forward ``lift`` m above the ground; the body moves at ``body_speed``."""
    frames, x = [], 0.0
    for i in range(n):
        planted = i < n // 2
        y = -body_speed * i * DT + (stance_speed * i * DT if planted else 0.0)
        z = offset_z if planted else lift + offset_z
        frames.append({"heel": (0.1 + x, 0.03 + y, z), "toe": (0.1 + x, -0.2 + y, z),
                       "root": (0.0, -body_speed * i * DT, 0.0), "SACRUM": (0.0, -body_speed * i * DT, 1.0)})
    return frames


def test_classify_and_loop_flag():
    assert qa.classify("Jog_Fwd_Loop") == "locomotion"
    assert qa.classify("Sword_Attack") == "combat"
    assert qa.classify("Swim_Idle_Loop") == "swim"
    assert qa.classify("Crouch_Idle_Loop") == "idle"
    assert qa.classify("Crouch_Fwd_Loop") == "locomotion"
    assert qa.classify("Totally_New_Clip") == "other"
    assert qa.is_loop("Walk_Loop") and not qa.is_loop("Death01")


def test_detect_contacts_uses_rest_height_and_ground_offset():
    assert qa.detect_contacts([0.0, 0.02, 0.05], rest_z=0.0, offset=0.0, threshold_m=0.03) == [True, True, False]
    # whole clip 5 cm low: the offset re-centres the ground
    assert qa.detect_contacts([-0.05, -0.03, 0.0], rest_z=0.0, offset=-0.05, threshold_m=0.03) == [True, True, False]


def test_sliding_only_counts_consecutive_contact_frames():
    pos = [(0, 0, 0), (0.01, 0, 0), (0.5, 0, 0), (0.51, 0, 0)]
    s = qa.sliding(pos, [True, True, False, True], DT)
    assert s.contact_steps == 1
    assert s.mean_m_s == pytest.approx(0.01 / DT)
    assert s.distance_m == pytest.approx(0.01)
    with pytest.raises(ValueError):
        qa.sliding(pos, [True], DT)


def test_contact_phases_and_stance_length():
    contacts = [True, True, False, False, True, True, True]
    assert qa.contact_phases(contacts) == [(0, 1), (4, 6)]
    pos = [(0, 0, 0), (0, -0.1, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0.2, 0), (0, 0.4, 0)]
    assert qa.stance_length(pos, contacts) == pytest.approx(0.4)


def test_root_motion_speed_is_horizontal_displacement_over_duration():
    rm = qa.root_motion([(0, 0, 0), (0, -1, 0.1), (0, -2, 0.0)], 0.5)
    assert rm.displacement_m == pytest.approx(2.0)
    assert rm.duration_s == pytest.approx(1.0)
    assert rm.speed_m_s == pytest.approx(2.0)
    assert qa.root_motion([], DT).speed_m_s is None


def test_planted_foot_in_root_motion_world_does_not_slide():
    frames = gait(30, body_speed=3.0, stance_speed=3.0)   # stance cancels body motion: planted in world
    out = qa.feet_qa(frames, REST, FEET, DT)
    assert out["ground_contact"]
    assert out["slide_mean_m_s"] == pytest.approx(0.0, abs=1e-9)
    assert out["penetration_m"] == pytest.approx(0.0)


def test_inplace_stance_speed_measures_the_speed_the_feet_imply():
    inplace = gait(30, body_speed=0.0, stance_speed=3.0)
    out = qa.feet_qa(inplace, REST, FEET, DT)
    assert out["stance_speed_m_s"] == pytest.approx(3.0)
    assert out["stance_length_m"] == pytest.approx(3.0 * 14 * DT)


def test_penetration_and_floating():
    low = qa.feet_qa(gait(30, 0.0, 0.0, offset_z=-0.04), REST, FEET, DT)
    assert low["penetration_m"] == pytest.approx(0.04)
    high = qa.feet_qa(gait(30, 0.0, 0.0, offset_z=0.2), REST, FEET, DT)
    assert not high["ground_contact"]          # above the airborne limit: no contact measured


def test_evaluate_clip_flags_a_root_twice_as_fast_as_the_feet():
    inplace = gait(30, body_speed=0.0, stance_speed=2.5)
    rm = gait(30, body_speed=5.0, stance_speed=2.5)     # root channel 2x what the feet support
    rec = qa.evaluate_clip("Jog_Fwd_Loop", dt=DT, inplace_target=inplace, rm_target=rm, target_rest=REST,
                           target_feet=FEET, inplace_source=inplace, rm_source=rm, source_rest=REST,
                           source_feet=FEET, seam_points=("heel", "toe"))
    assert rec["root_motion_source"]["speed_m_s"] == pytest.approx(5.0)
    assert rec["stance_speed_source_m_s"] == pytest.approx(2.5)
    assert rec["root_to_stance_speed_ratio"] == pytest.approx(2.0)
    assert rec["checks"]["root_speed_vs_feet"] == "fail"
    assert rec["checks"]["foot_sliding"] == "fail"           # 2.5 m/s residual slide in world space
    assert rec["status"] == "fail" and rec["provenance"] == "ESTIMATE"


def test_evaluate_clip_consistent_root_passes():
    inplace = gait(30, body_speed=0.0, stance_speed=3.0)
    rm = gait(30, body_speed=3.0, stance_speed=3.0)
    rec = qa.evaluate_clip("Walk_Fwd", dt=DT, inplace_target=inplace, rm_target=rm, target_rest=REST,
                           target_feet=FEET, inplace_source=inplace, rm_source=rm, source_rest=REST,
                           source_feet=FEET)
    assert rec["root_to_stance_speed_ratio"] == pytest.approx(1.0)
    assert rec["checks"]["root_speed_vs_feet"] == "ok"
    assert rec["checks"]["foot_sliding"] == "ok"
    assert "loop_seam" not in rec                           # not a *_Loop clip


def test_root_travelling_over_planted_feet_is_a_glide():
    inplace = gait(30, body_speed=0.0, stance_speed=0.0)     # feet never move back: no stepping
    rm = gait(30, body_speed=1.0, stance_speed=0.0)
    rec = qa.evaluate_clip("Sword_Dash", dt=DT, inplace_target=inplace, rm_target=rm, target_rest=REST,
                           target_feet=FEET, inplace_source=inplace, rm_source=rm, source_rest=REST,
                           source_feet=FEET)
    assert rec["root_glide"] is True
    assert rec["root_to_stance_speed_ratio"] is None
    assert rec["checks"]["root_speed_vs_feet"] == "fail"


def test_loop_seam_closed_and_open():
    n = 31
    closed = [{"p": (math.sin(2 * math.pi * i / (n - 1)), 0.0, 1.0)} for i in range(n)]
    seam = qa.loop_seam(closed, DT)
    assert seam.duplicated_end
    assert seam.position_m == pytest.approx(0.0, abs=1e-9)
    assert seam.excess_m_s < 0.05
    opened = [{"p": (0.01 * i, 0.0, 1.0)} for i in range(n)]
    assert qa.loop_seam(opened, DT).position_m == pytest.approx(0.3)
    with pytest.raises(ValueError):
        qa.loop_seam(closed[:3], DT)


def test_loop_seam_turnaround_at_the_wrap_is_not_a_discontinuity():
    # foot swinging forward and back, at its most forward point on frame 0 (velocity reverses there)
    n = 31
    swing = [{"p": (0.0, -0.4 * math.cos(2 * math.pi * i / (n - 1)), 0.1)} for i in range(n)]
    seam = qa.loop_seam(swing, DT)
    assert seam.velocity_jump_m_s > 0.5                  # a real change of velocity at the wrap...
    assert seam.excess_m_s == pytest.approx(0.0, abs=1e-6)   # ...no larger than elsewhere in the clip


def test_loop_seam_flags_a_kink_only_at_the_wrap():
    # constant-speed back-and-forth with a velocity kink introduced at the wrap
    n = 31
    pts = [{"p": (0.0, 0.01 * i, 0.0)} for i in range(n - 1)] + [{"p": (0.0, 0.0, 0.0)}]
    seam = qa.loop_seam(pts, DT)
    assert seam.duplicated_end
    assert seam.excess_m_s > 1.0


def test_swim_clips_skip_ground_checks():
    frames = gait(30, 0.0, 1.0, offset_z=0.5)
    rec = qa.evaluate_clip("Swim_Fwd_Loop", dt=DT, inplace_target=frames, rm_target=None, target_rest=REST,
                           target_feet=FEET)
    assert rec["checks"]["foot_sliding"] == "n/a"
    assert rec["checks"]["ground_penetration"] == "n/a"


def test_thresholds_are_estimates_and_summary_counts():
    assert qa.PROVENANCE == "ESTIMATE"
    recs = [{"category": "locomotion", "status": "fail", "checks": {"foot_sliding": "fail"}},
            {"category": "locomotion", "status": "ok", "checks": {}},
            {"category": "idle", "status": "warn", "checks": {"loop_seam": "warn"}}]
    s = qa.summarize(recs)
    assert s["locomotion"]["clips"] == 2 and s["locomotion"]["fail"] == 1
    assert s["locomotion"]["failed_checks"] == {"foot_sliding": 1}
    assert s["idle"]["warn"] == 1
    assert qa.worst_status(["n/a", "ok", "warn"]) == "warn"
    assert qa.worst_status(["n/a"]) == "ok"
