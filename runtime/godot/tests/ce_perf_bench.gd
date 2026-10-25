## Character Engine - Godot hardware benchmark (RIG-GAME-001 step 4).
##
##   godot --path runtime/godot --resolution 1280x720 --script res://tests/ce_perf_bench.gd -- --report <file.json>
##
## Must run WINDOWED (headless uses a dummy renderer). Vsync off, uncapped FPS. Scenarios:
##   - bones: canonical GLB (208) vs game GLB (66), 1 / 4 / 8 characters; every character carries the same
##     procedural skinned body mesh (BODY_VERTS vertices, 1 influence each, spread over all bones), so the
##     vertex work is equal and the difference is the bone count (skeleton update + skin matrices);
##     12 limb / spine bones are animated per character in both rigs (same motion);
##   - face: 4 game-rig characters + a procedural face mesh (FACE_GRID^2 vertices) on the head with
##     0 / 20 / 52 blend shapes, all weights animated every frame.
## Per scenario: WARMUP frames discarded, then FRAMES frames timed (wall clock between frames, which includes
## the GPU wait of the Compatibility renderer). The meshes are synthetic load,
## not character art; numbers compare configurations on this machine, they are not a game budget.
extends SceneTree

const WARMUP := 60
const FRAMES := 300
const BODY_VERTS := 7998   # triangle list without index: multiple of 3
const FACE_GRID := 40
const ANIM_CANON := ["HUMERUS_L", "HUMERUS_R", "RADIUS_L", "RADIUS_R", "FEMUR_L", "FEMUR_R", "TIBIA_L", "TIBIA_R",
		"LUMBAR_3", "THORACIC_6", "CERVICAL_4", "CLAVICLE_L"]
const ANIM_GAME := ["upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r", "thigh_l", "thigh_r", "calf_l", "calf_r",
		"spine_01", "spine_03", "neck_01", "clavicle_l"]
const CANON_GLB := "res://assets/human_adult_206_tpose.glb"
const GAME_GLB := "res://assets/human_game_v1_tpose.glb"

var report_path := ""


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	for i in range(args.size()):
		if args[i] == "--report" and i + 1 < args.size():
			report_path = args[i + 1]
	if report_path == "":
		report_path = ProjectSettings.globalize_path("res://").path_join("../../builds/tests/godot_perf.json")
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	var bench := Bench.new()
	bench.report_path = report_path
	root.add_child(bench)


class Bench extends Node:
	var report_path := ""
	var results: Array = []

	func _ready() -> void:
		await get_tree().process_frame
		print("== CE perf bench: Godot %s, %s, adapter '%s' (%s), driver %s, window %s ==" % [
				Engine.get_version_info()["string"], RenderingServer.get_current_rendering_method(),
				RenderingServer.get_video_adapter_name(), RenderingServer.get_video_adapter_vendor(),
				RenderingServer.get_video_adapter_api_version(), DisplayServer.window_get_size()])
		var cam := Camera3D.new()
		add_child(cam)
		cam.position = Vector3(0, 1.2, 6.0)
		cam.look_at(Vector3(0, 1.0, 0))
		var light := DirectionalLight3D.new()
		light.rotation_degrees = Vector3(-45, 30, 0)
		add_child(light)
		for n in [1, 4, 8]:
			for rig in ["canonical", "game"]:
				await run_scenario("%s_x%d" % [rig, n], rig, n, -1)
		for k in [0, 20, 52]:
			await run_scenario("game_x4_face_%d_shapes" % k, "game", 4, k)
		finish()

	func run_scenario(sid: String, rig: String, count: int, face_shapes: int) -> void:
		var stage := Node3D.new()
		add_child(stage)
		var chars: Array = []
		var faces: Array = []
		for i in range(count):
			var ch := CECharacter.new()
			ch.glb_path = CANON_GLB if rig == "canonical" else GAME_GLB
			ch.breathing_enabled = false
			ch.position = Vector3((i % 4 - 1.5) * 1.6, 0, -floorf(i / 4.0) * 1.5)
			stage.add_child(ch)
			_add_body_mesh(ch)
			chars.append(ch)
			if face_shapes >= 0:
				faces.append(_add_face(ch, face_shapes))
		var anim: Array = ANIM_CANON if rig == "canonical" else ANIM_GAME
		var times: Array = []
		var t_prev := Time.get_ticks_usec()
		for f in range(WARMUP + FRAMES):
			var phase := float(f) / 60.0
			for ch in chars:
				var sk: Skeleton3D = ch.skeleton
				for j in range(anim.size()):
					var idx := sk.find_bone(anim[j])
					if idx >= 0:
						sk.set_bone_pose_rotation(idx, sk.get_bone_rest(idx).basis.get_rotation_quaternion()
								* Quaternion(Vector3(1, 0, 0), 0.4 * sin(TAU * 0.5 * phase + j)))
			for face in faces:
				var mi: MeshInstance3D = face
				for s in range(face_shapes):
					mi.set_blend_shape_value(s, 0.5 + 0.5 * sin(TAU * 0.7 * phase + s * 0.37))
			await get_tree().process_frame
			var t := Time.get_ticks_usec()
			if f >= WARMUP:
				times.append(float(t - t_prev) / 1000.0)
			t_prev = t
		times.sort()
		var avg := 0.0
		for v in times:
			avg += v
		avg /= times.size()
		var bones: int = (chars[0] as CECharacter).bone_count()
		var r := {"scenario": sid, "rig": rig, "characters": count, "bones_per_character": bones,
				"face_shapes": face_shapes, "frames": FRAMES, "avg_ms": snappedf(avg, 0.001),
				"p95_ms": snappedf(times[int(times.size() * 0.95)], 0.001), "fps": snappedf(1000.0 / avg, 0.1),
				"draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)}
		results.append(r)
		print("  %-26s bones %3d x%d  avg %7.3f ms  p95 %7.3f ms  %6.1f fps  draws %d" % [
				sid, bones, count, r["avg_ms"], r["p95_ms"], r["fps"], r["draw_calls"]])
		stage.queue_free()
		await get_tree().process_frame

	## Procedural skinned body: BODY_VERTS small triangles, vertex v bound 100 % to bone v % bone_count.
	func _add_body_mesh(ch: CECharacter) -> void:
		var sk := ch.skeleton
		var n := sk.get_bone_count()
		var verts := PackedVector3Array()
		var bones := PackedInt32Array()
		var weights := PackedFloat32Array()
		for v in range(BODY_VERTS):
			var b := v % n
			var o := sk.get_bone_global_rest(b).origin
			var k := floori(float(v) / n)
			verts.append(o + Vector3(0.01 * sin(k * 1.7), 0.01 * cos(k * 2.3), 0.01 * sin(k * 0.9 + v % 3)))
			bones.append_array([b, 0, 0, 0])
			weights.append_array([1.0, 0.0, 0.0, 0.0])
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = verts
		arrays[Mesh.ARRAY_BONES] = bones
		arrays[Mesh.ARRAY_WEIGHTS] = weights
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		var skin := Skin.new()
		for b in range(n):
			skin.add_named_bind(sk.get_bone_name(b), sk.get_bone_global_rest(b).affine_inverse())
		var mi := MeshInstance3D.new()
		mi.mesh = mesh
		sk.add_child(mi)
		mi.skeleton = mi.get_path_to(sk)
		mi.skin = skin

	## Procedural face: FACE_GRID x FACE_GRID grid on the head with `shapes` blend shapes.
	func _add_face(ch: CECharacter, shapes: int) -> MeshInstance3D:
		var verts := PackedVector3Array()
		var idx := PackedInt32Array()
		for y in range(FACE_GRID):
			for x in range(FACE_GRID):
				verts.append(Vector3((x / float(FACE_GRID - 1) - 0.5) * 0.16, (y / float(FACE_GRID - 1) - 0.5) * 0.2, 0.09))
		for y in range(FACE_GRID - 1):
			for x in range(FACE_GRID - 1):
				var a := y * FACE_GRID + x
				idx.append_array([a, a + 1, a + FACE_GRID, a + 1, a + FACE_GRID + 1, a + FACE_GRID])
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = verts
		arrays[Mesh.ARRAY_INDEX] = idx
		var blend := []
		var mesh := ArrayMesh.new()
		for s in range(shapes):
			mesh.add_blend_shape("shape_%02d" % s)
			var sv := PackedVector3Array()
			for i in range(verts.size()):
				var w := maxf(0.0, sin(i * 0.013 + s * 0.71))
				sv.append(verts[i] + Vector3(0, 0, 0.01 * w))
			var sa := []
			sa.resize(Mesh.ARRAY_MAX)
			sa[Mesh.ARRAY_VERTEX] = sv
			blend.append(sa)
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, blend)
		var att := BoneAttachment3D.new()
		att.bone_name = "head"
		ch.skeleton.add_child(att)
		var mi := MeshInstance3D.new()
		mi.mesh = mesh
		att.add_child(mi)
		return mi

	func finish() -> void:
		var data := {"engine": "godot", "godot_version": Engine.get_version_info()["string"],
				"rendering_method": RenderingServer.get_current_rendering_method(),
				"adapter": RenderingServer.get_video_adapter_name(), "vendor": RenderingServer.get_video_adapter_vendor(),
				"api": RenderingServer.get_video_adapter_api_version(), "window": str(DisplayServer.window_get_size()),
				"warmup_frames": WARMUP, "body_verts": BODY_VERTS, "face_verts": FACE_GRID * FACE_GRID,
				"results": results}
		DirAccess.make_dir_recursive_absolute(report_path.get_base_dir())
		var f := FileAccess.open(report_path, FileAccess.WRITE)
		if f:
			f.store_string(JSON.stringify(data, "  "))
			f.close()
		print("report: " + report_path)
		print("== perf bench done: %d scenarios ==" % results.size())
		get_tree().quit(0)
