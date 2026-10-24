# Canonical Data Audit

**Sprint A0.2 - Forensic Analysis**  
**Date:** 2026-08-12  
**Status:** READ-ONLY DISCOVERY
**Update 2026-09-29:** the scale findings below (3.08 m stature, oversized head, short legs) were
addressed by **A07** (`A07_STATURE_RETARGET_180.md`): the skeleton is now 1.80 m with joint heights
from Drillis & Contini (1966). Structural findings (straight spine, joint gaps, schematic hands/feet) remain open.

---

## Executive Summary

The canonical anatomy data (`human_adult_206.json`) represents a **structurally valid but anatomically incomplete** skeleton. The data appears to be **generated geometric placeholders** rather than anatomically accurate bone definitions. While the structural integrity passes all current validation tests, the anatomical correctness fails for cinematic/fidelity requirements.

---

## Schema Structure

### Root Schema
```json
{
  "bones": [...],      // 206 anatomical bones
  "containers": [...]   // 2 logical containers
}
```

### Bone Schema
```json
{
  "canonical_name": "BONE_NAME",
  "name": "Display Name",
  "parent": "PARENT_NAME",
  "head": {"x": 0.0, "y": 0.0, "z": 0.0},
  "tail": {"x": 0.0, "y": 0.0, "z": 0.0}
}
```

### Container Schema
```json
{
  "canonical_name": "CONTAINER_NAME",
  "name": "Display Name",
  "parent": "PARENT_NAME"  // or null for root
}
```

---

## Coordinate System

### Current System
- **Type:** Z-up (feet at Z=0)
- **Units:** Meters
- **Handedness:** Right-handed
- **Origin:** Feet at Z=0, Y=0 (midline), X=0 (midline)

### Coordinate Ranges
- **X:** -0.395m to +0.395m (total width: 79cm)
- **Y:** -0.140m to +0.100m (total depth: 24cm)
- **Z:** 0.000m to +3.080m (total height: 308cm)

### Critical Finding
**Overall height of 3.08m (308cm) is anatomically incorrect for a human adult.** This suggests the coordinates are either:
1. Scaled incorrectly
2. Not representing actual human proportions
3. Generated without anatomical reference

---

## Units

- **Linear:** Meters (m)
- **Angular:** Not represented (no rotation data)
- **Scale:** No scale factors present

---

## Bone Ordering

### Organization Method
Bones are organized by **anatomical region** in the following sequence:

1. **Cranium/Face (22 bones)**
   - Neurocranium: FRONTAL, PARIETAL_L/R, TEMPORAL_L/R, OCCIPITAL, SPHENOID, ETHMOID
   - Viscerocranium: MAXILLA_L/R, ZYGOMATIC_L/R, NASAL_L/R, LACRIMAL_L/R, PALATINE_L/R, INFERIOR_NASAL_CONCHA_L/R, VOMER, MANDIBLE

2. **Ear Bones (6 bones)**
   - MALLEUS_L/R, INCUS_L/R, STAPES_L/R

3. **Hyoid (1 bone)**
   - HYOID

4. **Vertebral Column (26 bones)**
   - Cervical: CERVICAL_1 through CERVICAL_7
   - Thoracic: THORACIC_1 through THORACIC_12
   - Lumbar: LUMBAR_1 through LUMBAR_5
   - Sacrum: SACRUM
   - Coccyx: COCCYX

5. **Thoracic Cage (25 bones)**
   - STERNUM
   - RIBS: RIB_01 through RIB_12 (left and right)

6. **Upper Limbs (64 bones)**
   - Shoulder Girdle: CLAVICLE_L/R, SCAPULA_L/r
   - Arm: HUMERUS_L/r
   - Forearm: RADIUS_L/r, ULNA_L/r
   - Carpals: 8 carpal bones per hand
   - Metacarpals: 5 metacarpals per hand
   - Phalanges: 14 phalanges per hand

7. **Lower Limbs (62 bones)**
   - Pelvic Girdle: COXAL_L/r
   - Thigh: FEMUR_L/r
   - Knee: PATELLA_L/r
   - Leg: TIBIA_L/r, FIBULA_L/r
   - Tarsals: 7 tarsal bones per foot
   - Metatarsals: 5 metatarsals per foot
   - Phalanges: 14 phalanges per foot

### Naming Convention
- **Canonical:** UPPER_CASE with _L/_R suffix for bilateral bones
- **Display:** Spanish names (e.g., "Parietal I" for left parietal)
- **Separators:** Underscore for multi-word canonical names

---

## Parent Relationships

### Container Hierarchy
```
ROOT_SKELETON (null parent)
└── CRANIUM (parent: ROOT_SKELETON)
```

### Top-Level Parents
- **CRANIUM:** 30 children (all cranial/facial bones + CERVICAL_1)
- **ROOT_SKELETON:** 2 children (CLAVICLE_L, CLAVICLE_R)

### Key Parent Chains
```
CRANIUM → CERVICAL_1 → CERVICAL_2 → ... → CERVICAL_7
CERVICAL_7 → THORACIC_1 → THORACIC_2 → ... → THORACIC_12
THORACIC_12 → LUMBAR_1 → LUMBAR_2 → ... → LUMBAR_5
LUMBAR_5 → SACRUM → COCCYX

ROOT_SKELETON → CLAVICLE_L → SCAPULA_L → HUMERUS_L → RADIUS_L/ULNA_L
ROOT_SKELETON → CLAVICLE_R → SCAPULA_R → HUMERUS_R → RADIUS_R/ULNA_R

SACRUM → COXAL_L → FEMUR_L → TIBIA_L/FIBULA_L
SACRUM → COXAL_R → FEMUR_R → TIBIA_R/FIBULA_R
```

---

## Head/Tail Semantics

### Current Definition
- **Head:** Proximal end (closer to body center/parent)
- **Tail:** Distal end (farther from body center/parent)
- **Orientation:** Based on anatomical position, not function

### Critical Finding
**Head/tail does NOT represent anatomical joint centers.** The endpoints appear to be geometric points rather than biomechanically meaningful joint locations. This is evident from:

1. Large gaps between parent tail and child head (5-25cm)
2. No clear joint center representation
3. Endpoints appear to be mathematical rather than anatomical

---

## Container Semantics

### Purpose
Containers serve as **logical grouping nodes** for hierarchical organization without geometric representation.

### Current Containers
1. **ROOT_SKELETON**
   - Parent: null
   - Purpose: Root of entire skeleton hierarchy
   - Children: CLAVICLE_L, CLAVICLE_R
   - Geometry: Zero-length (head=tail=(0,0,0))

2. **CRANIUM**
   - Parent: ROOT_SKELETON
   - Purpose: Logical grouping for cranial bones
   - Children: 30 cranial/facial bones + CERVICAL_1
   - Geometry: Zero-length (head=tail=(0,0,0))

### Semantics
- **Not anatomical bones:** No physiological counterpart
- **Hierarchical only:** Serve as organization points
- **No geometry:** Zero-length bones for Blender armature structure
- **Validation impact:** Counted in total nodes (208) but not in anatomical bones (206)

---

## Coordinate Space

### Current Implementation
- **Type:** World-space coordinates
- **Reference:** Global origin (0,0,0) at foot level midline
- **No local transforms:** All coordinates are absolute world positions

### Evidence
1. No transformation matrices in bone data
2. No parent-relative coordinates
3. Direct world-space positioning for all bones
4. Blender importer uses world-space coordinates directly

---

## Anatomical Landmark Representation

### Current State
**The canonical data does NOT represent anatomical landmarks.** The coordinates appear to be:

1. **Mathematically generated:** Regular spacing, uniform lengths
2. **Geometric placeholders:** Simplified representations
3. **Not reference-based:** No anatomical measurement sources

### Evidence
- **Spine:** Perfectly straight vertical line (no curvature)
- **Limbs:** Uniform bone lengths within groups
- **Hands/Feet:** Identical phalanx lengths
- **Overall proportions:** Incorrect human scale (3.08m height)

---

## Anatomical Correctness Assessment

### Structural vs Anatomical
| Aspect | Status | Evidence |
|--------|--------|----------|
| Structural Integrity | ✅ VALID | Passes all validation tests |
| Hierarchy Integrity | ✅ VALID | No cycles, valid parent references |
| Geometric Validity | ✅ VALID | No zero-length bones, finite coordinates |
| Anatomical Scale | ❌ INVALID | 3.08m height incorrect |
| Anatomical Proportions | ❌ INVALID | Incorrect limb/torso ratios |
| Joint Representation | ❌ INVALID | Large gaps at articulations |
| Bone Lengths | ❌ INVALID | Uniform lengths within groups |
| Spine Curvature | ❌ INVALID | Perfectly straight (no lordosis/kyphosis) |
| Hand/Foot Anatomy | ❌ INVALID | Simplified mechanical structure |

### Conclusion
**The current 206-bone skeleton is a STRUCTURALLY VALID but ANATOMICALLY INCORRECT representation.** It appears to be generated geometric placeholders rather than anatomically accurate definitions suitable for cinematic character animation.

---

## Generation Method Analysis

### Evidence of Script Generation
Based on the coordinate patterns, the skeleton appears to be generated by `scripts/generate_human_template.py` with:

1. **Mathematical spacing:** Regular intervals (0.03m, 0.035m, 0.04m)
2. **Uniform dimensions:** Identical lengths within bone groups
3. **Linear progression:** Simple arithmetic sequences
4. **No anatomical variation:** No natural biological variation

### Script Characteristics
- **Algorithmic:** Loop-based generation with mathematical formulas
- **Hardcoded values:** Fixed offsets and dimensions
- **No reference data:** No anatomical measurement sources
- **Simplified anatomy:** Reduction to basic geometric forms

---

## Critical Unknowns

1. **Reference Data Source:** No anatomical measurement reference identified
2. **Scale Intent:** Unknown if 3.08m height is intentional or error
3. **Joint Center Method:** No methodology for anatomical joint center placement
4. **Pose Reference:** Unknown target pose (anatomical, T-pose, A-pose?)
5. **Population Data:** Unknown if based on specific population averages
6. **Age/Gender:** Unknown demographic target (adult male, female, average?)

---

## Recommendation

**The canonical anatomy data requires complete reconstruction** using:

1. **Anatomical reference data** from medical/biomechanical sources
2. **Proper human scale** (1.7-1.9m height for adults)
3. **Accurate joint center placement** based on biomechanical data
4. **Natural anatomical variation** in bone lengths and proportions
5. **Physiological spine curvature** (lordosis/kyphosis)
6. **Proper hand/foot anatomy** for cinematic requirements

**Current Status:** NOT SUITABLE for production character animation