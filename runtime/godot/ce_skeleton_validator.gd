## CHARACTER ENGINE - Godot 4 runtime validator for the canonical skeleton.
##
## Usage (editor or headless):
##   1. Export the asset:  python -m character_engine.export.gltf -o builds/gltf/human_adult_206.glb
##   2. Copy the .glb into the Godot project (e.g. res://assets/human_adult_206.glb)
##   3. Attach this script to any Node in a scene, set `glb_path`, run the scene.
##      Or headless:  godot4 --headless --path runtime/godot --script res://ce_skeleton_validator.gd
##
## The validator loads the glTF at runtime (GLTFDocument), finds the Skeleton3D
## and checks the M21 runtime contract:
##   - exactly EXPECTED_TOTAL_NODES bones (206 anatomical + 2 containers)
##   - required canonical names present (ROOT_SKELETON, CRANIUM, SACRUM, ...)
##   - Y-up: the lowest joint is at ground level (y ~= 0) and the skeleton is upright
##   - every bone has at most one parent and there are no cycles (Skeleton3D guarantees it)
## It prints a PASS/FAIL report and, when run as the main script, quits with exit code 0/1.
extends SceneTree

const EXPECTED_TOTAL_NODES := 208
const EXPECTED_ANATOMICAL := 206
const REQUIRED_BONES := ["ROOT_SKELETON", "CRANIUM", "SACRUM", "CERVICAL_1", "FEMUR_L", "FEMUR_R", "FRONTAL"]
const GROUND_TOLERANCE := 0.05

@export var glb_path: String = "res://human_adult_206.glb"


func _init() -> void:
	# Running as main script (headless). Try common locations.
	var candidates := [glb_path, "res://human_adult_206.glb", "res://../../builds/gltf/human_adult_206.glb"]
	var report: Dictionary = {}
	for candidate in candidates:
		if FileAccess.file_exists(candidate):
			report = validate_file(candidate)
			break
	if report.is_empty():
		push_error("CE VALIDATOR: no .glb found. Tried: %s" % [candidates])
		quit(1)
		return
	print_report(report)
	quit(0 if report["passed"] else 1)


## Load a .glb/.gltf and validate the first Skeleton3D found.
static func validate_file(path: String) -> Dictionary:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(path, state)
	if err != OK:
		return {"passed": false, "errors": ["GLTFDocument.append_from_file failed: %s" % error_string(err)], "path": path}
	var root := doc.generate_scene(state)
	if root == null:
		return {"passed": false, "errors": ["generate_scene returned null"], "path": path}
	var skeleton := _find_skeleton(root)
	var report := validate_skeleton(skeleton)
	report["path"] = path
	root.queue_free()
	return report


## Validate an already instantiated Skeleton3D (e.g. from an imported scene).
static func validate_skeleton(skeleton: Skeleton3D) -> Dictionary:
	var errors: Array[String] = []
	var warnings: Array[String] = []
	if skeleton == null:
		return {"passed": false, "errors": ["No Skeleton3D found in the scene (skin not imported?)"]}

	var count := skeleton.get_bone_count()
	if count != EXPECTED_TOTAL_NODES:
		errors.append("bone count %d != expected %d" % [count, EXPECTED_TOTAL_NODES])

	var names := {}
	for i in range(count):
		names[skeleton.get_bone_name(i)] = i
	for required in REQUIRED_BONES:
		if not names.has(required):
			errors.append("missing required bone: %s" % required)

	# Roots: containers may be roots; at least one root is expected
	var roots := 0
	var min_y := INF
	var max_y := -INF
	for i in range(count):
		if skeleton.get_bone_parent(i) == -1:
			roots += 1
		var global_rest := skeleton.get_bone_global_rest(i)
		min_y = min(min_y, global_rest.origin.y)
		max_y = max(max_y, global_rest.origin.y)
	if roots == 0:
		errors.append("skeleton has no root bone")

	# Y-up contract: ground contact near y=0 and skeleton upright (height along +Y)
	if abs(min_y) > GROUND_TOLERANCE:
		warnings.append("lowest joint at y=%.3f (expected ~0, ground plane)" % min_y)
	if max_y - min_y < 1.0:
		errors.append("skeleton height %.3f m along Y is too small: up-axis conversion failed?" % (max_y - min_y))

	return {
		"passed": errors.is_empty(),
		"errors": errors,
		"warnings": warnings,
		"bone_count": count,
		"roots": roots,
		"height_m": max_y - min_y,
		"ground_y": min_y,
	}


static func _find_skeleton(node: Node) -> Skeleton3D:
	if node is Skeleton3D:
		return node
	for child in node.get_children():
		var found := _find_skeleton(child)
		if found != null:
			return found
	return null


static func print_report(report: Dictionary) -> void:
	print("==== CHARACTER ENGINE runtime validation (Godot) ====")
	if report.has("path"):
		print("asset: %s" % report["path"])
	for key in ["bone_count", "roots", "height_m", "ground_y"]:
		if report.has(key):
			print("%s: %s" % [key, report[key]])
	for w in report.get("warnings", []):
		print("WARN: %s" % w)
	for e in report.get("errors", []):
		print("FAIL: %s" % e)
	print("RESULT: %s" % ("PASS" if report["passed"] else "FAIL"))
