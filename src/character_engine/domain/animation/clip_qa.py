"""Animation clip QA: foot contact, foot sliding, ground penetration, loop seam, root speed (pure Python).

Input is sampled world positions (canonical axes: Z-up, metres) per frame, as written by
``runtime/blender/ce_batch_retarget.py``. Nothing here reads files or imports Blender.

Every threshold in :data:`DEFAULT_THRESHOLDS` is an **ESTIMATE** (engineering judgement for game-ready clips,
no cited source); the report carries that provenance with each value it judges.

Definitions
-----------
* **Contact**: a foot point is in contact on a frame when its height above its own rest-pose height (feet flat
  on the ground in the T-pose), corrected by the clip's ground offset, is at most ``contact_height_m``.
* **Ground offset**: the lowest value of (height − rest height) over all foot points and frames. Negative =
  the foot goes below where it rests standing (penetration); positive = it never comes down (floating).
* **Sliding**: horizontal (XY) speed of a foot point between two consecutive contact frames.
* **Stance speed**: median horizontal foot speed while in contact. On an *in-place* clip a planted foot moves
  backwards at the body's speed, so this is the travel speed the feet imply; on a root-motion clip it is the
  residual slide.
* **Loop seam**: largest joint distance between the first and last frame, and how far the velocity change
  across the wrap exceeds the largest frame-to-frame velocity change inside the clip.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

Vec3 = Sequence[float]
PROVENANCE = "ESTIMATE"


@dataclass(frozen=True)
class Thresholds:
    """QA thresholds. All ESTIMATE (no cited source)."""

    contact_height_m: float = 0.03       # point within 3 cm of its flat-foot height = in contact
    slide_warn_m_s: float = 0.05         # mean slide speed while in contact
    slide_fail_m_s: float = 0.20
    penetration_warn_m: float = 0.01     # below the flat-foot height
    penetration_fail_m: float = 0.03
    float_warn_m: float = 0.03           # ground clip whose feet never get this close to the ground
    airborne_m: float = 0.10             # offset above this = no ground contact in the clip (skip sliding)
    seam_pos_warn_m: float = 0.005
    seam_pos_fail_m: float = 0.02
    seam_vel_warn_m_s: float = 0.3      # excess of the wrap's velocity change over the clip's largest
    seam_vel_fail_m_s: float = 1.0
    speed_ratio_warn: Tuple[float, float] = (0.8, 1.25)   # root speed / stance speed
    speed_ratio_fail: Tuple[float, float] = (0.67, 1.5)
    min_contact_frames: int = 2
    moving_root_m_s: float = 0.1         # below this the root (or the stance) counts as not travelling


DEFAULT_THRESHOLDS = Thresholds()

# First token(s) of the clip name -> category. Unknown names fall into "other".
CATEGORY_PREFIXES: Tuple[Tuple[str, str], ...] = (
    ("Walk", "locomotion"), ("Jog", "locomotion"), ("Sprint", "locomotion"), ("Run", "locomotion"),
    ("Crouch_Fwd", "locomotion"), ("Strafe", "locomotion"), ("Crawl", "locomotion"), ("Ninja", "locomotion"),
    ("Swim", "swim"), ("Jump", "jump"), ("Roll", "jump"), ("Climb", "traversal"), ("Ledge", "traversal"),
    ("Idle", "idle"), ("Crouch", "idle"), ("A_TPose", "pose"), ("TPose", "pose"),
    ("Sword", "combat"), ("Punch", "combat"), ("Kick", "combat"), ("Pistol", "combat"), ("Spell", "combat"),
    ("Hit", "combat"), ("Death", "combat"), ("Melee", "combat"), ("Shield", "combat"), ("Block", "combat"),
    ("Sitting", "seated"), ("Driving", "seated"),
)
NON_GROUND_CATEGORIES = frozenset({"swim"})
LOOP_MARKER = "_Loop"


def classify(clip: str) -> str:
    for prefix, category in CATEGORY_PREFIXES:
        if clip == prefix or clip.startswith(prefix + "_") or clip.startswith(prefix):
            return category
    return "other"


def is_loop(clip: str) -> bool:
    return LOOP_MARKER in clip


def horizontal_distance(a: Vec3, b: Vec3) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def distance(a: Vec3, b: Vec3) -> float:
    return math.sqrt(sum((b[i] - a[i]) ** 2 for i in range(3)))


def ground_offset(heights: Mapping[str, Sequence[float]], rest_z: Mapping[str, float]) -> Optional[float]:
    """Lowest (height − rest height) over all points and frames; None when there are no samples."""
    vals = [z - rest_z[n] for n, zs in heights.items() for z in zs]
    return min(vals) if vals else None


def detect_contacts(heights: Sequence[float], rest_z: float, offset: float, threshold_m: float) -> List[bool]:
    """Per frame: is the point within ``threshold_m`` of its flat-foot height (after the clip ground offset)?"""
    return [(z - rest_z - offset) <= threshold_m for z in heights]


@dataclass(frozen=True)
class SlideStats:
    contact_frames: int
    contact_steps: int            # consecutive contact pairs measured
    mean_m_s: Optional[float]
    median_m_s: Optional[float]
    max_m_s: Optional[float]
    distance_m: float


def sliding(positions: Sequence[Vec3], contacts: Sequence[bool], dt: float) -> SlideStats:
    """Horizontal speed between consecutive frames where the point is in contact on both."""
    if len(positions) != len(contacts):
        raise ValueError("positions and contacts differ in length")
    if dt <= 0:
        raise ValueError("dt must be positive")
    speeds = [horizontal_distance(positions[i - 1], positions[i]) / dt
              for i in range(1, len(positions)) if contacts[i - 1] and contacts[i]]
    return SlideStats(contact_frames=sum(contacts), contact_steps=len(speeds),
                      mean_m_s=statistics.fmean(speeds) if speeds else None,
                      median_m_s=statistics.median(speeds) if speeds else None,
                      max_m_s=max(speeds) if speeds else None,
                      distance_m=sum(speeds) * dt)


def contact_phases(contacts: Sequence[bool]) -> List[Tuple[int, int]]:
    """Runs of consecutive contact frames as (first, last) index pairs."""
    out, start = [], None
    for i, c in enumerate(contacts):
        if c and start is None:
            start = i
        if not c and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(contacts) - 1))
    return out


def stance_length(positions: Sequence[Vec3], contacts: Sequence[bool]) -> Optional[float]:
    """Longest horizontal distance covered by the point during one contact phase (in-place: the stance length)."""
    lengths = [horizontal_distance(positions[a], positions[b]) for a, b in contact_phases(contacts) if b > a]
    return max(lengths) if lengths else None


@dataclass(frozen=True)
class RootMotion:
    displacement_m: float         # horizontal, first -> last frame
    vertical_m: float
    duration_s: float
    speed_m_s: Optional[float]
    path_m: float                 # summed horizontal frame-to-frame distance


def root_motion(positions: Sequence[Vec3], dt: float) -> RootMotion:
    if not positions:
        return RootMotion(0.0, 0.0, 0.0, None, 0.0)
    duration = (len(positions) - 1) * dt
    disp = horizontal_distance(positions[0], positions[-1])
    path = sum(horizontal_distance(positions[i - 1], positions[i]) for i in range(1, len(positions)))
    return RootMotion(displacement_m=disp, vertical_m=positions[-1][2] - positions[0][2], duration_s=duration,
                      speed_m_s=disp / duration if duration > 0 else None, path_m=path)


@dataclass(frozen=True)
class LoopSeam:
    position_m: float               # largest |last − first| joint distance
    velocity_jump_m_s: float        # largest velocity change across the wrap
    interior_jump_m_s: float        # largest frame-to-frame velocity change inside the clip
    excess_m_s: float               # how far the wrap exceeds the clip's own largest change (graded)
    duplicated_end: bool            # last frame repeats the first (glTF loops usually do)
    worst_point: str


def _jump(a: Vec3, b: Vec3, c: Vec3, dt: float) -> float:
    """|v(b→c) − v(a→b)|."""
    return math.sqrt(sum(((c[i] - b[i]) - (b[i] - a[i])) ** 2 for i in range(3))) / dt


def loop_seam(frames: Sequence[Mapping[str, Vec3]], dt: float, points: Optional[Sequence[str]] = None,
              duplicate_tol_m: float = 1e-3) -> LoopSeam:
    """Pose and velocity discontinuity when the clip wraps from its end to its first frame.

    A velocity *change* at the wrap is normal when a joint turns around there (a foot at its most forward
    point), so the wrap's change is compared with the largest change inside the clip; only the excess counts.
    When the last frame repeats the first (gap ≤ ``duplicate_tol_m`` or ≤ 25 % of the joint's mean per-frame
    step, ESTIMATE), the wrap goes from the second-to-last frame to the first.
    """
    if len(frames) < 4:
        raise ValueError("a loop seam needs at least 4 frames")
    names = [n for n in (points or sorted(frames[0])) if n in frames[0]]
    if not names:
        raise ValueError("none of the seam points is sampled")
    pos = max(distance(frames[0][n], frames[-1][n]) for n in names)

    def mean_step(n: str) -> float:
        return statistics.fmean(distance(frames[i - 1][n], frames[i][n]) for i in range(1, len(frames)))

    # the last frame repeats the first when its gap is tiny next to how far that joint moves per frame
    dup = all(distance(frames[0][n], frames[-1][n]) <= max(duplicate_tol_m, 0.25 * mean_step(n)) for n in names)
    body = frames[:-1] if dup else frames
    worst, jump, interior, excess = names[0], 0.0, 0.0, 0.0
    for n in names:
        p = [f[n] for f in body]
        wrap = _jump(p[-1], p[0], p[1], dt)
        inner = max(_jump(p[i - 1], p[i], p[i + 1], dt) for i in range(1, len(p) - 1))
        jump, interior = max(jump, wrap), max(interior, inner)
        if wrap - inner > excess:
            excess, worst = wrap - inner, n
    if excess == 0.0:
        worst = max(names, key=lambda n: distance(frames[0][n], frames[-1][n]))
    return LoopSeam(position_m=pos, velocity_jump_m_s=jump, interior_jump_m_s=interior, excess_m_s=excess,
                    duplicated_end=dup, worst_point=worst)


def _grade(value: Optional[float], warn: float, fail: float) -> str:
    if value is None:
        return "n/a"
    return "fail" if value > fail else "warn" if value > warn else "ok"


def _grade_ratio(ratio: Optional[float], warn: Tuple[float, float], fail: Tuple[float, float]) -> str:
    if ratio is None:
        return "n/a"
    if not fail[0] <= ratio <= fail[1]:
        return "fail"
    return "warn" if not warn[0] <= ratio <= warn[1] else "ok"


def _round(x, nd=4):
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        return {k: _round(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, nd) for v in x]
    return x


def feet_qa(frames: Sequence[Mapping[str, Vec3]], rest: Mapping[str, Vec3], feet: Mapping[str, Sequence[str]],
            dt: float, th: Thresholds = DEFAULT_THRESHOLDS, ground: bool = True) -> Dict:
    """Contact, sliding, penetration and stance speed for the given foot points (``feet``: side -> point names)."""
    names = [n for pts in feet.values() for n in pts if n in rest and frames and n in frames[0]]
    heights = {n: [f[n][2] for f in frames] for n in names}
    rest_z = {n: rest[n][2] for n in names}
    offset = ground_offset(heights, rest_z)
    out: Dict = {"ground_offset_m": offset, "min_height_m": min((min(z) for z in heights.values()), default=None),
                 "penetration_m": max(0.0, -offset) if offset is not None else None, "feet": {}}
    airborne = offset is not None and offset > th.airborne_m
    out["ground_contact"] = bool(ground and offset is not None and not airborne)
    stance_speeds, stance_lengths = [], []
    for side, pts in feet.items():
        side_out = {}
        for n in pts:
            if n not in heights:
                continue
            pos = [f[n] for f in frames]
            if out["ground_contact"]:
                contacts = detect_contacts(heights[n], rest_z[n], offset, th.contact_height_m)
                s = sliding(pos, contacts, dt)
                side_out[n] = asdict(s)
                side_out[n]["stance_length_m"] = stance_length(pos, contacts)
                if s.contact_steps >= th.min_contact_frames:
                    stance_speeds += [horizontal_distance(pos[i - 1], pos[i]) / dt
                                      for i in range(1, len(pos)) if contacts[i - 1] and contacts[i]]
                if side_out[n]["stance_length_m"] is not None:
                    stance_lengths.append(side_out[n]["stance_length_m"])
        measured = [v for v in side_out.values() if v["contact_steps"] >= th.min_contact_frames]
        worst = max(measured, key=lambda v: v["mean_m_s"]) if measured else None
        out["feet"][side] = {"points": side_out, "slide_mean_m_s": worst["mean_m_s"] if worst else None,
                             "slide_max_m_s": max(v["max_m_s"] for v in measured) if measured else None}
    slides = [f["slide_mean_m_s"] for f in out["feet"].values() if f["slide_mean_m_s"] is not None]
    out["slide_mean_m_s"] = max(slides) if slides else None
    out["stance_speed_m_s"] = statistics.median(stance_speeds) if stance_speeds else None
    out["stance_length_m"] = max(stance_lengths) if stance_lengths else None
    return out


def evaluate_clip(clip: str, *, dt: float, inplace_target: Sequence[Mapping[str, Vec3]],
                  rm_target: Optional[Sequence[Mapping[str, Vec3]]], target_rest: Mapping[str, Vec3],
                  target_feet: Mapping[str, Sequence[str]],
                  inplace_source: Optional[Sequence[Mapping[str, Vec3]]] = None,
                  rm_source: Optional[Sequence[Mapping[str, Vec3]]] = None,
                  source_rest: Optional[Mapping[str, Vec3]] = None,
                  source_feet: Optional[Mapping[str, Sequence[str]]] = None,
                  root_point: str = "root", target_root_point: str = "SACRUM",
                  seam_points: Optional[Sequence[str]] = None, th: Thresholds = DEFAULT_THRESHOLDS) -> Dict:
    """Full QA record of one clip. ``rm_*`` = root-motion variant (world), the rest = in-place variant."""
    category = classify(clip)
    ground = category not in NON_GROUND_CATEGORIES
    world = rm_target if rm_target else inplace_target
    rec: Dict = {"clip": clip, "category": category, "loop": is_loop(clip), "frames": len(inplace_target),
                 "duration_s": (len(inplace_target) - 1) * dt, "provenance": PROVENANCE, "checks": {}}
    # feet on the canonical armature: sliding in world space (root-motion variant when available)
    tf = feet_qa(world, target_rest, target_feet, dt, th, ground)
    tf_inplace = feet_qa(inplace_target, target_rest, target_feet, dt, th, ground)
    rec["target_feet"] = tf
    rec["checks"]["foot_sliding"] = _grade(tf["slide_mean_m_s"], th.slide_warn_m_s, th.slide_fail_m_s) \
        if tf["ground_contact"] else "n/a"
    rec["checks"]["ground_penetration"] = _grade(tf["penetration_m"], th.penetration_warn_m, th.penetration_fail_m) \
        if ground else "n/a"
    rec["checks"]["floating"] = ("warn" if tf["ground_offset_m"] is not None and
                                 th.float_warn_m < tf["ground_offset_m"] <= th.airborne_m else "ok") \
        if ground else "n/a"
    # source feet: tells source defects apart from retarget defects
    if source_rest and source_feet:
        if rm_source:
            rec["source_feet_rm"] = feet_qa(rm_source, source_rest, source_feet, dt, th, ground)
        if inplace_source:
            rec["source_feet_inplace"] = feet_qa(inplace_source, source_rest, source_feet, dt, th, ground)
    # root motion vs. what the feet imply
    if rm_source and root_point in rm_source[0]:
        rm = root_motion([f[root_point] for f in rm_source], dt)
        rec["root_motion_source"] = asdict(rm)
        if rm_target and target_root_point in rm_target[0]:
            rec["root_motion_target"] = asdict(root_motion([f[target_root_point] for f in rm_target], dt))
        implied = (rec.get("source_feet_inplace") or {}).get("stance_speed_m_s")
        rec["stance_speed_source_m_s"] = implied
        moving = rm.speed_m_s is not None and rm.speed_m_s > th.moving_root_m_s
        stepping = implied is not None and implied > th.moving_root_m_s
        ratio = rm.speed_m_s / implied if moving and stepping else None
        rec["root_to_stance_speed_ratio"] = ratio
        # root travels while the planted feet of the in-place clip do not move: the travel is a glide
        rec["root_glide"] = bool(moving and not stepping)
        if not moving:
            rec["checks"]["root_speed_vs_feet"] = "n/a"
        elif not stepping:
            rec["checks"]["root_speed_vs_feet"] = "fail"
        else:
            rec["checks"]["root_speed_vs_feet"] = _grade_ratio(ratio, th.speed_ratio_warn, th.speed_ratio_fail)
        target_implied = tf_inplace.get("stance_speed_m_s")
        rec["stance_speed_target_m_s"] = target_implied
    if rec["loop"] and len(inplace_target) >= 4:
        seam = loop_seam(inplace_target, dt, seam_points)
        rec["loop_seam"] = asdict(seam)
        pos_g = _grade(seam.position_m, th.seam_pos_warn_m, th.seam_pos_fail_m)
        vel_g = _grade(seam.excess_m_s, th.seam_vel_warn_m_s, th.seam_vel_fail_m_s)
        rec["checks"]["loop_seam"] = worst_status([pos_g, vel_g])
    rec["status"] = worst_status(rec["checks"].values())
    return _round(rec)


_ORDER = {"n/a": 0, "ok": 1, "warn": 2, "fail": 3, "error": 4}


def worst_status(statuses) -> str:
    statuses = list(statuses)
    graded = [s for s in statuses if s != "n/a"]
    if not graded:
        return "ok"
    return max(graded, key=lambda s: _ORDER[s])


def summarize(records: Sequence[Mapping]) -> Dict[str, Dict]:
    """Per category: clip count, status counts and the failing check names."""
    out: Dict[str, Dict] = {}
    for r in records:
        cat = out.setdefault(r.get("category", "other"), {"clips": 0, "ok": 0, "warn": 0, "fail": 0, "error": 0,
                                                          "failed_checks": {}})
        cat["clips"] += 1
        cat[r.get("status", "error")] += 1
        for name, s in (r.get("checks") or {}).items():
            if s == "fail":
                cat["failed_checks"][name] = cat["failed_checks"].get(name, 0) + 1
    return dict(sorted(out.items()))
