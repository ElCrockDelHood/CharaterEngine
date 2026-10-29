"""Render views spec (pipeline/render_views.py): parsing, refusals, engine presets, orbit camera and framing."""

import math
from pathlib import Path

import pytest

from character_engine.pipeline.batch_export import BatchSpecError, load_spec
from character_engine.pipeline.render_views import (
    ENGINES,
    VIEWS,
    framing_distance,
    orbit_camera,
    output_names,
    parse,
    turntable_azimuths,
)

ROOT = Path(__file__).resolve().parents[2]
BODY = [{"templates": ["human_male_adult"], "poses": ["tpose"]}]


def test_default_spec_is_workbench_with_three_views_sheet_and_turntable():
    spec = parse(load_spec(ROOT / "scripts" / "render_specs" / "default.json"), root=ROOT)
    assert [j.name for j in spec.jobs] == ["human_male_adult_1800mm_tpose", "human_female_adult_1650mm_tpose"]
    assert spec.engine == "WORKBENCH" and spec.preset.blender_engine == "BLENDER_WORKBENCH"
    assert spec.views == ("front", "side", "back") and spec.contact_sheet
    assert spec.turntable.frames == 24 and spec.turntable.mp4 is False
    assert spec.effective_samples is None and spec.settings()["device"] is None


def test_overrides_select_opt_in_engines_and_samples():
    spec = parse({"matrices": BODY}, overrides={"engine": "cycles", "device": "cpu", "samples": 8, "views": None})
    assert (spec.engine, spec.device, spec.effective_samples) == ("CYCLES", "CPU", 8)
    assert parse({"matrices": BODY, "engine": "EEVEE"}).effective_samples == ENGINES["EEVEE"].samples
    assert parse({"matrices": BODY, "engine": "WORKBENCH", "samples": 64}).effective_samples is None


def test_every_error_is_reported_and_unavailable_templates_refused():
    with pytest.raises(BatchSpecError) as exc:
        parse({"matrices": [{"templates": ["horse_adult"], "poses": ["tpose"]}], "engine": "OCTANE",
               "device": "TPU", "samples": 0, "resolution": [10, 10], "views": ["top"],
               "turntable": {"frames": 2, "fps": 3}, "colour": 1})
    text = "\n".join(exc.value.errors)
    for needle in ("'horse_adult' refused", "unknown engine 'OCTANE'", "unknown device 'TPU'", "samples 0",
                   "'resolution' must be", "views ['top']", "turntable frames 2", "unknown keys ['fps']",
                   "unknown keys ['colour']"):
        assert needle in text, needle


def test_device_only_applies_to_cycles_and_clips_are_refused():
    with pytest.raises(BatchSpecError, match="only applies to CYCLES"):
        parse({"matrices": BODY, "engine": "EEVEE", "device": "GPU"})
    clip = {"path": "a.glb", "bone_map": "quaternius_ual"}
    with pytest.raises(BatchSpecError, match="clips are not rendered yet"):
        parse({"matrices": [{**BODY[0], "clips": [clip]}]})
    with pytest.raises(BatchSpecError, match="distinct"):
        parse({"matrices": BODY, "views": ["front", "front"]})


def test_turntable_can_be_disabled_and_output_names_follow_the_spec():
    spec = parse({"matrices": BODY, "turntable": None, "views": ["side"], "contact_sheet": False})
    assert spec.turntable is None and output_names(spec) == ["side.png", "render.json"]
    spec = parse({"matrices": BODY, "turntable": {"frames": 4, "mp4": True}})
    names = output_names(spec)
    assert names[:4] == ["front.png", "side.png", "back.png", "contact_sheet.png"]
    assert names[4:] == ["turntable/0001.png", "turntable/0002.png", "turntable/0003.png", "turntable/0004.png",
                         "turntable.mp4", "render.json"]


def test_turntable_azimuths_loop_without_repeating_the_first_frame():
    assert turntable_azimuths(4) == [0.0, 90.0, 180.0, 270.0]
    assert len(turntable_azimuths(24)) == 24 and turntable_azimuths(24)[-1] == pytest.approx(345.0)


@pytest.mark.parametrize("view, expected", [("front", (0.0, -5.0)), ("side", (5.0, 0.0)), ("back", (0.0, 5.0))])
def test_orbit_camera_follows_the_canonical_frame(view, expected):
    """Body faces -Y with its left at +X: front camera on -Y, side camera on the left (+X), back on +Y."""
    loc, rot = orbit_camera((0.0, 0.0, 1.0), 5.0, VIEWS[view])
    assert loc[:2] == pytest.approx(expected, abs=1e-9) and loc[2] == 1.0
    a = rot[2]
    # Euler (90 deg, 0, a) looks along (-sin a, cos a, 0): straight back at the centre
    look = (-math.sin(a), math.cos(a))
    assert look == pytest.approx((-loc[0] / 5.0, -loc[1] / 5.0), abs=1e-9)
    assert rot[0] == pytest.approx(math.pi / 2) and rot[1] == 0.0


def test_framing_distance_fits_height_and_turning_width():
    tall = [(0.0, 0.0, 0.0), (0.0, 0.0, 1.8), (0.1, 0.1, 0.9), (-0.1, -0.1, 0.9)]
    wide = [(0.0, 0.0, 0.0), (0.0, 0.0, 1.8), (0.9, 0.0, 1.4), (-0.9, 0.0, 1.4)]
    c, d_tall = framing_distance(tall, 50.0, 36.0, (1920, 1080))
    assert c == pytest.approx((0.0, 0.0, 0.9))
    half_v = math.atan(math.tan(math.atan(18.0 / 50.0)) * 1080 / 1920)
    radius = math.hypot(0.1, 0.1)
    assert d_tall == pytest.approx(max(1.8 * 1.1 / 2 / math.tan(half_v), radius * 1.1 / (18.0 / 50.0)) + radius)
    _, d_wide = framing_distance(wide, 50.0, 36.0, (1920, 1080))
    assert d_wide > d_tall                 # a T-pose arm span must stay in frame when it turns side-on
    _, d_square = framing_distance(tall, 50.0, 36.0, (1080, 1080))
    assert d_square < d_tall               # horizontal sensor fit: a square frame sees more height, stands closer
