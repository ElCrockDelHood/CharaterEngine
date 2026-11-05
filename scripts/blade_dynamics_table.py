"""Print the A34 tables: sabre body, effective mass and energy along the blade, and the cut against the placeholder.

    python scripts/blade_dynamics_table.py

Read-only: nothing is written and the placeholder blade of the shipped tables is not replaced. Every value is an
ESTIMATE; see docs/audit/A34_BLADE_DYNAMICS.md.
"""

from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.physics.body_strike import LayeredBody, sweep  # noqa: E402
from character_engine.domain.physics.collision import regional_target_mass_kg  # noqa: E402
from character_engine.domain.physics.cut import (  # noqa: E402
    Blade,
    blade_impact,
    coupled_arm_mass_kg,
    p1796_sabre_body,
    swing_from_tip_speed,
)

DATA = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
EDGE_WIDTH_M = 0.028                     # the placeholder's, kept so that only mass and speed differ
TIP_SPEEDS = (10.0, 13.0, 17.55)
GRIP_FRACTIONS = (0.0, 0.3)


def _stops(rows) -> str:
    counts = collections.Counter(r["stopped_in"] for r in rows)
    return ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))


def main() -> int:
    print("## Sabre body by assumed taper\n")
    print("| Tip / guard density | I_cg (kg·m²) | I_grip (kg·m²) | Centre of percussion (m from grip) |")
    print("|---|---|---|---|")
    for r in (0.25, 0.45, 0.7):
        b = p1796_sabre_body(r)
        print(f"| {r} | {b.inertia_cg_kg_m2:.4f} | {b.inertia_about_kg_m2(0.0):.4f} | "
              f"{b.center_of_percussion_m():.3f} |")

    sabre = p1796_sabre_body()
    cop = sabre.center_of_percussion_m()
    print(f"\nReference: M {sabre.mass_kg} kg, CG {sabre.cg_m:.4f} m, tip {sabre.tip_m:.2f} m, COP {cop:.3f} m.\n")
    points = (("0.30 m", 0.30), ("COP", cop), ("0.65 m", 0.65), ("0.75 m", 0.75), ("tip", sabre.tip_m))
    hand, arm = coupled_arm_mass_kg(), coupled_arm_mass_kg(include_forearm=True)
    print(f"## Along the blade, tip 15 m/s (coupled: hand {hand:.2f} kg, hand + forearm {arm:.2f} kg)\n")
    for frac in GRIP_FRACTIONS:
        s = swing_from_tip_speed(sabre, 15.0, frac)
        print(f"Grip speed = {frac} × tip speed\n")
        print("| Point | v (m/s) | m_eff free (kg) | E free (J) | E hand (J) | E hand + forearm (J) | E pinned (J) | "
              "Grip jolt (m/s per N·s) |")
        print("|---|---|---|---|---|---|---|---|")
        for name, x in points:
            f = blade_impact(sabre, s, x, EDGE_WIDTH_M)
            es = [blade_impact(sabre, s, x, EDGE_WIDTH_M, c).contact_energy_j for c in (hand, arm, math.inf)]
            print(f"| {name} | {f.speed_m_s:.1f} | {f.effective_mass_kg:.3f} | {f.contact_energy_j:.1f} | "
                  f"{es[0]:.1f} | {es[1]:.1f} | {es[2]:.1f} | {f.grip_velocity_change_per_impulse:+.2f} |")
        print()

    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    p = lambda d: (d["x"], d["y"], d["z"])  # noqa: E731
    pts = {b["canonical_name"]: (p(b["head"]), p(b["tail"])) for b in bones}
    body = LayeredBody(pts, target_mass_kg=regional_target_mass_kg())
    base = {r["segment"]: r for r in sweep(body, Blade(0.6, 10.0, EDGE_WIDTH_M))}
    print("## Cut against the placeholder (reduced mass on, 17 segments, frontal central strike)\n")
    print("| Tip speed | Grip fraction | Point | m_eff (kg) | v (m/s) | E (J) | Deeper / shallower / same | "
          "Severity changed | Where it stops |")
    print("|---|---|---|---|---|---|---|---|---|")
    print(f"| placeholder | - | - | 0.600 | 10.0 | 30.0 | - | - | {_stops(base.values())} |")
    for tip in TIP_SPEEDS:
        for frac in GRIP_FRACTIONS:
            s = swing_from_tip_speed(sabre, tip, frac)
            for name, x in (("COP", cop), ("tip", sabre.tip_m)):
                h = blade_impact(sabre, s, x, EDGE_WIDTH_M)
                rows = sweep(body, h.blade)
                deeper = sum(r["depth_mm"] > base[r["segment"]]["depth_mm"] for r in rows)
                less = sum(r["depth_mm"] < base[r["segment"]]["depth_mm"] for r in rows)
                sev = sum(r["severity"] != base[r["segment"]]["severity"] for r in rows)
                print(f"| {tip} | {frac} | {name} | {h.effective_mass_kg:.3f} | {h.speed_m_s:.1f} | "
                      f"{h.contact_energy_j:.1f} | {deeper} / {less} / {len(rows) - deeper - less} | {sev} | "
                      f"{_stops(rows)} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
