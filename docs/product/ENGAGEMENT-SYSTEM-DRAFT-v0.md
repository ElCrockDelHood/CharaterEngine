# Engagement system (draft v1)

**Status:** DRAFT v1 — not a decision. Scope declared by the owner (§4); layering §6 and phasing §7 are PROPOSALS awaiting approval (§8).
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

Recorded reading — **Claude's interpretation, awaiting the owner's confirmation**:
* **All eight areas Q1–Q8 are in scope**, with **every listed option** of each question selected (Q1 a–e,
  Q2 a–c, Q3 a–f, Q4 a–b, Q5 a–c, Q6 a–d, Q7 a–b, Q8 a–f; the "other" options stay empty). Where options
  conflict (Q4 a vs b, Q7 a vs b) see §5–§6.
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

## 6. Layering — PROPOSED (needs owner approval)

| Layer | Content | Determinism guarantee (proposed) | Unspecified |
|-------|---------|-----------------------------------|-------------|
| **L1 Combat logic** | States, moves, frame data, phases, lock-on, guard/throw rules, capsule *hit* tests, wounds — as today, extended | **Bit-identical replay from inputs, Python ↔ Godot** (today's reference-fight contract, Q4 a) | capsule geometry format |
| **L2 Physical reaction** | Capsule/body physics reacting to L1 events (impacts, pushes, falls): raw, complex result | Either (a) own fixed-step XPBD → deterministic, or (b) engine physics (Blender per Decision 42, or Godot) → **may vary** (Q4 b); in both cases the raw result is **recorded** | physics engine choice; recording format |
| **L3 Curation / polish** | The recorded raw reaction is refined ("pulir") into the final **manifestación** and baked into a canonical file consumed by Godot | The baked manifest is a file → **identical every playback** | bake format; what a "manifestación" contains exactly (pose tracks? per-capsule trajectories? per-region reactions?); who/what polishes (tool, manual, rules) |

With this split, outcomes (who hits, damage, wounds) stay deterministic in L1 while the visible reaction may
come from non-deterministic physics in L2 and is fixed once baked in L3.

## 7. Phasing — PROPOSAL (not a requirement), ordered by dependency

| Step | Sub-feature | Depends on | Acceptance criteria |
|------|-------------|------------|---------------------|
| E0 | Owner decisions: T-1 / layering §6, Q6 data origin, Q7 authority | — | PENDING |
| E1 | Capsule model in the combat domain (per region/bone, derived from the 208-bone skeleton) + Godot port | E0 | PENDING |
| E2 | Body blocking + pushback between capsules (L1) | E1 | PENDING |
| E3 | Capsule-based hit detection: real struck region instead of the fixed bone; guard capsule | E1 | PENDING |
| E4 | Physical reaction L2 (prototype, raw result recorded) | E0, E3 | PENDING |
| E5 | Curation/polish L3 + bake to a canonical manifest file + Godot playback | E4 | PENDING |
| E6 | Confrontation phases + explicit lock-on / target switch, multiple opponents (Q1) | E2 | PENDING |
| E7 | Combat systems (Q8): stamina, counters, parry, combos/juggles, weapons (sabre sockets), posture/balance — one per step | E3, E6 | PENDING |
| E8 | Styles souls_like / beat_em_up (Q5) | E6, E7 | PENDING |

## 8. Remaining open questions (owner)

1. Confirm the interpretation of §4 (all options of Q1–Q8) — or remove any option.
2. T-1 / §6: is the physical reaction allowed to vary between runs before polishing (L2 b), or must it be
   deterministic too (L2 a)?
3. Where does the L2 physics run: Blender (XPBD, offline, Decision 42), Godot at runtime, or both?
4. What exactly is the "manifestación" (the polished result Godot plays): animation/pose tracks, capsule
   trajectories, region reactions, or something else?
5. Accept the phasing order E0→E8, or name the step to start with.

Question 1 is still open; question 2 is moot under the reading below (offline L2 need not be deterministic);
**question 3 is ANSWERED** (§9); question 4 is partly answered (§9); question 5 is still open.

## 9. Owner answer 2 — where L2 runs (verbatim, 2026-10-24 21:16 UTC)

> "la simulacion Fuera de linea para trabajar el emegente de manifestacion de colicion rotura sistema de
> particulas, extraigo esa manifescaion tipo mesh a blender  para darle retoque o unirla para crear
> cinematografias, porque el video juego responde a estados de acuerdo a las coliciones, asi que cuando cambia de
> estados o es colisionado en el punto resulta reaccion, se entiende?."

**Q3 (§8): ANSWERED — L2 physics runs OFFLINE in Blender.**

Claude's interpretation — **CONFIRMED by the owner** 2026-10-24 21:19 UTC ("Ok simulamos en Blender y Runtime
Gameplay Godot.", DECISION_LOG §45):
1. L2 runs **offline in Blender** (collision, fracture/breaking, particle systems) and produces emergent results.
2. Those results are extracted as **mesh-type manifestations**, retouched or joined in Blender, and are usable
   for cinematics.
3. In the game, Godot does **not** simulate them: it runs the deterministic state machine (L1). When a state
   changes or a collision happens at a point, the resulting reaction is a **baked manifestation chosen and played
   from a library**.
4. Runtime determinism therefore holds even though the offline simulation need not be deterministic, provided
   each baked manifestation records its generation parameters/seed and a SHA-256 ID (ties to WORK-SIGNING).

OPEN / UNSPECIFIED:
* how reactions are keyed (state, collision point/region, energy, material) and blending between variants;
* baked format — verified on the baseline PC: Godot 4.7.2 scene importers are glTF, `.blend`, FBX (ufbx and
  FBX2glTF); **no Alembic importer class** exists (mesh-sequence caches would need conversion, e.g. glTF
  morph targets or bone animation — UNVERIFIED which works best);
* asset size and performance on the GT 740M with the Compatibility renderer (not measured);
* the offline physics tool (Blender Bullet / cloth / soft body / particles / geometry nodes, own XPBD, FEM).

### 9.1 Owner clarification (verbatim, 2026-10-24 21:27 UTC) — refines §9, does not replace it

> "En realidad Creo que son Bibliotecas de sistemas de medidas y de experimentos que nos da esa exprecion
> representativa, quiebres, movimientos de acuerdo a la gravedad, el viento, etc."

Claude's interpretation — **to be confirmed by the owner**: the library behind the baked reactions is not only a
catalogue of reaction clips but libraries of (a) **measurement systems** (units, standards, measured material
properties) and (b) **experiments** (reproducible scenarios with controlled conditions — gravity, wind, impact,
drop, breaking) whose results provide the "representative expression" (breaks, movements) that gets baked. Each
experiment definition + parameters + results carries a SHA-256 ID and provenance (WORK-SIGNING); measured values
come from cited sources (PROVEN/DERIVED) or are marked ESTIMATE when they come from our own simulation.

Open questions (owner):
6. Does the experiment library **replace** or **enrich** the reaction library of Decision 45?
7. Which measurement systems (units/standards, material property sets) and which experiments come first?
8. How does an experiment map to a runtime reaction (keying by conditions: state, region, energy, material,
   gravity, wind…)?
9. What is the first concrete experiment (e.g. a drop, an impact on a rib, a breaking test)?
