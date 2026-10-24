# Coordinate System Contract

**Version:** 1.0.0  
**Date:** 2026-08-13  
**Status:** CANONICAL  
**Purpose:** Formal definition of coordinate system conventions for anatomical reconstruction

---

## Canonical Conventions

### System Properties
- **Handedness:** Right-handed
- **Vertical Axis:** Z (positive Z points upward)
- **Linear Units:** Meters
- **Angular Units:** Radians everywhere in the domain (internal calculations, quaternions, kinematics).
  Degrees only at interfaces (UI, Euler input/output, reports), with a `_deg` suffix
  (Decision 27 / D-07).
- **Ground/Reference Plane:** Z = 0

### Axis Definitions

#### Z-Axis (Vertical)
- **Direction:** Positive Z points upward
- **Origin:** Ground level at foot midline
- **Semantic:** Height/elevation axis
- **Positive:** Above ground
- **Negative:** Below ground (not used for standard anatomy)

#### X-Axis (Lateral)
- **Direction:** Positive X points from left to right
- **Semantic:** Left-right anatomical axis
- **Positive:** Right side of body
- **Negative:** Left side of body
- **Midline:** X = 0

#### Y-Axis (Anterior/Posterior)
- **Direction:** Positive Y points posterior (backward)
- **Semantic:** Forward-backward anatomical axis
- **Positive:** Posterior (back)
- **Negative:** Anterior (front)
- **Reference:** Coronal plane

### Left/Right Convention

#### Standard Convention
- **Right side:** Positive X coordinates
- **Left side:** Negative X coordinates
- **Midline structures:** X = 0
- **Bilateral pairs:** Mirror across X = 0 plane

#### Naming Convention
- Left structures: `{STRUCTURE}_L` or `LEFT_{STRUCTURE}`
- Right structures: `{STRUCTURE}_R` or `RIGHT_{STRUCTURE}`
- Midline structures: `{STRUCTURE}` (no lateral suffix)

### Origin Definition

#### World Origin
- **Location:** Foot midline at ground level
- **Coordinates:** (0, 0, 0)
- **Semantic:** Reference point for all anatomical coordinates
- **Rationale:** Stable reference point for standing pose

#### Alternative Origins (for calculations)
- **Pelvic center:** Used for lower body calculations
- **Sacral promontory:** Used for spine calculations
- **Body center of mass:** Used for biomechanical calculations

### World-Space Semantics

#### Coordinate System Type
- **Global:** All anatomical coordinates are in world-space
- **No local transforms:** Bones use absolute world coordinates
- **No parent-relative coordinates:** All positions are absolute to origin
- **Rationale:** Simplifies validation and ensures determinism

#### Coordinate Transformations
- **Local to world:** Not used in current system
- **World to local:** Not used in current system
- **Parent to child:** Not used for positioning (only for hierarchy)
- **Mirror operations:** Performed on world coordinates

### Canonical Neutral Pose

#### Pose Definition
- **Standing pose:** Upright, facing anterior (negative Y direction)
- **Arms:** Neutral position at sides (A-pose)
- **Legs:** Straight, shoulder-width apart
- **Hands:** Neutral, fingers extended
- **Feet:** Parallel, shoulder-width apart

#### Joint Angles (Neutral Pose)
- **Shoulder:** 0° rotation (hanging at sides)
- **Elbow:** 0° extension (straight arm)
- **Wrist:** 0° flexion (neutral hand)
- **Hip:** 0° rotation (straight leg)
- **Knee:** 0° flexion (straight leg)
- **Ankle:** 0° dorsiflexion (neutral foot)

### Rotation Conventions

#### Rotation Order
- **Order:** ZYX (intrinsic rotations)
- **Rationale:** Standard convention, avoids gimbal lock for typical poses
- **Application:** Apply Z rotation, then Y rotation, then X rotation

#### Rotation Direction
- **Direction:** Counter-clockwise positive (right-hand rule)
- **Rationale:** Mathematical standard, matches Blender conventions
- **Axis rule:** Positive rotation follows right-hand rule around axis

#### Rotation Representation
- **Euler angles:** Used for human-readable specification
- **Quaternions:** Used for interpolation and calculations
- **Rotation matrices:** Used for coordinate transformations

### Mirror Operation

#### Mirror Transformation
- **Operation:** Mirror across X = 0 plane (YZ plane)
- **Formula:** `(x, y, z) → (-x, y, z)`
- **Application:** Convert left-side coordinates to right-side or vice versa
- **Involution:** `mirror(mirror(x)) == x` (mathematical invariant)

#### Mirror Semantics
- **Bilateral symmetry:** Assume perfect bilateral symmetry unless specified
- **Asymmetry tolerance:** Acceptable deviation ±2mm for natural variation
- **Landmark mirroring:** Apply to all bilateral landmarks
- **Joint center mirroring:** Apply to all bilateral joint centers

### Unit Conversions

#### Linear Units
- **Primary:** Meters (m)
- **Conversion factors:**
  - 1 meter = 1000 millimeters
  - 1 meter = 100 centimeters
  - 1 meter = 3.28084 feet
  - 1 meter = 39.3701 inches

#### Angular Units
- **Domain (canonical):** Radians (rad) — all internal angles and calculations
- **Interfaces only:** Degrees (°), named with a `_deg` suffix (e.g. `from_euler_zyx(roll_deg, …)`,
  `apply_tpose(abduction_deg=…)`)
- **Legacy, to migrate when touched** (degrees without `_deg`, interface-facing):
  `coordinate_system.py` Euler helpers (`rotation` tuples, `parent_rotation`/`child_rotation`) and
  angular tolerances; `hands/model.py`, `feet/model.py` `orientation`, `thumb_orientation`;
  `spine/model.py` `angle`, `sacral_orientation`.
- **Conversion factors:**
  - 1 radian = 57.2958 degrees
  - 1 degree = 0.0174533 radians

### Validation Constraints

#### Coordinate Validity
- **Finite values:** All coordinates must be finite (no NaN, no infinity)
- **Range constraints:** No hard limits except physical plausibility
- **Units:** All coordinates must be in meters
- **Precision:** Floating-point precision acceptable (no integer rounding required)

#### Orientation Validity
- **Right-handedness:** Cross product follows right-hand rule
- **Axis orthogonality:** X, Y, Z axes must be orthogonal
- **Unit vectors:** Direction vectors should be normalized where applicable

### Integration with Existing Pipeline

#### Compatibility
- **Existing data:** Current `human_adult_206.json` uses Z-up convention
- **Blender compatibility:** Z-up matches Blender default
- **Math compatibility:** Existing Vector3/Quaternion classes compatible
- **No breaking changes:** New conventions align with existing partial definitions

#### Migration Path
- **Forward axis:** Previously undefined, now defined as negative Y forward
- **Rotation conventions:** Previously undefined, now defined as ZYX order
- **World-space semantics:** Already used, now formally documented
- **No data migration required:** Existing data follows conventions

### Reference Implementation

The coordinate system is implemented in:
- **Code:** `src/character_engine/domain/anatomy/coordinate_system.py`
- **Tests:** `tests/anatomy/test_coordinate_system.py`
- **Documentation:** This file

### Version History

#### Version 1.0.0 (2026-08-13)
- Initial canonical coordinate system definition
- Established based on existing repository conventions
- Defined forward axis and rotation conventions
- Formalized world-space semantics

---

## Tolerance Definitions

### Coordinate Tolerances
- **Critical measurements:** 0.001m (1mm) - joint centers, landmarks
- **Important measurements:** 0.002m (2mm) - bone lengths, dimensions
- **General measurements:** 0.005m (5mm) - general positions
- **Bilateral symmetry:** 0.002m (2mm) - left-right equivalence

### Angular Tolerances
- **Critical angles:** 2° - spine curvature, joint axes
- **Important angles:** 3° - joint orientations
- **General angles:** 5° - general orientations

### Proportion Tolerances
- **Critical proportions:** 5% - major body ratios
- **Important proportions:** 10% - segment ratios
- **General proportions:** 15% - detailed ratios

---

## References

### Standards
- **ISB (International Society of Biomechanics):** Biomechanical coordinate system recommendations
- **Blender:** Z-up coordinate system convention
- **Mathematics:** Right-handed coordinate system standard

### Rationale
- **Z-up:** Industry standard for character animation, matches Blender
- **Right-handed:** Mathematical standard, consistent with cross products
- **Meters:** SI unit, international standard, matches scientific literature
- **World-space:** Simplifies validation, ensures determinism

---

**STATUS:** CANONICAL  
**NEXT REVIEW:** After A0.4 implementation  
**MAINTAINER:** Character Engine Team
