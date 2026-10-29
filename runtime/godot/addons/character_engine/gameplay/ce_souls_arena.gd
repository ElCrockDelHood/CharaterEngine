## Playable Souls-like arena (STYLE-SOULS-001 step 3): player vs Sentinel on the CE-GAME-v1 game rig.
##
## Kept apart from ce_arena.gd (Shenmue arena; the audio branch edits it). Godot only decides state here:
## CESoulsCombat (port of the Python domain) runs at 60 Hz in _physics_process; the characters follow the
## fighter positions and face each other. Animation clips are authored and baked in Blender (step 4); until
## then the HUD shows each fighter's state. Visuals are Workbench-level (plain meshes, flat colours).
##
## Keys: W/S forward-back (towards / away from the lock-on target), A/D strafe, J light, K heavy, Space dodge
## (+ direction; none = back-step), L guard (hold), Tab lock-on (always on in v1: the domain locks on to the
## nearest opponent; the key is registered for later).
class_name CESoulsArena
extends Node3D

const ACTIONS := {
	"ce_souls_forward": KEY_W, "ce_souls_back": KEY_S, "ce_souls_left": KEY_A, "ce_souls_right": KEY_D,
	"ce_souls_light": KEY_J, "ce_souls_heavy": KEY_K, "ce_souls_dodge": KEY_SPACE, "ce_souls_guard": KEY_L,
	"ce_souls_lock": KEY_TAB,
}

var data: CEGameplayData            # set by build() or loaded in _ready (RefCounted: not exportable)
@export_file("*.glb") var glb_path: String = "res://assets/human_game_v1_tpose.glb"
@export var player_weapon: String = "staff"
@export var sentinel_weapon: String = "staff"
@export var start_distance_m: float = 3.0
@export var show_hud: bool = true
## false: the arena only advances through step_once() (headless tests).
@export var autostep: bool = true
## Frames of scripted player input (tests / demos); empty = keyboard.
var autoplay_script: Dictionary = {}

var combat: CESoulsCombat
var sentinel: CESoulsCombat.Sentinel
var characters: Dictionary = {}          # fighter_id -> CECharacter
var hud: Label
var camera: Camera3D
var frames_stepped := 0
var _built := false


static func ensure_input_map() -> void:
	for action in ACTIONS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
			var ev := InputEventKey.new()
			ev.physical_keycode = ACTIONS[action]
			InputMap.action_add_event(action, ev)


static func build(p_data: CEGameplayData, p_glb := "res://assets/human_game_v1_tpose.glb") -> CESoulsArena:
	var arena := CESoulsArena.new()
	arena.name = "CESoulsArena"
	arena.data = p_data
	arena.glb_path = p_glb
	return arena


func _ready() -> void:
	if data == null:
		data = CEGameplayData.load_default()
	if not _built:
		_build_scene()


func _build_scene() -> void:
	_built = true
	ensure_input_map()
	# Same set-up as the Python reference scenarios: player at the origin, Sentinel at -Y (canonical frame).
	combat = CESoulsCombat.new(data, [])
	var player := combat.make_fighter("player", 0.0, 0.0, player_weapon)
	var opponent := combat.make_fighter("opponent", 0.0, -start_distance_m, sentinel_weapon)
	for f in [player, opponent]:
		f.hitboxes = data.hitboxes(f.stature_m)
		combat.fighters[f.fighter_id] = f
	sentinel = CESoulsCombat.Sentinel.new("opponent", combat.t)
	combat.souls_event.connect(_on_event)

	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(14, 14)
	floor.mesh = plane
	floor.name = "Floor"
	add_child(floor)
	for f in [player, opponent]:
		var ch := CECharacter.new()
		ch.name = "Character_" + f.fighter_id
		ch.glb_path = glb_path
		ch.breathing_enabled = false
		add_child(ch)
		characters[f.fighter_id] = ch
		ch.equip_weapon(data.weapon(f.weapon["weapon_id"]))
	camera = Camera3D.new()
	camera.name = "Camera"
	add_child(camera)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-50, 30, 0)
	add_child(light)
	if show_hud:
		var layer := CanvasLayer.new()
		add_child(layer)
		hud = Label.new()
		hud.position = Vector2(16, 16)
		layer.add_child(hud)
	_sync_scene()


## Keyboard (or autoplay) -> the same command dictionary the reference scenarios use.
## `autoplay_script` uses the scenario format {frame: {"player": command}} (int or string frame keys).
func player_command(frame: int) -> Dictionary:
	var entry = autoplay_script.get(frame, autoplay_script.get(str(frame), null))
	if entry != null:
		return (entry as Dictionary).get("player", {})
	if not autoplay_script.is_empty():
		return {}
	var dir := ""
	if Input.is_action_pressed("ce_souls_forward"):
		dir = "F"
	elif Input.is_action_pressed("ce_souls_back"):
		dir = "B"
	elif Input.is_action_pressed("ce_souls_left"):
		dir = "L"
	elif Input.is_action_pressed("ce_souls_right"):
		dir = "R"
	return {"direction": dir, "light": Input.is_action_just_pressed("ce_souls_light"),
			"heavy": Input.is_action_just_pressed("ce_souls_heavy"),
			"dodge": Input.is_action_just_pressed("ce_souls_dodge"),
			"guard": Input.is_action_pressed("ce_souls_guard")}


func _physics_process(_delta: float) -> void:
	if combat != null and autostep:
		step_once()


## Advance one 60 Hz frame: Sentinel decides, player input is fed (same order as `run_souls_scenario`).
func step_once() -> void:
	combat.feed("opponent", sentinel.decide(combat))
	combat.feed("player", CESoulsCombat.SoulsInput.from_dict(player_command(combat.frame + 1)))
	combat.step()
	frames_stepped += 1
	_sync_scene()


func _on_event(ev: Dictionary) -> void:
	if ev["kind"] != "hit" or combat.hits.is_empty():
		return
	var hit: Dictionary = combat.hits.back()
	var ch: CECharacter = characters.get(hit["defender"])
	if ch != null:
		ch.add_wound_marker(hit["bone_hit"], {"severity": hit["severity"]})


## Canonical (x, y) ground position -> Godot (x, 0, -y); each character faces its opponent (+Z = canonical forward).
func _sync_scene() -> void:
	for fid in characters:
		var f: CESoulsCombat.Fighter = combat.fighters[fid]
		var ch: CECharacter = characters[fid]
		ch.position = Vector3(f.px, 0.0, -f.py)
		var o := combat.nearest_opponent(f)
		if o != null:
			var d := Vector3(o.px - f.px, 0.0, -(o.py - f.py))
			if d.length() > 1e-6:
				ch.rotation.y = atan2(d.x, d.z)
	var p: CECharacter = characters["player"]
	var s: CECharacter = characters["opponent"]
	var back := (p.position - s.position).normalized() if p.position.distance_to(s.position) > 1e-6 else Vector3(0, 0, -1)
	camera.position = p.position + back * 3.0 + Vector3(0, 1.9, 0)
	camera.look_at((p.position + s.position) * 0.5 + Vector3(0, 1.1, 0), Vector3.UP)
	_update_hud()


func hud_text() -> String:
	var lines := PackedStringArray()
	lines.append("Character Engine - Souls-like (frame %d)" % combat.frame)
	for fid in ["player", "opponent"]:
		var f: CESoulsCombat.Fighter = combat.fighters[fid]
		lines.append("%-8s HP %5.1f  ST %5.1f  POISE %4.1f  %-9s %s" % [fid if fid == "player" else "sentinel",
				f.health, f.stamina, f.poise, f.state_name(), f.weapon["weapon_id"]])
	lines.append("W/S/A/D move  J light  K heavy  Space dodge  L guard (hold)  Tab lock-on (always on)")
	return "\n".join(lines)


func _update_hud() -> void:
	if hud != null:
		hud.text = hud_text()
