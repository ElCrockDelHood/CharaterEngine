"""Contact sheets of the judo key poses: one PNG per throw, one column per key, side view over front view.

    python scripts/judo_contact_sheet.py                 # -> builds/judo/<throw>.png and builds/judo/judo_clips.json
    python scripts/judo_contact_sheet.py --out DIR

Tori is blue, uke is red; each fighter's right arm and leg are drawn darker. Pure Python (no image library): the
figures are the game-rig bones as lines. Prints, per key, how far each gripping hand or reaping foot is from its
target and uke's balance, so a pose that does not touch is visible in numbers too.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.animation.judo_clips import JUDO_CLIPS, clip_reference, solve_clip  # noqa: E402
from character_engine.domain.physics.judo import THROWS, kuzushi  # noqa: E402
from character_engine.export.gltf_game import game_skeleton_points  # noqa: E402

SCALE, CELL_W, CELL_H, MARGIN = 150, 420, 330, 24            # pixels per metre, cell size
DRAW = ("pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head", "clavicle_l", "clavicle_r", "upperarm_l", "lowerarm_l",
        "hand_l", "upperarm_r", "lowerarm_r", "hand_r", "thigh_l", "calf_l", "foot_l", "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r")
COLORS = {("tori", False): (60, 120, 230), ("tori", True): (20, 50, 140), ("uke", False): (235, 90, 70), ("uke", True): (150, 30, 20)}


class Canvas:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.px = bytearray(b"\xff" * (w * h * 3))

    def dot(self, x: int, y: int, c, r: int = 1):
        for yy in range(y - r, y + r + 1):
            for xx in range(x - r, x + r + 1):
                if 0 <= xx < self.w and 0 <= yy < self.h:
                    i = (yy * self.w + xx) * 3
                    self.px[i:i + 3] = bytes(c)

    def line(self, a, b, c, r: int = 1):
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1
        for i in range(n + 1):
            t = i / n
            self.dot(round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t), c, r)

    def save(self, path: Path):
        raw = b"".join(b"\x00" + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3]) for y in range(self.h))

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
                         + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def sheet(points, throw_id: str, out: Path) -> None:
    solved = solve_clip(points, JUDO_CLIPS[throw_id])
    cv = Canvas(MARGIN + CELL_W * len(solved), MARGIN + CELL_H * 2)
    for col, s in enumerate(solved):
        cx = MARGIN + col * CELL_W + CELL_W // 2
        centre = [(s.tori["pelvis"][0][i] + s.uke["pelvis"][0][i]) / 2 for i in range(2)]
        for row, axis in enumerate((1, 0)):                       # side view: Y across; front view: X across
            ground = MARGIN + row * CELL_H + CELL_H - 30
            cv.line((cx - CELL_W // 2 + 6, ground), (cx + CELL_W // 2 - 6, ground), (170, 170, 170))
            for who, pts in (("uke", s.uke), ("tori", s.tori)):
                for b in DRAW:
                    h, t = pts[b]
                    sign = -1 if axis == 1 else 1                 # side view looks along +X, so -Y is to the right
                    a = (cx + sign * (h[axis] - centre[axis]) * SCALE, ground - h[2] * SCALE)
                    e = (cx + sign * (t[axis] - centre[axis]) * SCALE, ground - t[2] * SCALE)
                    cv.line(a, e, COLORS[(who, b.endswith("_r"))], 2 if b != "head" else 4)
        cv.line((MARGIN + col * CELL_W, 0), (MARGIN + col * CELL_W, cv.h - 1), (225, 225, 225), 0)
    cv.save(out / f"{throw_id}.png")
    throw = THROWS[throw_id]
    for s in solved:
        k = kuzushi(s.uke, throw.kuzushi, removed=(throw.removed_foot,) if s.phase in ("kake",) else ())
        miss = ", ".join(f"{n} {d * 100:.0f} cm" for n, d in sorted(s.miss_m.items())) or "-"
        margin = "no foot down" if not k.supported else f"{k.margin_m * 100:+.0f} cm"
        low = min(min(h[2], t[2]) for pts in (s.tori, s.uke) for h, t in pts.values())
        print(f"{throw_id:14s} f{s.frame:<3d} {s.phase:9s} uke balance {margin:>12s} ({throw.kuzushi}); lowest point {low * 100:+.0f} cm; reach: {miss}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "builds" / "judo")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    points = game_skeleton_points(pose="anatomical")
    for throw_id in JUDO_CLIPS:
        if not a.only or a.only == throw_id:
            sheet(points, throw_id, a.out)
    (a.out / "judo_clips.json").write_text(json.dumps(clip_reference(points), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"written: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
