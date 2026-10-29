"""Open the live-debug Blender window, or send it one command and print the reply (stdlib only).

    python scripts/live_debug.py open [--attack Sword_Attack --stance Sword_Idle --distance 0.9]
    python scripts/live_debug.py info
    python scripts/live_debug.py frame 22
    python scripts/live_debug.py shot --frame 22 --views side,contact --tag d1
    python scripts/live_debug.py screen
    python scripts/live_debug.py load --attack Sword_Regular_A --distance 0.9
    python scripts/live_debug.py play | stop
    python scripts/live_debug.py video --tag d1_block --slow 4

``open`` starts Blender with its UI (``runtime/blender/ce_live_debug.py``), logging through ``_logrun.py`` to
``logs/<UTC>_live_debug.log``. Other commands drop ``logs/live_debug/inbox/<id>.json`` and wait for the reply in
``outbox``. Shots land in ``logs/live_debug/shots``; the person's own captures go in ``logs/live_debug/from_mariano``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "logs" / "live_debug"
BLENDER = Path(os.environ.get("CE_BLENDER", r"C:\DEV\Tools\Blender\blender.exe"))
LIBS = [Path(r"C:\DEV\Assets\descargas\quaternius_ual1\extracted\Universal Animation Library[Standard]"
             r"\Unreal-Godot\UAL1_Standard.glb"),
        Path(r"C:\DEV\Assets\descargas\quaternius_ual2\extracted\Universal Animation Library 2[Standard]"
             r"\Unreal-Godot\UAL2_Standard.glb")]


def send(cmd: dict, timeout: float) -> dict:
    (LIVE / "inbox").mkdir(parents=True, exist_ok=True)
    name = f"{time.strftime('%H%M%S')}_{uuid.uuid4().hex[:6]}.json"
    tmp = LIVE / "inbox" / (name + ".tmp")
    tmp.write_text(json.dumps(cmd), encoding="utf-8")
    tmp.replace(LIVE / "inbox" / name)
    reply = LIVE / "outbox" / name
    t0 = time.time()
    while time.time() - t0 < timeout:
        if reply.exists():
            time.sleep(0.1)
            return json.loads(reply.read_text(encoding="utf-8"))
        time.sleep(0.2)
    raise SystemExit(f"no reply in {timeout} s: is the live-debug Blender open? ({LIVE / 'READY'})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["open", "info", "frame", "shot", "screen", "load", "play", "stop", "video", "eval"])
    ap.add_argument("value", nargs="?", help="frame number (frame) or code (eval)")
    ap.add_argument("--attack")
    ap.add_argument("--stance")
    ap.add_argument("--distance", type=float)
    ap.add_argument("--frame", type=int)
    ap.add_argument("--views", default="side,contact")
    ap.add_argument("--tag", default="")
    ap.add_argument("--slow", type=float, default=4.0, help="slow-motion factor around the contact (video)")
    ap.add_argument("--timeout", type=float, default=900.0)
    a = ap.parse_args()

    if a.cmd == "open":
        argv = [str(BLENDER), "--factory-startup", "--python", "runtime/blender/ce_live_debug.py", "--"]
        for lib in LIBS:
            argv += ["--lib", str(lib)]
        for flag in ("attack", "stance", "distance"):
            if getattr(a, flag) is not None:
                argv += [f"--{flag}", str(getattr(a, flag))]
        sys.path.insert(0, str(ROOT / "scripts"))
        from _logrun import run_logged, utf8_console
        utf8_console()
        return run_logged(argv, "live_debug")[0]

    cmd: dict = {"cmd": a.cmd}
    if a.cmd == "frame":
        cmd["frame"] = int(a.value)
    elif a.cmd == "shot":
        cmd.update(views=a.views.split(","), tag=a.tag)
        if a.frame is not None:
            cmd["frame"] = a.frame
    elif a.cmd == "video":
        cmd.update(tag=a.tag, slow=a.slow)
    elif a.cmd == "screen":
        cmd["tag"] = a.tag
    elif a.cmd == "load":
        cmd.update({k: getattr(a, k) for k in ("attack", "stance", "distance") if getattr(a, k) is not None})
    elif a.cmd == "eval":
        cmd["code"] = a.value
    reply = send(cmd, a.timeout)
    print(json.dumps(reply, indent=1, ensure_ascii=False))
    return 0 if reply.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
