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
var weapon_attachment: BoneAttachment3D = null
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


## Mount a PLACEHOLDER weapon (plain box, flat colour; no textures or shaders) on its grip bone.
## `weapon` is an entry of CEGameplayData.weapons(). The box is centred on the grip point (middle of
## the grip bone; the socket's 2 cm palmar offset is not applied) and runs along the grip channel of
## the fist, little-finger side -> index side (Decision 48), taken from the rest positions of
## METACARPAL_5 -> METACARPAL_2 on the grip side. Returns null for "unarmed" (nothing to show).
func equip_weapon(weapon: Dictionary) -> BoneAttachment3D:
	unequip_weapon()
	var grip: String = weapon.get("grip_bone", "")
	if skeleton == null or not has_bone(grip) or float(weapon.get("length_m", 0.0)) <= 0.0:
		return null
	var side := grip.substr(grip.length() - 1)
	var idx := skeleton.find_bone(grip)
	var rest := skeleton.global_transform * skeleton.get_bone_global_rest(idx)
	var children := skeleton.get_bone_children(idx)
	var tip := rest.origin if children.is_empty() else skeleton.global_transform * skeleton.get_bone_global_rest(children[0]).origin
	var grip_point := (rest.origin + tip) * 0.5
	var axis := (bone_rest_position("METACARPAL_2_" + side) - bone_rest_position("METACARPAL_5_" + side)).normalized()
	var length := float(weapon["length_m"])   # world metres: rest.affine_inverse() below cancels the stature scale
	var centre := grip_point + axis * (0.5 - float(weapon.get("grip_fraction", 0.5))) * length
	var att := BoneAttachment3D.new()
	att.bone_name = grip
	att.name = "Weapon_%s" % weapon.get("weapon_id", "weapon")
	skeleton.add_child(att)
	var mesh := MeshInstance3D.new()
	mesh.name = "PLACEHOLDER"
	var box := BoxMesh.new()
	var w := maxf(float(weapon.get("width_m", 0.02)), 0.005)
	box.size = Vector3(w, length, w * (0.25 if weapon.get("category", "") == "blade" else 1.0))
	mesh.mesh = box
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.55, 0.4, 0.25) if weapon.get("category", "") == "blunt" else Color(0.75, 0.78, 0.8)
	mesh.material_override = mat
	# Local transform relative to the grip bone's rest frame: box +Y along the grip axis.
	var y := axis
	var x := y.cross(Vector3.UP if absf(y.dot(Vector3.UP)) < 0.9 else Vector3.FORWARD).normalized()
	var world := Transform3D(Basis(x, y, x.cross(y)), centre)
	mesh.transform = rest.affine_inverse() * world
	att.add_child(mesh)
	att.set_meta("ce_weapon", weapon)
	weapon_attachment = att
	return att


func unequip_weapon() -> void:
	if weapon_attachment != null:
		weapon_attachment.queue_free()
		weapon_attachment = null
