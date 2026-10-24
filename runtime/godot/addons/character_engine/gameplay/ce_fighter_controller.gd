## Drives one CEShenmueCombat fighter: keyboard input for the player, a simple AI for
## opponents, and keeps the CECharacter node in sync with the fighter position.
##
## Default keys (registered in the InputMap if missing):
##   W/S forward-back, A/D side-step, J punch, K kick, L throw, Space guard.
class_name CEFighterController
extends Node

const ACTIONS := {
	"ce_forward": KEY_W, "ce_back": KEY_S, "ce_left": KEY_A, "ce_right": KEY_D,
	"ce_up": KEY_UP, "ce_down": KEY_DOWN,
	"ce_punch": KEY_J, "ce_kick": KEY_K, "ce_throw": KEY_L, "ce_guard": KEY_SPACE,
}

@export var fighter_id: String = "player"
@export var is_player: bool = true
@export var move_speed_mps: float = 1.6
@export var ai_aggression: float = 0.35   # 0..1 probability per decision window
@export var ai_decision_frames: int = 30

var combat: CEShenmueCombat
var fighter: CEShenmueCombat.Fighter
var character: CECharacter
var autoplay_script: Dictionary = {}       # frame -> input dict (tests / demos)
var _rng := RandomNumberGenerator.new()


static func ensure_input_map() -> void:
	for action in ACTIONS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
			var ev := InputEventKey.new()
			ev.physical_keycode = ACTIONS[action]
			InputMap.action_add_event(action, ev)


func setup(p_combat: CEShenmueCombat, p_fighter: CEShenmueCombat.Fighter, p_character: CECharacter, seed := 7) -> void:
	combat = p_combat
	fighter = p_fighter
	character = p_character
	_rng.seed = seed
	if is_player:
		ensure_input_map()
	sync_character()


## Build this frame's input and feed it into the simulation (call before combat.step()).
func collect_input() -> CEShenmueCombat.CombatInput:
	var inp: CEShenmueCombat.CombatInput
	var next_frame := combat.frame + 1
	if autoplay_script.has(next_frame):
		inp = CEShenmueCombat.CombatInput.from_dict(autoplay_script[next_frame])
	elif autoplay_script.has(str(next_frame)):
		inp = CEShenmueCombat.CombatInput.from_dict(autoplay_script[str(next_frame)])
	elif is_player:
		inp = _player_input()
	else:
		inp = _ai_input()
	combat.feed(fighter_id, inp)
	_apply_locomotion(inp)
	return inp


func _player_input() -> CEShenmueCombat.CombatInput:
	var dir := ""
	if Input.is_action_pressed("ce_forward"):
		dir = "F"
	elif Input.is_action_pressed("ce_back"):
		dir = "B"
	elif Input.is_action_pressed("ce_up"):
		dir = "U"
	elif Input.is_action_pressed("ce_down"):
		dir = "D"
	return CEShenmueCombat.CombatInput.make(dir, Input.is_action_just_pressed("ce_punch"),
			Input.is_action_just_pressed("ce_kick"), Input.is_action_just_pressed("ce_throw"),
			Input.is_action_pressed("ce_guard"))


func _ai_input() -> CEShenmueCombat.CombatInput:
	var inp := CEShenmueCombat.CombatInput.new()
	var target := combat.nearest_opponent(fighter)
	if target == null or not fighter.can_act():
		return inp
	var d := fighter.distance_to(target)
	if combat.frame % ai_decision_frames == 0:
		var roll := _rng.randf()
		if d > 0.9:
			inp.direction = "F"
		elif roll < ai_aggression:
			inp.punch = roll < ai_aggression * 0.6
			inp.kick = not inp.punch
		elif roll < ai_aggression + 0.25:
			inp.guard = true
	elif d > 0.9:
		inp.direction = "F"
	return inp


func _apply_locomotion(inp: CEShenmueCombat.CombatInput) -> void:
	if not (fighter.state == CEShenmueCombat.State.IDLE or fighter.state == CEShenmueCombat.State.MOVE):
		return
	var target := combat.nearest_opponent(fighter)
	if target == null:
		return
	var to_target := (target.position - fighter.position)
	to_target.z = 0.0
	if to_target.length() < 1e-6:
		return
	var step := move_speed_mps / float(combat.data.frame_rate())
	var dir := to_target.normalized()
	var delta := Vector3.ZERO
	if inp.direction == "F" and to_target.length() > 0.45:
		delta = dir * step
	elif inp.direction == "B":
		delta = -dir * step
	if delta != Vector3.ZERO:
		fighter.position += delta
		fighter.state = CEShenmueCombat.State.MOVE
	elif fighter.state == CEShenmueCombat.State.MOVE and not fighter.guarding:
		fighter.state = CEShenmueCombat.State.IDLE
	fighter.facing = dir
	sync_character()


## Canonical (Z-up, -Y forward) fighter position -> Godot (Y-up) node transform.
func sync_character() -> void:
	if character == null:
		return
	var p := fighter.position
	character.global_position = Vector3(p.x, p.z, -p.y)
	var f := fighter.facing
	var forward := Vector3(f.x, 0.0, -f.y)
	if forward.length() > 1e-6:
		character.look_at(character.global_position + forward, Vector3.UP, true)
