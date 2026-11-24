## Keeps a held weapon out of bodies, for the eye only (review items 12-13, Decision 88): after the pose of the frame,
## the weapon mesh turns about the grip by the smallest angle that takes it out of every body capsule (the opponent's,
## and its holder's except the holding arm). The fight is not touched: hits, events and replays come from CESoulsCombat.
##
## Capsules follow the game-rig bones (bone origin to its first child), with the envelope radii of
## domain/rigging/block_dummy.py (ESTIMATE, 1.80 m adult, scaled by the character's height). Search: 8 directions
## around the weapon, STEP_DEG steps up to MAX_DEG; when nothing clears, the weapon is left as animated.
class_name CEWeaponClearance
extends RefCounted

const RADIUS := {"head": 0.085, "neck_01": 0.06, "spine_03": 0.13, "spine_02": 0.13, "spine_01": 0.13,
		"pelvis": 0.14, "upperarm": 0.05, "lowerarm": 0.04, "hand": 0.018, "thigh": 0.08, "calf": 0.055, "foot": 0.03}
const HEAD_LENGTH_M := 0.2
const STEP_DEG := 3.0
const MAX_DEG := 60.0
const SAMPLES := 12
const REFERENCE_STATURE_M := 1.80


## [[a, b, radius], ...] world-space capsules of `ch`, without the bones in `skip`.
static func capsules(ch: CECharacter, skip: PackedStringArray = PackedStringArray()) -> Array:
	var out: Array = []
	var sk := ch.skeleton
	if sk == null:
		return out
	var k := ch.height_m() / REFERENCE_STATURE_M if ch.height_m() > 0.5 else 1.0
	for i in range(sk.get_bone_count()):
		var name := sk.get_bone_name(i)
		if name in skip:
			continue
		var key := name.trim_suffix("_l").trim_suffix("_r")
		if not RADIUS.has(key):
			continue
		var a := sk.global_transform * sk.get_bone_global_pose(i).origin
		var b := a
		var kids: Array = []
		for c in sk.get_bone_children(i):
			if not sk.get_bone_name(c).contains("twist"):     # the twist helpers sit mid-limb
				kids.append(c)
		if name == "head" or kids.is_empty():
			b = a + (sk.global_transform.basis * sk.get_bone_global_pose(i).basis.y).normalized() * HEAD_LENGTH_M * k
		else:
			b = sk.global_transform * sk.get_bone_global_pose(kids[0]).origin
		out.append([a, b, float(RADIUS[key]) * k])
	return out


static func _segment_point_distance(a: Vector3, b: Vector3, p: Vector3) -> float:
	var ab := b - a
	var t := clampf((p - a).dot(ab) / maxf(ab.length_squared(), 1e-12), 0.0, 1.0)
	return p.distance_to(a + ab * t)


## Deepest penetration (m, 0 = clear) of the weapon segment p0-p1 into `caps`.
static func penetration(p0: Vector3, p1: Vector3, caps: Array) -> float:
	var worst := 0.0
	for i in range(SAMPLES + 1):
		var p := p0.lerp(p1, float(i) / SAMPLES)
		for c in caps:
			worst = maxf(worst, float(c[2]) - _segment_point_distance(c[0], c[1], p))
	return worst


## Weapon ends in world space: [grip point, end A, end B] from the mesh as animated (rest transform restored first).
static func _ends(mesh: MeshInstance3D, weapon: Dictionary) -> Array:
	var length := float(weapon.get("length_m", 0.0))
	var g := float(weapon.get("grip_fraction", 0.5))
	var gt := mesh.global_transform
	var axis := gt.basis.y.normalized()
	var grip := gt.origin - axis * (0.5 - g) * length
	return [grip, gt.origin + axis * 0.5 * length, gt.origin - axis * 0.5 * length]


## Turn `holder`'s weapon out of the bodies. Returns the angle used (deg), 0 when it was already clear or nothing
## cleared it within MAX_DEG.
static func solve(holder: CECharacter, others: Array) -> float:
	var att := holder.weapon_attachment
	if att == null or att.get_child_count() == 0:
		return 0.0
	var mesh := att.get_child(0) as MeshInstance3D
	var weapon: Dictionary = att.get_meta("ce_weapon", {})
	if mesh == null or weapon.is_empty():
		return 0.0
	if not mesh.has_meta("ce_rest_transform"):
		mesh.set_meta("ce_rest_transform", mesh.transform)
	mesh.transform = mesh.get_meta("ce_rest_transform")
	var side := String(weapon.get("grip_bone", "_R")).right(1).to_lower()
	var caps := capsules(holder, PackedStringArray(["upperarm_" + side, "lowerarm_" + side, "hand_" + side,
			"clavicle_" + side]))
	for o in others:
		caps.append_array(capsules(o))
	var e := _ends(mesh, weapon)
	var grip: Vector3 = e[0]
	var end_a: Vector3 = e[1]
	var end_b: Vector3 = e[2]
	if penetration(grip, end_a, caps) <= 0.0 and penetration(grip, end_b, caps) <= 0.0:
		return 0.0
	var axis: Vector3 = (end_a - grip).normalized()
	var u := axis.cross(Vector3.UP if absf(axis.dot(Vector3.UP)) < 0.9 else Vector3.RIGHT).normalized()
	var v := axis.cross(u)
	var deg := STEP_DEG
	while deg <= MAX_DEG:
		for k in range(8):
			var turn_axis := (u * cos(k * PI / 4.0) + v * sin(k * PI / 4.0)).normalized()
			var rot := Basis(turn_axis, deg_to_rad(deg))
			var a1: Vector3 = grip + rot * (end_a - grip)
			var b1: Vector3 = grip + rot * (end_b - grip)
			if penetration(grip, a1, caps) <= 0.0 and penetration(grip, b1, caps) <= 0.0:
				var world := mesh.global_transform
				world = Transform3D(rot, Vector3.ZERO) * Transform3D(Basis.IDENTITY, -grip) * world
				world.origin += grip
				mesh.global_transform = world
				return deg
		deg += STEP_DEG
	return 0.0


## Penetration (m) of `holder`'s weapon as it is now drawn, into the same capsules `solve` avoids (for checks).
static func residual(holder: CECharacter, others: Array) -> float:
	var att := holder.weapon_attachment
	if att == null or att.get_child_count() == 0:
		return 0.0
	var mesh := att.get_child(0) as MeshInstance3D
	var weapon: Dictionary = att.get_meta("ce_weapon", {})
	if mesh == null or weapon.is_empty():
		return 0.0
	var side := String(weapon.get("grip_bone", "_R")).right(1).to_lower()
	var caps := capsules(holder, PackedStringArray(["upperarm_" + side, "lowerarm_" + side, "hand_" + side,
			"clavicle_" + side]))
	for o in others:
		caps.append_array(capsules(o))
	var e := _ends(mesh, weapon)
	var grip: Vector3 = e[0]
	return maxf(penetration(grip, e[1], caps), penetration(grip, e[2], caps))
