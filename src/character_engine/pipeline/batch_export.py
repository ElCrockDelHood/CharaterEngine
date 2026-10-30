"""Batch asset export: job spec, matrix expansion, provenance records and manifest (pure Python).

A spec is a JSON document with one or more *matrices*; each matrix is the product
``templates x statures x poses x clips`` and expands into :class:`BatchJob` objects with
deterministic output names. The Blender side (``infrastructure/blender/addon/batch.py``)
executes the jobs; this module never touches ``bpy``.

    {
      "spec_version": 1,
      "output_dir": "builds/exports/batch",
      "matrices": [
        {"templates": ["human_male_adult"], "statures_m": [1.80], "poses": ["tpose", "anatomical"],
         "clips": [null, {"path": "assets/anim/ual.glb", "bone_map": "quaternius_ual", "clip": "Walk"}],
         "mesh": "block_dummy"}
      ]
    }

``statures_m`` may be omitted or contain ``null`` (= the template's own stature); ``clips``
may be omitted (= no clip). Unavailable templates (horse, dog: no canonical data) are refused,
never approximated with a human skeleton.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..domain.anatomy.pose.tpose import POSES
from ..domain.anatomy.reference.source import ProvenanceState
from ..domain.animation import BONE_MAPS
from ..domain.character import TEMPLATES

SPEC_VERSION = 1
DEFAULT_OUTPUT_DIR = "builds/exports/batch"
# Stature bounds of the addon's Body panel (properties.py); outside them the stature retarget is untested.
STATURE_RANGE_M = (0.4, 2.6)
ANIMATION_SUFFIXES = (".bvh", ".fbx", ".glb", ".gltf")   # same list as build.ANIMATION_SUFFIXES
# What the exported GLB contains besides the armature. Block dummy radii are ESTIMATE (rigging/block_dummy.py).
# "tissues" (bones, tendons, muscles, skin) has no single state: each layer's provenance is read from the tags the
# addon builders put on the objects and reported per layer and per aspect (see ``layer_provenance``).
MESH_MODES = {"block_dummy": ProvenanceState.ESTIMATE, "tissues": None, "none": None}
PER_LAYER = "per_layer"
_STATES = {s.value for s in ProvenanceState}
DEFAULT_MESH = "block_dummy"
# Each run writes manifest_<spec>_<UTC>.json; this name always holds a copy of the newest one (the pre-run-id file).
LATEST_MANIFEST = "manifest.json"


class BatchSpecError(ValueError):
    """The spec is invalid; ``errors`` lists every problem found (not only the first)."""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__("invalid batch spec:\n  - " + "\n  - ".join(self.errors))


@dataclass(frozen=True)
class ClipSpec:
    path: str           # as written in the spec (relative paths resolve against the repo root)
    bone_map: str
    clip: str = ""      # part of the clip name; empty = the file's default clip

    def slug(self) -> str:
        return _slug(self.clip or Path(self.path).stem)

    def to_dict(self) -> dict:
        return {"path": self.path, "bone_map": self.bone_map, "clip": self.clip}


@dataclass(frozen=True)
class BatchJob:
    name: str
    template_id: str
    stature_m: float
    stature_overridden: bool
    pose: str
    mesh: str = DEFAULT_MESH
    clip: Optional[ClipSpec] = None

    def to_dict(self) -> dict:
        return {"name": self.name, "template": self.template_id, "stature_m": self.stature_m,
                "stature_overridden": self.stature_overridden, "pose": self.pose, "mesh": self.mesh,
                "clip": self.clip.to_dict() if self.clip else None}

    @classmethod
    def from_dict(cls, d: Mapping) -> BatchJob:
        clip = d.get("clip")
        return cls(name=d["name"], template_id=d["template"], stature_m=float(d["stature_m"]),
                   stature_overridden=bool(d["stature_overridden"]), pose=d["pose"], mesh=d.get("mesh", DEFAULT_MESH),
                   clip=ClipSpec(clip["path"], clip["bone_map"], clip.get("clip", "")) if clip else None)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s or "clip"


def job_name(template_id: str, stature_m: float, pose: str, clip: Optional[ClipSpec] = None) -> str:
    """``<template>_<stature mm>mm_<pose>[__<bone map>_<clip>]`` — stable across runs and machines."""
    name = f"{template_id}_{round(stature_m * 1000):04d}mm_{pose}"
    if clip is not None:
        name += f"__{clip.bone_map}_{clip.slug()}"
    return name


def _as_list(value, key: str, errors: List[str], where: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{where}: '{key}' must be a list")
        return []
    return value


def expand(spec: Mapping, root: Optional[Path] = None) -> List[BatchJob]:
    """Validate ``spec`` and expand it into jobs (in spec order). Raises :class:`BatchSpecError`.

    With ``root`` the clip files must exist (relative paths resolve against it).
    """
    errors: List[str] = []
    if not isinstance(spec, Mapping):
        raise BatchSpecError(["spec must be a JSON object"])
    if spec.get("spec_version", SPEC_VERSION) != SPEC_VERSION:
        errors.append(f"spec_version {spec.get('spec_version')!r} not supported (expected {SPEC_VERSION})")
    matrices = _as_list(spec.get("matrices"), "matrices", errors, "spec")
    if not matrices and not errors:
        errors.append("spec: 'matrices' is empty")
    jobs: List[BatchJob] = []
    for i, m in enumerate(matrices):
        where = f"matrices[{i}]"
        if not isinstance(m, Mapping):
            errors.append(f"{where}: must be an object")
            continue
        unknown = set(m) - {"templates", "statures_m", "poses", "clips", "mesh"}
        if unknown:
            errors.append(f"{where}: unknown keys {sorted(unknown)}")
        templates = _as_list(m.get("templates"), "templates", errors, where)
        if not templates:
            errors.append(f"{where}: 'templates' is required")
        statures = _as_list(m.get("statures_m"), "statures_m", errors, where) or [None]
        poses = _as_list(m.get("poses"), "poses", errors, where)
        if not poses:
            errors.append(f"{where}: 'poses' is required")
        mesh = m.get("mesh", DEFAULT_MESH)
        if mesh not in MESH_MODES:
            errors.append(f"{where}: mesh '{mesh}' unknown; expected one of {sorted(MESH_MODES)}")
        for tid in templates:
            t = TEMPLATES.get(tid)
            if t is None:
                errors.append(f"{where}: unknown template '{tid}'; known: {sorted(TEMPLATES)}")
            elif not t.available:
                errors.append(f"{where}: template '{tid}' refused (unavailable): {t.notes}")
        for s in statures:
            if s is not None and (not isinstance(s, (int, float)) or isinstance(s, bool)
                                  or not STATURE_RANGE_M[0] <= s <= STATURE_RANGE_M[1]):
                errors.append(f"{where}: stature {s!r} outside {STATURE_RANGE_M[0]}-{STATURE_RANGE_M[1]} m")
        for p in poses:
            if p not in POSES:
                errors.append(f"{where}: unknown pose '{p}'; expected one of {sorted(POSES)}")
        clips: List[Optional[ClipSpec]] = []
        for j, c in enumerate(_as_list(m.get("clips"), "clips", errors, where) or [None]):
            cw = f"{where}.clips[{j}]"
            if c is None:
                clips.append(None)
                continue
            if not isinstance(c, Mapping) or not c.get("path") or not c.get("bone_map"):
                errors.append(f"{cw}: needs 'path' and 'bone_map'")
                continue
            clip = ClipSpec(str(c["path"]), str(c["bone_map"]), str(c.get("clip", "") or ""))
            if clip.bone_map not in BONE_MAPS:
                errors.append(f"{cw}: unknown bone map '{clip.bone_map}'; known: {sorted(BONE_MAPS)}")
            if Path(clip.path).suffix.lower() not in ANIMATION_SUFFIXES:
                errors.append(f"{cw}: '{clip.path}' is not one of {ANIMATION_SUFFIXES}")
            elif root is not None and not resolve(root, clip.path).exists():
                errors.append(f"{cw}: clip file not found: {resolve(root, clip.path)}")
            clips.append(clip)
        for tid in templates:
            t = TEMPLATES.get(tid)
            if t is None or not t.available:
                continue
            for s in statures:
                stature = float(t.params.stature_m if s is None else s)
                for p in poses:
                    for clip in clips:
                        jobs.append(BatchJob(job_name(tid, stature, p, clip), tid, stature,
                                             s is not None and stature != t.params.stature_m, p, mesh, clip))
    seen: Dict[str, int] = {}
    for job in jobs:
        seen[job.name] = seen.get(job.name, 0) + 1
    dupes = sorted(n for n, k in seen.items() if k > 1)
    if dupes:
        errors.append(f"duplicate job names (same template/stature/pose/clip twice): {dupes}")
    if errors:
        raise BatchSpecError(errors)
    return jobs


def load_spec(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BatchSpecError([f"{path}: not valid JSON ({exc})"]) from exc


def resolve(root: Path, path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else Path(root) / p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance_record(job: BatchJob, *, blender_version: str, addon_version: str, glb_sha256: str,
                      glb_bytes: int, extra: Optional[Mapping] = None) -> dict:
    """Provenance sidecar for one GLB: what was built, from which data, with which tools.

    A stature given in the spec is ``USER_INPUT``; otherwise the template's own stature provenance applies.
    """
    t = TEMPLATES[job.template_id]
    mesh_prov = MESH_MODES[job.mesh]
    rec = {
        "job": job.name,
        "template": job.template_id,
        "template_label": t.label,
        "source_id": t.source_id,
        "stature_m": job.stature_m,
        "pose": job.pose,
        "mesh": job.mesh,
        "clip": job.clip.to_dict() if job.clip else None,
        "bone_map": job.clip.bone_map if job.clip else None,
        "provenance": {
            "stature": (ProvenanceState.USER_INPUT if job.stature_overridden else t.stature_provenance).value,
            "proportions": t.proportion_provenance.value,
            "mesh": PER_LAYER if job.mesh == "tissues" else (mesh_prov.value if mesh_prov else None),
        },
        "blender_version": blender_version,
        "addon_version": addon_version,
        "glb_sha256": glb_sha256,
        "glb_bytes": glb_bytes,
    }
    if extra:
        rec.update(extra)
    return rec


def layer_provenance(tag: str) -> Dict[str, str]:
    """Split an addon provenance tag into aspect -> state, e.g. ``PROVEN_ATTACHMENTS/ESTIMATE_GEOMETRY`` ->
    ``{"attachments": "proven", "geometry": "estimate"}``; a bare state (``ESTIMATE``) is the ``geometry`` state.

    A state that is not a ``ProvenanceState`` becomes ``unknown`` (never guessed).
    """
    out: Dict[str, str] = {}
    for part in (p.strip() for p in str(tag).split("/") if p.strip()):
        low = part.lower()
        state = next((s for s in sorted(_STATES, key=len, reverse=True) if low == s or low.startswith(s + "_")), None)
        if state is None:
            out[low] = ProvenanceState.UNKNOWN.value
            continue
        aspect = low[len(state) + 1:] or "geometry"
        out[aspect] = state
    return out


def layer_summary(tag_counts: Mapping[str, int]) -> List[dict]:
    """``{tag: count}`` of one tissue layer -> ``[{"tag", "count", "aspects"}]`` sorted by count, then tag."""
    return [{"tag": t, "count": n, "aspects": layer_provenance(t)}
            for t, n in sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))]


class ClipChoiceError(ValueError):
    """No clip matches the requested name, or only an ambiguous partial match exists."""


def pick_clip(names: Sequence[str], wanted: str) -> Tuple[str, str]:
    """Choose the clip named by ``wanted`` among an animation file's ``names``. Returns (name, rule).

    Rules in order: ``exact`` (case-insensitive), ``prefix`` (the shortest name starting with ``wanted`` + "_"; the
    glTF importer appends "_<object>"), ``substring`` (only when exactly one name contains ``wanted``).
    Several substring matches are refused with the candidates listed: the old first-match rule picked
    ``Crouch_Idle_Loop`` for ``Idle_Loop``. Used by the batch runner and the *Import & retarget* operator.
    """
    w = wanted.lower()
    exact = [n for n in names if n.lower() == w]
    if exact:
        return exact[0], "exact"
    prefixed = sorted((n for n in names if n.lower().startswith(w + "_")), key=lambda n: (len(n), n))
    if prefixed:
        return prefixed[0], "prefix"
    sub = sorted(n for n in names if w in n.lower())
    if len(sub) == 1:
        return sub[0], "substring"
    if sub:
        raise ClipChoiceError(f"clip name '{wanted}' is ambiguous: {len(sub)} clips contain it {sub[:20]}; "
                              f"give the exact name")
    raise ClipChoiceError(f"no clip matching '{wanted}' among {sorted(names)[:20]}")


def run_id(now: Optional[datetime] = None) -> str:
    """UTC stamp of a run, ``yyyymmddTHHMMSSZ`` (sorts chronologically as text)."""
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def manifest_name(spec_path, run: str) -> str:
    """``manifest_<spec stem>_<run id>.json`` — one file per run, so earlier runs are kept."""
    return f"manifest_{_slug(Path(spec_path).stem)}_{run}.json"


def write_manifest(out_dir: Path, name: str, doc: Mapping) -> Path:
    """Write the run's manifest and refresh the ``manifest.json`` copy of the newest run. Returns the run file."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    shutil.copyfile(path, out_dir / LATEST_MANIFEST)
    return path


def manifest(jobs: Sequence[BatchJob], results: Mapping[str, Mapping], **meta) -> dict:
    """PASS/FAIL per job, in job order. A job with no result is FAIL ("not run")."""
    rows = []
    for job in jobs:
        r = dict(results.get(job.name) or {"status": "FAIL", "error": "not run"})
        rows.append({"name": job.name, **r})
    passed = sum(1 for r in rows if r.get("status") == "PASS")
    return {**meta, "jobs_total": len(rows), "passed": passed, "failed": len(rows) - passed, "jobs": rows}
