## Playable Souls-like arena (STYLE-SOULS-001 step 3): player vs Sentinel on the CE-GAME-v1 game rig.
##
## Kept apart from ce_arena.gd (Shenmue arena; the audio branch edits it). Godot only decides state here:
## CESoulsCombat (port of the Python domain) runs at 60 Hz in _physics_process; the characters follow the
## fighter positions and face each other. Animation clips are authored and baked in Blender (step 4); until
## then the HUD shows each fighter's state. Visuals are Workbench-level (plain meshes, flat colours).
## Step 4: CESoulsAnimator plays the Blender-baked placeholder clips (data/souls_clips.glb) by combat state.
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
## Opt-in strike physics (Decisions 58 and 59): fracture, concussion and knockdown on blunt hits (CEStrikePhysics).
@export var strike_physics: bool = false
## false: the arena only advances through step_once() (headless tests).
@export var autostep: bool = true
## Frames of scripted player input (tests / demos); empty = keyboard.
var autoplay_script: Dictionary = {}

var combat: CESoulsCombat
var sentinel: CESoulsCombat.Sentinel
var characters: Dictionary = {}          # fighter_id -> CECharacter
var animators: Dictionary = {}           # fighter_id -> CESoulsAnimator
var _move_start := {"player": -1, "opponent": -1}
var _bars := {}                          # fighter_id -> {hp, st, poise: ProgressBar, state: Label}
const PLAYER_COLOR := Color(0.36, 0.46, 0.62)
const SENTINEL_COLOR := Color(0.62, 0.34, 0.22)
## false: no clip playback (pure state tests).
@export var animate: bool = true
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
	if strike_physics:
		combat.physics = CEStrikePhysics.load_default()
	var player := combat.make_fighter("player", 0.0, 0.0, player_weapon)
	var opponent := combat.make_fighter("opponent", 0.0, -start_distance_m, sentinel_weapon)
	for f in [player, opponent]:
		f.hitboxes = data.hitboxes(f.stature_m)
		combat.fighters[f.fighter_id] = f
	sentinel = CESoulsCombat.Sentinel.new("opponent", combat.t)
	combat.souls_event.connect(_on_event)

	_build_floor()
	for f in [player, opponent]:
		var ch := CECharacter.new()
		ch.name = "Character_" + f.fighter_id
		ch.glb_path = glb_path
		ch.breathing_enabled = false
		add_child(ch)
		characters[f.fighter_id] = ch
		ch.equip_weapon(data.weapon(f.weapon["weapon_id"]))
		ch.attach_body(PLAYER_COLOR if f.fighter_id == "player" else SENTINEL_COLOR)
		if animate:
			var an := CESoulsAnimator.new()
			an.name = "Animator_" + f.fighter_id
			add_child(an)
			if an.setup(ch) == OK:
				animators[f.fighter_id] = an
	camera = Camera3D.new()
	camera.name = "Camera"
	add_child(camera)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-50, 30, 0)
	add_child(light)
	if show_hud:
		_build_hud()
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
	for fid in animators:
		var telegraph: bool = fid == sentinel.fighter_id and sentinel.phase == "telegraph"
		(animators[fid] as CESoulsAnimator).update_from(combat.fighters[fid], combat.frame, _move_start[fid], telegraph)
	_sync_scene()


func _on_event(ev: Dictionary) -> void:
	if ev["kind"] == "move_start":
		_move_start[ev["fighter"]] = int(ev["frame"])
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
	var sep := p.position.distance_to(s.position)
	var back := (p.position - s.position).normalized() if sep > 1e-6 else Vector3(0, 0, -1)
	var side := back.cross(Vector3.UP).normalized()          # over-the-shoulder: both fighters stay in view
	# Pull back and up as the fighters separate so both stay framed.
	camera.position = p.position + back * (2.4 + 0.45 * sep) + side * 1.3 + Vector3(0, 1.6 + 0.15 * sep, 0)
	camera.look_at((p.position + s.position) * 0.5 + Vector3(0, 1.0, 0), Vector3.UP)
	_update_hud()


func hud_text() -> String:
	var lines := PackedStringArray()
	lines.append("Character Engine - Souls-like (frame %d)" % combat.frame)
	for fid in ["player", "opponent"]:
		var f: CESoulsCombat.Fighter = combat.fighters[fid]
		lines.append("%-8s HP %5.1f  ST %5.1f  POISE %4.1f  %-9s %s" % [fid if fid == "player" else "sentinel",
				f.health, f.stamina, f.poise, f.state_name(), f.weapon["weapon_id"]])
	if combat.physics != null and not combat.hits.is_empty() and combat.hits.back().has("physics"):
		var ph: Dictionary = combat.hits.back()["physics"]
		lines.append("last blow: %s %.0f N fracture p%.2f%s  stagger %s%s" % [ph["region"], ph["peak_force_n"],
				ph["fracture_probability"], " BROKEN" if ph["fractured"] else "", ph["stagger"]["level"],
				"  concussion p%.2f" % float(ph["head"]["concussion_probability"]) if ph["head"] != null else ""])
	return "\n".join(lines)


func _update_hud() -> void:
	if hud != null:
		hud.text = hud_text()
	for fid in _bars:
		var f: CESoulsCombat.Fighter = combat.fighters[fid]
		_bars[fid]["hp"].value = f.health
		_bars[fid]["st"].value = f.stamina
		_bars[fid]["poise"].value = f.poise
		_bars[fid]["state"].text = "%s  (%s)" % [f.state_name(), (animators[fid] as CESoulsAnimator).current if animators.has(fid) else "-"]


## Readable floor: flat grey plane, a darker 1 m grid and a lighter ring of the engage range around the centre.
func _build_floor() -> void:
	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(14, 14)
	floor.mesh = plane
	floor.name = "Floor"
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.52, 0.53, 0.5)
	floor.material_override = fm
	add_child(floor)
	var lm := StandardMaterial3D.new()
	lm.albedo_color = Color(0.36, 0.37, 0.35)
	for i in range(-7, 8):
		for along_x in [true, false]:
			var line := MeshInstance3D.new()
			var b := BoxMesh.new()
			b.size = Vector3(14.0, 0.004, 0.02) if along_x else Vector3(0.02, 0.004, 14.0)
			line.mesh = b
			line.material_override = lm
			line.position = Vector3(0, 0.002, i) if along_x else Vector3(i, 0.002, 0)
			floor.add_child(line)
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 2.95
	torus.outer_radius = 3.0
	ring.mesh = torus
	var rm := StandardMaterial3D.new()
	rm.albedo_color = Color(0.75, 0.74, 0.68)
	ring.material_override = rm
	ring.position = Vector3(0, 0.003, -start_distance_m * 0.5)
	ring.scale = Vector3(1, 0.05, 1)
	floor.add_child(ring)


## HUD: one panel per fighter with health / stamina / poise bars (flat colours, no textures) + state and clip.
func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = Label.new()                       # text summary (kept for tests and screenshots)
	hud.position = Vector2(16, 600)
	hud.add_theme_font_size_override("font_size", 12)
	layer.add_child(hud)
	var x := 16
	for fid in ["player", "opponent"]:
		var box := VBoxContainer.new()
		box.position = Vector2(x, 16)
		box.custom_minimum_size = Vector2(300, 0)
		layer.add_child(box)
		var title := Label.new()
		title.text = "PLAYER" if fid == "player" else "SENTINEL"
		box.add_child(title)
		var bars := {}
		for spec in [["hp", "HP", 100.0, Color(0.75, 0.2, 0.2)], ["st", "STAMINA", float(combat.t["stamina_max"]), Color(0.3, 0.7, 0.3)],
				["poise", "POISE", float(combat.t["poise_max"]), Color(0.85, 0.7, 0.25)]]:
			var bar := ProgressBar.new()
			bar.max_value = spec[2]
			bar.custom_minimum_size = Vector2(300, 14)
			bar.show_percentage = false
			var fill := StyleBoxFlat.new()
			fill.bg_color = spec[3]
			var bg := StyleBoxFlat.new()
			bg.bg_color = Color(0.12, 0.12, 0.12, 0.8)
			bar.add_theme_stylebox_override("fill", fill)
			bar.add_theme_stylebox_override("background", bg)
			bar.tooltip_text = spec[1]
			box.add_child(bar)
			bars[spec[0]] = bar
		var st := Label.new()
		box.add_child(st)
		bars["state"] = st
		_bars[fid] = bars
		x += 1280 - 32 - 300
	var keys := Label.new()
	keys.text = "W/S/A/D move   J light   K heavy   Space dodge   L guard (hold)   Tab lock-on (always on)"
	keys.position = Vector2(16, 690)
	keys.add_theme_font_size_override("font_size", 12)
	layer.add_child(keys)
