"""Generate data/fracture_events.json: the bone fragments (schema ce-fracture/1) of every blunt Souls blow that fractures.

    .venv\\Scripts\\python.exe runtime\\godot\\tests\\make_fracture_events.py [--physics-root <checkout>]

Same idea as the pre-computed wounds of the gameplay table: Python decides, Godot draws. The fragments come from
``fracture_event.strike_fracture`` (Decision 80, A33), with its seed per blow, so Godot needs no port of Python's random
generator. ``--physics-root`` names the checkout that holds ``fracture_event.py`` while it is not on this branch; by
default it is this repository. Also holds ``test_heavy_blow``: A33's heavy test blow (8 kg at 12 m/s, not a gameplay
move), the only sample of the skull's spiderweb pattern, used by the demo scene and never by the fight.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "runtime" / "godot" / "addons" / "character_engine" / "data" / "fracture_events.json"
ANATOMY = REPO / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
GAMEPLAY = REPO / "runtime" / "godot" / "addons" / "character_engine" / "data" / "gameplay_shenmue.json"
SEGMENT_OF_REGION = {"head": "head", "neck": "neck", "thorax": "thorax", "abdomen": "abdomen", "pelvis": "pelvis",
                     "upper_arm": "upper_arm.L", "forearm": "forearm.L", "hand": "hand.L", "thigh": "thigh.L",
                     "leg": "leg.L", "foot": "foot.L"}
TEST_BLOW = {"mass_kg": 8.0, "speed_m_s": 12.0, "contact_radius_m": 0.04}      # A33, ASSUMED


def _commit(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], text=True).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--physics-root", type=Path, default=REPO)
    args = ap.parse_args()
    sys.path.insert(0, str(args.physics_root / "src"))
    from character_engine.domain.gameplay.souls import UNARMED_CONTACT_RADIUS_M
    from character_engine.domain.materials.catalog import MaterialKind
    from character_engine.domain.physics.body_strike import LayeredBody
    from character_engine.domain.physics.fracture_event import SCHEMA, strike_fracture
    from character_engine.domain.physics.strike_model import Striker

    bones = json.loads(ANATOMY.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    body = LayeredBody(pts)
    table = json.loads(GAMEPLAY.read_text(encoding="utf-8"))
    events = {}
    # strike_fracture needs a bone shell; a segment without one (the force model can still say "fractured") has no shards.
    no_bone = sorted(r for r, seg in SEGMENT_OF_REGION.items()
                     if not any(sh.material is MaterialKind.BONE for sh in body.capsules[seg].shells))
    for move_id, mv in sorted(table["souls_like_rules"]["moves"].items()):
        weapon = table["weapons"][mv["weapon_id"]]
        if weapon["category"] == "blade":                 # the fracture model is blunt only
            continue
        radius = UNARMED_CONTACT_RADIUS_M if weapon["category"] == "unarmed" else weapon["contact_radius_m"]
        striker = Striker.from_move(mv["energy_j"], radius, mv["kind"])
        for region, segment in SEGMENT_OF_REGION.items():
            if region in no_bone:
                continue
            _, event = strike_fracture(body, segment, striker)
            if event.fractured:
                events[f"{move_id}|{region}"] = event.to_dict()
    _, heavy = strike_fracture(body, "head", Striker(**{"effective_mass_kg": TEST_BLOW["mass_kg"],
                                                        "speed_m_s": TEST_BLOW["speed_m_s"],
                                                        "contact_radius_m": TEST_BLOW["contact_radius_m"]}))
    events["test_heavy_blow|head"] = heavy.to_dict()
    doc = {"schema": SCHEMA, "generator": "runtime/godot/tests/make_fracture_events.py", "repo_commit": _commit(REPO),
           "fracture_commit": _commit(args.physics_root), "decisions": [80],
           "provenance": "ASSUMED (A33): a plausible drawing, not a prediction of how a real bone breaks",
           "regions_without_bone_shell": no_bone, "test_heavy_blow": TEST_BLOW, "events": events}
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}: {len(events)} events, largest {max(len(e['fragments']) for e in events.values())} fragments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
