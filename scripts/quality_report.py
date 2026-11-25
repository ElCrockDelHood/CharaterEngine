"""Judge the quality tolerances in force (Decision 89) against the latest measurements.

    python scripts/quality_report.py                   # -> builds/reports/quality_tolerances.json / .md
    python scripts/quality_report.py --a20 C:/DEV/Assets/BodyParts3D_4.0/out/quality/f2_long_bones_fit_results.json

Reads, never measures: A20 / A22 (``docs/audit``, or a fresh fit result with ``--a20``), the batch retarget report
(``scripts/retarget_batch.py``), the Blender headless report (``scripts/engine_tests.py blender``) and the Godot perf
report (``scripts/godot_perf.py``). Missing inputs give NOT_MEASURED with the reason, never a relaxed limit.
Exit 1 when any tolerance fails, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.quality import tolerances as tq  # noqa: E402
from character_engine.domain.rigging.face import ARKIT_52, GAME_FACE_SHAPES  # noqa: E402

DEFAULTS = {
    "a20": ROOT / "docs" / "audit" / "A20_F2_LONG_BONES_FIT.json",
    "a22": ROOT / "docs" / "audit" / "A22_SKELETON_REGIONS_FIT.json",
    "retarget": ROOT / "builds" / "animations" / "quality" / "retarget_report.json",
    "blender": ROOT / "builds" / "tests" / "blender_addon_report.json",
    "perf": ROOT / "builds" / "tests" / "godot_perf.json",
}
OUT = ROOT / "builds" / "reports" / "quality_tolerances"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else None


def an1_rows(doc):
    """A20 summary (``rows``) or a raw long-bone fit result (``bones`` -> side -> ``rms_mm``)."""
    if not doc:
        return None
    if doc.get("rows"):
        return doc["rows"]
    return [{"bone": b, "side": s, "rms_mm": v[s]["rms_mm"]} for b, v in doc.get("bones", {}).items()
            for s in ("L", "R") if isinstance(v.get(s), dict) and "rms_mm" in v[s]]


def an3_pairs(doc):
    if not doc:
        return None
    return doc.get("mirror_pairs") or doc.get("mirror")


def blender_checks(doc):
    """RG-1 (game rig: canonical rest error, mm) and PF-4 (Workbench render, s) from the headless report."""
    rg1 = pf4 = None
    for r in (doc or {}).get("results", []):
        if r.get("status") != "PASS":
            continue
        if r["check"].startswith("game rig: build"):
            m = re.search(r"rest error ([0-9.]+) mm\)", r["detail"])
            rg1 = float(m.group(1)) if m else None
        elif r["check"].startswith("CINE-GR-001 (a)+(d)"):
            m = re.search(r"render ([0-9.]+) s", r["detail"])
            pf4 = float(m.group(1)) if m else None
    return rg1, pf4


def perf_arena(doc):
    if not doc:
        return None, None
    arena = next((r for r in doc.get("results", []) if r.get("scenario") == "souls_arena_2_bodies"), None)
    return doc.get("adapter"), arena


def markdown(verdicts, sources) -> str:
    lines = ["# Quality tolerances in force (Decision 89) — all ESTIMATE", "",
             "| ID | Profile | Status | Measured | Limit | Note |", "|---|---|---|---|---|---|"]
    for v in verdicts:
        m = {k: x for k, x in v.measured.items() if k not in ("over", "over_cm")}
        lines.append(f"| {v.id} | {v.profile} | **{v.status}** | {json.dumps(m)} | {json.dumps(dict(v.limit))} | "
                     f"{v.detail} |")
    for v in verdicts:
        over = v.measured.get("over") or v.measured.get("over_cm")
        if over:
            lines += ["", f"## {v.id} ({v.profile}) failing items", ""]
            lines += [f"- {k}: {val}" for k, val in sorted(over.items())]
    lines += ["", "## Sources", ""] + [f"- {k}: `{p}` ({'found' if p.exists() else 'missing'})" for k, p in sources.items()]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k, p in DEFAULTS.items():
        ap.add_argument(f"--{k}", type=Path, default=p)
    ap.add_argument("--out", type=Path, default=OUT, help="output path without extension")
    a = ap.parse_args(argv)
    sources = {k: getattr(a, k) for k in DEFAULTS}
    rg1, pf4 = blender_checks(_load(a.blender))
    adapter, arena = perf_arena(_load(a.perf))
    retarget = _load(a.retarget)
    verdicts = tq.judge(an1_rows=an1_rows(_load(a.a20)), an3_pairs=an3_pairs(_load(a.a22)),
                        retarget_clips=(retarget or {}).get("clips"), rg1_mm=rg1,
                        face_game=len(GAME_FACE_SHAPES), face_cinema=len(ARKIT_52), face_mesh=None,
                        perf_adapter=adapter, perf_arena=arena, pf4_seconds=pf4)
    report = {"decision": 89, "provenance": tq.PROVENANCE, "sources": {k: str(p) for k, p in sources.items()},
              "verdicts": [v.as_dict() for v in verdicts]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.with_suffix(".json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    a.out.with_suffix(".md").write_text(markdown(verdicts, sources), encoding="utf-8")
    for v in verdicts:
        m = {k: x for k, x in v.measured.items() if k not in ("over", "over_cm")}
        print(f"{v.id:5s} {v.profile:7s} {v.status:12s} {m}  limit {dict(v.limit)}  {v.detail}")
    print(f"report: {a.out.with_suffix('.json')}  table: {a.out.with_suffix('.md')}")
    return 1 if any(v.status == tq.FAIL for v in verdicts) else 0


if __name__ == "__main__":
    sys.exit(main())
