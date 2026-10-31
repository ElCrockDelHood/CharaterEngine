"""Generate data/strike_physics.json for the Godot port of the strike physics (Decisions 58 and 59).

    .venv\\Scripts\\python.exe runtime\\godot\\tests\\make_strike_physics_reference.py

Reads only the committed Python modules (``collision.py``, ``strike_model.py``, ``head_kinematics.py``); it changes
nothing there. The JSON carries (1) the tables the GDScript port uses, so the numbers live in one place (Python), and
(2) reference cases computed by ``strike_blunt`` + ``knockback_of`` that ``ce_test_runner.gd`` replays with
``CEStrikePhysics``. Not exported: the tissue-layer depth of ``strike_blunt`` (``blunt_through``); the Godot port only
covers the force / fracture / knock-back part.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from character_engine.domain.physics import collision  # noqa: E402
from character_engine.domain.physics import head_kinematics as hk  # noqa: E402
from character_engine.domain.physics import strike_model as sm  # noqa: E402
from character_engine.domain.physics.body_strike import LayeredBody  # noqa: E402

OUT = REPO / "runtime" / "godot" / "addons" / "character_engine" / "data" / "strike_physics.json"
ANATOMY = REPO / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
GAMEPLAY = REPO / "runtime" / "godot" / "addons" / "character_engine" / "data" / "gameplay_shenmue.json"
SEGMENT_OF_REGION = {"head": "head", "neck": "neck", "thorax": "thorax", "abdomen": "abdomen", "pelvis": "pelvis",
                     "upper_arm": "upper_arm.L", "forearm": "forearm.L", "hand": "hand.L", "thigh": "thigh.L",
                     "leg": "leg.L", "foot": "foot.L"}


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def tables() -> dict:
    return {
        "default_body_mass_kg": collision.DEFAULT_BODY_MASS_KG,
        "segment_mass_fraction": {r.value: f for r, f in collision.SEGMENT_MASS_FRACTION.items()},
        "segment_mass_provenance": collision.SEGMENT_MASS_PROVENANCE.value,
        "region_response": {r.value: {"stiffness_n_per_m": rr.stiffness_n_per_m,
                                      "fracture_force_n": list(rr.fracture_force_n),
                                      "fracture_energy_j": list(rr.fracture_energy_j) if rr.fracture_energy_j else None,
                                      "note": rr.note, "provenance": rr.provenance.value}
                            for r, rr in sm.REGION_RESPONSE.items()},
        "nominal_speed_m_s": dict(sm.NOMINAL_SPEED_M_S),
        "g": hk.G,
        "lever_straight_m": hk.LEVER_STRAIGHT_M,
        "lever_hook_m": hk.LEVER_HOOK_M,
        "head_inertia_kg_m2": hk.HEAD_INERTIA_KG_M2,
        "rowson_2012_rotational": [list(p) for p in hk.ROWSON_2012_ROTATIONAL],
        "saturation_rad_s2": hk.SATURATION_RAD_S2,
        "saturation_probability": hk.SATURATION_PROBABILITY,
        "p_step_n_s": hk.P_STEP_N_S,
        "multi_step_ratio": hk.MULTI_STEP_RATIO,
        "fall_ratio": hk.FALL_RATIO,
        "stagger_levels": list(hk.STAGGER_LEVELS),
        "head_regions": [r.value for r in hk.HEAD_REGIONS],
    }


def strikers() -> list:
    """Souls moves through ``Striker.from_move`` (kind light/heavy -> the punch fallback) plus fixed strikers."""
    souls = json.loads(GAMEPLAY.read_text(encoding="utf-8"))["souls_like_rules"]["moves"]
    out = [{"label": mid, "energy_j": mv["energy_j"], "kind": mv["kind"]} for mid, mv in sorted(souls.items())]
    out += [{"label": "walilko_olympic", "mass_kg": 2.9, "speed_m_s": 9.14},
            {"label": "kick_nominal", "energy_j": 150.0, "kind": "kick"},
            {"label": "light_tap", "mass_kg": 0.5, "speed_m_s": 3.0},
            {"label": "heavy_ram", "mass_kg": 20.0, "speed_m_s": 6.0}]
    return out


def cases() -> list:
    bones = json.loads(ANATOMY.read_text(encoding="utf-8"))["bones"]
    pts = {b["canonical_name"]: tuple(tuple(b[k][c] for c in "xyz") for k in ("head", "tail")) for b in bones}
    body = LayeredBody(pts)
    out = []
    for s in strikers():
        st = (sm.Striker.from_move(s["energy_j"], 0.04, s["kind"]) if "energy_j" in s
              else sm.Striker(s["mass_kg"], s["speed_m_s"], 0.04))
        for region, seg in SEGMENT_OF_REGION.items():
            for lever, bracing in ((hk.LEVER_STRAIGHT_M, 1.0), (hk.LEVER_HOOK_M, 1.0), (hk.LEVER_STRAIGHT_M, 1.5)):
                o = sm.strike_blunt(body, seg, st)
                kb = hk.knockback_of(o, st, lever, bracing)
                out.append({
                    "striker": s, "region": region, "lever_arm_m": lever, "bracing": bracing,
                    "striker_mass_kg": st.effective_mass_kg, "speed_m_s": st.speed_m_s,
                    "expect": {
                        "striker_energy_j": o.striker_energy_j, "reduced_mass_kg": o.reduced_mass_kg,
                        "dissipated_j": o.dissipated_j, "knockback_j": o.knockback_j,
                        "target_speed_after_m_s": o.target_speed_after_m_s, "peak_force_n": o.peak_force_n,
                        "fracture_probability": o.fracture_probability, "fractured": o.fractured,
                        "energy_criterion_met": o.energy_criterion_met,
                        "head": None if kb.head is None else {
                            "linear_g": kb.head.linear_g, "rotational_rad_s2": kb.head.rotational_rad_s2,
                            "concussion_probability": kb.head.concussion_probability},
                        "stagger": {"impulse_n_s": kb.stagger.impulse_n_s, "level": kb.stagger.level,
                                    "threshold_n_s": kb.stagger.threshold_n_s,
                                    "segment_speed_m_s": kb.stagger.segment_speed_m_s},
                        "knocked_down": kb.knocked_down}})
    return out


def main() -> None:
    doc = {"schema": 1, "generator": "runtime/godot/tests/make_strike_physics_reference.py", "repo_commit": _commit(),
           "decisions": [58, 59], "provenance": "segment mass fractions SOURCED (de Leva 1996, Table 4); region stiffness, fracture forces, "
           "lever arms, head inertia and stagger thresholds ESTIMATE / ASSUMED (see A14, A15, A16); force, fracture and knock-back "
           "only, no tissue-layer depth", "tables": tables(), "cases": cases()}
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(doc['cases'])} cases)")


if __name__ == "__main__":
    main()
