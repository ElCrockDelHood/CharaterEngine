# Reference Data Documentation

**Version:** 1.0.0  
**Date:** 2026-08-13  
**Status:** FOUNDATION  
**Purpose:** Define reference data sources and structure for anatomical reconstruction

---

## Reference Data Philosophy

Every anatomical value used in reconstruction must have provenance. No arbitrary values should be presented as biological facts. Reference data provides the scientific and anatomical basis for all reconstruction parameters.

---

## Source Types

### PRIMARY_RESEARCH
Peer-reviewed research articles with original data collection. Highest confidence when methodology is sound and sample size is adequate.

### STANDARD
Established standards from recognized bodies (ISB, ASTM, ISO, etc.). High confidence when widely adopted.

### DATABASE
Curated datasets from recognized institutions (NHANES, WHO, etc.). High confidence when methodology is documented.

### TEXTBOOK
Established anatomical/anthropometric textbooks. Medium confidence - secondary sources.

### SECONDARY_REFERENCE
Literature reviews, meta-analyses, or summaries. Medium confidence.

### ASSUMPTION
Values assumed due to lack of data. Low confidence - explicitly marked.

### DERIVED
Values calculated from other reference data. Confidence depends on source data quality.

---

## Reference Data Categories

### Anthropometric Data
External body measurements used for scaling and proportions.

**Data Types:**
- Height distributions by age/gender
- Body segment lengths as percentages of height
- Body widths (shoulder, hip, chest)
- Body depths (chest, abdominal)
- Circumferences (chest, waist, hip)

**Target Sources:**
- NHANES (National Health and Nutrition Examination Survey)
- WHO Global Database on Body Mass Index
- ANSUR (Anthropometric Survey of U.S. Army Personnel)
- CAESAR (Civilian American and European Surface Anthropometry Resource)

### Osteometric Data
Bone-specific measurements used for detailed reconstruction.

**Data Types:**
- Individual bone lengths (femur, tibia, humerus, etc.)
- Bone dimensions (width, height, depth)
- Articular surface dimensions
- Landmark positions on bones

**Target Sources:**
- Osteometric databases
- Forensic anthropology references
- Medical imaging studies
- Anatomical research collections

### Biomechanical Data
Joint center locations and motion ranges.

**Data Types:**
- Joint center positions relative to landmarks
- Joint rotation axes
- Motion range limits
- Joint constraint definitions

**Target Sources:**
- ISB (International Society of Biomechanics) recommendations
- Biomechanical research studies
- Clinical measurement standards
- Motion capture calibration studies

### Proportion Data
Anatomical proportion relationships.

**Data Types:**
- Head-to-body ratio
- Torso-to-limb ratio
- Upper-to-lower limb ratio
- Segment proportions

**Target Sources:**
- Classical proportion systems (Vitruvian, Leonardo)
- Modern anthropometric research
- Ergonomics databases
- Developmental biology research

### Demographic Data
Age, gender, and population-specific variations.

**Data Types:**
- Age-related anatomical changes
- Gender-specific differences
- Population/ethnic variations
- Developmental progression

**Target Sources:**
- Geriatric anthropology studies
- Sexual dimorphism research
- Population genetics studies
- Growth chart references

---

## Reference Data Structure

### Source Metadata
Each reference must include:
- `source_id`: Unique identifier
- `name`: Source name/title
- `type`: Source type (PRIMARY_RESEARCH, STANDARD, etc.)
- `authors`: Authors or institution
- `year`: Publication year
- `doi`: DOI where available
- `url`: URL where available
- `sample_size`: Sample size for studies
- `population`: Population description
- `confidence`: Subjective confidence assessment (HIGH/MEDIUM/LOW)
- `notes`: Additional context

### Value Metadata
Each reference value must include:
- `value_id`: Unique identifier
- `parameter`: Parameter name
- `value`: Numerical value
- `unit`: Unit of measurement
- `source_id`: Reference to source
- `population`: Target population
- `age_range`: Applicable age range
- `gender`: Applicable gender (MALE/FEMALE/BOTH)
- `confidence`: Value confidence (HIGH/MEDIUM/LOW/UNKNOWN)
- `derivation`: How value was obtained (MEASURED/CALCULATED/ASSUMED)
- `notes`: Additional context

---

## Current Reference Data Status

### Available Data (A0.4 Foundation)
- **NONE** - No reference data currently acquired

### Placeholder Strategy
During A0.4, reference data will be marked as:
- `UNKNOWN` - Value needed but not yet acquired
- `ASSUMED` - Temporary assumption with explicit documentation

### Acquisition Timeline
- **A0.4:** Establish reference data structure and placeholder system
- **A0.5:** Acquire critical reference data (anthropometric, osteometric)
- **A0.6:** Acquire detailed reference data (hand, foot, specialized)

---

## Reference Data Files

### File Structure
```
src/character_engine/data/anatomy/reference/
├── sources.json          # Source metadata
├── anthropometry.json    # Anthropometric data
├── osteometry.json       # Osteometric data
├── joint_centers.json    # Joint center data
└── proportions.json      # Proportion data
```

### Placeholder Format
Until real data is acquired, files will contain placeholder entries with status indicators:

```json
{
  "value_id": "PLACEHOLDER_TOTAL_HEIGHT",
  "parameter": "total_body_height",
  "value": null,
  "unit": "meters",
  "source_id": "UNKNOWN",
  "status": "UNKNOWN",
  "notes": "Reference data not yet acquired"
}
```

---

## Provenance Tracking

### Value Chain
Every value must maintain its provenance chain:
```
PRIMARY_SOURCE → MEASUREMENT → REFERENCE_VALUE → PARAMETER → RECONSTRUCTION
```

### Traceability Requirements
- Each parameter must reference its source value
- Each source value must reference its source
- Each source must have bibliographic information
- Derivations must document calculation method

### Validation Rules
- No value without traceable source
- No assumption without explicit marking
- No derivation without documented formula
- No circular references in source chain

---

## Reference Data Quality

### Quality Metrics
- **Accuracy:** Proximity to true anatomical value
- **Precision:** Consistency of measurement
- **Representativeness:** Applicability to target population
- **Currency:** Age of data (prefer <20 years)
- **Completeness:** Coverage of required parameters

### Validation Process
1. Cross-reference multiple sources where possible
2. Verify methodology documentation
3. Check sample size and population relevance
4. Assess publication quality and peer review
5. Evaluate consistency with established standards

---

## Future Acquisition Plan

### Priority 1: Critical Data (A0.5)
- NHANES anthropometric data
- ISB joint center recommendations
- Basic osteometric reference data
- Standard proportion relationships

### Priority 2: Detailed Data (A0.6)
- Detailed hand/foot osteometry
- Spine curvature parameters
- Age-specific modifications
- Gender-specific variations

### Priority 3: Specialized Data (Future)
- Population-specific variations
- Pathological ranges
- Clinical measurement data
- Advanced biomechanical models

---

## Integration with Reconstruction

### Data Flow
```
Reference Source → Reference Dataset → Parameter Set → Reconstruction
```

### Parameter Normalization
- Raw reference values may need normalization
- Apply age/gender adjustments as needed
- Scale to target height/weight as needed
- Document all normalization steps

### Version Control
- Reference datasets must be versioned
- Changes to reference data must be tracked
- Reconstruction reproducibility depends on reference data version

---

## Documentation Standards

### Source Documentation
Each source must have:
- Complete bibliographic citation
- DOI or URL where available
- Methodology description
- Sample characteristics
- Limitations noted

### Value Documentation
Each value must have:
- Clear parameter definition
- Measurement method
- Applicability conditions
- Uncertainty estimate
- Limitations noted

---

## References

### Standards Organizations
- **ISB:** International Society of Biomechanics
- **ASTM:** American Society for Testing and Materials
- **ISO:** International Organization for Standardization

### Data Repositories
- **NHANES:** https://www.cdc.gov/nchs/nhanes/
- **WHO:** https://www.who.int/data/
- **ANSUR:** https://open.ancestry.mil/

### Anatomical References
- Gray's Anatomy
- Netter's Atlas of Human Anatomy
- Williams' Clinical Anatomy

---

**STATUS:** FOUNDATION STRUCTURE ESTABLISHED  
**NEXT:** Acquire actual reference data in A0.5  
**MAINTAINER:** Character Engine Team
