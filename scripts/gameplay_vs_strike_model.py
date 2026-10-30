"""Compare the shipped gameplay table (legacy 400 J mapping) with the reduced-mass, force-criterion strike model.

    python scripts/gameplay_vs_strike_model.py

Read-only; nothing is written into the table. Each (move, hitbox bone) pair is one central blunt strike on the block
segment of that bone; the striker comes from the move via ``Striker.from_move`` (table energy kept, speed by kind).
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from character_engine.domain.physics.body_strike import LayeredBody  # noqa: E402
from character_engine.domain.physics.strike_model import Striker, strike_blunt  # noqa: E402
from gameplay_vs_layered import DATA, TABLE, segment_of  # noqa: E402


def main() -> int:
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    body = LayeredBody(pts)
    n_zones = len(next(iter(table["moves"].values()))["impacts"])
    print(f"| Move | Energy (J) | m_eff (kg) | v (m/s) | Legacy severity | Model severity | Fractures (of {n_zones}) "
          "| Expected fractures | Tissue J (mean) | Knock-back J (mean) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    higher = lower = 0
    for mid, mv in table["moves"].items():
        st = Striker.from_move(mv["energy_j"], mv["contact_radius_m"], mv["kind"])
        legacy, model = collections.Counter(), collections.Counter()
        fr = exp = tissue = knock = 0.0
        for bone, imp in mv["impacts"].items():
            o = strike_blunt(body, segment_of(bone), st)
            sev = o.assessment.severity.value
            legacy[imp["severity"]] += 1
            model[sev] += 1
            fr += o.fractured
            exp += o.fracture_probability
            tissue += o.dissipated_j
            knock += o.knockback_j
            higher += sev > imp["severity"]
            lower += sev < imp["severity"]
        fmt = lambda c: ", ".join(f"{k}x{v}" for k, v in sorted(c.items()))  # noqa: E731
        print(f"| {mid} | {mv['energy_j']} | {st.effective_mass_kg:.1f} | {st.speed_m_s} | {fmt(legacy)} | {fmt(model)} "
              f"| {int(fr)} | {exp:.1f} | {tissue / n_zones:.0f} | {knock / n_zones:.0f} |")
    print(f"\nSeverity: model higher in {higher} of {n_zones * len(table['moves'])} pairs, lower in {lower}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
