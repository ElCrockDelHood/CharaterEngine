## A Character Engine character in Godot: loads a canonical skeleton GLB (anatomical or
## T-pose, exported by `scripts/export_gltf.py`), exposes the Skeleton3D, scales to the
## requested stature and hosts runtime layers (breathing modifier, wound markers).
##
## Godot consumes the exported asset only; it never touches the Python domain.
## Coordinate note: the GLB is Y-up. Canonical (x, y, z) -> Godot (x, z, -y), so canonical
## forward (-Y) is Godot +Z.
@tool
class_name CECharacter
extends Node3D

const EXPECTED_BONES := 208
const BASE_STATURE_M := 1.80
const SEVERITY_COLORS := [Color.GRAY, Color(0.2, 0.8, 0.2), Color(0.9, 0.9, 0.1), Color(1.0, 0.6, 0.0),
		Color(1.0, 0.2, 0.0), Color(0.7, 0.0, 0.1), Color(0.1, 0.0, 0.0)]

@export_file("*.glb", "*.gltf") var glb_path: String = "res://assets/human_adult_206_tpose.glb"
@export var stature_m: float = 1.80:
	set(v):
		stature_m = v
		_apply_stature()
@export var breathing_enabled: bool = true
@export var breathing_amplitude: float = 1.0
@export var breathing_rate_hz: float = 0.25

var skeleton: Skeleton3D
var breathing: CEBreathing
var wound_markers: Array[Node3D] = []
var load_error: String = ""
var _scene_root: Node


func _ready() -> void:
	if skeleton == null and glb_path != "":
		load_glb(glb_path)


## Load a GLB at runtime with GLTFDocument (no import step required).
func load_glb(path: String) -> Error:
	load_error = ""
	if _scene_root != null:
		_scene_root.queue_free()
		_scene_root = null
		skeleton = null
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(path, state)
	if err != OK:
		load_error = "append_from_file(%s): %s" % [path, error_string(err)]
		push_error("CECharacter: " + load_error)
		return err
	var root := doc.generate_scene(state)
	if root == null:
		load_error = "generate_scene returned null"
		return ERR_CANT_CREATE
	add_child(root)
	_scene_root = root
	skeleton = find_skeleton(root)
	if skeleton == null:
		load_error = "no Skeleton3D in %s" % path
		return ERR_INVALID_DATA
	_apply_stature()
	if breathing_enabled:
		_install_breathing()
	return OK


static func find_skeleton(node: Node) -> Skeleton3D:
	if node is Skeleton3D:
		return node
	for child in node.get_children():
		var found := find_skeleton(child)
		if found != null:
			return found
	return null


func _apply_stature() -> void:
	if _scene_root != null:
		var k := stature_m / BASE_STATURE_M
		_scene_root.scale = Vector3(k, k, k)


func _install_breathing() -> void:
	if skeleton == null:
		return
	breathing = CEBreathing.new()
	breathing.name = "CEBreathing"
	breathing.amplitude = breathing_amplitude
	breathing.rate_hz = breathing_rate_hz
	skeleton.add_child(breathing)


func bone_count() -> int:
	return skeleton.get_bone_count() if skeleton else 0


func has_bone(bone: String) -> bool:
	return skeleton != null and skeleton.find_bone(bone) >= 0


## Global position of a canonical bone head (current pose, modifiers included).
func bone_global_position(bone: String) -> Vector3:
	var idx := skeleton.find_bone(bone)
	if idx < 0:
		return global_position
	return skeleton.global_transform * skeleton.get_bone_global_pose(idx).origin


## Global rest position of a canonical bone head.
func bone_rest_position(bone: String) -> Vector3:
	var idx := skeleton.find_bone(bone)
	if idx < 0:
		return global_position
	return skeleton.global_transform * skeleton.get_bone_global_rest(idx).origin


## Height of the rest skeleton along Godot +Y in metres (after stature scaling).
func height_m() -> float:
	if skeleton == null:
		return 0.0
	var lo := INF
	var hi := -INF
	for i in range(skeleton.get_bone_count()):
		var y := (skeleton.global_transform * skeleton.get_bone_global_rest(i).origin).y
		lo = minf(lo, y)
		hi = maxf(hi, y)
	return hi - lo


## Attach a severity-coloured marker at `bone` (impact = entry of the gameplay table).
func add_wound_marker(bone: String, impact: Dictionary) -> Node3D:
	if skeleton == null or not has_bone(bone):
		return null
	var att := BoneAttachment3D.new()
	att.bone_name = bone
	att.name = "Wound_%s_%d" % [bone, wound_markers.size()]
	skeleton.add_child(att)
	var mesh := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	var sev := clampi(int(impact.get("severity", 1)), 0, 6)
	sphere.radius = 0.02 + 0.008 * sev
	sphere.height = sphere.radius * 2.0
	mesh.mesh = sphere
	var mat := StandardMaterial3D.new()
	mat.albedo_color = SEVERITY_COLORS[sev]
	mesh.material_override = mat
	att.add_child(mesh)
	att.set_meta("ce_impact", impact)
	wound_markers.append(att)
	return att


func clear_wounds() -> void:
	for m in wound_markers:
		m.queue_free()
	wound_markers.clear()
