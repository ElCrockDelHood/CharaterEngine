"""Quality tolerances in force (Decision 89, first batch) and their judges (pure Python).

Two axes: the **profile** (``game``: real time, Godot; ``cinema``: offline, Blender) and the **quality level**
(``Q0`` = what runs today on the GT 740M with Blender 3.6 and Godot ``gl_compatibility``; Q1 and Q2 follow better
hardware). "Q" avoids a clash with the engagement layers L1-L3 of Decision 44. Canonical anatomy has one bar for
every profile and level (``profile="all"``).

Every threshold is **ESTIMATE**: set from what the repository already measured and production judgement, not from a
published norm. The other rows of ``docs/architecture/QUALITY_TOLERANCES.md`` are targets, not in force, and are not
judged here. A judge never relaxes a limit: with nothing to measure it answers ``NOT_MEASURED`` and says why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

PROVENANCE = "ESTIMATE"
PASS, FAIL, NOT_MEASURED = "PASS", "FAIL", "NOT_MEASURED"
Q0_ADAPTER = "GT 740M"          # PF-1 Q0 reference hardware (A12)
REFERENCE = "BodyParts3D 4.0"   # the reference meshes AN-1 / AN-3 measure (A18)


@dataclass(frozen=True)
class Exception_:
    """A documented exception: one item a tolerance does not judge, with its cause and evidence (never silent).

    It applies only to the stated reference and only while the measured value matches the evidence: a test checks
    that, so a changed reference or a fix turns it red. Verdicts list every exception they applied."""
    id: str
    item: str
    reference: str
    cause: str
    evidence: Tuple[Tuple[str, float], ...]
    status: str                     # "pending owner approval" or "approved (date)"


EXCEPTIONS: Tuple[Exception_, ...] = (
    Exception_("AN-3", "INFERIOR_NASAL_CONCHA", REFERENCE,
               "real asymmetry of the single BodyParts3D subject: the right concha sits 3.84 mm forward or back of "
               "the left and is 20.0 mm tall against 15.4 mm; mapping correct (FMA54738 / FMA54737), the canonical "
               "skeleton is not part of the measurement, the subject's midline mirror still gives p95 7.12 mm",
               (("mean_mm", 2.43), ("p95_mm", 8.15)), "pending owner approval"),
)

EXCLUDED_FROM_MO2 = ("jump", "swim")   # jumps: left out for now (pointed toes, Decision 85); swim: no ground at all


@dataclass(frozen=True)
class Tolerance:
    id: str
    name: str
    profile: str                    # "all", "game" or "cinema"
    level: str                      # "all" or "Q0"
    limits: Tuple[Tuple[str, float], ...]
    unit: str
    measured_by: str
    provenance: str = PROVENANCE

    @property
    def limit(self) -> Dict[str, float]:
        return dict(self.limits)


TOLERANCES: Tuple[Tolerance, ...] = (
    Tolerance("AN-1", "Per-bone fit to the reference (anchor RMS), acceptance", "all", "all",
              (("rms_mm", 4.0),), "mm", "A20 long-bone fit (scripts/f2_femur_fit.py)"),
    Tolerance("AN-3", "Left/right mirror symmetry, per pair", "all", "all",
              (("mean_mm", 2.5), ("p95_mm", 6.0)), "mm", "A22 region fit, mirror pairs"),
    Tolerance("MO-2", "Sole height on stance frames (median |h| per clip), jumps excluded", "game", "all",
              (("abs_m", 0.01),), "m", "batch retarget with leg grounding (domain/animation/leg_quality.py)"),
    Tolerance("MO-2", "Sole height on stance frames (median |h| per clip), jumps excluded", "cinema", "all",
              (("abs_m", 0.003),), "m", "batch retarget with leg grounding (domain/animation/leg_quality.py)"),
    Tolerance("MO-3", "Knee direction against the mocap source, per clip", "game", "all",
              (("median_deg", 5.0), ("p90_deg", 10.0)), "deg", "batch retarget with leg grounding"),
    Tolerance("MO-3", "Knee direction against the mocap source, per clip", "cinema", "all",
              (("median_deg", 3.0), ("p90_deg", 6.0)), "deg", "batch retarget with leg grounding"),
    Tolerance("RG-1", "Game rig against canonical rig in the rest pose", "all", "all",
              (("max_mm", 0.1),), "mm", "Blender headless check 'game rig: build' (RIG-GAME-001)"),
    Tolerance("RG-6", "ARKit face shapes", "game", "all", (("max_shapes", 20),), "shapes",
              "face contract (domain/rigging/face.py); shapes on a head mesh when one exists"),
    Tolerance("RG-6", "ARKit face shapes", "cinema", "all", (("shapes", 52),), "shapes",
              "face contract (domain/rigging/face.py); shapes on a head mesh when one exists"),
    Tolerance("PF-1", "Frame time, 2-character arena", "game", "Q0",
              (("mean_ms", 16.7), ("p95_ms", 20.0)), "ms", "scripts/godot_perf.py, scenario souls_arena_2_bodies"),
    Tolerance("PF-4", "Workbench test render 1920x1080", "cinema", "Q0", (("seconds", 30.0),), "s",
              "Blender headless check 'CINE-GR-001 (a)+(d)'"),
)
IN_FORCE: Tuple[str, ...] = ("AN-1", "AN-3", "MO-2", "MO-3", "RG-1", "RG-6", "PF-1", "PF-4")


def tolerance(tid: str, profile: str = "all") -> Tolerance:
    for t in TOLERANCES:
        if t.id == tid and t.profile == profile:
            return t
    raise KeyError((tid, profile))


@dataclass(frozen=True)
class Verdict:
    id: str
    profile: str
    status: str
    measured: Mapping[str, object] = field(default_factory=dict)
    limit: Mapping[str, float] = field(default_factory=dict)
    detail: str = ""

    def as_dict(self) -> Dict[str, object]:
        return {"id": self.id, "profile": self.profile, "status": self.status, "measured": dict(self.measured),
                "limit": dict(self.limit), "detail": self.detail, "provenance": PROVENANCE}


def _v(tid: str, profile: str, status: str, measured=None, detail: str = "") -> Verdict:
    return Verdict(tid, profile, status, measured or {}, tolerance(tid, profile).limit, detail)


def judge_an1(rows: Optional[Sequence[Mapping[str, object]]]) -> Verdict:
    """``rows``: one per bone and side with ``rms_mm`` (A20 ``rows``)."""
    if not rows:
        return _v("AN-1", "all", NOT_MEASURED, detail="no A20 fit rows")
    lim = tolerance("AN-1").limit["rms_mm"]
    worst = max(rows, key=lambda r: float(r["rms_mm"]))
    over = [f"{r['bone']}_{r['side']} {float(r['rms_mm']):.2f}" for r in rows if float(r["rms_mm"]) > lim]
    return _v("AN-1", "all", FAIL if over else PASS,
              {"bone_sides": len(rows), "worst": f"{worst['bone']}_{worst['side']}",
               "worst_rms_mm": round(float(worst["rms_mm"]), 3), "over": over})


def judge_an3(pairs: Optional[Mapping[str, Mapping[str, float]]], reference: str = REFERENCE) -> Verdict:
    """``pairs``: {name: {mean_mm, p95_mm}} (A22 mirror pairs)."""
    if not pairs:
        return _v("AN-3", "all", NOT_MEASURED, detail="no A22 mirror pairs")
    lim = tolerance("AN-3").limit
    out = {k: {"mean_mm": round(v["mean_mm"], 2), "p95_mm": round(v["p95_mm"], 2)} for k, v in pairs.items()
           if v["mean_mm"] > lim["mean_mm"] or v["p95_mm"] > lim["p95_mm"]}
    excepted = {e.item: e for e in EXCEPTIONS if e.id == "AN-3" and e.reference == reference and e.item in out}
    over = {k: v for k, v in out.items() if k not in excepted}
    return _v("AN-3", "all", FAIL if over else PASS,
              {"pairs": len(pairs), "max_mean_mm": round(max(v["mean_mm"] for v in pairs.values()), 3),
               "max_p95_mm": round(max(v["p95_mm"] for v in pairs.values()), 3), "over": over,
               "exceptions": {k: {**out[k], "cause": e.cause, "status": e.status} for k, e in excepted.items()}},
              detail=(f"exceptions applied: {', '.join(sorted(excepted))} ({REFERENCE}; "
                      f"{', '.join(sorted({e.status for e in excepted.values()}))})") if excepted else "")


def _leg_values(clips: Iterable[Mapping[str, object]], key: str, exclude: Sequence[str] = ()):
    for c in clips:
        if c.get("category") in exclude:
            continue
        legs = c.get("legs") or {}
        variant = "rm" if "rm" in legs else "standard"   # one value per clip; the root-motion variant when present
        if legs.get(variant, {}).get(key) is not None:
            yield f"{c.get('library')}/{c['clip']}", legs[variant]


def judge_mo2(clips: Optional[Sequence[Mapping[str, object]]], profile: str) -> Verdict:
    vals = list(_leg_values(clips or (), "sole_median_m", EXCLUDED_FROM_MO2))
    if not vals:
        return _v("MO-2", profile, NOT_MEASURED, detail="no retarget report with leg metrics")
    lim = tolerance("MO-2", profile).limit["abs_m"]
    over = {k: round(v["sole_median_m"] * 100, 2) for k, v in vals if abs(v["sole_median_m"]) > lim}
    worst = max(vals, key=lambda kv: abs(kv[1]["sole_median_m"]))
    judged = {k for k, _ in vals}
    not_judged = sorted(f"{c.get('library')}/{c['clip']}" for c in clips or ()
                        if c.get("category") not in EXCLUDED_FROM_MO2 and c.get("legs")
                        and f"{c.get('library')}/{c['clip']}" not in judged)
    return _v("MO-2", profile, FAIL if over else PASS,
              {"clips": len(vals), "failing": len(over), "worst": worst[0],
               "worst_cm": round(worst[1]["sole_median_m"] * 100, 2), "over_cm": over, "not_judged": not_judged},
              detail=f"categories excluded: {', '.join(EXCLUDED_FROM_MO2)}; {len(not_judged)} clips not judged "
                     f"(fewer than 10 support frames)")


def judge_mo3(clips: Optional[Sequence[Mapping[str, object]]], profile: str) -> Verdict:
    vals = list(_leg_values(clips or (), "knee_median_deg"))
    if not vals:
        return _v("MO-3", profile, NOT_MEASURED, detail="no retarget report with leg metrics")
    lim = tolerance("MO-3", profile).limit
    over = {k: (v["knee_median_deg"], v["knee_p90_deg"]) for k, v in vals
            if v["knee_median_deg"] > lim["median_deg"] or v["knee_p90_deg"] > lim["p90_deg"]}
    worst = max(vals, key=lambda kv: kv[1]["knee_p90_deg"])
    return _v("MO-3", profile, FAIL if over else PASS,
              {"clips": len(vals), "failing": len(over), "worst": worst[0],
               "worst_median_deg": worst[1]["knee_median_deg"], "worst_p90_deg": worst[1]["knee_p90_deg"],
               "over": over})


def judge_rg1(rest_error_mm: Optional[float]) -> Verdict:
    if rest_error_mm is None:
        return _v("RG-1", "all", NOT_MEASURED, detail="no Blender headless report with the game-rig check")
    lim = tolerance("RG-1").limit["max_mm"]
    return _v("RG-1", "all", PASS if rest_error_mm <= lim else FAIL, {"max_mm": rest_error_mm})


def judge_rg6(shapes: int, profile: str, on_mesh: Optional[int] = None) -> Verdict:
    """Contract count, and the count on a head mesh when one exists (``on_mesh``)."""
    lim = tolerance("RG-6", profile).limit
    ok = shapes <= lim["max_shapes"] if profile == "game" else shapes == lim["shapes"]
    measured = {"contract_shapes": shapes, "mesh_shapes": on_mesh}
    if not ok:
        return _v("RG-6", profile, FAIL, measured)
    if on_mesh is None:
        return _v("RG-6", profile, PASS, measured,
                  detail="contract only: no head mesh with ARKit shapes exists yet, so the asset part is not measured")
    ok_mesh = on_mesh <= lim["max_shapes"] if profile == "game" else on_mesh == lim["shapes"]
    return _v("RG-6", profile, PASS if ok_mesh else FAIL, measured)


def judge_pf1(adapter: Optional[str], arena: Optional[Mapping[str, float]]) -> Verdict:
    if not adapter or Q0_ADAPTER not in adapter:
        return _v("PF-1", "game", NOT_MEASURED, {"adapter": adapter},
                  detail=f"Q0 is defined on the {Q0_ADAPTER}; this report comes from other hardware or none")
    if not arena:
        return _v("PF-1", "game", NOT_MEASURED, {"adapter": adapter},
                  detail="the perf report has no souls_arena_2_bodies scenario")
    lim = tolerance("PF-1", "game").limit
    ok = arena["avg_ms"] <= lim["mean_ms"] and arena["p95_ms"] <= lim["p95_ms"]
    return _v("PF-1", "game", PASS if ok else FAIL,
              {"adapter": adapter, "mean_ms": arena["avg_ms"], "p95_ms": arena["p95_ms"]})


def judge_pf4(seconds: Optional[float]) -> Verdict:
    if seconds is None:
        return _v("PF-4", "cinema", NOT_MEASURED, detail="no Blender headless report with the CINE-GR-001 render")
    lim = tolerance("PF-4", "cinema").limit["seconds"]
    return _v("PF-4", "cinema", PASS if seconds <= lim else FAIL, {"seconds": seconds})


def judge(an1_rows=None, an3_pairs=None, retarget_clips=None, rg1_mm=None, face_game=0, face_cinema=0,
          face_mesh=None, perf_adapter=None, perf_arena=None, pf4_seconds=None) -> Tuple[Verdict, ...]:
    """All verdicts of the batch in force, in table order."""
    return (judge_an1(an1_rows), judge_an3(an3_pairs),
            judge_mo2(retarget_clips, "game"), judge_mo2(retarget_clips, "cinema"),
            judge_mo3(retarget_clips, "game"), judge_mo3(retarget_clips, "cinema"),
            judge_rg1(rg1_mm), judge_rg6(face_game, "game", face_mesh), judge_rg6(face_cinema, "cinema", face_mesh),
            judge_pf1(perf_adapter, perf_arena), judge_pf4(pf4_seconds))
