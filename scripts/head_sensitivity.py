"""Sensitivity of head rotational acceleration and concussion probability to the lever arm and the striker (A17).

    python scripts/head_sensitivity.py              # markdown tables, one per head-hitting move
    python scripts/head_sensitivity.py --summary    # one line per move: probability range over the grid

Read-only. No published lever arm exists for hooks, so this is a sensitivity analysis, not a prediction: for every
move that can hit the head, concussion probability and rotational acceleration for lever arms 0.03 / 0.04 / 0.06 /
0.08 / 0.10 m and for the move's striker at low / nominal / high (``move_strikers.py``: low mass with low speed,
nominal with nominal, high with high). The risk table (Rowson 2012) comes from helmeted American-football impacts,
not from bare-headed or gloved blows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from character_engine.domain.physics.body_strike import LayeredBody  # noqa: E402
from character_engine.domain.physics.head_kinematics import knockback_of  # noqa: E402
from character_engine.domain.physics.move_strikers import MOVE_STRIKERS  # noqa: E402
from character_engine.domain.physics.strike_model import Striker, strike_blunt  # noqa: E402
from gameplay_vs_layered import DATA, TABLE  # noqa: E402

LEVERS = (0.03, 0.04, 0.06, 0.08, 0.10)
HEAD_BONES = ("CRANIUM", "MANDIBLE", "TEMPORAL_L", "TEMPORAL_R")
LEVELS = ("low", "nominal", "high")


def grid(body, rec):
    out = {}
    for i, level in enumerate(LEVELS):
        st = Striker(rec.mass_kg[i], rec.speed_m_s[i], rec.contact_radius_m)
        o = strike_blunt(body, "head", st)
        out[level] = (st, o, [knockback_of(o, st, d).head for d in LEVERS])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    body = LayeredBody(pts)
    moves = [m for m, mv in table["moves"].items() if any(b in mv["impacts"] for b in HEAD_BONES)]
    if a.summary:
        print("| Move | Default lever (m) | P at nominal, default lever | P range over the grid | alpha range (rad/s^2) |")
        print("|---|---|---|---|---|")
    for mid in moves:
        rec = MOVE_STRIKERS[mid]
        g = grid(body, rec)
        heads = [h for level in LEVELS for h in g[level][2]]
        if a.summary:
            nominal = g["nominal"][2][LEVERS.index(rec.lever_arm_m[1])].concussion_probability
            ps = [h.concussion_probability for h in heads]
            al = [h.rotational_rad_s2 for h in heads]
            print(f"| {mid} | {rec.lever_arm_m[1]} | {nominal:.2f} | {min(ps):.2f}-{max(ps):.2f} | "
                  f"{min(al):.0f}-{max(al):.0f} |")
            continue
        print(f"\n### {mid}\n")
        print("| Striker | m (kg) | v (m/s) | F_peak (N) | " + " | ".join(f"d = {d} m" for d in LEVERS) + " |")
        print("|---|---|---|---|" + "---|" * len(LEVERS))
        for level in LEVELS:
            st, o, hs = g[level]
            cells = " | ".join(f"{h.concussion_probability:.2f} ({h.rotational_rad_s2 / 1000:.1f} k)" for h in hs)
            print(f"| {level} | {st.effective_mass_kg} | {st.speed_m_s} | {o.peak_force_n:.0f} | {cells} |")
    if not a.summary:
        print("\nCell: concussion probability (rotational acceleration, thousands of rad/s^2).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
