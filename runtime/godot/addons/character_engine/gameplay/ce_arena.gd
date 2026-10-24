## Playable free-battle arena: floor, two CECharacters, camera, HUD and the shared
## CEShenmueCombat simulation stepped at 60 Hz in _physics_process.
##
## Created from the Character Engine dock ("Create arena") or programmatically:
##   var arena := CEArena.build(CEGameplayData.load_default(), "shenmue")
##   add_child(arena)
## Gameplay styles other than "shenmue" are listed but have no moves yet (planned).
class_name CEArena
extends Node3D

@export var style_id: String = "shenmue"
@export var glb_path: String = "res://assets/human_adult_206_tpose.glb"
@export var player_stature_m: float = 1.80
@export var opponent_stature_m: float = 1.80
@export var start_distance_m: float = 1.6
@export var autoplay_frames: int = 0       # >0: player follows a scripted combo loop (demo / tests)
@export var show_hud: bool = true

var data: CEGameplayData
var combat: CEShenmueCombat
var controllers: Array[CEFighterController] = []
var characters: Dictionary = {}            # fighter_id -> CECharacter
var hud: Label
var frames_stepped := 0
var _built := false

signal fight_finished(summary: Dictionary)


static func build(p_data: CEGameplayData, p_style := "shenmue", p_glb := "res://assets/human_adult_206_tpose.glb") -> CEArena:
	var arena := CEArena.new()
	arena.name = "CEArena"
	arena.data = p_data
	arena.style_id = p_style
	arena.glb_path = p_glb
	return arena


func _ready() -> void:
	if data == null:
		data = CEGameplayData.load_default()
	if not _built:
		_build_scene()


func _build_scene() -> void:
	_built = true
	# Fighters in the canonical frame (Z-up, -Y forward): player at origin facing -Y.
	var player := CEShenmueCombat.Fighter.new("player", Vector3(0, 0, 0), player_stature_m)
	var opponent := CEShenmueCombat.Fighter.new("opponent", Vector3(0, -start_distance_m, 0), opponent_stature_m)
	opponent.facing = Vector3(0, 1, 0)
	combat = CEShenmueCombat.new(data, [player, opponent], style_id)
	combat.hit_landed.connect(_on_hit)

	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(12, 12)
	floor.mesh = plane
	floor.name = "Floor"
	add_child(floor)

	for f in [player, opponent]:
		var ch := CECharacter.new()
		ch.name = "Character_" + f.fighter_id
		ch.glb_path = glb_path
		ch.stature_m = f.stature_m
		add_child(ch)
		characters[f.fighter_id] = ch
		var ctl := CEFighterController.new()
		ctl.name = "Controller_" + f.fighter_id
		ctl.fighter_id = f.fighter_id
		ctl.is_player = f.fighter_id == "player"
		add_child(ctl)
		ctl.setup(combat, f, ch)
		controllers.append(ctl)
	if autoplay_frames > 0:
		controllers[0].autoplay_script = autoplay_script(autoplay_frames)

	var cam := Camera3D.new()
	cam.name = "Camera"
	add_child(cam)
	cam.global_position = Vector3(3.2, 1.7, -start_distance_m * 0.5)
	cam.look_at(Vector3(0, 1.0, -start_distance_m * 0.5), Vector3.UP)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-50, 30, 0)
	add_child(light)

	if show_hud:
		var layer := CanvasLayer.new()
		add_child(layer)
		hud = Label.new()
		hud.position = Vector2(16, 16)
		layer.add_child(hud)
		_update_hud()


## Player script used by demos and tests: jab every 40 frames, front kick 20 frames later.
static func autoplay_script(frames: int) -> Dictionary:
	var out := {}
	for fr in range(1, frames + 1):
		if fr % 40 == 1:
			out[fr] = {"punch": true, "direction": "F"}
		elif fr % 40 == 21:
			out[fr] = {"kick": true}
		elif fr < 40:
			out[fr] = {"direction": "F"}      # close the distance first
	return out


func _physics_process(_delta: float) -> void:
	if combat == null:
		return
	if autoplay_frames > 0 and frames_stepped >= autoplay_frames:
		return
	step_once()
	if autoplay_frames > 0 and frames_stepped == autoplay_frames:
		fight_finished.emit(combat.summary())


## Advance the fight by exactly one 60 Hz frame (also used by headless tests).
func step_once() -> void:
	for ctl in controllers:
		ctl.collect_input()
	combat.step()
	frames_stepped += 1
	_update_hud()


func _on_hit(hit: Dictionary) -> void:
	if hit["blocked"]:
		return
	var ch: CECharacter = characters.get(hit["defender"])
	if ch != null:
		ch.add_wound_marker(hit["bone_hit"], hit["impact"])


func _update_hud() -> void:
	if hud == null:
		return
	var lines := PackedStringArray()
	lines.append("Character Engine - %s (frame %d)" % [data.style(style_id).get("label", style_id), combat.frame])
	for fid in combat.fighters:
		var f: CEShenmueCombat.Fighter = combat.fighters[fid]
		lines.append("%-9s HP %5.1f  %-9s  wounds %d" % [fid, f.health, f.state_name(), f.wounds.size()])
	lines.append("W/S move  J punch  K kick  L throw  Space guard  |  F,F+J elbow  F+K crescent  F+L throw")
	hud.text = "\n".join(lines)
