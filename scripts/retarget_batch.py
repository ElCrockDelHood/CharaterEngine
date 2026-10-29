"""Batch retarget + clip QA of the Quaternius Universal Animation Library onto the canonical armature.

    python scripts/retarget_batch.py                          # UAL1 + UAL2, standard + root-motion variants
    python scripts/retarget_batch.py --libraries ual1 --clips Jog_Fwd,Sprint
    python scripts/retarget_batch.py --report-only            # recompute QA from the last samples (no Blender)
    python scripts/retarget_batch.py --no-export              # QA only, no per-clip GLB

Each (library, variant) runs in its own Blender 3.6 process (``runtime/blender/ce_batch_retarget.py``) through
``_logrun`` (``logs/<UTC>_retarget_batch.log``). Outputs (git-ignored): ``builds/animations/<lib>/<clip>.glb``
(in place) and ``<clip>_RM.glb`` (root motion), raw samples in ``builds/animations/samples/`` and the QA report
``builds/animations/retarget_report.json`` (+ ``.md``). Every QA threshold is ESTIMATE
(``character_engine.domain.animation.clip_qa``). The input libraries are read in place and never copied.

The report also reads the ``root`` translation channel of every clip straight from the GLB (stdlib parser,
no Blender) so the root speed can be checked independently of the importer.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from _logrun import run_logged, utf8_console
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.animation import clip_qa  # noqa: E402

SCRIPT = ROOT / "runtime" / "blender" / "ce_batch_retarget.py"
OUT_DIR = ROOT / "builds" / "animations"
ASSETS = Path("C:/DEV/Assets/descargas")
LIBRARIES = {
    "ual1": ("quaternius_ual1/extracted/Universal Animation Library[Standard]/Unreal-Godot", "UAL1_Standard"),
    "ual2": ("quaternius_ual2/extracted/Universal Animation Library 2[Standard]/Unreal-Godot", "UAL2_Standard"),
}
VARIANTS = {"standard": "", "rm": "_RM"}
SEAM_POINTS = ("SACRUM", "THORACIC_8", "CERVICAL_1", "CAPITATE_L", "CAPITATE_R", "RADIUS_L", "RADIUS_R",
               "TIBIA_L", "TIBIA_R", "CALCANEUS_L", "CALCANEUS_R", "TOE_PHALANX_PROXIMAL_3_L",
               "TOE_PHALANX_PROXIMAL_3_R")
# Foot contact points (Decision 54 foot layout, all at z = 0 in the rest pose): heel, ball (MTP 3) and the end
# of the toe-3 proximal phalanx. Only toe 3 is driven by the source ball joint (bone map quaternius_ual), so
# the other toes stay rigid with the foot; the big-toe tip is reported apart (UNDRIVEN_TOE_TIPS), ungraded.
TARGET_FEET = {"L": ("CALCANEUS_L", "TOE_PHALANX_PROXIMAL_3_L", "TOE_PHALANX_PROXIMAL_3_L.tail"),
               "R": ("CALCANEUS_R", "TOE_PHALANX_PROXIMAL_3_R", "TOE_PHALANX_PROXIMAL_3_R.tail")}
UNDRIVEN_TOE_TIPS = ("TOE_PHALANX_DISTAL_1_L.tail", "TOE_PHALANX_DISTAL_1_R.tail")
# Source (Quaternius UE-style rig): ankle, ball joint, ball end (toe tip).
SOURCE_FEET = {"L": ("foot_l", "ball_l", "ball_l.tail"), "R": ("foot_r", "ball_r", "ball_r.tail")}


# ----------------------------------------------------------------------------- GLB (stdlib) ---

_COMPONENTS = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4), 5121: ("B", 1)}
_TYPE_SIZE = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}


def read_glb(path: Path) -> tuple[dict, bytes]:
    """JSON chunk and BIN chunk of a binary glTF file."""
    data = Path(path).read_bytes()
    magic, version, _length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError(f"{path} is not a glTF 2.0 binary")
    off, doc, binary = 12, None, b""
    while off < len(data):
        length, kind = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + length]
        if kind == 0x4E4F534A:
            doc = json.loads(chunk.decode("utf-8"))
        elif kind == 0x004E4942:
            binary = chunk
        off += 8 + length
    if doc is None:
        raise ValueError(f"{path} has no JSON chunk")
    return doc, binary


def read_accessor(doc: dict, binary: bytes, index: int) -> list:
    acc = doc["accessors"][index]
    view = doc["bufferViews"][acc["bufferView"]]
    fmt, size = _COMPONENTS[acc["componentType"]]
    n = _TYPE_SIZE[acc["type"]]
    stride = view.get("byteStride") or size * n
    base = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    out = []
    for i in range(acc["count"]):
        vals = struct.unpack_from("<" + fmt * n, binary, base + i * stride)
        out.append(vals[0] if n == 1 else list(vals))
    return out


def glb_root_channels(path: Path, node_name: str = "root") -> dict:
    """Per animation: duration and horizontal displacement of ``node_name``'s translation, read from the file.

    glTF is Y-up, so the horizontal plane is XZ. Times are seconds (no frame rate involved).
    """
    doc, binary = read_glb(path)
    nodes = [i for i, nd in enumerate(doc.get("nodes", [])) if nd.get("name") == node_name]
    out = {}
    for anim in doc.get("animations", []):
        name = anim.get("name", "")
        times = [t for ch in anim["channels"] for t in read_accessor(doc, binary, anim["samplers"][ch["sampler"]]["input"])]
        rec = {"duration_s": (max(times) - min(times)) if times else 0.0, "keys": None,
               "displacement_m": 0.0, "first": None, "last": None}
        for ch in anim["channels"]:
            tgt = ch["target"]
            if tgt.get("node") in nodes and tgt.get("path") == "translation":
                s = anim["samplers"][ch["sampler"]]
                t = read_accessor(doc, binary, s["input"])
                v = read_accessor(doc, binary, s["output"])
                rec.update(keys=len(t), first=v[0], last=v[-1], channel_duration_s=t[-1] - t[0],
                           displacement_m=math.hypot(v[-1][0] - v[0][0], v[-1][2] - v[0][2]))
        rec["speed_m_s"] = rec["displacement_m"] / rec["duration_s"] if rec["duration_s"] > 0 else None
        out[name] = rec
    return out


# ----------------------------------------------------------------------------- report ---

def clip_records(samples: dict[str, dict]) -> dict[str, dict]:
    """{variant: {clip: record}} from the per-variant sample files of one library."""
    return {v: {c["clip"]: c for c in s.get("clips", [])} for v, s in samples.items()}


def evaluate_library(lib: str, samples: dict[str, dict], glb_checks: dict[str, dict]) -> list[dict]:
    by_variant = clip_records(samples)
    std, rm = by_variant.get("standard", {}), by_variant.get("rm", {})
    meta = samples.get("standard") or samples.get("rm")
    fps = meta["fps"]
    dt = 1.0 / fps
    target_feet, source_feet = TARGET_FEET, SOURCE_FEET
    out = []
    for clip in sorted(set(std) | set(rm)):
        s, r = std.get(clip), rm.get(clip)
        errors = [f"{v}: {c.get('error')}" for v, c in (("standard", s), ("rm", r)) if c and c["status"] != "ok"]
        base = s if s and s["status"] == "ok" else r if r and r["status"] == "ok" else None
        if base is None:
            out.append({"library": lib, "clip": clip, "category": clip_qa.classify(clip), "status": "error",
                        "errors": errors or ["missing in both variants"], "checks": {}})
            continue
        rm_ok = r if r and r["status"] == "ok" else None
        rec = clip_qa.evaluate_clip(
            clip, dt=dt, inplace_target=base["target"], rm_target=rm_ok["target"] if rm_ok else None,
            target_rest=meta["target_rest"], target_feet=target_feet,
            inplace_source=base["source"], rm_source=rm_ok["source"] if rm_ok else None,
            source_rest=meta["source_rest"], source_feet=source_feet, seam_points=SEAM_POINTS)
        rec["library"] = lib
        rec["frame_end_raw"] = base.get("frame_end_raw")
        rec["integer_frames"] = abs(base.get("frame_end_raw", 0) - round(base.get("frame_end_raw", 0))) < 1e-3
        rec["glb"] = {v: c.get("glb_out") for v, c in (("standard", s), ("rm", r)) if c and c.get("glb_out")}
        rec["mapped_bones"] = base.get("mapped_bones")
        tips = [f[n][2] - meta["target_rest"][n][2] for f in base["target"] for n in UNDRIVEN_TOE_TIPS
                if n in f and n in meta["target_rest"]]
        if tips:   # diagnostic only: toes 1, 2, 4, 5 do not bend with the source ball joint
            rec["undriven_toe_tip_min_height_m"] = round(min(tips), 4)
        for v, checks in glb_checks.items():
            raw = checks.get(base.get("action", "")) or checks.get(clip)
            if raw:
                rec.setdefault("glb_root_channel", {})[v] = {k: raw[k] for k in
                                                             ("duration_s", "displacement_m", "speed_m_s", "keys")}
        if errors:
            rec["errors"] = errors
            rec["status"] = "error"
        out.append(rec)
    return out


def _f(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def markdown(report: dict) -> str:
    lines = [f"# Retarget batch QA — {report['started']}", "",
             f"Blender `{report['blender']}` · bone map `{report['bone_map']}` · {report['fps']} fps · "
             "all thresholds **ESTIMATE** (see `thresholds`).", "",
             "| Category | Clips | ok | warn | fail | error | Failing checks |",
             "|---|---|---|---|---|---|---|"]
    for cat, s in report["summary"].items():
        fc = ", ".join(f"{k} ×{v}" for k, v in s["failed_checks"].items()) or "—"
        lines.append(f"| {cat} | {s['clips']} | {s['ok']} | {s['warn']} | {s['fail']} | {s['error']} | {fc} |")
    lines += ["", "| Lib | Clip | Cat | Status | Slide m/s | Pen. m | Seam m | Root m/s | Stance m/s | Ratio |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in report["clips"]:
        tf = r.get("target_feet", {})
        lines.append(f"| {r['library']} | {r['clip']} | {r['category']} | {r['status']} | "
                     f"{_f(tf.get('slide_mean_m_s'))} | {_f(tf.get('penetration_m'), 3)} | "
                     f"{_f((r.get('loop_seam') or {}).get('position_m'), 3)} | "
                     f"{_f((r.get('root_motion_source') or {}).get('speed_m_s'))} | "
                     f"{_f(r.get('stance_speed_source_m_s'))} | {_f(r.get('root_to_stance_speed_ratio'))} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", default=None, help="Blender 3.6 executable (default: CE_BLENDER / C:/DEV/Tools/Blender)")
    ap.add_argument("--assets", type=Path, default=ASSETS, help="folder holding quaternius_ual1/ and quaternius_ual2/")
    ap.add_argument("--libraries", default=",".join(LIBRARIES))
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--clips", default="", help="comma-separated substrings (subset run)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--timeout", type=int, default=3600, help="seconds per Blender process")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--report-only", action="store_true", help="skip Blender; reuse samples in <out-dir>/samples")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    libs = [x.strip() for x in a.libraries.split(",") if x.strip()]
    variants = [x.strip() for x in a.variants.split(",") if x.strip()]
    if any(x not in LIBRARIES for x in libs) or any(v not in VARIANTS for v in variants):
        print(f"[retarget] unknown library/variant; known: {list(LIBRARIES)} / {list(VARIANTS)}")
        return 2
    exe = None if a.report_only else find_blender(a.blender)
    if exe is None and not a.report_only:
        print("[retarget] Blender not found (use --blender or CE_BLENDER)")
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sample_dir = a.out_dir / "samples"
    logs, records, failures = [], [], []
    for lib in libs:
        folder, stem = LIBRARIES[lib]
        samples, glb_checks = {}, {}
        for v in variants:
            glb = a.assets / folder / f"{stem}{VARIANTS[v]}.glb"
            out = sample_dir / f"{lib}_{v}.json"
            if not glb.exists():
                failures.append(f"{lib}/{v}: input not found {glb}")
                print(f"[retarget] missing input {glb}")
                continue
            glb_checks[v] = glb_root_channels(glb)
            if not a.report_only:
                cmd = [exe, "-b", "--factory-startup", "--python", SCRIPT, "--", "--glb", glb, "--library", lib,
                       "--variant", v, "--fps", str(a.fps), "--out-dir", a.out_dir, "--samples", out]
                if a.clips:
                    cmd += ["--clips", a.clips]
                if a.no_export:
                    cmd.append("--no-export")
                print(f"\n[retarget] {lib} {v}: {glb.name}", flush=True)
                code, _secs, log = run_logged(cmd, "retarget_batch", timeout=a.timeout, echo=not a.quiet)
                logs.append(str(log))
                if code != 0:
                    failures.append(f"{lib}/{v}: Blender exit {code} (log {log})")
            if out.exists():
                samples[v] = json.loads(out.read_text(encoding="utf-8"))
        if samples:
            records += evaluate_library(lib, samples, glb_checks)

    meta = next(iter(json.loads(p.read_text(encoding="utf-8")) for p in sorted(sample_dir.glob("*.json"))), {}) \
        if sample_dir.exists() else {}
    report = {"started": stamp, "blender": meta.get("blender"), "bone_map": meta.get("bone_map"), "fps": a.fps,
              "stature_m": meta.get("stature_m"), "provenance": clip_qa.PROVENANCE,
              "thresholds": {**asdict(clip_qa.DEFAULT_THRESHOLDS), "provenance": clip_qa.PROVENANCE},
              "libraries": libs, "variants": variants, "logs": logs, "run_failures": failures,
              "summary": clip_qa.summarize(records), "clips": records}
    a.out_dir.mkdir(parents=True, exist_ok=True)
    js, md = a.out_dir / "retarget_report.json", a.out_dir / "retarget_report.md"
    js.write_text(json.dumps(report, indent=1), encoding="utf-8")
    md.write_text(markdown(report), encoding="utf-8")
    print("\n" + markdown(report).split("\n\n| Lib")[0])
    print(f"\n[retarget] report: {js}\n[retarget] table:  {md}")
    if failures:
        print("[retarget] run failures:\n  " + "\n  ".join(failures))
    errors = [r["clip"] for r in records if r["status"] == "error"]
    if errors:
        print(f"[retarget] clips with errors: {errors}")
    return 1 if failures or errors else 0


if __name__ == "__main__":
    sys.exit(main())
