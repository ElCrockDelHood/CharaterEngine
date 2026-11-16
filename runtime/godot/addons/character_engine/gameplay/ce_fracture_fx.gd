## Bone fragments of one fractured blow, drawn from a `ce-fracture/1` event (Decision 80, A33): hard-edged shards, like
## broken glass, instead of a blurred or sliding bone. Purely visual: it reads the event and never touches the fight.
##
## Few reused pieces: one shard mesh per kind (shared by every effect), one MultiMesh per kind, at most MAX_FRAGMENTS.
## The event comes from data/fracture_events.json (Python decides, tests/make_fracture_events.py). `pose_at` is a pure
## function of time, so the same event always draws the same shards.
##
## Viewer choices, ASSUMED and not physics (the event has "no drag in tissue"): each shard starts at the event's velocity
## and spin and slows down exponentially over a stopping distance of at most MAX_TRAVEL_M, so it stays around the bone;
## SLOW_MOTION stretches those few milliseconds so the eye can follow them; shards are drawn over the opaque block body;
## VISUAL_SCALE enlarges them. The long side of a shard follows the pattern (ribs across the body, long bones along it,
## the rest radial), because the event gives no orientation.
class_name CEFractureFx
extends Node3D

const TABLE_PATH := "res://addons/character_engine/data/fracture_events.json"
const SCHEMA := "ce-fracture/1"
const MAX_FRAGMENTS := 24
const MAX_TRAVEL_M := 0.07
const DRAG_TIME_S := 0.006
const SLOW_MOTION := 0.05
const HOLD_S := 1.6                      # real seconds on screen after the blow
const VISUAL_SCALE := 1.5
const BONE_COLOR := Color(0.93, 0.89, 0.78)

static var _meshes: Dictionary = {}      # kind -> ArrayMesh, shared by every effect
static var _material: StandardMaterial3D = null

var event: Dictionary = {}
var fragment_count := 0
var elapsed := 0.0                       # real seconds since the blow
var _layers: Array = []                  # [[MultiMesh, fragments of that kind], ...]


static func load_table(p := TABLE_PATH) -> Dictionary:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(p))
	if not (parsed is Dictionary) or parsed.get("schema") != SCHEMA:
		push_error("CEFractureFx: no %s table at %s" % [SCHEMA, p])
		return {}
	return parsed


## Canonical (Z-up, -Y forward) to the skeleton space of the GLB (Y-up, +Z forward).
static func canonical_to_skeleton(v: Array) -> Vector3:
	return Vector3(float(v[0]), float(v[2]), -float(v[1]))


## Attach an effect to `ch` at the impact of `ev`, on the bone that carries it (the shards stay with the body).
## Returns null when the event has no fragments or the bone is missing.
static func spawn_on(ch: CECharacter, ev: Dictionary) -> CEFractureFx:
	var carrier := ch.carrier_bone(str(ev.get("bone", "")))
	if carrier == "" or (ev.get("fragments", []) as Array).is_empty():
		return null
	var att := BoneAttachment3D.new()
	att.name = "Fracture_%s" % ev["bone"]
	att.bone_name = carrier
	ch.skeleton.add_child(att)
	var fx := CEFractureFx.new()
	fx.name = "CEFractureFx"
	var rest := ch.skeleton.get_bone_global_rest(ch.skeleton.find_bone(carrier))
	fx.transform = rest.affine_inverse() * frame_transform(ev)
	att.add_child(fx)
	fx.setup(ev)
	return fx


## The event's local frame (x lateral, y along the segment, z inward) in skeleton space, at the impact point.
static func frame_transform(ev: Dictionary) -> Transform3D:
	var fr: Dictionary = ev["frame"]
	return Transform3D(Basis(canonical_to_skeleton(fr["x"]), canonical_to_skeleton(fr["y"]), canonical_to_skeleton(fr["z"])),
			canonical_to_skeleton(ev["impact_point_m"]))


## Stopping time and distance of a shard of speed `speed`: starts at that speed, never travels beyond MAX_TRAVEL_M.
static func _stop_time(speed: float) -> float:
	var natural := speed * DRAG_TIME_S
	return MAX_TRAVEL_M * (1.0 - exp(-natural / MAX_TRAVEL_M)) / speed if speed > 1e-9 else DRAG_TIME_S


## Pose of a fragment `t` seconds of event time after the blow, in the event's local frame (pure).
static func pose_at(fragment: Dictionary, pattern: String, thickness_m: float, t: float) -> Transform3D:
	var p0 := _vec(fragment["position_m"])
	var v := _vec(fragment["velocity_m_s"])
	var tau := _stop_time(v.length())
	var s := tau * (1.0 - exp(-t / tau))         # integral of exp(-t / tau): velocity at t = 0 is exactly v
	var size := float(fragment["size_m"]) * VISUAL_SCALE
	var root_aspect := sqrt(maxf(float(fragment["aspect"]), 1.0))   # same plate area as size x size
	var width := size / root_aspect
	var length := size * root_aspect
	var yaw := _long_side_angle(p0, pattern)
	var axis := _vec(fragment["spin_axis"]).normalized()
	var spin := Basis(axis, float(fragment["angular_speed_rad_s"]) * s) if axis.length() > 0.5 else Basis.IDENTITY
	var scale_b := Basis.from_scale(Vector3(length, width, maxf(thickness_m, 0.002) * VISUAL_SCALE))
	return Transform3D(spin * Basis(Vector3(0, 0, 1), yaw) * scale_b, p0 + v * s)


static func _vec(v: Array) -> Vector3:
	return Vector3(float(v[0]), float(v[1]), float(v[2]))


static func _long_side_angle(p0: Vector3, pattern: String) -> float:
	match pattern:
		"transverse_ribs":
			return 0.0
		"butterfly":
			return PI * 0.5
	return atan2(p0.y, p0.x) if absf(p0.x) + absf(p0.y) > 1e-6 else 0.0


func setup(ev: Dictionary) -> void:
	event = ev
	var groups := {}
	var frags: Array = ev["fragments"]
	if frags.size() > MAX_FRAGMENTS:
		push_warning("CEFractureFx: %d fragments, drawing %d" % [frags.size(), MAX_FRAGMENTS])
		frags = frags.slice(0, MAX_FRAGMENTS)
	fragment_count = frags.size()
	for f in frags:
		if not groups.has(f["kind"]):
			groups[f["kind"]] = []
		groups[f["kind"]].append(f)
	for kind in groups:
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_colors = true
		mm.mesh = _shard_mesh(kind)
		mm.instance_count = (groups[kind] as Array).size()
		for i in range(mm.instance_count):
			var shade := 0.82 + 0.18 * float((int(groups[kind][i]["id"]) * 7) % 5) / 4.0
			mm.set_instance_color(i, Color(BONE_COLOR.r * shade, BONE_COLOR.g * shade, BONE_COLOR.b * shade))
		var inst := MultiMeshInstance3D.new()
		inst.multimesh = mm
		inst.material_override = _shard_material()
		inst.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(inst)
		_layers.append([mm, groups[kind]])
	_apply()


## Advance the effect (real seconds); frees its attachment when the time is over.
func advance(delta: float) -> void:
	elapsed += delta
	if elapsed >= HOLD_S:
		remove()
		return
	_apply()


func remove() -> void:
	var parent := get_parent()
	if parent is BoneAttachment3D:
		parent.queue_free()
	else:
		queue_free()


func _process(delta: float) -> void:
	advance(delta)


func _apply() -> void:
	var t := elapsed * SLOW_MOTION
	var pattern := str(event.get("pattern", ""))
	var thick := float(event.get("shell_thickness_m", 0.005))
	for layer in _layers:
		var mm: MultiMesh = layer[0]
		for i in range(mm.instance_count):
			mm.set_instance_transform(i, pose_at(layer[1][i], pattern, thick, t))


static func _shard_material() -> StandardMaterial3D:
	if _material == null:
		_material = StandardMaterial3D.new()
		_material.vertex_color_use_as_albedo = true
		_material.roughness = 0.35
		_material.emission_enabled = true
		_material.emission = BONE_COLOR * 0.25
		_material.cull_mode = BaseMaterial3D.CULL_DISABLED
		_material.no_depth_test = true           # same as the wound markers: visible through the block body
		_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		_material.render_priority = 2
	return _material


## Unit plate with a jagged outline and flat faces: every face has its own normals, so the edges stay hard.
static func _shard_mesh(kind: String) -> ArrayMesh:
	if _meshes.has(kind):
		return _meshes[kind]
	var outline: PackedVector2Array
	if kind == "wedge":
		outline = PackedVector2Array([Vector2(-0.5, -0.45), Vector2(0.5, -0.5), Vector2(0.08, 0.5)])
	else:
		outline = PackedVector2Array([Vector2(-0.5, -0.18), Vector2(-0.2, -0.5), Vector2(0.12, -0.32), Vector2(0.5, -0.42),
				Vector2(0.38, 0.1), Vector2(0.5, 0.42), Vector2(-0.06, 0.5), Vector2(-0.34, 0.26)])
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var tris: Array = []
	var n := outline.size()
	for i in range(1, n - 1):                    # both plates, fan from the first corner (the outlines are star-shaped enough)
		tris.append([Vector3(outline[0].x, outline[0].y, 0.5), Vector3(outline[i].x, outline[i].y, 0.5), Vector3(outline[i + 1].x, outline[i + 1].y, 0.5)])
		tris.append([Vector3(outline[0].x, outline[0].y, -0.5), Vector3(outline[i + 1].x, outline[i + 1].y, -0.5), Vector3(outline[i].x, outline[i].y, -0.5)])
	for i in range(n):                           # broken edge
		var a := outline[i]
		var b := outline[(i + 1) % n]
		tris.append([Vector3(a.x, a.y, 0.5), Vector3(a.x, a.y, -0.5), Vector3(b.x, b.y, 0.5)])
		tris.append([Vector3(b.x, b.y, 0.5), Vector3(a.x, a.y, -0.5), Vector3(b.x, b.y, -0.5)])
	for tri in tris:
		var nrm: Vector3 = (tri[1] - tri[0]).cross(tri[2] - tri[0]).normalized()
		for vtx in tri:
			verts.append(vtx)
			normals.append(nrm)
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	_meshes[kind] = mesh
	return mesh
