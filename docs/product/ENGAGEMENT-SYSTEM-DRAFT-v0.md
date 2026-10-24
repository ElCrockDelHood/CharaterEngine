# Engagement system (draft v0)

**Status:** DRAFT — not a decision. Nothing here is a requirement until the owner answers §3.
**Owner:** Mariano Martin Galli · **Date:** 2026-10-24 · **Matrix row:** ENGAGEMENT-001
**Context:** Decision 42 (production in Blender, gameplay runtime in Godot) and its clarification: the fight
engagement system lives in Godot; Blender provides models, simulation results and cinematography as baked
canonical files.

## 1. Owner definition (verbatim, 2026-10-24)

> "engagement es el sistema de enfrentamiento determinado, no una simulacion de coliciones tras los golpes
> solamente, sistemas de combate elaborados ademas de los golpes y coliciones, etc, interacciones entre las
> capsulas de coliciones."

Reading kept literal (no added scope): a **determined (deterministic) confrontation system**; **more than**
post-hit collision simulation; **elaborate combat systems** beyond strikes and collisions; **interactions
between collision capsules**.

## 2. What exists today (facts from the code, 2026-10-24)

| Area | Implemented | Where | Evidence |
|------|-------------|-------|----------|
| Deterministic fixed-step combat (60 Hz) | **Yes** — frame-based state machine, no randomness inside the simulation | `src/character_engine/domain/gameplay/combat.py` (`ShenmueCombat`), line-by-line GDScript port `runtime/godot/addons/character_engine/gameplay/ce_shenmue_combat.gd` | 7 scripted reference fights replay identically in Python and Godot (Godot suite 21/21) |
| Fighter states | **Yes**: idle, move, startup, active, recovery, guard, hitstun, knockdown, grabbed, KO | `CombatState` | pytest + Godot |
| Moves / frame data | **Yes**: 8 Shenmue-style moves (startup/active/recovery, energy, reach, hitstun, knockdown, cancel windows), command inputs (`F,F+P`, …) with a 12-frame input buffer | `SHENMUE_MOVES`, generated table `gameplay_shenmue.json` | pytest (`test_gameplay_runtime_table.py` fails on stale JSON) |
| Lock-on | **Partial**: every action targets the *nearest* living opponent; no explicit lock/unlock or target switch | `nearest_opponent()` | — |
| Guard vs throw | **Yes**: guard blocks strikes (reduced stun), throws beat guard | `_resolve_hit()` | reference fights `guard_blocks_jab`, `throw_beats_guard` |
| Hit detection | **Simple only**: hit if the 2-D distance between the two fighters' *root positions* ≤ `reach_m` (scaled by stature) on the first active frame. The struck bone is the move's fixed `target_region_bone` | `_resolve_hit()` | `whiff_out_of_reach` |
| Hitboxes | **Data only**: per-bone sphere radii (21 bones, gameplay constants) — **not used geometrically** (only checked for membership) | `default_hitboxes()` | — |
| Wounds | **Yes**: each landed strike → blunt-impact `WoundAssessment` on the struck bone (ESTIMATE provenance) → health cost; Godot attaches a coloured wound marker to the bone | `domain/trauma`, `CECharacter.add_wound_marker()` | Godot "wound marker attached" |
| Collision capsules | **No** in the combat domain or Godot runtime. Only the optional UPBGE scene uses one Bullet `CHARACTER` capsule per fighter (radius 0.25 m, 1.8 m) for physics | `infrastructure/blender/addon/runtime_upbge.py` | — |
| Body blocking / pushback / spacing | **No**. Godot locomotion only stops walking forward at 0.45 m from the target; fighters can still overlap | `ce_fighter_controller.gd` `_apply_locomotion()` | — |
| Opponent AI | **Simple, random-based** (seeded RNG in the controller, outside the simulation) | `ce_fighter_controller.gd` `_ai_input()` | — |
| Styles | `shenmue` implemented; `souls_like`, `beat_em_up` listed as *planned* (no moves) | `GAMEPLAY_STYLES` | Godot "planned gameplay styles listed" |

**Summary:** today's system is a deterministic *frame-data* combat with distance-based hit checks. There is
**no capsule geometry, no capsule–capsule interaction, no body blocking, and no engagement layer** above
single moves.

## 3. Open questions for the owner (answer by letter; several allowed)

**Q1 — Confrontation phases.** Which phases must the engagement system model?
(a) approach / spacing (b) explicit lock-on with target switching (c) clinch / grapple holds (d) break /
disengage (e) multiple opponents with turn-taking (f) other: ___

**Q2 — Capsule granularity.**
(a) one capsule per fighter (whole body) (b) capsules per body region (head, torso, arms, legs)
(c) capsules per canonical bone or bone group, driven by the 208-bone skeleton (d) other: ___

**Q3 — Capsule–capsule interactions (pick all that apply).**
(a) body blocking (no interpenetration) (b) pushback on hit / on block (c) hit = attacking capsule
(fist/foot/elbow) intersecting a defender capsule, with the real struck region (d) guard as a blocking
capsule (e) throws/clinches require capsule contact (f) ring-out / walls / terrain (g) other: ___

**Q4 — Determinism scope.**
(a) the whole fight must replay bit-identically from inputs (Python ↔ Godot, like today's 7 reference fights)
(b) only the combat logic is deterministic; engine physics may differ (c) other: ___

**Q5 — Which styles?** (a) shenmue only for now (b) shenmue + souls_like (c) all three (d) other: ___

**Q6 — What comes from Blender vs is defined in Godot?**
(a) capsule sizes/placement authored in Blender and exported (b) capsules derived automatically from the
canonical skeleton / body mesh (c) defined by hand in Godot (d) animations / move timings from Blender
(e) other: ___

**Q7 — Where does the authoritative logic live?** (a) pure Python domain + GDScript port (today's model,
replays proven equal) (b) Godot only (c) other: ___

**Q8 — "Sistemas de combate elaborados"**: which ones first? (a) stamina (b) counters / reversals
(c) parries (d) combos / juggles (e) weapons (sabre, links to the equipment sockets of CINE-GR-001)
(f) posture / balance (g) other: ___

Not specified yet (pending decision): units and tolerances, capsule data format, acceptance criteria,
performance targets for the baseline PC.

## 4. Owner answer 1 (verbatim, 2026-10-24 19:50 UTC)

> "me gustaria integrar los 8 puntos. por ejemplo en el punto N2 el cuerpo va a reaccionar fisicamente y nos
> va a dar un resultado complejo que luego lo vamos a intentar pulir para que nos de la manifestacion."

Recorded reading (to be confirmed by the owner, see §5):
* **All eight areas Q1–Q8 are in scope** of the engagement system (not a choice of one).
* **Q2 (capsules):** the body **reacts physically** through its capsules; the raw result is expected to be
  complex and is then **refined ("pulir") into the final manifestation** (the visible reaction). This points
  to per-body-part capsules (Q2 b/c) driving a physical reaction, plus a refinement stage.
* Which option(s) inside each question, and the order of delivery, are **not yet stated**.

## 5. Tension to resolve before specifying (no decision taken)

**T-1 Determinism vs physical reaction.** The owner asks for a *determined* confrontation (Q4) and for a
*physical* body reaction (Q2). Godot's built-in physics is not guaranteed to replay bit-identically across
runs/machines, while today's combat replays identically in Python and Godot. Options for the owner:
(a) own fixed-step, deterministic capsule physics in the combat domain (Python, ported to GDScript like
today), so the whole fight still replays from inputs; (b) deterministic combat logic + engine physics only
for the visual reaction (the "manifestation" may differ between runs, outcomes do not); (c) other.

**T-2 Order of delivery.** Integrating Q1–Q8 at once is large for the baseline PC and the
spec-before-code rule; a proposed order (owner to accept or change): capsules + body blocking + capsule hit
detection (Q2/Q3) → physical reaction + refinement (Q2) → phases and lock-on (Q1) → combat systems (Q8) →
other styles (Q5). Q4, Q6, Q7 are cross-cutting and must be fixed first.
