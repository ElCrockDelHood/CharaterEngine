## Character Engine editor dock: pick a skeleton asset and a gameplay style, drop a
## character or a playable arena into the edited scene, validate the GLB contract and
## replay the reference fight scenarios against the GDScript combat port.
@tool
extends VBoxContainer

const VALIDATOR := preload("res://ce_skeleton_validator.gd")
const ASSETS := {
	"T-pose (rigging / gameplay)": "res://assets/human_adult_206_tpose.glb",
	"Anatomical rest pose": "res://assets/human_adult_206.glb",
}

var data: CEGameplayData
var style_opt: OptionButton
var asset_opt: OptionButton
var stature_spin: SpinBox
var autoplay_check: CheckBox
var log_label: RichTextLabel


func _ready() -> void:
	data = CEGameplayData.load_default()
	custom_minimum_size = Vector2(240, 0)

	_title("Character")
	asset_opt = OptionButton.new()
	for label in ASSETS:
		asset_opt.add_item(label)
	add_child(asset_opt)
	var row := HBoxContainer.new()
	row.add_child(_label("Stature (m)"))
	stature_spin = SpinBox.new()
	stature_spin.min_value = 0.8
	stature_spin.max_value = 2.3
	stature_spin.step = 0.01
	stature_spin.value = 1.80
	row.add_child(stature_spin)
	add_child(row)
	_button("Add character to scene", _add_character)
	_button("Validate skeleton GLB", _validate)

	_title("Gameplay / runtime")
	style_opt = OptionButton.new()
	var idx := 0
	for sid in data.style_ids():
		var st := data.style(sid)
		var moves: Array = st.get("moves", [])
		style_opt.add_item("%s%s" % [st.get("label", sid), "" if moves.size() > 0 else "  (planned)"])
		style_opt.set_item_metadata(idx, sid)
		style_opt.set_item_disabled(idx, moves.is_empty())
		if sid == "shenmue":
			style_opt.select(idx)
		idx += 1
	add_child(style_opt)
	autoplay_check = CheckBox.new()
	autoplay_check.text = "Autoplay demo (180 frames)"
	add_child(autoplay_check)
	_button("Create arena in scene", _add_arena)
	_button("Replay reference fights", _replay_reference)

	log_label = RichTextLabel.new()
	log_label.fit_content = true
	log_label.custom_minimum_size = Vector2(0, 120)
	log_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(log_label)
	_log("Character Engine ready. Styles: %s" % ", ".join(data.style_ids()))


func _selected_style() -> String:
	return str(style_opt.get_item_metadata(style_opt.selected))


func _selected_asset() -> String:
	return ASSETS[asset_opt.get_item_text(asset_opt.selected)]


func _add_character() -> void:
	var root := _scene_root()
	if root == null:
		return
	var ch := CECharacter.new()
	ch.name = "CECharacter"
	ch.glb_path = _selected_asset()
	ch.stature_m = stature_spin.value
	root.add_child(ch, true)
	ch.owner = root
	_log("Added CECharacter (%s, %.2f m)." % [_selected_asset().get_file(), stature_spin.value])


func _add_arena() -> void:
	var root := _scene_root()
	if root == null:
		return
	var arena := CEArena.build(data, _selected_style(), _selected_asset())
	arena.player_stature_m = stature_spin.value
	arena.autoplay_frames = 180 if autoplay_check.button_pressed else 0
	root.add_child(arena, true)
	arena.owner = root
	_log("Added CEArena (%s). Press F6 to play the scene." % _selected_style())


func _validate() -> void:
	var report: Dictionary = VALIDATOR.validate_file(_selected_asset())
	_log("%s: %s (bones %s, height %.2f m)" % [_selected_asset().get_file(),
			"PASS" if report.get("passed", false) else "FAIL", report.get("bone_count", "?"), report.get("height_m", 0.0)])
	for e in report.get("errors", []):
		_log("  FAIL " + str(e))


func _replay_reference() -> void:
	var ok := 0
	var total := 0
	for sc in data.reference_scenarios():
		total += 1
		var got := CEShenmueCombat.replay(data, sc["spec"])
		if CEGameplayData.deep_equal(got, sc["expected"]):
			ok += 1
		else:
			_log("  MISMATCH %s" % sc["spec"]["scenario_id"])
	_log("Reference fights: %d/%d identical to the Python domain." % [ok, total])


func _scene_root() -> Node:
	var root := EditorInterface.get_edited_scene_root()
	if root == null:
		_log("Open or create a 3D scene first.")
	return root


func _title(text: String) -> void:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", 14)
	add_child(l)


func _label(text: String) -> Label:
	var l := Label.new()
	l.text = text
	return l


func _button(text: String, cb: Callable) -> void:
	var b := Button.new()
	b.text = text
	b.pressed.connect(cb)
	add_child(b)


func _log(text: String) -> void:
	print("[CE] " + text)
	if log_label != null:
		log_label.append_text(text + "\n")
