"""Render views: spec, engine presets and camera framing for automatic stills and turntables (pure Python).

A render spec reuses the batch-export body matrices (``pipeline/batch_export.py``) and adds what to render:

    {
      "spec_version": 1,
      "output_dir": "builds/renders/views",
      "engine": "WORKBENCH",            # WORKBENCH (default) | EEVEE | CYCLES
      "device": "AUTO",                 # CYCLES only: AUTO (GPU if a CUDA device exists, else CPU) | CPU | GPU
      "samples": null,                  # EEVEE / CYCLES; null = the preset's value
      "resolution": [1920, 1080],
      "views": ["front", "side", "back"],
      "contact_sheet": true,
      "turntable": {"frames": 24, "resolution": [960, 540], "mp4": false},
      "matrices": [{"templates": ["human_male_adult"], "poses": ["tpose"]}]
    }

Canonical frame: the body faces -Y, its left side is +X. Azimuth 0 puts the camera on -Y (front); 90 on +X
(the body's left side); 180 on +Y (back). The Blender side (``infrastructure/blender/addon/render.py``)
executes the jobs; this module never touches ``bpy``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .batch_export import BatchJob, BatchSpecError, expand

SPEC_VERSION = 1
DEFAULT_OUTPUT_DIR = "builds/renders/views"
VIEWS: Dict[str, float] = {"front": 0.0, "side": 90.0, "back": 180.0}
DEVICES = ("AUTO", "CPU", "GPU")


@dataclass(frozen=True)
class EnginePreset:
    preset_id: str
    blender_engine: str
    samples: Optional[int]      # None = engine without sampling (Workbench)
    notes: str


# Sample counts are working defaults chosen for preview speed on the reference PC, not quality targets.
ENGINES: Dict[str, EnginePreset] = {
    "WORKBENCH": EnginePreset("WORKBENCH", "BLENDER_WORKBENCH", None,
                              "default; solid shading with material colours, no textures, no shaders"),
    "EEVEE": EnginePreset("EEVEE", "BLENDER_EEVEE", 16, "opt-in; needs an OpenGL 3.3 context even in background"),
    "CYCLES": EnginePreset("CYCLES", "CYCLES", 32, "opt-in; CPU, or CUDA GPU when a device is present"),
}


@dataclass(frozen=True)
class TurntableSpec:
    frames: int = 24
    resolution: Tuple[int, int] = (960, 540)
    mp4: bool = False


@dataclass(frozen=True)
class RenderSpec:
    jobs: List[BatchJob]
    engine: str = "WORKBENCH"
    device: str = "AUTO"
    samples: Optional[int] = None
    resolution: Tuple[int, int] = (1920, 1080)
    views: Tuple[str, ...] = ("front", "side", "back")
    contact_sheet: bool = True
    turntable: Optional[TurntableSpec] = field(default_factory=TurntableSpec)
    output_dir: str = DEFAULT_OUTPUT_DIR

    @property
    def preset(self) -> EnginePreset:
        return ENGINES[self.engine]

    @property
    def effective_samples(self) -> Optional[int]:
        if self.preset.samples is None:
            return None
        return self.samples if self.samples is not None else self.preset.samples

    def settings(self) -> dict:
        tt = self.turntable
        return {"engine": self.engine, "blender_engine": self.preset.blender_engine,
                "device": self.device if self.engine == "CYCLES" else None, "samples": self.effective_samples,
                "resolution": list(self.resolution), "views": list(self.views), "contact_sheet": self.contact_sheet,
                "turntable": None if tt is None else {"frames": tt.frames, "resolution": list(tt.resolution),
                                                      "mp4": tt.mp4}}


def _resolution(value, key: str, errors: List[str]) -> Tuple[int, int]:
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or not all(isinstance(v, int) and not isinstance(v, bool) and 16 <= v <= 8192 for v in value)):
        errors.append(f"'{key}' must be [width, height], integers 16-8192")
        return (16, 16)
    return (value[0], value[1])


def parse(spec: Mapping, root=None, overrides: Optional[Mapping] = None) -> RenderSpec:
    """Validate a render spec (plus CLI ``overrides``) and expand its bodies. Raises :class:`BatchSpecError`."""
    errors: List[str] = []
    if not isinstance(spec, Mapping):
        raise BatchSpecError(["spec must be a JSON object"])
    spec = {**spec, **{k: v for k, v in (overrides or {}).items() if v is not None}}
    known = {"spec_version", "output_dir", "engine", "device", "samples", "resolution", "views", "contact_sheet",
             "turntable", "matrices"}
    unknown = set(spec) - known
    if unknown:
        errors.append(f"unknown keys {sorted(unknown)}")
    jobs: List[BatchJob] = []
    try:
        jobs = expand({"spec_version": spec.get("spec_version", SPEC_VERSION), "matrices": spec.get("matrices")},
                      root=root)
    except BatchSpecError as exc:
        errors += exc.errors
    if any(j.clip for j in jobs):
        errors.append("clips are not rendered yet: render specs take bodies only (no 'clips')")
    engine = str(spec.get("engine", "WORKBENCH")).upper()
    if engine not in ENGINES:
        errors.append(f"unknown engine '{spec.get('engine')}'; expected one of {sorted(ENGINES)}")
    device = str(spec.get("device", "AUTO")).upper()
    if device not in DEVICES:
        errors.append(f"unknown device '{spec.get('device')}'; expected one of {list(DEVICES)}")
    elif device != "AUTO" and engine != "CYCLES":
        errors.append(f"device '{device}' only applies to CYCLES (engine is {engine})")
    samples = spec.get("samples")
    if samples is not None and (not isinstance(samples, int) or isinstance(samples, bool) or not 1 <= samples <= 4096):
        errors.append(f"samples {samples!r} must be an integer 1-4096")
    resolution = _resolution(spec.get("resolution", [1920, 1080]), "resolution", errors)
    views = spec.get("views", ["front", "side", "back"])
    if not isinstance(views, list) or not views or any(v not in VIEWS for v in views) or len(set(views)) != len(views):
        errors.append(f"views {views!r} must be a non-empty list of distinct {sorted(VIEWS)}")
        views = []
    tt_raw = spec.get("turntable", {})
    turntable = None
    if tt_raw is not None:
        if not isinstance(tt_raw, Mapping):
            errors.append("'turntable' must be an object or null")
        else:
            bad = set(tt_raw) - {"frames", "resolution", "mp4"}
            if bad:
                errors.append(f"turntable: unknown keys {sorted(bad)}")
            frames = tt_raw.get("frames", 24)
            if not isinstance(frames, int) or isinstance(frames, bool) or not 4 <= frames <= 720:
                errors.append(f"turntable frames {frames!r} must be an integer 4-720")
            turntable = TurntableSpec(frames, _resolution(tt_raw.get("resolution", [960, 540]),
                                                          "turntable.resolution", errors), bool(tt_raw.get("mp4")))
    if errors:
        raise BatchSpecError(errors)
    return RenderSpec(jobs, engine, device, samples, resolution, tuple(views), bool(spec.get("contact_sheet", True)),
                      turntable, str(spec.get("output_dir", DEFAULT_OUTPUT_DIR)))


def turntable_azimuths(frames: int) -> List[float]:
    """Evenly spaced azimuths in degrees, starting at the front, without repeating 360 (loops cleanly)."""
    return [i * 360.0 / frames for i in range(frames)]


def orbit_camera(centre: Sequence[float], distance: float, azimuth_deg: float) -> Tuple[Tuple[float, float, float],
                                                                                       Tuple[float, float, float]]:
    """Camera location and XYZ Euler rotation (radians) looking horizontally at ``centre`` from ``azimuth_deg``.

    Blender cameras look along their local -Z; Euler (90°, 0, a) turns that into the horizontal direction
    (-sin a, cos a, 0), i.e. from (sin a, -cos a)·d towards the centre.
    """
    a = math.radians(azimuth_deg)
    loc = (centre[0] + distance * math.sin(a), centre[1] - distance * math.cos(a), centre[2])
    return loc, (math.radians(90.0), 0.0, a)


def framing_distance(points: Sequence[Sequence[float]], lens_mm: float, sensor_width_mm: float,
                     resolution: Tuple[int, int], margin: float = 1.10) -> Tuple[Tuple[float, float, float], float]:
    """(centre, camera distance) so the points stay in frame from **every** azimuth (horizontal sensor fit).

    Uses the bounding cylinder around the vertical axis through the bounding-box centre: its radius limits the
    width, the box height limits the height, and the camera stands off by the radius so the near side fits too.
    """
    xs, ys, zs = [p[0] for p in points], [p[1] for p in points], [p[2] for p in points]
    centre = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
    radius = max(math.hypot(p[0] - centre[0], p[1] - centre[1]) for p in points)
    height = max(zs) - min(zs)
    half_h = math.atan(sensor_width_mm / 2 / lens_mm)
    half_v = math.atan(math.tan(half_h) * resolution[1] / resolution[0])
    dist = max(height * margin / 2 / math.tan(half_v), radius * margin / math.tan(half_h)) + radius
    return centre, dist


def output_names(spec: RenderSpec) -> List[str]:
    """Relative paths a job folder will hold (for the manifest and the tests)."""
    names = [f"{v}.png" for v in spec.views]
    if spec.contact_sheet:
        names.append("contact_sheet.png")
    if spec.turntable is not None:
        names += [f"turntable/{i + 1:04d}.png" for i in range(spec.turntable.frames)]
        if spec.turntable.mp4:
            names.append("turntable.mp4")
    return names + ["render.json"]
