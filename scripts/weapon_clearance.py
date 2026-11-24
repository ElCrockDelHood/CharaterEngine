"""Weapon clearance: does the held sabre go into its own wielder? One Blender run over the UAL clips.

    python scripts/weapon_clearance.py                              # 11 sword / idle clips, margin 0
    python scripts/weapon_clearance.py --clips Sword_Attack --margin 0.01
    python scripts/weapon_clearance.py --gate                       # exit 1 when any clip fails
    python scripts/weapon_clearance.py --fix                        # turn the wrist, re-measure, before/after PNGs

Runs ``runtime/blender/ce_weapon_clearance.py`` in Blender 3.6 (background) through ``_logrun``
(``logs/<UTC>_weapon_clearance.log``). Report (git-ignored): ``builds/reports/weapon_clearance/<UTC>.json`` plus
``latest.json``. The math is ``character_engine.domain.animation.weapon_clearance`` (exact capsule distances, real blade
thickness); the gripping hand is the only segment allowed to touch the weapon.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from _logrun import run_logged, utf8_console
from engine_tests import find_blender

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "blender" / "ce_weapon_clearance.py"
OUT = ROOT / "builds" / "reports" / "weapon_clearance"
LIBS = [Path(r"C:\DEV\Assets\descargas\quaternius_ual1\extracted\Universal Animation Library[Standard]"
             r"\Unreal-Godot\UAL1_Standard.glb"),
        Path(r"C:\DEV\Assets\descargas\quaternius_ual2\extracted\Universal Animation Library 2[Standard]"
             r"\Unreal-Godot\UAL2_Standard.glb")]


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lib", type=Path, action="append", help="glTF animation library (default: UAL1 + UAL2)")
    ap.add_argument("--clips", default=None, help="comma-separated clip names (default: the runtime script's list)")
    ap.add_argument("--margin", type=float, default=0.0, help="required clearance in metres (PLACEHOLDER)")
    ap.add_argument("--gate", action="store_true", help="exit 1 when the weapon enters its wielder in any clip")
    ap.add_argument("--fix", action="store_true",
                    help="also turn the wrist where needed, re-measure, and render the worst frame before / after")
    ap.add_argument("--blender", default=None)
    a = ap.parse_args(argv)

    libs = a.lib or LIBS
    absent = [str(p) for p in libs if not p.exists()]
    if absent:
        print(f"animation libraries not found: {absent}")
        return 2
    blender = find_blender(a.blender)
    if blender is None:
        print("no Blender executable found (--blender or $CE_BLENDER)")
        return 2
    out = OUT / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    cmd = [blender, "-b", "--factory-startup", "--python", SCRIPT, "--", "--out", out, "--margin", str(a.margin)]
    for p in libs:
        cmd += ["--lib", p]
    if a.clips:
        cmd += ["--clips", a.clips]
    if a.fix:
        cmd += ["--fix", "--shots", OUT / out.stem]
    code, secs, log = run_logged([str(c) for c in cmd], "weapon_clearance")
    if code != 0 or not out.exists():
        print(f"Blender failed (exit {code}); log: {log}")
        return code or 1
    shutil.copyfile(out, OUT / "latest.json")
    doc = json.loads(out.read_text(encoding="utf-8"))
    print(f"\nreport: {out}\nlog:    {log}")
    for clip, s in doc["clips"].items():
        mark = "OK " if s["passed"] else "MAL"
        worst = s["worst"]
        where = f"  peor {worst['body']} {-worst['gap_m'] * 100:.1f} cm (cuadro {worst['frame']})" if worst else ""
        fixed = ""
        if "fix" in s:
            after = s["fix"]["after"]
            fixed = (f"  -> corregido: {after['frames_in_violation']} cuadros, giro max "
                     f"{s['fix']['max_angle_deg']:.0f} grados")
        print(f"  {mark} {clip:22s} {s['frames_in_violation']:3d}/{s['frames']:3d} cuadros{where}{fixed}")
    return 1 if a.gate and not doc["passed"] else 0


if __name__ == "__main__":
    sys.exit(main())
