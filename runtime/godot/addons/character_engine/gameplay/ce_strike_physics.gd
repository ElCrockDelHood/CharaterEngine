## Strike physics of a blunt blow (Decisions 58 and 59): reduced-mass energy split, peak force and fracture, head
## kinematics, concussion probability and knock-back stagger. Additive and opt-in.
##
## Formula-by-formula port of `domain/physics/collision.py`, `strike_model.py` (force part) and `head_kinematics.py`.
## The tables (segment mass fractions, region stiffness and fracture forces, Rowson 2012, stagger thresholds) are read
## from data/strike_physics.json, written by tests/make_strike_physics_reference.py from the Python modules, so the
## numbers live in one place. Not ported: the tissue-layer depth of `strike_blunt` (`blunt_through`); wounds in the
## fight mockups keep coming from the pre-computed gameplay table. Segment mass fractions are SOURCED (de Leva 1996);
## the rest is ESTIMATE / ASSUMED (A14, A15, A16). Per-table provenance is in the JSON.
class_name CEStrikePhysics
extends RefCounted

const DEFAULT_PATH := "res://addons/character_engine/data/strike_physics.json"

var doc: Dictionary = {}
var tb: Dictionary = {}
var target_mass: Dictionary = {}         # region -> kg (body mass x fraction x bracing)


static func load_default() -> CEStrikePhysics:
	return load_from(DEFAULT_PATH)


static func load_from(p: String, body_mass_kg := -1.0, bracing := 1.0) -> CEStrikePhysics:
	var s := CEStrikePhysics.new()
	var f := FileAccess.open(p, FileAccess.READ)
	if f == null:
		push_error("CEStrikePhysics: cannot open %s" % p)
		return s
	var parsed = JSON.parse_string(f.get_as_text())
	if parsed is Dictionary:
		s.doc = parsed
		s.tb = parsed.get("tables", {})
		s.target_mass = s.regional_target_mass(body_mass_kg if body_mass_kg > 0.0 else float(s.tb["default_body_mass_kg"]), bracing)
	return s


func is_valid() -> bool:
	return not tb.is_empty() and not target_mass.is_empty()


func cases() -> Array:
	return doc.get("cases", [])


# ---- collision.py ----------------------------------------------------------------------------------------
func regional_target_mass(body_mass_kg: float, bracing := 1.0) -> Dictionary:
	if body_mass_kg <= 0.0 or bracing < 1.0:
		push_error("body mass must be positive and bracing >= 1")
		return {}
	var out := {}
	var fr: Dictionary = tb["segment_mass_fraction"]
	for r in fr:
		out[r] = snappedf(body_mass_kg * float(fr[r]) * bracing, 0.0001)
	return out


static func reduced_mass(m_striker: float, m_target: float) -> float:
	if is_inf(m_target):
		return m_striker
	return m_striker * m_target / (m_striker + m_target)


## Kinetic, deformation (½ μ v²) and knock-back (rest) energy; common speed after a perfectly inelastic contact.
static func split(m_striker: float, speed: float, m_target: float) -> Dictionary:
	var mu := reduced_mass(m_striker, m_target)
	var ke := 0.5 * m_striker * speed * speed
	var deform := 0.5 * mu * speed * speed
	return {"reduced_mass_kg": mu, "kinetic_j": ke, "deformation_j": deform, "momentum_j": ke - deform,
			"target_speed_m_s": m_striker * speed / (m_striker + m_target)}


# ---- strike_model.py (force criterion) -------------------------------------------------------------------
static func peak_force(v: float, k: float, mu: float) -> float:
	return v * sqrt(k * mu)


static func fracture_probability(force: float, rng: Array) -> float:
	var low := float(rng[0])
	var mid := float(rng[1])
	var high := float(rng[2])
	if force <= low:
		return 0.0
	if force >= high:
		return 1.0
	return 0.5 * (force - low) / (mid - low) if force <= mid else 0.5 + 0.5 * (force - mid) / (high - mid)


## Nominal striker of a gameplay move (`Striker.from_move`): v by kind (unknown kinds use the punch speed), m = 2E/v².
func striker_from_move(energy_j: float, kind: String) -> Dictionary:
	var speeds: Dictionary = tb["nominal_speed_m_s"]
	var v := float(speeds.get(kind, speeds["punch"]))
	return {"mass_kg": 2.0 * energy_j / (v * v), "speed_m_s": v}


## Force / fracture part of `strike_blunt` for one region (no layer depth, no wound).
func strike(region: String, m: float, v: float) -> Dictionary:
	var resp: Dictionary = tb["region_response"][region]
	var big_m := float(target_mass[region])
	var mu := reduced_mass(m, big_m)
	var e_diss := 0.5 * mu * v * v
	var ke := 0.5 * m * v * v
	var force := peak_force(v, float(resp["stiffness_n_per_m"]), mu)
	var rng: Array = resp["fracture_force_n"]
	var fractured := force >= float(rng[1])
	var energy_ok = null
	if resp.get("fracture_energy_j") != null:
		var fe: Array = resp["fracture_energy_j"]
		energy_ok = e_diss >= 0.5 * (float(fe[0]) + float(fe[1]))
		fractured = fractured and energy_ok          # skull: both criteria
	return {"region": region, "striker_energy_j": ke, "reduced_mass_kg": mu, "dissipated_j": e_diss,
			"knockback_j": ke - e_diss, "target_speed_after_m_s": m * v / (m + big_m), "peak_force_n": force,
			"fracture_force_n": rng, "fracture_probability": fracture_probability(force, rng), "fractured": fractured,
			"energy_criterion_met": energy_ok}


# ---- head_kinematics.py ----------------------------------------------------------------------------------
func concussion_probability(alpha: float) -> float:
	var pts: Array = [[0.0, 0.0]]
	pts.append_array(tb["rowson_2012_rotational"])
	pts.append([float(tb["saturation_rad_s2"]), float(tb["saturation_probability"])])
	if alpha <= 0.0:
		return 0.0
	if alpha >= float(pts[-1][0]):
		return float(tb["saturation_probability"])
	for i in range(pts.size() - 1):
		var x0 := float(pts[i][0])
		var p0 := float(pts[i][1])
		var x1 := float(pts[i + 1][0])
		var p1 := float(pts[i + 1][1])
		if alpha <= x1:
			return p0 + (p1 - p0) * (alpha - x0) / (x1 - x0)
	return float(tb["saturation_probability"])


func head_kinematics(force: float, head_mass_kg: float, lever_arm_m: float) -> Dictionary:
	var alpha := force * lever_arm_m / float(tb["head_inertia_kg_m2"])
	return {"linear_g": force / head_mass_kg / float(tb["g"]), "rotational_rad_s2": alpha,
			"concussion_probability": concussion_probability(alpha), "lever_arm_m": lever_arm_m}


func stagger(m: float, v: float, m_target: float, bracing := 1.0) -> Dictionary:
	var j := reduced_mass(m, m_target) * v
	var thr := float(tb["p_step_n_s"]) * bracing
	var level := 0 if j < thr else 1 if j < float(tb["multi_step_ratio"]) * thr else 2 if j < float(tb["fall_ratio"]) * thr else 3
	return {"striker_momentum_n_s": m * v, "impulse_n_s": j, "segment_speed_m_s": m * v / (m + m_target),
			"level": tb["stagger_levels"][level], "threshold_n_s": thr}


## Head kinematics (head / neck only) and stagger of one normal blow; knocked down = fall or concussion >= 0.5.
func knockback(region: String, m: float, v: float, force: float, lever_arm_m := -1.0, bracing := 1.0) -> Dictionary:
	var lever := lever_arm_m if lever_arm_m > 0.0 else float(tb["lever_straight_m"])
	var m_t := float(target_mass[region])
	var st := stagger(m, v, m_t, bracing)
	var head = head_kinematics(force, m_t, lever) if (tb["head_regions"] as Array).has(region) else null
	var down: bool = st["level"] == "fall" or (head != null and float(head["concussion_probability"]) >= 0.5)
	return {"region": region, "head": head, "stagger": st, "knocked_down": down}


## Whole blow: force / fracture of `strike` plus `knockback`, in one dictionary.
func blow(region: String, m: float, v: float, lever_arm_m := -1.0, bracing := 1.0) -> Dictionary:
	var s := strike(region, m, v)
	s.merge(knockback(region, m, v, float(s["peak_force_n"]), lever_arm_m, bracing))
	s["striker_mass_kg"] = m
	s["speed_m_s"] = v
	return s
