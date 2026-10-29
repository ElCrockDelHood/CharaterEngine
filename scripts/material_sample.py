"""Material samples driver: 1 = forearm + wool sleeve (+ steel bracer) struck by a sabre edge;
2 = thorax with ribs and cavity + wool coat (+ padded vest) hit by a blunt impactor.

    python scripts/material_sample.py                         # sample 1 (forearm), both variants, write the report
    python scripts/material_sample.py --sample thorax --render --samples 128   # sample 2 (thorax, vest)
    python scripts/material_sample.py --render                # + Blender scene and EEVEE / Cycles stills
    python scripts/material_sample.py --render --samples 512 --resolution 2560x1440 --turntable 48
    python scripts/material_sample.py --render --gpu-probe    # one tiny Cycles render per GPU backend, then stop

The simulation is pure Python (``domain/physics/forearm_strike.py``) and fully reproducible: the report carries
the seed, the sleeve state hash after settling and after the strike, and a sha256 of the whole result. Blender
only draws what the domain computed. Outputs: ``builds/material_sample/<UTC>/`` (JSON per variant, summary
``.md``, renders, ``.blend``). Every non-canonical value is ESTIMATE / ASSUMED / PLACEHOLDER (see the report).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _logrun import run_logged, utf8_console
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.physics import forearm_strike, torso_strike  # noqa: E402

DATA = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
SCRIPT = ROOT / "runtime" / "blender" / "ce_material_sample.py"
OUT = ROOT / "builds" / "material_sample"


def canonical_points():
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    p = lambda d: (d["x"], d["y"], d["z"])  # noqa: E731
    return {b["canonical_name"]: (p(b["head"]), p(b["tail"])) for b in bones}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _renders_md(render: dict | None) -> list[str]:
    if not render:
        return []
    lines = ["", "## Renders", "", "| File | Engine | Device | Samples | Seconds |", "|---|---|---|---|---|"]
    for item in render.get("renders", []):
        lines.append(f"| {Path(item['path']).name} | {item['engine']} | {item.get('device', '-')} | "
                     f"{item.get('samples', '-')} | {item['seconds']} |")
    return lines


def summary_md(stamp: str, sample: str, results: dict, render: dict | None) -> str:
    first = next(iter(results.values()))
    if sample == "forearm":
        lines = [f"# Material sample 1 — forearm strike ({stamp})", "",
                 "All values ESTIMATE / ASSUMED / PLACEHOLDER (see each JSON). Pure-Python XPBD + cut-energy model.",
                 "", "| Variant | Blade stopped in | Depth below skin (mm) | Wound | Deepest layer | Severity | "
                 "Sleeve links cut | Sim s | Final state hash |", "|---|---|---|---|---|---|---|---|---|"]
        for name, r in results.items():
            w = r["wound"] or {}
            lines.append(f"| {name} | {r['cut']['stopped_in']} | {r['cut']['skin_depth_m'] * 1000:.1f} | "
                         f"{w.get('type', '-')} | {w.get('deepest_layer', '-')} | {w.get('severity', '-')} | "
                         f"{r['sleeve']['constraints_cut']} | {r['timing']['simulate_s']} | "
                         f"`{r['hash']['final_state'][:16]}` |")
        lines += ["", f"Blade kinetic energy: {first['blade']['kinetic_energy_j']} J "
                      "(mass PLACEHOLDER, speed ESTIMATE).", f"Seed: {first['config']['seed']}."]
        return "\n".join(lines + _renders_md(render)) + "\n"
    lines = [f"# Material sample 2 — thorax blunt strike ({stamp})", "",
             "All values ESTIMATE / ASSUMED / PLACEHOLDER (see each JSON). Pure-Python XPBD + plateau crush model; "
             "thorax block is a sphere, layers are stacked on a cylinder along the spine segment.", "",
             "| Variant | Impactor stopped in | Affected depth (mm) | Ribs fractured | Deepest layer | Severity | "
             "Legacy mapping severity | Sim s | Final state hash |", "|---|---|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        b, w, lg = r["blunt"], r["wound"], r["wound_legacy_mapping"]
        lines.append(f"| {name} | {b['stopped_in']} | {b['affected_depth_m'] * 1000:.1f} | {b['fractured']} | "
                     f"{w['deepest_layer']} | {w['severity']} | {lg['severity']} | {r['timing']['simulate_s']} | "
                     f"`{r['hash']['final_state'][:16]}` |")
    lines += ["", f"Impactor kinetic energy: {first['impactor']['kinetic_energy_j']} J "
                  "(mass PLACEHOLDER, speed ESTIMATE). Seed: " + str(first["config"]["seed"]) + ".",
              "", "## Energy sweep (impactor speed → rib fracture)", "",
              "| Speed (m/s) | Energy (J) | " + " | ".join(f"{n}: stops in / fractured" for n in results) + " |",
              "|---|---|" + "---|" * len(results)]
    for i, row in enumerate(first["sweep"]):
        cells = []
        for r in results.values():
            sw = r["sweep"][i]
            cells.append(f"{sw['stopped_in']} / {'yes' if sw['ribs_fractured'] else 'no'}")
        lines.append(f"| {row['speed_m_s']} | {row['energy_j']} | " + " | ".join(cells) + " |")
    return "\n".join(lines + _renders_md(render)) + "\n"


def main() -> int:
    utf8_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="build the Blender scene and render stills")
    ap.add_argument("--blender", default=None)
    ap.add_argument("--engines", default="eevee,cycles")
    ap.add_argument("--samples", type=int, default=256, help="Cycles samples")
    ap.add_argument("--resolution", default="1920x1080")
    ap.add_argument("--turntable", type=int, default=0, help="EEVEE turntable frames (0 = none)")
    ap.add_argument("--gpu-probe", action="store_true", help="only probe Cycles GPU backends and exit")
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sample", choices=("forearm", "thorax"), default="forearm")
    a = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT / (stamp if a.sample == "forearm" else f"{stamp}_{a.sample}")
    out.mkdir(parents=True, exist_ok=True)
    blender = find_blender(a.blender) if (a.render or a.gpu_probe) else None
    if (a.render or a.gpu_probe) and blender is None:
        print("[sample] Blender not found (set CE_BLENDER or --blender)")
        return 2

    if a.gpu_probe:
        report = out / "gpu_probe.json"
        code, secs, log = run_logged([blender, "-b", "--factory-startup", "--python", SCRIPT, "--",
                                      "--gpu-probe", "--out", out], "material_sample", timeout=a.timeout)
        print(f"[sample] gpu probe exit {code} in {secs:.1f} s -> {report}")
        return code

    module, prefix = (forearm_strike, "forearm") if a.sample == "forearm" else (torso_strike, "thorax")
    cfg = module.SampleConfig(seed=a.seed)
    pts = canonical_points()
    results = {}
    for protected in (False, True):
        t = time.perf_counter()
        r = module.run_variant(pts, protected, cfg)
        r["timing"] = {"simulate_s": round(time.perf_counter() - t, 2)}
        path = out / f"{prefix}_{r['variant']}.json"
        path.write_text(json.dumps(r), encoding="utf-8")
        results[r["variant"]] = r
        w = r["wound"] or {}
        if a.sample == "forearm":
            what = (f"stopped in {r['cut']['stopped_in']}, skin depth {r['cut']['skin_depth_m'] * 1000:.1f} mm, "
                    f"wound {w.get('type')} / {w.get('deepest_layer')} / severity {w.get('severity')}, "
                    f"sleeve links cut {r['sleeve']['constraints_cut']}")
        else:
            what = (f"stopped in {r['blunt']['stopped_in']}, affected depth {r['blunt']['affected_depth_m'] * 1000:.1f} "
                    f"mm, ribs fractured {r['blunt']['fractured']}, deepest {w['deepest_layer']} / severity "
                    f"{w['severity']} (legacy mapping severity {r['wound_legacy_mapping']['severity']})")
        print(f"[sample] {r['variant']}: {what}, sim {r['timing']['simulate_s']} s, sha256 {r['sha256'][:16]}",
              flush=True)

    render = None
    if a.render:
        cmd = [blender, "-b", "--factory-startup", "--python", SCRIPT, "--", "--input", out, "--out", out,
               "--engines", a.engines, "--samples", str(a.samples), "--resolution", a.resolution,
               "--turntable", str(a.turntable), "--sample", a.sample]
        code, secs, log = run_logged(cmd, "material_sample", timeout=a.timeout)
        rp = out / "render_report.json"
        render = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {"error": f"exit {code}"}
        render["log"], render["wall_s"] = str(log), round(secs, 1)
        for item in render.get("renders", []):
            p = Path(item["path"])
            if p.exists():
                item["sha256"] = sha256(p)
        rp.write_text(json.dumps(render, indent=2), encoding="utf-8")
        print(f"[sample] blender exit {code} in {secs:.1f} s", flush=True)

    (out / "summary.md").write_text(summary_md(stamp, a.sample, results, render), encoding="utf-8")
    print(f"[sample] report: {out}")
    return 0 if render is None or "error" not in render else 1


if __name__ == "__main__":
    sys.exit(main())
