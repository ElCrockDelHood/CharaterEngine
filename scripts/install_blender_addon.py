"""Install the Character Engine addon into a Blender / UPBGE user addons folder.

    python scripts/install_blender_addon.py                     # auto-detect Blender & UPBGE
    python scripts/install_blender_addon.py --target "C:/Users/me/AppData/Roaming/Blender Foundation/Blender/5.0/scripts/addons"
    python scripts/install_blender_addon.py --zip builds/character_engine_blender.zip   # for "Install from file"
    python scripts/install_blender_addon.py --blender C:/DEV/Tools/Blender/blender.exe   # that Blender's user addons

The addon is copied as ``character_engine_blender`` together with a ``ce_src_path.txt`` marker
pointing at this repository's ``src`` folder, so the domain code is importable from Blender.
Enable it in Preferences > Add-ons > "Character Engine" (Rigging).
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON_SRC = ROOT / "src" / "character_engine" / "infrastructure" / "blender" / "addon"
ADDON_NAME = "character_engine_blender"


def default_targets() -> list[Path]:
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    out = []
    for pattern in (appdata / "Blender Foundation" / "Blender" / "*" / "scripts" / "addons",
                    appdata / "UPBGE" / "Blender" / "*" / "scripts" / "addons",
                    appdata / "Blender Foundation" / "UPBGE" / "*" / "scripts" / "addons"):
        out += [Path(p) for p in glob.glob(str(pattern))]
    # portable UPBGE install (config next to the executable)
    for p in glob.glob(r"C:/Tools/UPBGE/**/scripts/addons", recursive=True):
        out.append(Path(p))
    return sorted(set(out))


def blender_user_addons(blender_exe: Path) -> Path:
    """User addons folder of a given Blender build (asks that Blender; works for 3.6 and 4.x)."""
    expr = "import bpy; print('CE_ADDONS=' + bpy.utils.user_resource('SCRIPTS', path='addons'))"
    out = subprocess.run([str(blender_exe), "-b", "--factory-startup", "--python-expr", expr],
                         capture_output=True, text=True, timeout=300).stdout
    for line in out.splitlines():
        if line.startswith("CE_ADDONS="):
            return Path(line[len("CE_ADDONS="):].strip())
    raise RuntimeError(f"could not query the addons folder of {blender_exe}")


def install(target: Path) -> Path:
    dst = target / ADDON_NAME
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(ADDON_SRC, dst, ignore=shutil.ignore_patterns("__pycache__"))
    (dst / "ce_src_path.txt").write_text(str(ROOT / "src"), encoding="utf-8")
    return dst


def make_zip(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in ADDON_SRC.rglob("*.py"):
            zf.write(file, Path(ADDON_NAME) / file.relative_to(ADDON_SRC))
        zf.writestr(f"{ADDON_NAME}/ce_src_path.txt", str(ROOT / "src"))
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=Path, action="append", help="addons folder (repeatable)")
    ap.add_argument("--zip", type=Path, default=None)
    ap.add_argument("--blender", type=Path, default=os.environ.get("CE_BLENDER"),
                    help="Blender executable whose user addons folder is the target (default: $CE_BLENDER)")
    a = ap.parse_args(argv)
    if a.zip:
        print(f"zip written: {make_zip(a.zip)}")
    targets = list(a.target or [])
    if a.blender:
        targets.append(blender_user_addons(Path(a.blender)))
    targets = targets or default_targets()
    if not targets and not a.zip:
        print("no Blender/UPBGE addons folder found; pass --target or --zip")
        return 1
    for t in targets:
        t.mkdir(parents=True, exist_ok=True)
        print(f"installed: {install(t)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
