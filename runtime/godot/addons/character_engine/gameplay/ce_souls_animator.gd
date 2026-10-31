## Plays the Souls-like placeholder clips (STYLE-SOULS-001 step 4) on a CECharacter by combat state.
##
## The clips are authored and baked in Blender (scripts/bake_souls_clips.py -> data/souls_clips.glb, game-rig
## bones only). Blender's bone rest frames differ from the Python game GLB's, so every rotation key is moved
## between the two rests: with C_b = rest_src_b^-1 * rest_tgt_b (global rest rotations of bone b),
## key_tgt = C_parent^-1 * key_src * C_b, which keeps the same world motion. Clips are in place: only rotation
## tracks are kept (bone positions and lengths come from the target skeleton). Lengths equal the Python frame data,
## so the state machine (CESoulsCombat) stays the truth; Godot only chooses which clip plays.
class_name CESoulsAnimator
extends Node

const CLIPS_GLB := "res://addons/character_engine/data/souls_clips.glb"
const CLIPS_JSON := "res://addons/character_engine/data/souls_clips.json"
const LIBRARY := "souls"

var character: CECharacter
var player: AnimationPlayer
var table: Dictionary = {}
var current := ""
var played: Array = []                 # [frame, clip] history (tests)
var load_error := ""
var _last_move_frame := -1


static func load_table() -> Dictionary:
	if not FileAccess.file_exists(CLIPS_JSON):
		return {}
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(CLIPS_JSON))
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


## Load the baked clips GLB: [scene root, Skeleton3D, AnimationPlayer] (empty on failure).
static func load_source() -> Array:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(CLIPS_GLB, state) != OK:
		return []
	# generate_scene resamples animations at bake_fps (default 30): use 60 so keys on odd frames are kept.
	var root := doc.generate_scene(state, 60.0)
	if root == null:
		return []
	var skel := CECharacter.find_skeleton(root)
	var ap: AnimationPlayer = _find_player(root)
	if skel == null or ap == null:
		root.free()
		return []
	return [root, skel, ap]


static func _find_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node
	for c in node.get_children():
		var f := _find_player(c)
		if f != null:
			return f
	return null


static func _global_rest_rotation(skel: Skeleton3D, idx: int) -> Quaternion:
	return skel.get_bone_global_rest(idx).basis.get_rotation_quaternion()


## Rotation-only copy of every source animation, re-expressed for `tgt` (tracks addressed by `track_prefix:bone`).
static func retarget_library(src_player: AnimationPlayer, src: Skeleton3D, tgt: Skeleton3D, track_prefix: String,
		clips: Dictionary) -> AnimationLibrary:
	var lib := AnimationLibrary.new()
	var corr := {}
	for i in range(tgt.get_bone_count()):
		var name := tgt.get_bone_name(i)
		var si := src.find_bone(name)
		if si >= 0:
			corr[name] = _global_rest_rotation(src, si).inverse() * _global_rest_rotation(tgt, i)
	for anim_name in src_player.get_animation_list():
		var sa: Animation = src_player.get_animation(anim_name)
		var clip_id := String(anim_name).get_file()
		var ta := Animation.new()
		ta.length = sa.length
		var info: Dictionary = clips.get(clip_id, {})
		ta.loop_mode = Animation.LOOP_LINEAR if bool(info.get("loop", false)) else Animation.LOOP_NONE
		for t in range(sa.get_track_count()):
			if sa.track_get_type(t) != Animation.TYPE_ROTATION_3D:
				continue
			var bone := String(sa.track_get_path(t).get_concatenated_subnames())
			if not corr.has(bone):
				continue
			var parent_idx := tgt.get_bone_parent(tgt.find_bone(bone))
			var c_parent: Quaternion = corr[tgt.get_bone_name(parent_idx)] if parent_idx >= 0 else Quaternion.IDENTITY
			var c_bone: Quaternion = corr[bone]
			var nt := ta.add_track(Animation.TYPE_ROTATION_3D)
			ta.track_set_path(nt, NodePath(track_prefix + ":" + bone))
			ta.track_set_interpolation_type(nt, sa.track_get_interpolation_type(t))
			for k in range(sa.track_get_key_count(t)):
				var q: Quaternion = sa.track_get_key_value(t, k)
				ta.rotation_track_insert_key(nt, sa.track_get_key_time(t, k), (c_parent.inverse() * q * c_bone).normalized())
		lib.add_animation(clip_id, ta)
	return lib


func setup(p_character: CECharacter) -> Error:
	character = p_character
	table = load_table()
	var src := load_source()
	if table.is_empty() or src.is_empty() or character.skeleton == null:
		load_error = "clips table or GLB missing (run scripts/bake_souls_clips.py)"
		push_error("CESoulsAnimator: " + load_error)
		return ERR_FILE_NOT_FOUND
	player = AnimationPlayer.new()
	player.name = "SoulsClips"
	character.add_child(player)                     # root_node ".." = the character
	var prefix := String(character.get_path_to(character.skeleton))
	player.add_animation_library(LIBRARY, retarget_library(src[2], src[1], character.skeleton, prefix,
			table.get("clips", {})))
	(src[0] as Node).free()
	return OK


func clip_names() -> PackedStringArray:
	return player.get_animation_library(LIBRARY).get_animation_list() if player else PackedStringArray()


## Clip for a fighter state: moves pick light_1..3 / heavy, the Sentinel's telegraph plays the wind-up.
func clip_for(f: CESoulsCombat.Fighter, telegraph := false) -> String:
	var state := f.state_name()
	if state == "startup" or state == "active" or state == "recovery":
		return "heavy" if f.current_move.ends_with("_heavy") else "light_%d" % clampi(f.chain, 1, 3)
	if telegraph and state == "idle":
		return "windup"
	if state == "knockdown":            # opt-in strike physics; no knockdown clip baked yet: placeholder
		return "stagger"
	for cid in table.get("clips", {}):
		if (table["clips"][cid]["states"] as Array).has(state):
			return cid
	return "idle"


## Play the clip for this frame's state; a new move restarts its clip even when the clip id repeats.
func update_from(f: CESoulsCombat.Fighter, frame: int, move_start_frame: int, telegraph := false) -> void:
	if player == null:
		return
	var clip := clip_for(f, telegraph)
	var restart := move_start_frame != _last_move_frame and move_start_frame >= 0
	if clip != current or restart:
		current = clip
		_last_move_frame = move_start_frame
		player.play(LIBRARY + "/" + clip)
		played.append([frame, clip])
