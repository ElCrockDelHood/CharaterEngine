"""Souls-like duel (STYLE-SOULS-001 step 1): stamina, dodge with i-frames, light / heavy attacks, poise, Sentinel.

Deterministic, frame-based (60 Hz) like :class:`~.combat.ShenmueCombat`; pure Python, no engine code. Call
:meth:`SoulsCombat.feed` for every fighter, then :meth:`SoulsCombat.step` once per frame.

Rules (spec ``docs/architecture/STYLE-SOULS-001_SPEC.md``):

* **Stamina** — every action costs stamina; an action whose cost exceeds the current stamina is dropped. It
  regenerates after ``regen_delay`` frames without spending (×``guard_regen_factor`` while guarding). Blocking a
  hit drains ``energy / block_divisor``; reaching 0 while guarding is a **guard break** (stagger).
* **Dodge** — a roll of ``dodge_frames`` covering ``dodge_distance``; hits resolved on dodge frames
  ``iframes`` miss (``dodged``). Not possible during attack startup / active frames; possible during attack
  recovery from frame ``dodge_cancel_from``.
* **Attacks** — per weapon set (unarmed, staff, short blade): light attacks chain up to 3 within the first
  ``chain_window`` recovery frames; a heavy may finish a chain (entered in the same window) but chains into
  nothing. Hits go through the weapon / trauma path (staff BLUNT, blade INCISION, unarmed BLUNT).
* **Poise** — hits subtract poise; at 0 the target **staggers** and poise resets; heavies have hyper-armour from
  startup frame ``armour_from`` to the end of their active frames (hit but not interrupted). A hit that neither
  breaks poise nor meets armour causes a short hitstun.
* **Input buffer** — attack and dodge presses wait up to ``input_buffer_frames`` frames for a legal moment.
* **Sentinel** — a deterministic enemy pattern: approach, telegraph, light → light → heavy, punish window,
  step back, repeat.

Every tuning value is **PLACEHOLDER** (to be adjusted by playing); weapon and trauma values are not changed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..trauma import WoundAssessment, assess_wound, blunt_impact_to_wound
from .combat import FRAME_RATE, _health_cost, default_hitboxes
from .weapons import WEAPONS, Weapon, WeaponCategory

Vec = Tuple[float, float, float]

#: Gameplay tuning — all PLACEHOLDER (STYLE-SOULS-001 §4).
SOULS_TUNING: Mapping[str, float] = {
    "stamina_max": 100.0, "stamina_regen": 0.75, "regen_delay": 30, "guard_regen_factor": 0.3,
    "dodge_cost": 20.0, "dodge_frames": 26, "iframe_start": 4, "iframe_end": 15, "dodge_distance": 2.0,
    "dodge_cancel_from": 8, "chain_window": 10, "max_chain": 3, "block_divisor": 10.0,
    "poise_max": 50.0, "poise_regen": 0.5, "poise_regen_delay": 60, "stagger_frames": 40,
    "walk_speed": 1.6, "input_buffer_frames": 8,
    "engage_range": 1.3, "retreat_range": 2.6, "telegraph_frames": 20, "punish_window": 40,
}
PROVENANCE = ProvenanceState.PLACEHOLDER


class SoulsState(Enum):
    IDLE = "idle"
    WALK = "walk"
    GUARD = "guard"
    STARTUP = "startup"
    ACTIVE = "active"
    RECOVERY = "recovery"
    DODGE = "dodge"
    HITSTUN = "hitstun"
    STAGGER = "stagger"
    KO = "ko"


@dataclass(frozen=True)
class SoulsMove:
    move_id: str
    weapon_id: str
    kind: str                     # "light" | "heavy"
    startup: int
    active: int
    recovery: int
    energy_multiplier: float      # over the weapon-scaled base energy
    stamina_cost: float
    poise_damage: float
    hitstun: int
    target_bone: str
    armour_from: Optional[int] = None   # heavy: hyper-armour from this startup frame to the end of active


BASE_ENERGY_J = 60.0              # light strike before weapon / heavy multipliers (Shenmue jab energy)
BASE_REACH_M = 0.85               # arm reach at 1.80 m stature (Shenmue jab reach); the weapon adds its reach
UNARMED_CONTACT_RADIUS_M = 0.045  # Shenmue punch contact radius

_FRAME_DATA: Mapping[str, Tuple[Tuple[int, int, int, float], Tuple[int, int, int, float]]] = {
    #               light (startup, active, recovery, poise)   heavy (startup, active, recovery, poise)
    "unarmed": ((8, 3, 12, 10.0), (16, 4, 20, 25.0)),
    "staff": ((12, 4, 18, 15.0), (24, 5, 26, 35.0)),
    "short_blade": ((9, 3, 14, 12.0), (18, 4, 22, 28.0)),
}

SOULS_MOVES: Dict[str, SoulsMove] = {}
for _wid, ((_ls, _la, _lr, _lp), (_hs, _ha, _hr, _hp)) in _FRAME_DATA.items():
    SOULS_MOVES[f"{_wid}_light"] = SoulsMove(f"{_wid}_light", _wid, "light", _ls, _la, _lr, 1.0, 15.0, _lp, 12,
                                             "RIB_08_L")
    SOULS_MOVES[f"{_wid}_heavy"] = SoulsMove(f"{_wid}_heavy", _wid, "heavy", _hs, _ha, _hr, 1.8, 30.0, _hp, 20,
                                             "TEMPORAL_L", armour_from=8)


def souls_move(weapon_id: str, kind: str) -> SoulsMove:
    return SOULS_MOVES[f"{weapon_id}_{kind}"]


@dataclass
class SoulsInput:
    direction: str = ""          # "", "F" (towards the lock-on target), "B", "L", "R" (strafe)
    light: bool = False
    heavy: bool = False
    dodge: bool = False
    guard: bool = False


@dataclass
class SoulsFighter:
    fighter_id: str
    position: Vec = (0.0, 0.0, 0.0)
    weapon: Weapon = WEAPONS["unarmed"]
    stature_m: float = 1.80
    health: float = 100.0
    stamina: float = SOULS_TUNING["stamina_max"]
    poise: float = SOULS_TUNING["poise_max"]
    state: SoulsState = SoulsState.IDLE
    state_frames: int = 0
    current_move: Optional[str] = None
    chain: int = 0
    stun_frames: int = 0
    guarding: bool = False
    walk_dir: str = ""
    dodge_vector: Vec = (0.0, 0.0, 0.0)
    since_spend: int = 10_000
    since_poise_hit: int = 10_000
    buffered: Optional[Tuple[int, str]] = None        # (frame pressed, "light" | "heavy" | "dodge:<dir>")
    wounds: List[WoundAssessment] = field(default_factory=list)
    hitboxes: Dict[str, float] = field(default_factory=dict)

    @property
    def alive(self) -> bool:
        return self.state != SoulsState.KO

    def distance_to(self, other: SoulsFighter) -> float:
        return math.hypot(self.position[0] - other.position[0], self.position[1] - other.position[1])


@dataclass(frozen=True)
class SoulsEvent:
    frame: int
    fighter: str
    kind: str        # move_start hit blocked guard_break dodged whiff armoured poise_break no_stamina dodge ko telegraph
    detail: str = ""


@dataclass(frozen=True)
class SoulsHit:
    frame: int
    attacker: str
    defender: str
    move_id: str
    bone_hit: str
    energy_j: float
    assessment: WoundAssessment


def _r(v: float) -> float:
    return round(v, 6)


class SoulsCombat:
    """Fixed-step Souls-like duel between N fighters (lock-on to the nearest living opponent)."""

    def __init__(self, fighters: Sequence[SoulsFighter], tuning: Mapping[str, float] = SOULS_TUNING):
        self.t = tuning
        self.fighters: Dict[str, SoulsFighter] = {f.fighter_id: f for f in fighters}
        for f in self.fighters.values():
            if not f.hitboxes:
                f.hitboxes = default_hitboxes(f.stature_m)
        self.frame = 0
        self.events: List[SoulsEvent] = []
        self.hits: List[SoulsHit] = []
        self._resolved: Dict[str, bool] = {}

    # ---- helpers ----------------------------------------------------------------------------------------
    def nearest_opponent(self, f: SoulsFighter) -> Optional[SoulsFighter]:
        others = [o for o in self.fighters.values() if o is not f and o.alive]
        return min(others, key=f.distance_to) if others else None

    def _emit(self, fighter: str, kind: str, detail: str = "") -> None:
        self.events.append(SoulsEvent(self.frame, fighter, kind, detail))

    def _axes(self, f: SoulsFighter) -> Tuple[Vec, Vec]:
        """(towards target, strafe-left) unit vectors in the canonical ground plane."""
        tgt = self.nearest_opponent(f)
        if tgt is None or f.distance_to(tgt) < 1e-9:
            fwd = (0.0, -1.0, 0.0)
        else:
            d = f.distance_to(tgt)
            fwd = ((tgt.position[0] - f.position[0]) / d, (tgt.position[1] - f.position[1]) / d, 0.0)
        return fwd, (-fwd[1], fwd[0], 0.0)

    def _dir_vector(self, f: SoulsFighter, direction: str) -> Vec:
        fwd, left = self._axes(f)
        return {"F": fwd, "B": (-fwd[0], -fwd[1], 0.0), "L": left, "R": (-left[0], -left[1], 0.0)}.get(
            direction, (-fwd[0], -fwd[1], 0.0))    # no direction = back-step

    def _spend(self, f: SoulsFighter, cost: float) -> None:
        f.stamina = _r(f.stamina - cost)
        f.since_spend = 0

    # ---- input ------------------------------------------------------------------------------------------
    def feed(self, fighter_id: str, inp: SoulsInput) -> None:
        f = self.fighters[fighter_id]
        if not f.alive:
            return
        f.walk_dir = inp.direction
        f.guarding = inp.guard
        if inp.dodge:
            f.buffered = (self.frame, f"dodge:{inp.direction}")
        elif inp.heavy:
            f.buffered = (self.frame, "heavy")
        elif inp.light:
            f.buffered = (self.frame, "light")
        self._try_buffered(f)

    def _try_buffered(self, f: SoulsFighter) -> None:
        if f.buffered is None:
            return
        pressed, action = f.buffered
        if self.frame - pressed > int(self.t["input_buffer_frames"]):
            f.buffered = None
            return
        free = f.state in (SoulsState.IDLE, SoulsState.WALK, SoulsState.GUARD)
        in_recovery = f.state == SoulsState.RECOVERY
        if action.startswith("dodge"):
            if not (free or (in_recovery and f.state_frames >= int(self.t["dodge_cancel_from"]))):
                return
            f.buffered = None
            if f.stamina < self.t["dodge_cost"]:
                self._emit(f.fighter_id, "no_stamina", "dodge")
                return
            self._spend(f, self.t["dodge_cost"])
            v = self._dir_vector(f, action.split(":", 1)[1])
            step = self.t["dodge_distance"] / self.t["dodge_frames"]
            f.dodge_vector = (v[0] * step, v[1] * step, 0.0)
            f.state, f.state_frames, f.current_move, f.chain = SoulsState.DODGE, 0, None, 0
            self._emit(f.fighter_id, "dodge", action.split(":", 1)[1] or "back")
            return
        chaining = (in_recovery and f.current_move is not None and SOULS_MOVES[f.current_move].kind == "light"
                    and f.state_frames <= int(self.t["chain_window"])
                    and (action == "heavy" or f.chain < int(self.t["max_chain"])))
        if not (free or chaining):
            return
        f.buffered = None
        mv = souls_move(f.weapon.weapon_id, action)
        if f.stamina < mv.stamina_cost:
            self._emit(f.fighter_id, "no_stamina", mv.move_id)
            return
        self._spend(f, mv.stamina_cost)
        f.chain = f.chain + 1 if (chaining and action == "light") else (1 if action == "light" else 0)
        f.state, f.state_frames, f.current_move = SoulsState.STARTUP, 0, mv.move_id
        self._resolved[f.fighter_id] = False
        self._emit(f.fighter_id, "move_start", f"{mv.move_id}#{f.chain}" if action == "light" else mv.move_id)

    # ---- simulation -------------------------------------------------------------------------------------
    def step(self) -> None:
        self.frame += 1
        for f in list(self.fighters.values()):
            if not f.alive:
                continue
            f.state_frames += 1
            f.since_spend += 1
            f.since_poise_hit += 1
            self._regen(f)
            if f.state == SoulsState.STARTUP:
                mv = SOULS_MOVES[f.current_move]
                if f.state_frames > mv.startup:
                    f.state, f.state_frames = SoulsState.ACTIVE, 0
                    self._resolve_hit(f, mv)
            elif f.state == SoulsState.ACTIVE:
                mv = SOULS_MOVES[f.current_move]
                if not self._resolved.get(f.fighter_id):
                    self._resolve_hit(f, mv)
                if f.state_frames >= mv.active:
                    f.state, f.state_frames = SoulsState.RECOVERY, 0
            elif f.state == SoulsState.RECOVERY:
                if f.state_frames >= SOULS_MOVES[f.current_move].recovery:
                    f.state, f.state_frames, f.current_move, f.chain = SoulsState.IDLE, 0, None, 0
            elif f.state == SoulsState.DODGE:
                f.position = (_r(f.position[0] + f.dodge_vector[0]), _r(f.position[1] + f.dodge_vector[1]),
                              f.position[2])
                if f.state_frames >= int(self.t["dodge_frames"]):
                    f.state, f.state_frames = SoulsState.IDLE, 0
            elif f.state in (SoulsState.HITSTUN, SoulsState.STAGGER):
                if f.state_frames >= f.stun_frames:
                    f.state, f.state_frames = SoulsState.IDLE, 0
            if f.state in (SoulsState.IDLE, SoulsState.WALK, SoulsState.GUARD):
                self._locomotion(f)
            self._try_buffered(f)
            f.walk_dir, f.guarding = "", False      # held inputs must be fed every frame

    def _regen(self, f: SoulsFighter) -> None:
        if f.since_spend > self.t["regen_delay"] and f.state not in (SoulsState.STARTUP, SoulsState.ACTIVE,
                                                                     SoulsState.DODGE):
            rate = self.t["stamina_regen"] * (self.t["guard_regen_factor"] if f.state == SoulsState.GUARD else 1.0)
            f.stamina = _r(min(self.t["stamina_max"], f.stamina + rate))
        if f.since_poise_hit > self.t["poise_regen_delay"]:
            f.poise = _r(min(self.t["poise_max"], f.poise + self.t["poise_regen"]))

    def _locomotion(self, f: SoulsFighter) -> None:
        if f.guarding:
            f.state = SoulsState.GUARD
            return
        if f.walk_dir:
            v = self._dir_vector(f, f.walk_dir)
            step = self.t["walk_speed"] / FRAME_RATE
            f.position = (_r(f.position[0] + v[0] * step), _r(f.position[1] + v[1] * step), f.position[2])
            f.state = SoulsState.WALK
        else:
            f.state = SoulsState.IDLE

    def _armoured(self, f: SoulsFighter) -> bool:
        if f.current_move is None:
            return False
        mv = SOULS_MOVES[f.current_move]
        if mv.armour_from is None:
            return False
        return (f.state == SoulsState.STARTUP and f.state_frames >= mv.armour_from) or f.state == SoulsState.ACTIVE

    def _resolve_hit(self, a: SoulsFighter, mv: SoulsMove) -> None:
        self._resolved[a.fighter_id] = True
        target = self.nearest_opponent(a)
        reach = BASE_REACH_M * (a.stature_m / 1.80) + a.weapon.reach_m
        if target is None or a.distance_to(target) > reach:
            self._emit(a.fighter_id, "whiff", mv.move_id)
            return
        if (target.state == SoulsState.DODGE
                and self.t["iframe_start"] <= target.state_frames <= self.t["iframe_end"]):
            self._emit(target.fighter_id, "dodged", mv.move_id)
            return
        energy = _r(BASE_ENERGY_J * a.weapon.energy_multiplier * mv.energy_multiplier)
        if target.state == SoulsState.GUARD:
            target.stamina = _r(target.stamina - energy / self.t["block_divisor"])
            target.since_spend = 0
            if target.stamina <= 0.0:
                target.stamina = 0.0
                self._stun(target, SoulsState.STAGGER, int(self.t["stagger_frames"]))
                self._emit(target.fighter_id, "guard_break", mv.move_id)
            else:
                self._emit(target.fighter_id, "blocked", mv.move_id)
            return
        bone = mv.target_bone if mv.target_bone in target.hitboxes else "STERNUM"
        if a.weapon.category is WeaponCategory.UNARMED:
            wound = blunt_impact_to_wound(bone, contact_radius_m=UNARMED_CONTACT_RADIUS_M, energy_j=energy)
        else:
            wound = a.weapon.strike_wound(bone, energy)
        assessment = assess_wound(wound)
        target.wounds.append(assessment)
        target.health = _r(max(0.0, target.health - _health_cost(assessment, None, energy)))  # type: ignore[arg-type]
        target.poise = _r(target.poise - mv.poise_damage)
        target.since_poise_hit = 0
        self.hits.append(SoulsHit(self.frame, a.fighter_id, target.fighter_id, mv.move_id, bone, energy, assessment))
        self._emit(target.fighter_id, "hit", f"{mv.move_id}->{bone} sev{assessment.severity.value}")
        if target.health <= 0.0 or assessment.is_lethal:
            target.state, target.state_frames, target.current_move = SoulsState.KO, 0, None
            self._emit(target.fighter_id, "ko")
        elif target.poise <= 0.0:
            target.poise = self.t["poise_max"]
            self._stun(target, SoulsState.STAGGER, int(self.t["stagger_frames"]))
            self._emit(target.fighter_id, "poise_break", mv.move_id)
        elif self._armoured(target):
            self._emit(target.fighter_id, "armoured", mv.move_id)
        else:
            self._stun(target, SoulsState.HITSTUN, mv.hitstun)

    def _stun(self, f: SoulsFighter, state: SoulsState, frames: int) -> None:
        f.state, f.state_frames, f.stun_frames, f.current_move, f.chain = state, 0, frames, None, 0
        f.buffered = None


class Sentinel:
    """Deterministic enemy pattern: approach → telegraph → light, light, heavy → punish window → step back."""

    def __init__(self, fighter_id: str, tuning: Mapping[str, float] = SOULS_TUNING):
        self.fighter_id = fighter_id
        self.t = tuning
        self.phase = "approach"
        self.phase_frames = 0
        self.presses = 0

    def _go(self, phase: str) -> None:
        self.phase, self.phase_frames, self.presses = phase, 0, 0

    def decide(self, sim: SoulsCombat) -> SoulsInput:
        me = sim.fighters[self.fighter_id]
        target = sim.nearest_opponent(me)
        self.phase_frames += 1
        if target is None or not me.alive:
            return SoulsInput()
        if me.state in (SoulsState.HITSTUN, SoulsState.STAGGER):
            if self.phase != "approach":
                self._go("approach")
            return SoulsInput()
        dist = me.distance_to(target)
        if self.phase == "approach":
            if dist > self.t["engage_range"]:
                return SoulsInput(direction="F")
            self._go("telegraph")
            sim._emit(self.fighter_id, "telegraph")
            return SoulsInput()
        if self.phase == "telegraph":
            if target.state == SoulsState.DODGE:           # no tracking mid-dodge in v1: wait it out
                self.phase_frames -= 1
            if self.phase_frames >= self.t["telegraph_frames"]:
                self._go("string")
            return SoulsInput()
        if self.phase == "string":
            plan = ("light", "light", "heavy")
            if self.presses < len(plan):
                kind = plan[self.presses]
                ready = me.state in (SoulsState.IDLE, SoulsState.WALK) or (
                    me.state == SoulsState.RECOVERY and me.state_frames <= self.t["chain_window"])
                if ready and me.buffered is None:
                    self.presses += 1
                    return SoulsInput(light=kind == "light", heavy=kind == "heavy")
                return SoulsInput()
            if me.state in (SoulsState.IDLE, SoulsState.WALK):
                self._go("recover")
            return SoulsInput()
        if self.phase == "recover":
            if self.phase_frames >= self.t["punish_window"]:
                self._go("retreat")
            return SoulsInput()
        if self.phase == "retreat":
            if dist < self.t["retreat_range"]:
                return SoulsInput(direction="B")
            self._go("approach")
        return SoulsInput()


# ---- reference scenarios (the parity gate for the Godot port, step 2) -------------------------------------

def run_souls_scenario(spec: Mapping[str, object]) -> Dict[str, object]:
    """Run a scripted duel. ``spec``: distance_m, frames, weapons {fid: id}, sentinel (fid or None),
    start {fid: {stamina, poise}}, script {frame: {fid: SoulsInput kwargs}}, hold {fid: kwargs every frame}."""
    weapons: Mapping[str, str] = spec.get("weapons", {})  # type: ignore[assignment]
    d = float(spec["distance_m"])
    fighters = [SoulsFighter("player", (0.0, 0.0, 0.0), WEAPONS[weapons.get("player", "unarmed")]),
                SoulsFighter("opponent", (0.0, -d, 0.0), WEAPONS[weapons.get("opponent", "unarmed")])]
    for f in fighters:
        for k, v in dict(spec.get("start", {})).get(f.fighter_id, {}).items():  # type: ignore[union-attr]
            setattr(f, k, float(v))
    sim = SoulsCombat(fighters)
    sentinel = Sentinel(str(spec["sentinel"])) if spec.get("sentinel") else None
    script: Mapping[int, Mapping[str, Mapping[str, object]]] = spec.get("script", {})  # type: ignore[assignment]
    hold: Mapping[str, Mapping[str, object]] = spec.get("hold", {})  # type: ignore[assignment]
    for _ in range(int(spec["frames"])):
        nxt = sim.frame + 1
        inputs: Dict[str, Dict[str, object]] = {fid: dict(kw) for fid, kw in hold.items()}
        for fid, kw in script.get(nxt, {}).items():
            inputs.setdefault(fid, {}).update(kw)
        if sentinel is not None:
            s_in = sentinel.decide(sim)
            sim.feed(sentinel.fighter_id, s_in)
        for fid, kw in inputs.items():
            sim.feed(fid, SoulsInput(**kw))
        sim.step()
    return {
        "scenario_id": spec["scenario_id"],
        "frames": sim.frame,
        "hits": [{"frame": h.frame, "attacker": h.attacker, "defender": h.defender, "move_id": h.move_id,
                  "bone_hit": h.bone_hit, "energy_j": h.energy_j, "severity": h.assessment.severity.value}
                 for h in sim.hits],
        "events": [{"frame": e.frame, "fighter": e.fighter, "kind": e.kind, "detail": e.detail} for e in sim.events],
        "fighters": {fid: {"health": f.health, "stamina": f.stamina, "poise": f.poise, "state": f.state.value,
                           "wounds": len(f.wounds), "position": [f.position[0], f.position[1]]}
                     for fid, f in sim.fighters.items()},
    }


def souls_reference_specs() -> List[Dict[str, object]]:
    """The 9 STYLE-SOULS-001 reference scenarios (the Godot parity gate in step 2)."""
    return [
        {"scenario_id": "light_chain_lands", "distance_m": 1.0, "frames": 120, "weapons": {"player": "staff"},
         "script": {1: {"player": {"light": True}}, 15: {"player": {"light": True}}, 33: {"player": {"light": True}}}},
        {"scenario_id": "dodge_through_heavy", "distance_m": 1.2, "frames": 80, "weapons": {"opponent": "staff"},
         "script": {1: {"opponent": {"heavy": True}}, 22: {"player": {"dodge": True, "direction": "L"}}}},
        {"scenario_id": "dodge_too_late", "distance_m": 1.2, "frames": 80, "weapons": {"opponent": "staff"},
         "script": {1: {"opponent": {"heavy": True}}, 24: {"player": {"dodge": True, "direction": "L"}}}},
        {"scenario_id": "stamina_exhausted", "distance_m": 3.0, "frames": 110, "weapons": {"player": "unarmed"},
         "script": {fr: {"player": {"light": True}} for fr in range(1, 110, 6)}},
        {"scenario_id": "guard_break", "distance_m": 1.0, "frames": 120, "weapons": {"player": "staff"},
         "start": {"opponent": {"stamina": 20.0}}, "hold": {"opponent": {"guard": True}},
         "script": {1: {"player": {"light": True}}, 15: {"player": {"light": True}}, 33: {"player": {"light": True}},
                    50: {"player": {"heavy": True}}}},
        {"scenario_id": "poise_break", "distance_m": 1.0, "frames": 140, "weapons": {"player": "staff"},
         "script": {1: {"player": {"heavy": True}}, 60: {"player": {"heavy": True}}}},
        {"scenario_id": "hyper_armour_trade", "distance_m": 0.8, "frames": 80, "weapons": {"opponent": "staff"},
         "script": {1: {"opponent": {"heavy": True}}, 10: {"player": {"light": True}}}},
        {"scenario_id": "sentinel_cycle_600", "distance_m": 3.0, "frames": 600, "weapons": {"opponent": "staff"},
         "sentinel": "opponent"},
        {"scenario_id": "sentinel_punished", "distance_m": 3.0, "frames": 260,
         "weapons": {"player": "staff", "opponent": "staff"}, "sentinel": "opponent",
         "script": {192: {"player": {"light": True}}}},
    ]
