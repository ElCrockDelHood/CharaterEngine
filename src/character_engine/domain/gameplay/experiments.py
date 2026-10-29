"""Experiment library (Deliverable 1): offline experiments run in Blender, recorded as Godot-readable JSON.

Experiment 001 — contact threshold: the same attack clip against the same stance at a grid of spacings; for each
spacing the minimum signed sabre-to-body distance over the clip says whether the blade reaches the body. The
threshold spacing is bracketed by the grid and then refined by bisection between the last spacing with contact
and the first without it, down to a stated resolution (``tolerance_m``, a measurement choice, not a property of
the bodies). Linear interpolation of the minimum distance between the two grid points is recorded as a second,
independent estimate.

Every record carries its conditions (clips, sources, frames, geometry), its measurements, provenance and a
SHA-256 of its canonical JSON. Pure Python, no engine code.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

EXPERIMENT_SCHEMA_VERSION = 1

RECORD_KEYS = ("id", "title", "question", "conditions", "grid", "bisection", "threshold", "provenance",
               "limitations", "sha256")
POINT_KEYS = ("distance_m", "min_signed_distance_m", "contact", "first_contact_frame", "bone", "min_frame")


def grid(lo: float, hi: float, n: int, digits: int = 4) -> List[float]:
    """``n`` evenly spaced values from ``lo`` to ``hi`` inclusive, rounded to ``digits``."""
    if n < 2 or hi <= lo:
        raise ValueError("need n >= 2 and hi > lo")
    step = (hi - lo) / (n - 1)
    return [round(lo + i * step, digits) for i in range(n)]


def bracket(points: Sequence[Mapping[str, Any]]) -> Tuple[Optional[float], Optional[float], bool]:
    """(largest spacing with contact, smallest spacing without contact above it, monotonic) from grid points.

    ``monotonic`` is False when a spacing without contact lies below one with contact, so a single threshold does
    not describe the series.
    """
    pts = sorted(points, key=lambda p: p["distance_m"])
    hits = [p["distance_m"] for p in pts if p["contact"]]
    if not hits:
        return None, (pts[0]["distance_m"] if pts else None), True
    last = max(hits)
    above = [p["distance_m"] for p in pts if not p["contact"] and p["distance_m"] > last]
    monotonic = all(p["contact"] for p in pts if p["distance_m"] <= last)
    return last, (min(above) if above else None), monotonic


def interpolate_zero(d0: float, m0: float, d1: float, m1: float) -> Optional[float]:
    """Spacing where the minimum signed distance crosses zero, linear between (d0, m0) and (d1, m1)."""
    if m0 == m1 or (m0 > 0) == (m1 > 0):
        return None
    return d0 + (0.0 - m0) * (d1 - d0) / (m1 - m0)


def bisect_threshold(contact: Callable[[float], bool], lo: float, hi: float, tolerance: float,
                     digits: int = 4) -> List[Tuple[float, bool]]:
    """Bisection between ``lo`` (contact) and ``hi`` (no contact) until ``hi - lo <= tolerance``.

    Returns the evaluated (spacing, contact) steps in order; the threshold lies between the last contact spacing
    and the first no-contact spacing among them.
    """
    steps: List[Tuple[float, bool]] = []
    while hi - lo > tolerance:
        mid = round((lo + hi) / 2, digits)
        if mid in (lo, hi):
            break
        c = contact(mid)
        steps.append((mid, c))
        if c:
            lo = mid
        else:
            hi = mid
    return steps


def threshold_from(points: Sequence[Mapping[str, Any]], steps: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Threshold interval from the grid and bisection points: largest contact below smallest no-contact."""
    every = list(points) + list(steps)
    hits = [p["distance_m"] for p in every if p["contact"]]
    misses = [p["distance_m"] for p in every if not p["contact"]]
    if not hits or not misses:
        return {"contact_up_to_m": max(hits) if hits else None, "no_contact_from_m": min(misses) if misses else None,
                "width_m": None}
    lo = max(hits)
    hi = min([m for m in misses if m > lo], default=None)
    return {"contact_up_to_m": lo, "no_contact_from_m": hi,
            "width_m": round(hi - lo, 6) if hi is not None else None}


def record_sha256(record: Mapping[str, Any]) -> str:
    """SHA-256 of the record's canonical JSON (sorted keys), excluding its own ``sha256`` field."""
    body = {k: v for k, v in record.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_experiments(data: Mapping[str, Any]) -> List[str]:
    """Problems found in an experiments document (empty list = valid)."""
    problems: List[str] = []
    if data.get("schema_version") != EXPERIMENT_SCHEMA_VERSION:
        problems.append(f"schema_version must be {EXPERIMENT_SCHEMA_VERSION}")
    records = data.get("experiments")
    if not isinstance(records, list) or not records:
        return problems + ["experiments must be a non-empty list"]
    for r in records:
        rid = r.get("id", "?")
        missing = [k for k in RECORD_KEYS if k not in r]
        if missing:
            problems.append(f"{rid}: missing {missing}")
            continue
        pts, steps = r["grid"], r["bisection"]["steps"]
        for p in list(pts) + list(steps):
            if [k for k in POINT_KEYS if k not in p]:
                problems.append(f"{rid}: bad point {p.get('distance_m')}")
            elif p["contact"] != (p["min_signed_distance_m"] <= 0.0):
                problems.append(f"{rid}: contact flag inconsistent at {p['distance_m']}")
        if problems:
            continue
        if threshold_from(pts, steps) != {k: r["threshold"][k] for k in ("contact_up_to_m", "no_contact_from_m",
                                                                          "width_m")}:
            problems.append(f"{rid}: threshold does not follow from the measurements")
        if not r["conditions"].get("sources"):
            problems.append(f"{rid}: conditions must list the clip sources")
        if r["sha256"] != record_sha256(r):
            problems.append(f"{rid}: sha256 mismatch")
    return problems
