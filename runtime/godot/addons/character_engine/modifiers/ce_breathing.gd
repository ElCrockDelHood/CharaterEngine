## Breathing layer for the canonical skeleton: a sinusoidal thoracic expansion applied on
## top of any animation through Godot's SkeletonModifier3D pipeline.
##
## Mirrors the Blender addon's CTRL-breath drivers (STERNUM + ribs translate forward).
## Runtime gameplay layer only: cinematics keep the baked animation untouched.
## Godot forward for the canonical -Y axis is +Z (Y-up conversion), so the offset is +Z.
@tool
class_name CEBreathing
extends SkeletonModifier3D

const STERNUM_BONE := "STERNUM"
const RIB_PREFIX := "RIB_"

## Peak forward displacement of the sternum, metres, at amplitude 1.0.
@export var sternum_travel_m: float = 0.012
@export var amplitude: float = 1.0
@export var rate_hz: float = 0.25
@export var rib_gain: float = 0.6

var phase_time: float = 0.0
var last_offset_m: float = 0.0
var _bones: Array = []      # [idx, gain, parent_inverse_basis]
var _resolved := false


func _resolve() -> void:
	_bones.clear()
	var sk := get_skeleton()
	if sk == null:
		return
	for i in range(sk.get_bone_count()):
		var n := sk.get_bone_name(i)
		var gain := 0.0
		if n == STERNUM_BONE:
			gain = 1.0
		elif n.begins_with(RIB_PREFIX):
			gain = rib_gain
		if gain > 0.0:
			var parent := sk.get_bone_parent(i)
			var pbasis := sk.get_bone_global_rest(parent).basis if parent >= 0 else Basis.IDENTITY
			_bones.append([i, gain, pbasis.inverse()])
	_resolved = true


func _process_modification() -> void:
	var sk := get_skeleton()
	if sk == null:
		return
	if not _resolved:
		_resolve()
	phase_time += get_process_delta_time()
	last_offset_m = sternum_travel_m * amplitude * sin(TAU * rate_hz * phase_time)
	for entry in _bones:
		var idx: int = entry[0]
		var gain: float = entry[1]
		var inv: Basis = entry[2]
		var forward_local: Vector3 = inv * Vector3(0, 0, last_offset_m * gain)
		# Position only (rotations from animation/mocap are kept); rest-relative so it never drifts.
		sk.set_bone_pose_position(idx, sk.get_bone_rest(idx).origin + forward_local)
