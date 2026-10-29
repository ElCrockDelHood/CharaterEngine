"""Per-clip root scale from the measured stance speed (domain/animation/stance_scale.py)."""

import pytest

from character_engine.domain.animation import stance_scale as ss

DT = 1.0 / 30.0
REST = {"ball": (0.1, -0.15, 0.0)}


def walk(n: int, stance_speed: float, hips_y_speed: float = 0.0):
    """Foot planted for the first half (moving back relative to the hips), swinging 10 cm up afterwards."""
    frames = []
    for i in range(n):
        planted = i < n // 2
        hips_y = -hips_y_speed * i * DT
        rel_y = stance_speed * i * DT if planted else 0.0
        frames.append({"ball": (0.1, -0.15 + hips_y + rel_y, 0.0 if planted else 0.1), ss.HIPS: (0.0, hips_y, 1.0)})
    return frames


def test_stance_speed_is_measured_relative_to_the_hips():
    # root motion moves hips and foot together: the relative stance speed is unchanged
    assert ss.stance_speed(walk(30, 1.0), REST, ["ball"], DT).speed_m_s == pytest.approx(1.0)
    assert ss.stance_speed(walk(30, 1.0, hips_y_speed=1.0), REST, ["ball"], DT).speed_m_s == pytest.approx(1.0)


def test_scale_is_target_over_source():
    r = ss.stance_scale(walk(30, 1.0), REST, ["ball"], walk(30, 1.15), REST, ["ball"], DT)
    assert r.reason == "measured"
    assert r.scale == pytest.approx(1.15)


def test_no_stepping_or_no_points_gives_no_scale():
    idle = ss.stance_scale(walk(30, 0.0), REST, ["ball"], walk(30, 0.0), REST, ["ball"], DT)
    assert idle.scale is None and idle.reason == "feet do not step"
    empty = ss.stance_scale([], {}, [], [], {}, [], DT)
    assert empty.scale is None and empty.reason == "too few planted frames"


def test_implausible_ratio_is_rejected():
    r = ss.stance_scale(walk(30, 0.5), REST, ["ball"], walk(30, 3.0), REST, ["ball"], DT)
    assert r.scale is None and r.reason.startswith("ratio")
