"""Gameplay styles (engine-neutral logic). Runtimes port or embed these modules."""

from .combat import (
    GAMEPLAY_STYLES,
    SHENMUE_MOVES,
    CombatEvent,
    CombatInput,
    CombatState,
    Fighter,
    HitEvent,
    Move,
    MoveKind,
    ShenmueCombat,
    default_hitboxes,
)
from .runtime_table import gameplay_runtime_table, run_scenario

__all__ = [
    "gameplay_runtime_table",
    "run_scenario",
    "GAMEPLAY_STYLES",
    "SHENMUE_MOVES",
    "CombatEvent",
    "CombatInput",
    "CombatState",
    "Fighter",
    "HitEvent",
    "Move",
    "MoveKind",
    "ShenmueCombat",
    "default_hitboxes",
]
