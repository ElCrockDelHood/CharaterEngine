# Anatomical Reconstruction Architecture

## Overview

The anatomical reconstruction architecture provides a deterministic, parameterized system for generating human anatomical skeletons from subject profiles. This architecture implements the foundation for Sprint A0.4 "Anatomical Foundation Engineering."

## Architecture Components

### 1. Reference Data Infrastructure

**Location**: `src/character_engine/domain/anatomy/reference/`

The reference data infrastructure manages anatomical reference data with full provenance tracking:

- **ReferenceManager**: Manages reference data sources and their acquisition status
- **ReferenceDataManager**: Loads and provides access to anthropometric and biomechanical data
- **ReferenceData**: Data structure with provenance tracking (value, unit, confidence, source)
- **ReferenceSourceEntry**: Metadata for reference data sources

**Key Features**:
- Placeholder data support for development
- Source registry for tracking data acquisition
- Confidence levels for all reference values
- Gender-specific adjustments
- Joint center offset data

### 2. Parameter Normalization

**Location**: `src/character_engine/domain/anatomy/reconstruction/parameter_normalizer.py`

The parameter normalizer converts raw anatomical parameters to standardized reference values:

- **ParameterNormalizer**: Normalizes subject parameters using reference data
- **NormalizedParameter**: Standardized parameter with normalization method
- **NormalizationMethod**: Enum of normalization approaches (height-based, gender-adjusted, etc.)

**Key Features**:
- Height-based normalization for ratio parameters
- Gender-specific adjustments
- Age-specific corrections (framework)
- Population-based adjustments (framework)
- Caching for performance

### 3. Proportion Calculation

**Location**: `src/character_engine/domain/anatomy/reconstruction/proportion_calculator.py`

The proportion calculator derives body proportions from normalized parameters:

- **ProportionCalculator**: Calculates body segment proportions
- **CalculatedProportion**: Proportion with calculation method and metadata
- **CalculationMethod**: Enum of calculation approaches (ratio derivation, formula-based, etc.)

**Key Features**:
- Body segment calculation (head, torso, limbs)
- Bone dimension derivation from segments
- Limb proportion calculation
- Coordinate position calculation
- Proportion chain validation

### 4. Landmark Positioning

**Location**: `src/character_engine/domain/anatomy/reconstruction/landmark_positioner.py`

The landmark positioner calculates 3D positions for anatomical landmarks:

- **LandmarkPositioner**: Positions landmarks in anatomical coordinate system
- **LandmarkPosition**: 3D position with provenance and method tracking
- **PositioningMethod**: Enum of positioning approaches (ratio derivation, offset-based, etc.)

**Key Features**:
- Core landmark positioning (origin, vertex, center of mass)
- Joint center positioning
- Body segment endpoint positioning
- Bilateral landmark positioning (left/right)
- Distance calculation between landmarks

### 5. Bone Generation

**Location**: `src/character_engine/domain/anatomy/reconstruction/bone_generator.py`

The bone generator creates bone geometries from parameters and landmarks:

- **BoneGenerator**: Generates complete skeleton bone geometries
- **BoneGeometry**: Geometric representation with dimensions and positions
- **BoneGenerationMethod**: Enum of generation approaches (parameter-based, landmark-based, etc.)

**Key Features**:
- Axial skeleton generation (spine, skull, ribs)
- Appendicular skeleton generation (limbs)
- Bone dimension calculation
- Volume and surface area estimation
- Proportional scaling

### 6. Pipeline Orchestrator

**Location**: `src/character_engine/domain/anatomy/reconstruction/pipeline.py`

The pipeline orchestrator coordinates the complete reconstruction process:

- **ReconstructionPipeline**: Main pipeline coordinator
- **PipelineResult**: Complete reconstruction output with status
- **PipelineStage**: Enum of pipeline stages
- **PipelineStatus**: Enum of pipeline status

**Key Features**:
- Stage-by-stage execution
- Error handling and recovery
- Progress tracking
- Validation at each stage
- Comprehensive result reporting

### 7. Integration Adapter

**Location**: `src/character_engine/domain/anatomy/reconstruction/integration.py`

The integration adapter connects reconstruction with the existing pipeline:

- **ReconstructionIntegrationAdapter**: Bridge between reconstruction and existing pipeline
- **IntegrationConfig**: Configuration for integration behavior

**Key Features**:
- Seamless integration with existing skeleton data
- Enhancement of existing skeletons with reconstruction data
- Validation of integration results
- Configurable validation modes
- Subject profile generation from existing data

## Pipeline Flow

```
Subject Profile
     ↓
Parameter Normalization
     ↓
Proportion Calculation
     ↓
Landmark Positioning
     ↓
Bone Generation
     ↓
Validation
     ↓
Integration (optional)
     ↓
Enhanced Skeleton
```

## Data Flow

1. **Input**: Subject profile (height, weight, age, gender, ethnicity)
2. **Normalization**: Parameters normalized using reference data
3. **Proportion Calculation**: Body proportions derived from normalized parameters
4. **Landmark Positioning**: 3D positions calculated using proportions
5. **Bone Generation**: Bone geometries created from landmarks and proportions
6. **Output**: Complete skeleton with full provenance tracking

## Coordinate System

The reconstruction uses the anatomical coordinate system defined in `coordinate_system.py`:

- **Origin**: Mid-foot ground level
- **Y-axis**: Vertical (upward positive)
- **X-axis**: Lateral (right positive)
- **Z-axis**: Anterior-posterior (forward positive)
- **Handedness**: Right-handed coordinate system
- **Rotation**: Counter-clockwise positive when looking toward origin

## Reference Data Structure

Reference data is organized in JSON files under the references directory:

```
references/
├── source_registry.json      # Source metadata and status
├── anthropometry.json       # Anthropometric measurements
└── biomechanics.json        # Biomechanical data
```

## Testing

Comprehensive test coverage for all reconstruction components:

- **test_reference_manager.py**: Tests for reference data infrastructure
- **test_parameter_normalizer.py**: Tests for parameter normalization
- **test_proportion_calculator.py**: Tests for proportion calculation

## Integration with Existing Pipeline

The reconstruction architecture integrates with the existing character engine pipeline through:

1. **Enhancement Mode**: Reconstruction data enhances existing skeleton data
2. **Validation**: Existing validation system applies to reconstructed skeletons
3. **Serialization**: Reconstructed skeletons can be serialized like existing ones
4. **Builder Pattern**: Uses existing SkeletonBuilder for final skeleton construction

## Non-Negotiable Rules

The reconstruction architecture adheres to the following rules:

1. **Do not destroy existing pipeline**: Integration is additive, not replacement
2. **Do not overwrite human_adult_206.json**: Original data preserved
3. **Require provenance for all values**: Every anatomical value has traceable origin
4. **Do not "fit the tests":** Implementation based on architectural requirements
5. **Use placeholder data with clear marking**: All placeholder data marked as such

## Future Enhancements

The current implementation provides a foundation for future enhancements:

1. **Detailed Spine Model**: Individual vertebrae and intervertebral discs
2. **Hand/Foot Models**: Detailed bone structures for extremities
3. **Muscle System**: Muscle attachment points and volumes
4. **Advanced Validation**: Biomechanical constraint validation
5. **Real Reference Data**: Replace placeholders with actual anthropometric data

## Usage Example

```python
from character_engine.domain.anatomy.reconstruction import (
    ReconstructionPipeline,
    SubjectProfile
)
from character_engine.domain.anatomy.coordinate_system import CoordinateSystem
from pathlib import Path

# Initialize pipeline
references_dir = Path("references")
coordinate_system = CoordinateSystem()
pipeline = ReconstructionPipeline(references_dir, coordinate_system)

# Create subject profile
profile = SubjectProfile(
    height=1.80,  # meters
    weight=75.0,  # kg
    age=30,
    gender="male"
)

# Run reconstruction
result = pipeline.reconstruct(profile)

# Access results
print(f"Status: {result.status}")
print(f"Landmarks: {len(result.landmark_positions)}")
print(f"Bones: {len(result.bone_geometries)}")
```

## Documentation References

- **Coordinate System**: `docs/anatomy/COORDINATE_SYSTEM.md`
- **Reference Data**: `docs/anatomy/REFERENCE_DATA.md`
- **Joint Centers**: `docs/anatomy/JOINT_CENTERS.md`
- **Architecture**: `docs/audit/A03_RECONSTRUCTION_ARCHITECTURE.json`

## Status

This implementation represents the completion of Sprint A0.4 "Anatomical Foundation Engineering." All foundational components are in place with placeholder data, ready for enhancement with real reference data in future sprints.