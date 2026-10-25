# STYLE-SOULS-001 — `souls_like` gameplay style (SPECIFICATION, awaiting owner approval)

**Date:** 2026-10-25 · **Status:** APPROVED (Decision 53: Sentinel with the bo, keyboard only in v1); step 1
implemented · **Context:** the owner chose the Souls-like as the first
genre to develop (option A). This spec turns the planned `souls_like` entry of `GAMEPLAY_STYLES` into a playable
style: stamina, dodge with invulnerability frames, light / heavy attacks with the staff and the short blade, and one
enemy with a simple, readable pattern.

## 1. Objective

A deterministic, frame-based (60 Hz) Souls-like duel that runs identically in Python (truth), Godot (GDScript port)
and tests, reusing what already exists: `Fighter` / frame windows, lock-on, the weapon table (Decision 50), the trauma
domain (wounds per canonical bone), the CE-GAME-v1 game rig with hand grips (Decision 51).

**Production boundary (owner rule):** animation and cinematography are authored and polished in Blender; Godot only
plays finished, baked clips on the game rig selected by the state machine (Decision 45). This spec defines rules and
data, not animation art.

## 2. Scope

| In scope | Out of scope (later, separate approval) |
|----------|------------------------------------------|
| Stamina, dodge roll with i-frames, guard with stamina drain and guard break | Parry / riposte, backstab |
| Light and heavy attacks, short light chains, per-weapon move sets (unarmed, staff, short blade) | Weapon switching mid-fight, two-weapon sets |
| Poise (stagger when broken) | Status effects, bleed build-up, healing items |
| One enemy, "Sentinel" (staff), with a fixed telegraphed pattern | Multiple enemy types, group AI, boss phases |
| Lock-on (nearest target) and strafing | Camera system beyond the existing arena camera |
| Reference scenarios + Godot parity | Final animations, sound design (audio branch), UI art |

The Shenmue style stays untouched: its 9 reference fights must stay bit-identical.

## 3. Rules

### 3.1 Stamina

- Pool `stamina_max`; every action has a cost; an action whose cost exceeds the current stamina cannot start
  (the input is dropped).
- Regeneration per frame after `regen_delay` frames without spending; no regeneration while guarding is held
  (regen ×`guard_regen_factor`).
- Blocking a hit drains `block_cost(energy)`; reaching 0 while guarding = **guard break** → stagger.

### 3.2 Dodge roll

- Input: dodge + direction (no direction = back-step). Fixed displacement over the roll, `dodge_frames` total.
- **I-frames** window `[iframe_start, iframe_end]`: hits resolved inside it miss (event `dodged`). Outside it the
  roller can be hit (recovery frames are punishable).
- Cost `dodge_cost`. Cannot dodge during startup / active frames of an attack (no animation cancelling), allowed
  during attack recovery after `dodge_cancel_from` frames.

### 3.3 Attacks

- **Light** (chainable): up to 3 in a chain, each entered during the previous one's recovery (`chain_window`).
- **Heavy**: slower startup, more energy and poise damage, no chain.
- Each weapon defines its own frame data, reach and energy; the hit goes through the existing weapon path (staff →
  BLUNT, short blade → INCISION) and the trauma domain, so wounds, severity and health cost work as in Shenmue.
- Target bone per move (as in Shenmue) so wound markers land on a canonical bone carried by the game rig.

### 3.4 Poise and stagger

- Each fighter has `poise_max`; hits subtract `poise_damage`; at 0 → **stagger** (`stagger_frames`, cannot act), poise
  resets. Poise regenerates after `poise_regen_delay`.
- Heavy attacks have **hyper-armour** frames (taking a hit during them does not interrupt; damage still applies).

### 3.5 Lock-on and movement

- Lock-on to the nearest living opponent (existing rule); with lock-on, left/right strafe around the target, forward /
  back changes distance. Walking speed `walk_speed`, no running in v1.

### 3.6 Enemy "Sentinel" (staff)

Deterministic pattern (no randomness, so Python and Godot replay it identically):

1. **Approach** until distance ≤ `engage_range`.
2. **Telegraph** `telegraph_frames` (readable wind-up; a baked "wind-up" clip in Godot).
3. **String**: light → light → heavy (staff move set).
4. **Recover** `punish_window` frames (the opening the player must learn to use).
5. **Step back** to `retreat_range`, then loop from 1.
- Reactions: if staggered → after stagger, back to 1. If the player is dodging inside its reach during the
  telegraph, it waits until the dodge ends (no tracking mid-string in v1).
- Sentinel stamina and poise follow the same rules as the player.

## 4. Proposed starting values (all **PLACEHOLDER** gameplay tuning, to be adjusted by playing)

| Parameter | Value | Parameter | Value |
|-----------|-------|-----------|-------|
| stamina_max | 100 | regen per frame / regen_delay | 0.75 / 30 frames |
| light cost / heavy cost / dodge cost | 15 / 30 / 20 | guard_regen_factor | 0.3 |
| dodge_frames / i-frames | 26 / frames 4–15 | dodge distance | 2.0 m |
| dodge_cancel_from (attack recovery) | 8 | chain_window | first 10 recovery frames |
| poise_max / regen delay | 50 / 60 frames | stagger_frames | 40 |
| walk_speed | 1.6 m/s | engage / retreat range | 1.3 m / 2.6 m (engage corrected in step 1: 1.6 m exceeded the staff reach of 1.45 m) |
| telegraph / punish window | 20 / 40 frames | | |

Per-weapon frame data (startup / active / recovery frames, energy multiplier over the weapon's own):

| Weapon | Light | Heavy | Light poise dmg | Heavy poise dmg |
|--------|-------|-------|-----------------|-----------------|
| unarmed | 8 / 3 / 12 | 16 / 4 / 20 (×1.8) | 10 | 25 |
| staff | 12 / 4 / 18 | 24 / 5 / 26 (×1.8) | 15 | 35 |
| short_blade | 9 / 3 / 14 | 18 / 4 / 22 (×1.8) | 12 | 28 |

Heavy hyper-armour: from startup frame 8 to the end of active frames. Block cost (stamina) = energy (J) / 10.

## 5. Data contract and runtime

- **Domain** (pure Python): `domain/gameplay/souls.py` — `SoulsCombat` (stamina, dodge, chains, poise, guard break),
  `SOULS_MOVES` per weapon, `Sentinel` pattern; reuses `Fighter`, weapons, trauma, `_health_cost`.
- **JSON**: `gameplay_shenmue.json` keeps its name; schema `ce-gameplay/3` adds the `souls_like` move set,
  the stamina / poise table, the Sentinel pattern and reference scenarios (pre-computed impacts as today).
- **Godot**: `ce_souls_combat.gd` port + `CEArena` style switch (`shenmue` | `souls_like`) + Sentinel controller;
  input: WASD move, J light, K heavy, Space dodge, L (hold) guard, Tab lock-on (keyboard; gamepad later).
- **Blender**: placeholder clips on the game rig for idle, walk, light ×3, heavy, dodge, guard, hit, stagger,
  wind-up — keyed poses using the hand grip library, baked to glTF; Godot picks clips by state. (Separate step.)
- **UPBGE**: not gating (Decision 40); the domain runs there unchanged.

## 6. Reference scenarios (parity gate)

1. `light_chain_lands` — three lights land on a passive target; stamina drops 45 then regenerates.
2. `dodge_through_heavy` — dodge timed so the heavy's active frames hit inside the i-frames → `dodged`, no wound.
3. `dodge_too_late` — same with a late input → hit lands during dodge recovery.
4. `stamina_exhausted` — chain until stamina < cost → the next input is dropped.
5. `guard_break` — guarding a string until stamina 0 → guard break → stagger → punished.
6. `poise_break` — heavies break poise → stagger frames.
7. `hyper_armour_trade` — light hits a heavy in its armour frames → heavy still lands.
8. `sentinel_cycle_600` — Sentinel vs passive player for 600 frames: pattern timing and wounds.
9. `sentinel_punished` — player waits out the string and hits in the punish window.

Godot replays every scenario and must reproduce frames, stamina, poise, health and states exactly.

## 7. Steps (each one: spec → code → tests → owner OK)

1. **DONE** — `domain/gameplay/souls.py` (`SoulsCombat`, `SoulsFighter`, `SOULS_MOVES`, `Sentinel`,
   `run_souls_scenario`, `souls_reference_specs`) + `tests/unit/test_souls.py`. Implementation choices within the
   spec: attack / dodge presses are buffered 8 frames (the style's `input_buffer_frames`); a heavy may finish a
   light chain (entered in the chain window: Sentinel's light → light → heavy); a hit that neither breaks poise
   nor meets armour causes a short hitstun (light 12, heavy 20 frames); held inputs (walk, guard) must be fed
   every frame. Shenmue untouched (no JSON change until step 2).
   Domain `souls.py` + pytest (rules + the 9 scenarios).
2. JSON `ce-gameplay/3` + Godot port + parity checks (Shenmue fights still identical).
3. Godot arena: style switch, player controls, Sentinel controller, HUD (health, stamina, poise).
4. Blender placeholder clips on the game rig (grips from the pose library), baked glTF; Godot plays them by state.
5. Play-testing pass on the GT 740M and value tuning (values stay PLACEHOLDER until then).

## 8. Files

| Authorized (new or changed) | Untouchable |
|-----------------------------|-------------|
| `src/character_engine/domain/gameplay/souls.py` (new), `gameplay/__init__.py`, `runtime_table.py` | Canonical data (`data/anatomy/*`) and its fingerprints (Decision 52) |
| `runtime/godot/addons/character_engine/gameplay/ce_souls_combat.gd` (new), `ce_arena.gd`, `ce_fighter_controller.gd`, `ce_gameplay_data.gd` | `combat.py` Shenmue rules (only shared helpers may be imported) |
| `runtime/godot/tests/ce_test_runner.gd`, `tests/unit/test_souls*.py` (new) | Trauma model values, weapon table values (Decision 50) |
| `scripts/export_gameplay_data.py`, docs (07, 19, DECISION_LOG) | Other sessions' uncommitted work (materials/physics, audio branch) |

## 9. Acceptance criteria

- pytest: rules and 9 scenarios deterministic; Shenmue 9 reference fights unchanged.
- Godot: every souls scenario replays identically to Python; arena playable with keyboard; Sentinel cycles its pattern.
- All tuning values marked PLACEHOLDER; no anatomy or trauma value changed.
- Runs on the GT 740M at the arena's current frame rate class (re-measure with `scripts/godot_perf.py` if needed).

## 10. Risks

- Feel depends on animation: until Blender clips exist, the duel is read through placeholders and the HUD.
- Determinism vs real-time input: Godot input feeds the same frame-stepped machine (as Shenmue); parity covers
  scripted input only.
- The audio branch also edits `ce_arena.gd`: merge order to be agreed before step 3.
- Stamina/poise numbers are guesses (PLACEHOLDER); the first playtest will move them.

## 11. Owner decisions requested

1. Approve the rules (§3) and the v1 scope (§2) — yes / changes.
2. Keyboard mapping (§5) — yes / changes (gamepad needed in v1?).
3. Enemy: one Sentinel with the staff — yes / prefer the short blade.
4. Start with step 1 only — yes / no.
