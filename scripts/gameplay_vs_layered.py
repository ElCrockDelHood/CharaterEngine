"""Compare the shipped gameplay wound table (legacy 400 J mapping) with the layered body model, move by move.

    python scripts/gameplay_vs_layered.py                 # catalog default (25 J rigid shell, sample 2 behaviour)
    python scripts/gameplay_vs_layered.py --calibrated    # per-region rigid-shell energies (ASSUMED, unsourced)

Read-only: nothing is written into the gameplay table. Each (move, hitbox bone) pair becomes one central frontal
blunt strike on the block segment of that bone (kinetic energy = the move's energy_j, contact radius = the move's).
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from character_engine.domain.physics.blunt import Impactor  # noqa: E402
from character_engine.domain.physics.body_strike import FIGHT_RIGID_SHELL_ENERGY_J, LayeredBody  # noqa: E402
from character_engine.domain.tissue.layers import region_of_bone  # noqa: E402

TABLE = ROOT / "runtime" / "godot" / "addons" / "character_engine" / "data" / "gameplay_shenmue.json"
DATA = ROOT / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
SIDED = {"upper_arm", "forearm", "hand", "thigh", "leg", "foot"}


def segment_of(bone: str) -> str:
    region = region_of_bone(bone).value
    return f"{region}.{bone[-1]}" if region in SIDED and bone.endswith(("_L", "_R")) else region


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrated", action="store_true")
    a = ap.parse_args()
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    bones = json.loads(DATA.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    body = LayeredBody(pts, rigid_shell_energy_j=FIGHT_RIGID_SHELL_ENERGY_J if a.calibrated else None)
    print(f"| Move | Energy (J) | Legacy severity | Layered severity | Layered fractures (of {len(table['hitboxes_1p80'])}) |")
    print("|---|---|---|---|---|")
    higher = lower = pairs = 0
    for mid, mv in table["moves"].items():
        legacy, layered, fr = collections.Counter(), collections.Counter(), 0
        for bone, imp in mv["impacts"].items():
            e = mv["energy_j"]
            r = body.central_strike(segment_of(bone), Impactor(2.0 * e, 1.0, mv["contact_radius_m"]))
            sev = r.assessment.severity.value
            legacy[imp["severity"]] += 1
            layered[sev] += 1
            fr += int(r.assessment.fracture)
            pairs += 1
            higher += sev > imp["severity"]
            lower += sev < imp["severity"]
        fmt = lambda c: ", ".join(f"{k}x{v}" for k, v in sorted(c.items()))  # noqa: E731
        print(f"| {mid} | {mv['energy_j']} | {fmt(legacy)} | {fmt(layered)} | {fr} |")
    print(f"\n{pairs} pairs: layered higher in {higher}, lower in {lower}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
