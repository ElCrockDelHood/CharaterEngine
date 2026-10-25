"""Shenmue-style hand-to-hand combat: deterministic, frame-based state machine.

Design (Shenmue I/II "Free Battle"): fixed-timestep (60 Hz), moves defined by
startup / active / recovery frame windows, directional inputs + Punch / Kick /
Throw / Guard buttons, short command combos (e.g. ``→→P`` = Elbow Assault),
lock-on to the nearest opponent, throws as grabs with a range check, and a guard that
absorbs strikes but not throws. Damage is *not* a bare hit-point number: each landed
strike produces a :class:`HitEvent` with the canonical bone struck, the impact energy
and a :class:`~character_engine.domain.trauma.WoundAssessment`, so runtime layers
can show bruising, stagger or, at high energy, fractures. A fighter may carry a
:class:`~.weapons.Weapon` that extends the reach and changes the energy and wound type
of its hand strikes (default ``unarmed``: no change).

The class is pure Python with no engine dependencies. ``runtime/godot/gameplay/
ce_shenmue_combat.gd`` is a line-by-line port; UPBGE embeds this module directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..trauma import WoundAssessment, assess_wound, blunt_impact_to_wound
from .weapons import UNARMED, Weapon

FRAME_RATE = 60
Vec = Tuple[float, float, float]


class MoveKind(Enum):
    PUNCH = "punch"
    KICK = "kick"
    THROW = "throw"


class CombatState(Enum):
    IDLE = "idle"
    MOVE = "move"            # walking / side-step
    STARTUP = "startup"
    ACTIVE = "active"
    RECOVERY = "recovery"
    GUARD = "guard"
    HITSTUN = "hitstun"
    KNOCKDOWN = "knockdown"
    GRABBED = "grabbed"
    KO = "ko"


@dataclass(frozen=True)
class Move:
    move_id: str
    label: str
    kind: MoveKind
    command: Tuple[str, ...]           # e.g. ("F", "F", "P")  F/B/U/D directions + P/K/T buttons
    startup: int                       # frames
    active: int
    recovery: int
    energy_j: float                    # kinetic energy delivered on hit (blunt)
    contact_radius_m: float
    striking_bone: str                 # attacker canonical bone
    target_region_bone: str            # default defender bone struck at neutral height
    reach_m: float
    hitstun: int = 18
    knockdown: bool = False
    cancel_into: Tuple[str, ...] = ()  # move ids that may chain from this one during recovery

    @property
    def total_frames(self) -> int:
        return self.startup + self.active + self.recovery


# Energy values are gameplay tuning constants, not biomechanical measurements.
SHENMUE_MOVES: Dict[str, Move] = {m.move_id: m for m in (
    Move("jab", "Straight punch", MoveKind.PUNCH, ("P",), 5, 3, 9, 60.0, 0.045, "PHALANX_PROXIMAL_3_R",
         "MANDIBLE", 0.85, hitstun=14, cancel_into=("straight", "hook", "elbow_assault")),
    Move("straight", "Twin Blades", MoveKind.PUNCH, ("P", "P"), 7, 3, 12, 90.0, 0.045, "PHALANX_PROXIMAL_3_L",
         "STERNUM", 0.90, hitstun=16, cancel_into=("hook",)),
    Move("hook", "Pit Blow", MoveKind.PUNCH, ("F", "P"), 9, 3, 15, 130.0, 0.05, "PHALANX_PROXIMAL_3_R",
         "RIB_08_L", 0.80, hitstun=20),
    Move("elbow_assault", "Elbow Assault", MoveKind.PUNCH, ("F", "F", "P"), 8, 4, 16, 170.0, 0.05, "ULNA_R",
         "STERNUM", 0.75, hitstun=24),
    Move("front_kick", "Front kick", MoveKind.KICK, ("K",), 9, 4, 16, 150.0, 0.06, "METATARSAL_3_R",
         "RIB_10_L", 1.10, hitstun=20, cancel_into=("crescent_kick",)),
    Move("crescent_kick", "Crescent Kick", MoveKind.KICK, ("F", "K"), 12, 4, 20, 220.0, 0.06, "TIBIA_R",
         "TEMPORAL_L", 1.15, hitstun=28, knockdown=True),
    Move("sweep", "Trample / sweep", MoveKind.KICK, ("D", "K"), 10, 4, 22, 140.0, 0.06, "TIBIA_R",
         "TIBIA_L", 1.00, hitstun=22, knockdown=True),
    Move("shoulder_throw", "Vortex Throw", MoveKind.THROW, ("F", "T"), 8, 2, 30, 260.0, 0.10, "HUMERUS_R",
         "SCAPULA_L", 0.60, hitstun=40, knockdown=True),
)}

GAMEPLAY_STYLES: Mapping[str, Mapping[str, object]] = {
    "shenmue": {
        "label": "Shenmue-style free battle",
        "moves": tuple(SHENMUE_MOVES),
        "lock_on": True,
        "frame_rate": FRAME_RATE,
        "guard_absorbs": ("punch", "kick"),
        "input_buffer_frames": 12,
    },
    # Placeholders the user plans to add later; the runtime panels list them as "coming soon".
    "souls_like": {"label": "Stamina / lock-on melee (planned)", "moves": (), "lock_on": True,
                   "frame_rate": FRAME_RATE, "guard_absorbs": ("punch", "kick"), "input_buffer_frames": 8},
    "beat_em_up": {"label": "Side-scroll beat 'em up (planned)", "moves": (), "lock_on": False,
                   "frame_rate": FRAME_RATE, "guard_absorbs": (), "input_buffer_frames": 6},
}


@dataclass
class CombatInput:
    direction: str = ""        # "", "F", "B", "U", "D"
    punch: bool = False
    kick: bool = False
    throw: bool = False
    guard: bool = False

    def tokens(self) -> List[str]:
        out = [self.direction] if self.direction else []
        out += [t for t, b in (("P", self.punch), ("K", self.kick), ("T", self.throw)) if b]
        return out


@dataclass
class Fighter:
    fighter_id: str
    position: Vec = (0.0, 0.0, 0.0)
    facing: Vec = (0.0, -1.0, 0.0)     # canonical -Y forward
    stature_m: float = 1.80
    health: float = 100.0
    state: CombatState = CombatState.IDLE
    state_frames: int = 0
    current_move: Optional[str] = None
    guarding: bool = False
    stun_frames: int = 18
    input_history: List[Tuple[int, str]] = field(default_factory=list)   # (frame, token)
    wounds: List[WoundAssessment] = field(default_factory=list)
    hitboxes: Dict[str, float] = field(default_factory=dict)              # bone -> radius m
    weapon: Weapon = UNARMED

    @property
    def alive(self) -> bool:
        return self.state != CombatState.KO

    def distance_to(self, other: Fighter) -> float:
        dx, dy = self.position[0] - other.position[0], self.position[1] - other.position[1]
        return (dx * dx + dy * dy) ** 0.5


@dataclass(frozen=True)
class HitEvent:
    frame: int
    attacker: str
    defender: str
    move_id: str
    bone_hit: str
    energy_j: float
    blocked: bool
    assessment: Optional[WoundAssessment]
    knockdown: bool
    weapon_id: str = "unarmed"


@dataclass(frozen=True)
class CombatEvent:
    frame: int
    fighter: str
    kind: str                # "move_start", "hit", "blocked", "whiff", "knockdown", "ko", "state"
    detail: str = ""


def default_hitboxes(stature_m: float = 1.80) -> Dict[str, float]:
    """Sphere radii per canonical target bone; scaled with stature (gameplay constants)."""
    k = stature_m / 1.80
    return {name: round(r * k, 4) for name, r in {
        "CRANIUM": 0.10, "MANDIBLE": 0.06, "TEMPORAL_L": 0.06, "TEMPORAL_R": 0.06,
        "STERNUM": 0.12, "RIB_08_L": 0.09, "RIB_08_R": 0.09, "RIB_10_L": 0.09, "RIB_10_R": 0.09,
        "SCAPULA_L": 0.08, "SCAPULA_R": 0.08, "LUMBAR_3": 0.11, "SACRUM": 0.10,
        "HUMERUS_L": 0.06, "HUMERUS_R": 0.06, "RADIUS_L": 0.045, "RADIUS_R": 0.045,
        "FEMUR_L": 0.08, "FEMUR_R": 0.08, "TIBIA_L": 0.05, "TIBIA_R": 0.05,
    }.items()}


class ShenmueCombat:
    """Fixed-step simulation of N fighters. Call :meth:`step` once per frame."""

    def __init__(self, fighters: Sequence[Fighter], moves: Mapping[str, Move] = SHENMUE_MOVES,
                 input_buffer_frames: int = 12):
        self.fighters: Dict[str, Fighter] = {f.fighter_id: f for f in fighters}
        for f in self.fighters.values():
            if not f.hitboxes:
                f.hitboxes = default_hitboxes(f.stature_m)
        self.moves = moves
        self.input_buffer = input_buffer_frames
        self.frame = 0
        self.events: List[CombatEvent] = []
        self.hits: List[HitEvent] = []
        self._pending_hit: Dict[str, bool] = {}   # fighter -> already resolved this move

    # ---- input -----------------------------------------------------------------------
    def _match_command(self, f: Fighter) -> Optional[Move]:
        recent = [t for fr, t in f.input_history if self.frame - fr <= self.input_buffer]
        best: Optional[Move] = None
        for mv in self.moves.values():
            cmd = list(mv.command)
            if len(recent) >= len(cmd) and recent[-len(cmd):] == cmd:
                if best is None or len(mv.command) > len(best.command):
                    best = mv
        return best

    def feed(self, fighter_id: str, inp: CombatInput) -> None:
        f = self.fighters[fighter_id]
        f.guarding = inp.guard and f.state in (CombatState.IDLE, CombatState.MOVE, CombatState.GUARD)
        for tok in inp.tokens():
            if not f.input_history or f.input_history[-1] != (self.frame, tok):
                f.input_history.append((self.frame, tok))
        f.input_history = [(fr, t) for fr, t in f.input_history if self.frame - fr <= self.input_buffer * 2]
        if f.state in (CombatState.IDLE, CombatState.MOVE, CombatState.GUARD) and (inp.punch or inp.kick or inp.throw):
            mv = self._match_command(f)
            if mv:
                self._start_move(f, mv)
        elif f.state == CombatState.RECOVERY and f.current_move and (inp.punch or inp.kick):
            mv = self._match_command(f)
            if mv and mv.move_id in self.moves[f.current_move].cancel_into:
                self._start_move(f, mv)

    def _start_move(self, f: Fighter, mv: Move) -> None:
        f.state, f.state_frames, f.current_move, f.guarding = CombatState.STARTUP, 0, mv.move_id, False
        f.input_history.clear()
        self._pending_hit[f.fighter_id] = False
        self.events.append(CombatEvent(self.frame, f.fighter_id, "move_start", mv.move_id))

    # ---- simulation ------------------------------------------------------------------
    def nearest_opponent(self, f: Fighter) -> Optional[Fighter]:
        others = [o for o in self.fighters.values() if o is not f and o.alive]
        return min(others, key=f.distance_to) if others else None

    def step(self) -> None:
        self.frame += 1
        for f in list(self.fighters.values()):
            if not f.alive:
                continue
            f.state_frames += 1
            if f.state == CombatState.STARTUP:
                mv = self.moves[f.current_move]
                if f.state_frames > mv.startup:
                    f.state, f.state_frames = CombatState.ACTIVE, 0
                    self._resolve_hit(f, mv)   # first active frame connects
            elif f.state == CombatState.ACTIVE:
                mv = self.moves[f.current_move]
                if not self._pending_hit.get(f.fighter_id):
                    self._resolve_hit(f, mv)
                if f.state_frames >= mv.active:
                    f.state, f.state_frames = CombatState.RECOVERY, 0
            elif f.state == CombatState.RECOVERY:
                mv = self.moves[f.current_move]
                if f.state_frames >= mv.recovery:
                    f.state, f.state_frames, f.current_move = CombatState.IDLE, 0, None
            elif f.state in (CombatState.HITSTUN, CombatState.GRABBED):
                if f.state_frames >= f.stun_frames:
                    f.state, f.state_frames = CombatState.IDLE, 0
            elif f.state == CombatState.KNOCKDOWN:
                if f.state_frames >= 60:
                    f.state, f.state_frames = CombatState.IDLE, 0
            elif f.state in (CombatState.IDLE, CombatState.MOVE):
                if f.guarding:
                    f.state = CombatState.GUARD
            elif f.state == CombatState.GUARD and not f.guarding:
                f.state = CombatState.IDLE

    def _resolve_hit(self, attacker: Fighter, mv: Move) -> None:
        self._pending_hit[attacker.fighter_id] = True
        target = self.nearest_opponent(attacker)
        armed = attacker.weapon.applies_to(mv.kind.value, mv.striking_bone)
        reach = mv.reach_m * (attacker.stature_m / 1.80)
        if armed:
            reach += attacker.weapon.reach_m
        if target is None or attacker.distance_to(target) > reach:
            self.events.append(CombatEvent(self.frame, attacker.fighter_id, "whiff", mv.move_id))
            return
        bone = mv.target_region_bone if mv.target_region_bone in target.hitboxes else "STERNUM"
        blocked = target.state == CombatState.GUARD and mv.kind != MoveKind.THROW
        energy_j = mv.energy_j * attacker.weapon.energy_multiplier if armed else mv.energy_j
        assessment: Optional[WoundAssessment] = None
        if blocked:
            self.events.append(CombatEvent(self.frame, target.fighter_id, "blocked", mv.move_id))
            target.state, target.state_frames = CombatState.HITSTUN, 0
            target.stun_frames = max(4, mv.hitstun // 3)
        else:
            if armed:
                assessment = assess_wound(attacker.weapon.strike_wound(bone, energy_j))
            else:
                assessment = assess_wound(blunt_impact_to_wound(bone, contact_radius_m=mv.contact_radius_m,
                                                                energy_j=mv.energy_j))
            target.wounds.append(assessment)
            target.health = max(0.0, target.health - _health_cost(assessment, mv, energy_j))
            self.events.append(CombatEvent(self.frame, target.fighter_id, "hit",
                                           f"{mv.move_id}->{bone} sev{assessment.severity.value}"))
            if target.health <= 0.0 or assessment.is_lethal:
                target.state, target.state_frames = CombatState.KO, 0
                self.events.append(CombatEvent(self.frame, target.fighter_id, "ko"))
            elif mv.knockdown or assessment.incapacitating:
                target.state, target.state_frames = CombatState.KNOCKDOWN, 0
                self.events.append(CombatEvent(self.frame, target.fighter_id, "knockdown", mv.move_id))
            else:
                target.state, target.state_frames = CombatState.HITSTUN, 0
                target.stun_frames = mv.hitstun
        self.hits.append(HitEvent(self.frame, attacker.fighter_id, target.fighter_id, mv.move_id, bone,
                                  energy_j, blocked, assessment, (not blocked) and mv.knockdown,
                                  attacker.weapon.weapon_id if armed else "unarmed"))


def _health_cost(a: WoundAssessment, mv: Move, energy_j: Optional[float] = None) -> float:
    """Gameplay abstraction: severity drives the bar; energy adds a small linear term.

    ``energy_j`` overrides the move energy (a weapon multiplies it); default = ``mv.energy_j``.
    """
    e = mv.energy_j if energy_j is None else energy_j
    return round(4.0 * a.severity.value + e / 40.0 + (10.0 if a.fracture else 0.0), 2)
