"""UPBGE runtime: Shenmue-style fighter driven by the shared combat domain.

Two entry points share one implementation (:class:`FighterLogic`):

* ``ce_combat.CEFighter`` — a ``KX_PythonComponent`` (attach from the Logic editor or the
  addon's *Runtime* tab when running the UPBGE UI).
* ``ce_combat.run`` — a *module-mode Python controller* wired to an Always sensor (pulse).
  This is what the addon uses in background/headless mode, because UPBGE 0.50's
  ``python_component_register`` operator crashes without a UI.

Both embed :class:`character_engine.domain.gameplay.ShenmueCombat` — the same pure-Python
state machine pytest exercises — so gameplay rules are identical in UPBGE, Godot (GDScript
port) and tests.

Controls (player): WASD move, J punch, K kick, L throw, SPACE guard. Directional command
tokens: W = towards the lock-on target (F), S = away (B), A/D = side-step (U/D).
"""

from __future__ import annotations

import os
import random
import sys
from collections import OrderedDict
from pathlib import Path

try:
    import bge  # type: ignore
    from bge.types import KX_PythonComponent  # type: ignore
except ImportError:  # imported outside the running game engine (tests, editor)
    bge = None

    class KX_PythonComponent:  # minimal stand-in so the class can be imported
        object = None
        args = {}


def _ensure_domain() -> None:
    try:
        import character_engine.domain  # noqa: F401
        return
    except ImportError:
        pass
    candidates = []
    env = os.environ.get("CHARACTER_ENGINE_SRC")
    if env:
        candidates.append(Path(env))
    starts = []
    try:  # never touch bge.logic here: outside a running game it is not initialised
        import bpy  # type: ignore

        if bpy.data.filepath:
            starts.append(Path(bpy.data.filepath).resolve().parent)
    except Exception:  # noqa: BLE001
        pass
    if "__file__" in globals():
        starts.append(Path(__file__).resolve().parent)
    for start in starts:
        for parent in [start, *start.parents]:
            candidates.append(parent / "src")
    for cand in candidates:
        if (cand / "character_engine" / "domain").is_dir():
            sys.path.insert(0, str(cand))
            return
    raise ImportError("character_engine sources not found; set CHARACTER_ENGINE_SRC")


_ensure_domain()

from character_engine.domain.gameplay import (  # noqa: E402
    CombatInput,
    CombatState,
    Fighter,
    ShenmueCombat,
)

_REGISTRY: OrderedDict[str, FighterLogic] = OrderedDict()   # fighter_id -> logic (scene-wide)
_SIM = {"sim": None}

DEFAULT_ARGS = OrderedDict([
    ("fighter_id", "player"),
    ("is_player", True),
    ("style", "shenmue"),
    ("stature_m", 1.80),
    ("move_speed", 2.0),
    ("ai_aggression", 0.02),
    ("autoplay_frames", 0),      # >0: scripted smoke test — player jabs, game ends after N frames
    ("report_path", ""),         # where the smoke test writes its JSON summary
])


def shared_sim() -> ShenmueCombat:
    if _SIM["sim"] is None:
        _SIM["sim"] = ShenmueCombat([logic.fighter for logic in _REGISTRY.values()])
    return _SIM["sim"]


def reset() -> None:
    _REGISTRY.clear()
    _SIM["sim"] = None


class FighterLogic:
    """Engine-facing glue around one :class:`Fighter`; ``obj`` is a KX_GameObject (or a stub)."""

    def __init__(self, obj, args: dict):
        self.object = obj
        self.fighter_id = str(args.get("fighter_id", "player"))
        self.is_player = bool(args.get("is_player", True))
        self.speed = float(args.get("move_speed", 2.0))
        self.ai_aggression = float(args.get("ai_aggression", 0.02))
        self.autoplay_frames = int(args.get("autoplay_frames", 0) or 0)
        self.report_path = str(args.get("report_path", "") or "")
        self.frames = 0
        pos = obj.worldPosition
        self.fighter = Fighter(self.fighter_id, (pos.x, pos.y, pos.z), stature_m=float(args.get("stature_m", 1.80)))
        _REGISTRY[self.fighter_id] = self
        _SIM["sim"] = None            # rebuilt lazily once every fighter has registered
        obj["ce_health"] = 100.0
        obj["ce_state"] = CombatState.IDLE.value
        self._last_event_index = 0

    # ------------------------------------------------------------------ input
    def _keys(self) -> dict:
        kb = bge.logic.keyboard.inputs
        ev = bge.events

        def down(code):
            return kb[code].active or kb[code].activated

        return {
            "w": down(ev.WKEY), "s": down(ev.SKEY), "a": down(ev.AKEY), "d": down(ev.DKEY),
            "punch": kb[ev.JKEY].activated, "kick": kb[ev.KKEY].activated, "throw": kb[ev.LKEY].activated,
            "guard": kb[ev.SPACEKEY].active,
        }

    @staticmethod
    def direction_token(keys: dict) -> str:
        if keys.get("w"):
            return "F"
        if keys.get("s"):
            return "B"
        if keys.get("a"):
            return "U"
        if keys.get("d"):
            return "D"
        return ""

    def _move(self, keys: dict) -> None:
        f = self.fighter
        if f.state not in (CombatState.IDLE, CombatState.MOVE, CombatState.GUARD):
            return
        dx = (1.0 if keys["d"] else 0.0) - (1.0 if keys["a"] else 0.0)
        dy = (1.0 if keys["w"] else 0.0) - (1.0 if keys["s"] else 0.0)
        if dx or dy:
            step = self.speed / 60.0
            self.object.applyMovement((dx * step, dy * step, 0.0), False)
            f.state = CombatState.MOVE
        elif f.state == CombatState.MOVE:
            f.state = CombatState.IDLE

    def _ai(self, sim: ShenmueCombat) -> None:
        target = sim.nearest_opponent(self.fighter)
        if target is None or self.fighter.state not in (CombatState.IDLE, CombatState.MOVE):
            return
        dist = self.fighter.distance_to(target)
        if dist > 0.8:
            me, other = self.object.worldPosition, target.position
            step = self.speed / 60.0
            dx, dy = other[0] - me.x, other[1] - me.y
            n = (dx * dx + dy * dy) ** 0.5 or 1.0
            self.object.applyMovement((dx / n * step, dy / n * step, 0.0), False)
        elif random.random() < self.ai_aggression:
            sim.feed(self.fighter_id, CombatInput(punch=random.random() < 0.6, kick=random.random() < 0.3,
                                                  guard=random.random() < 0.2))

    # ------------------------------------------------------------------ frame
    def _autoplay_keys(self) -> dict:
        return {"w": False, "s": False, "a": False, "d": False, "punch": self.frames % 20 == 0,
                "kick": self.frames % 90 == 45, "throw": False, "guard": False}

    def _finish_autoplay(self, sim: ShenmueCombat) -> None:
        import json

        summary = {
            "frames": sim.frame, "hits": len(sim.hits), "events": len(sim.events),
            "fighters": {fid: {"health": f.health, "state": f.state.value, "wounds": len(f.wounds)}
                         for fid, f in sim.fighters.items()},
            "engine": "upbge", "entry": "autoplay",
        }
        if self.report_path:
            Path(self.report_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[CE combat] autoplay finished: {summary}")
        if bge is not None:
            bge.logic.endGame()

    def update(self, keys: dict | None = None) -> None:
        sim = shared_sim()
        self.frames += 1
        pos = self.object.worldPosition
        self.fighter.position = (pos.x, pos.y, pos.z)
        if self.is_player:
            if keys is None:
                keys = self._autoplay_keys() if self.autoplay_frames > 0 else self._keys()
            self._move(keys)
            sim.feed(self.fighter_id, CombatInput(direction=self.direction_token(keys), punch=keys["punch"],
                                                  kick=keys["kick"], throw=keys["throw"], guard=keys["guard"]))
        else:
            self._ai(sim)
        # Only the first registered fighter advances the shared simulation each frame.
        if next(iter(_REGISTRY)) == self.fighter_id:
            sim.step()
            for ev in sim.events[self._last_event_index:]:
                if ev.kind in ("hit", "blocked", "knockdown", "ko"):
                    print(f"[CE combat] f{ev.frame} {ev.fighter}: {ev.kind} {ev.detail}")
            self._last_event_index = len(sim.events)
        self.object["ce_health"] = self.fighter.health
        self.object["ce_state"] = self.fighter.state.value
        if self.fighter.wounds:
            self.object["ce_last_wound"] = self.fighter.wounds[-1].notes
        if self.is_player and self.autoplay_frames > 0 and self.frames >= self.autoplay_frames:
            self._finish_autoplay(sim)


# ---------------------------------------------------------------------------- component ----

class CEFighter(KX_PythonComponent):
    args = DEFAULT_ARGS

    def start(self, args):
        self.logic = FighterLogic(self.object, dict(args))

    def update(self):
        self.logic.update()


# ---------------------------------------------------------------------------- logic brick --

def run(cont) -> None:
    """Module-mode Python controller entry point (Always sensor, pulse mode).

    Reads the fighter arguments from game properties named like :data:`DEFAULT_ARGS`.
    """
    obj = cont.owner
    logic = _REGISTRY.get(obj.get("_ce_logic_key", ""))
    if logic is None:
        args = {k: obj.get(k, v) for k, v in DEFAULT_ARGS.items()}
        logic = FighterLogic(obj, args)
        obj["_ce_logic_key"] = logic.fighter_id
    logic.update()
