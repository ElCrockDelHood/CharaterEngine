## Demo of the bone fragments (fracture_demo.tscn). Run it, or record it with Godot's movie writer:
##
##   godot --path runtime/godot res://fracture_demo.tscn
##   godot --path runtime/godot res://fracture_demo.tscn --fixed-fps 30 --write-movie builds/fracture_demo.avi
##
## Three still blows, one per pattern (ribs, long bone, skull with A33's heavy test blow, not a gameplay move), then a
## live exchange of blows with strike physics on. Quits at the end of the script.
extends Node3D

const SHOTS := [
	{"at": 0.5, "key": "unarmed_heavy|thorax", "look": Vector3(0.0, 1.35, 0.0), "dist": 0.75, "label": "Costillas: piezas largas"},
	{"at": 3.0, "key": "unarmed_heavy|thigh", "look": Vector3(0.1, 0.75, 0.0), "dist": 0.75, "label": "Fémur: cuña y piezas"},
	{"at": 5.5, "key": "test_heavy_blow|head", "look": Vector3(0.0, 1.65, 0.0), "dist": 0.7, "label": "Cráneo: golpe de prueba, no es de juego"},
]
const FIGHT_AT := 8.0
const END_AT := 15.0

var arena: CESoulsArena
var table: Dictionary
var cam: Camera3D
var title: Label
var clock := 0.0
var next_shot := 0
var fighting := false
var clearance := {"frames": 0, "turned": 0, "still_inside": 0, "worst_m": 0.0}


func _ready() -> void:
	table = CEFractureFx.load_table()
	arena = CESoulsArena.build(CEGameplayData.load_default())
	arena.autostep = false
	arena.strike_physics = true
	arena.start_distance_m = 1.2
	var script := {}
	for f in range(30, 420, 70):              # the player presses light every 70 frames
		script[f] = {"player": {"light": true}}
	arena.autoplay_script = script
	add_child(arena)
	for fid in arena.animators:               # idle clip from the start, not the rest T-pose
		(arena.animators[fid] as CESoulsAnimator).update_from(arena.combat.fighters[fid], 0, 0)
	cam = Camera3D.new()
	add_child(cam)
	cam.current = true
	var fill := DirectionalLight3D.new()      # the camera looks at the side the arena's light leaves dark
	fill.rotation_degrees = Vector3(-25, 200, 0)
	fill.light_energy = 0.7
	add_child(fill)
	arena.combat.souls_event.connect(func(ev: Dictionary) -> void:
		if ev["kind"] == "fracture":
			print("fracture at clock %.2f s: %s %s" % [clock, ev["fighter"], ev["detail"]]))
	var layer := CanvasLayer.new()
	add_child(layer)
	title = Label.new()
	title.position = Vector2(20, 165)
	title.add_theme_font_size_override("font_size", 26)
	layer.add_child(title)
	_aim(Vector3(0.0, 1.2, 0.0), 2.0)


func _aim(look: Vector3, dist: float) -> void:
	var ch: CECharacter = arena.characters["opponent"]
	var target := ch.global_position + look
	cam.global_position = target + (ch.global_transform.basis.z.normalized() + Vector3(0.6, 0.15, 0.0)).normalized() * dist
	cam.look_at(target, Vector3.UP)


## Fight framing: both fighters in view from the side, the camera at FIGHT_CAM_M from their midpoint.
const FIGHT_CAM_M := 3.4


func _aim_fight() -> void:
	var a: Vector3 = (arena.characters["player"] as CECharacter).global_position
	var b: Vector3 = (arena.characters["opponent"] as CECharacter).global_position
	var mid := (a + b) * 0.5 + Vector3(0.0, 1.1, 0.0)
	var across := (b - a).cross(Vector3.UP).normalized()
	cam.global_position = mid + across * FIGHT_CAM_M + Vector3(0.0, 0.5, 0.0)
	cam.look_at(mid, Vector3.UP)


func _process(delta: float) -> void:
	clock += delta
	if next_shot < SHOTS.size() and clock >= float(SHOTS[next_shot]["at"]):
		var s: Dictionary = SHOTS[next_shot]
		_aim(s["look"], s["dist"])
		title.text = s["label"]
		CEFractureFx.spawn_on(arena.characters["opponent"], table["events"][s["key"]])
		next_shot += 1
	if not fighting and clock >= FIGHT_AT:
		fighting = true
		arena.autostep = true
		title.text = "Pelea: física de golpe activada"
	if fighting:
		_aim_fight()
		for fid in arena.characters:
			var others: Array = []
			for o in arena.characters:
				if o != fid:
					others.append(arena.characters[o])
			var left := CEWeaponClearance.residual(arena.characters[fid], others)
			clearance["frames"] += 1
			clearance["turned"] += 1 if float(arena.last_clearance_deg.get(fid, 0.0)) > 0.0 else 0
			clearance["still_inside"] += 1 if left > 0.005 else 0
			clearance["worst_m"] = maxf(clearance["worst_m"], left)
	if clock >= END_AT:
		print("weapon clearance: %s" % clearance)
		get_tree().quit()
