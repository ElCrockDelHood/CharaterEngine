"""Head kinematics, concussion probability and stagger of every gameplay move that can hit the head (A16).

    python scripts/gameplay_head_kinematics.py

Read-only; nothing is written into the table. For each move with a head hitbox (CRANIUM / MANDIBLE / TEMPORAL_L/R):
the striker of ``Striker.from_move``, one central blunt strike on the head segment through ``strike_model``, then
``head_kinematics.knockback_of``. All head hitboxes map to the one head segment of the block body, so one row per
move. Lever arm: hook-type moves (hook, crescent kick, elbow) 0.08 m, the rest 0.04 m (both ASSUMED).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from character_engine.domain.physics.body_strike import LayeredBody  # noqa: E402
from character_engine.domain.physics.head_kinematics import (  # noqa: E402
    LEVER_HOOK_M,
    LEVER_STRAIGHT_M,
    knockback_of,
)
from character_engine.domain.physics.strike_model import Striker, strike_blunt  # noqa: E402
from gameplay_vs_layered import DATA, TABLE  # noqa: E402

HEAD_BONES = ("CRANIUM", "MANDIBLE", "TEMPORAL_L", "TEMPORAL_R")
HOOK_TYPE = {"hook", "crescent_kick", "elbow_assault"}


def main() -> int:
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    body = LayeredBody(pts)
    print("| Move | Head hitboxes | m (kg) | v (m/s) | Lever (m) | F_peak (N) | a (g) | alpha (rad/s^2) | P(concussion) "
          "| m*v (N s) | Impulse mu*v (N s) | Stagger |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for mid, mv in table["moves"].items():
        hits = [b for b in HEAD_BONES if b in mv["impacts"]]
        if not hits:
            continue
        st = Striker.from_move(mv["energy_j"], mv["contact_radius_m"], mv["kind"])
        lever = LEVER_HOOK_M if mid in HOOK_TYPE else LEVER_STRAIGHT_M
        o = strike_blunt(body, "head", st)
        k = knockback_of(o, st, lever)
        print(f"| {mid} | {len(hits)} | {st.effective_mass_kg:.1f} | {st.speed_m_s} | {lever} | {o.peak_force_n:.0f} | "
              f"{k.head.linear_g:.0f} | {k.head.rotational_rad_s2:.0f} | {k.head.concussion_probability:.2f} | "
              f"{k.stagger.striker_momentum_n_s:.1f} | {k.stagger.impulse_n_s:.1f} | {k.stagger.level} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
