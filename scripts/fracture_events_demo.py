"""Write sample fracture events (schema ce-fracture/1) for the Blender and Godot threads, and print a summary (A33).

    python scripts/fracture_events_demo.py

Output: ``builds/fracture_events/<segment>_<striker>.json``. Read-only on the gameplay table. Six cases from the moves'
strikers (``Striker.from_move``), plus one heavy blow on the head: no gameplay move reaches the skull's fracture force, so
without it the spiderweb pattern would have no sample.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from character_engine.domain.physics.body_strike import LayeredBody  # noqa: E402
from character_engine.domain.physics.fracture_event import strike_fracture  # noqa: E402
from character_engine.domain.physics.strike_model import Striker  # noqa: E402
from gameplay_vs_layered import DATA, TABLE  # noqa: E402

OUT = ROOT / "builds" / "fracture_events"
CASES = (("head", "jab"), ("head", "straight"), ("head", "front_kick"),
         ("thorax", "jab"), ("thorax", "front_kick"), ("thigh.L", "front_kick"))
HEAVY = ("head", "heavy_blow", Striker(8.0, 12.0, 0.04))      # ASSUMED: 8 kg at 12 m/s, not a gameplay move


def main() -> int:
    moves = json.loads(TABLE.read_text(encoding="utf-8"))["moves"]
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    body = LayeredBody(pts)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [(s, m, Striker.from_move(moves[m]["energy_j"], moves[m]["contact_radius_m"], moves[m]["kind"])) for s, m in CASES]
    print("| Segment | Striker | m (kg) | v (m/s) | F_peak (N) | Fractured | Pattern | Excess J | Fragments | Mass (g) "
          "| Largest (mm) | Fastest (m/s) | Fragment KE (J) | File |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for seg, name, st in rows + [HEAVY]:
        o, e = strike_fracture(body, seg, st)
        path = OUT / f"{seg}_{name}.json"
        path.write_text(json.dumps(e.to_dict(), indent=1) + "\n", encoding="utf-8")
        largest = max((f.size_m for f in e.fragments), default=0.0) * 1000
        fastest = max((sum(c * c for c in f.velocity_m_s) ** 0.5 for f in e.fragments), default=0.0)
        print(f"| {seg} | {name} | {st.effective_mass_kg:.1f} | {st.speed_m_s} | {o.peak_force_n:.0f} | "
              f"{'yes' if e.fractured else 'no'} | {e.pattern} | {e.excess_energy_j:.1f} | {len(e.fragments)} | "
              f"{e.patch_mass_kg * 1000:.0f} | {largest:.0f} | {fastest:.1f} | {e.fragment_kinetic_j:.2f} | "
              f"{path.relative_to(ROOT).as_posix()} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
