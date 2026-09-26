# Joint Centers Documentation

**Version:** 1.0.0  
**Date:** 2026-08-13  
**Status:** FOUNDATION  
**Purpose:** Define joint center representation semantics and calculation methodology

---

## Joint Center Semantics

### Critical Distinction

This system makes a critical distinction between different types of joint representations:

1. **Anatomical Joint Center** - The true center of rotation of the joint in anatomical space
2. **Bone Endpoint** - The geometric endpoint of a bone representation
3. **Articular Surface** - The center of the articular surface
4. **Geometric Representation** - A simplified geometric center for reconstruction

### Important Notes

**Bone Endpoint ≠ Joint Center**

A skeletal bone is a geometric representation, not a literal anatomical surface mesh. Therefore:

- Bone endpoints do not automatically correspond to anatomical joint centers
- Joint centers are not automatically determined by cartilage thickness
- The relationship between bone endpoints and joint centers depends on the representation model

**No Arbitrary Cartilage Gaps**

We do not impose arbitrary "5 mm cartilage gaps" or similar assumptions. All joint center geometry and bone endpoint relationships must follow the actual representation model and be traceable to reference data.

---

## Joint Types

### Shoulder
- **Anatomical Center:** Glenohumeral joint center
- **Representation:** Center of glenoid fossa
- **Note:** Complex 3-DOF joint, center may vary with rotation

### Elbow
- **Anatomical Center:** Humeroulnar joint center
- **Representation:** Medial epicondyle region
- **Note:** Primarily a hinge joint (1-DOF)

### Wrist
- **Anatomical Center:** Radiocarpal joint center
- **Representation:** Center of radiocarpal articulation
- **Note:** Complex multi-DOF joint

### Hip
- **Anatomical Center:** Femoral head center
- **Representation:** Center of femoral head sphere
- **Note:** Ball-and-socket joint (3-DOF)

### Knee
- **Anatomical Center:** Tibiofemoral joint center
- **Representation:** Center of tibial plateau
- **Note:** Primarily a hinge joint (1-DOF)

### Ankle
- **Anatomical Center:** Talocrural joint center
- **Representation:** Center of talus
- **Note:** Hinge joint (1-DOF)

---

## Joint Center Calculation Methodology

### Reference Sources

Joint center locations should be determined from:

1. **ISB Recommendations** - International Society of Biomechanics standards
2. **Biomechanical Research** - Peer-reviewed joint center studies
3. **Clinical Measurement** - Standard clinical measurement protocols
4. **Medical Imaging** - MRI/CT-based joint center determination

### Calculation Methods

#### ISB Method (Preferred)
The ISB recommends specific methods for joint center determination:

- **Shoulder:** Regression equations based on anatomical landmarks
- **Elbow:** Flexion axis method
- **Hip:** Functional method or regression equations
- **Knee:** Functional method or regression equations
- **Ankle:** Functional method

#### Regression Equations
Many joint centers can be calculated from anatomical landmarks using regression equations:

```
joint_center = landmark_1 * a + landmark_2 * b + landmark_3 * c + offset
```

Where coefficients (a, b, c) and offset are determined from population studies.

#### Functional Methods
Functional methods determine joint centers from motion data by finding the point of minimal displacement during rotation.

---

## Representation Semantics

### Current Repository Representation

The current repository uses a simple line segment representation for bones:
- Each bone has a `head` (proximal endpoint)
- Each bone has a `tail` (distal endpoint)
- No explicit joint center representation

### Future Representation

The reconstruction system will support:
- Explicit joint center definitions
- Bone endpoint definitions
- Relationship between joint centers and bone endpoints
- Multiple representation types per joint

### Integration Strategy

The reconstruction system will:
1. Calculate anatomical joint centers from landmarks
2. Define bone endpoints based on representation model
3. Maintain the distinction between these two concepts
4. Provide clear documentation of the relationship

---

## Coordinate System

### World-Space Coordinates

All joint centers are defined in world-space coordinates using the canonical coordinate system:
- Right-handed, Z-up
- Meters
- Origin at foot midline ground level
- Positive X = right side
- Positive Y = posterior (backward)
- Positive Z = upward

### Bilateral Symmetry

Bilateral joint centers should be symmetric across the X = 0 plane:
- Left joint centers have negative X coordinates
- Right joint centers have positive X coordinates
- Midline structures have X = 0

---

## Validation Criteria

### Geometric Validity
- Joint center coordinates must be finite
- Bilateral pairs must be symmetric within tolerance (±2mm)
- Joint centers must be within anatomically plausible ranges

### Anatomical Validity
- Joint centers must be at expected anatomical locations
- Joint centers must respect joint hierarchy
- Joint centers must not create impossible anatomical configurations

### Continuity Validity
- Bone endpoints should be close to joint centers (within appropriate tolerance)
- Parent-child bone relationships should be respected
- No impossible bone lengths should result

---

## Current Status

### Available Data (A0.4 Foundation)
- **NONE** - No joint center data currently acquired

### Placeholder Strategy
During A0.4, joint centers will be marked as:
- `UNKNOWN` - Joint center needed but not yet acquired
- `ASSUMED` - Temporary assumption with explicit documentation

### Acquisition Timeline
- **A0.4:** Establish joint center model and placeholder system
- **A0.5:** Acquire ISB recommendations and basic joint center data
- **A0.6:** Acquire detailed joint center methodology and validation data

---

## Implementation Notes

### No bpy Dependencies
Joint center calculations must be purely mathematical:
- Use Python math operations
- Use existing Vector3/Quaternion classes
- No Blender scene state
- No cursor-dependent operations
- No bpy.ops.transform operations

### Determinism
Joint center calculations must be deterministic:
- Same inputs → same outputs
- No random values
- No time-dependent calculations
- No external state dependencies

### Provenance Tracking
Every joint center must maintain provenance:
- Calculation method used
- Source landmarks used
- Reference data source
- Confidence assessment
- Derivation metadata

---

## Future Enhancements

### Advanced Features
- Functional joint center determination from motion data
- Population-specific joint center adjustments
- Age-related joint center modifications
- Pathological joint center variants

### Validation Enhancements
- Range of motion validation
- Joint axis validation
- Kinematic chain validation
- Biomechanical plausibility checks

---

## References

### Standards
- **ISB:** International Society of Biomechanics recommendations
- **ISO:** International Organization for Standardization

### Research
- Biomechanical joint center determination studies
- Clinical measurement protocols
- Medical imaging-based joint center research

---

**STATUS:** FOUNDATION STRUCTURE ESTABLISHED  
**NEXT:** Acquire ISB recommendations and reference data in A0.5  
**MAINTAINER:** Character Engine Team
