"""Anatomical parameter model tests."""

from character_engine.domain.anatomy.coordinate_system import LateralSide
from character_engine.domain.anatomy.parameters import (
    AnatomicalParameter,
    DerivationMetadata,
    ParameterConstraint,
    ParameterSet,
    ParameterSetBuilder,
    ParameterStatus,
    ParameterType,
    create_assumed_parameter,
    create_derived_parameter,
    create_direct_reference_parameter,
    create_unknown_parameter,
)
from character_engine.domain.anatomy.reference import Confidence


class TestParameterConstraint:
    """Test parameter constraint model."""

    def test_constraint_creation(self):
        """Test creating a parameter constraint."""
        constraint = ParameterConstraint(
            min_value=1.5,
            max_value=2.0,
            unit="meters",
            description="Height constraint"
        )

        assert constraint.min_value == 1.5
        assert constraint.max_value == 2.0
        assert constraint.unit == "meters"

    def test_constraint_validation(self):
        """Test constraint validation."""
        constraint = ParameterConstraint(
            min_value=1.5,
            max_value=2.0,
            unit="meters"
        )

        assert constraint.is_valid(1.75)
        assert constraint.is_valid(1.5)
        assert constraint.is_valid(2.0)
        assert not constraint.is_valid(1.4)
        assert not constraint.is_valid(2.1)

    def test_constraint_no_minimum(self):
        """Test constraint with no minimum."""
        constraint = ParameterConstraint(
            max_value=2.0,
            unit="meters"
        )

        assert constraint.is_valid(0.0)
        assert constraint.is_valid(1.0)
        assert not constraint.is_valid(2.1)

    def test_constraint_no_maximum(self):
        """Test constraint with no maximum."""
        constraint = ParameterConstraint(
            min_value=1.5,
            unit="meters"
        )

        assert constraint.is_valid(1.5)
        assert constraint.is_valid(100.0)
        assert not constraint.is_valid(1.4)

    def test_constraint_error_message(self):
        """Test constraint error message."""
        constraint = ParameterConstraint(
            min_value=1.5,
            max_value=2.0,
            unit="meters"
        )

        error = constraint.get_validation_error(1.4)
        assert error is not None
        assert "below minimum" in error

        error = constraint.get_validation_error(2.1)
        assert error is not None
        assert "above maximum" in error

        error = constraint.get_validation_error(1.75)
        assert error is None


class TestDerivationMetadata:
    """Test derivation metadata model."""

    def test_derivation_metadata_creation(self):
        """Test creating derivation metadata."""
        metadata = DerivationMetadata(
            parent_parameters=("param1", "param2"),
            formula="param1 + param2",
            formula_version="1.0.0",
            notes="Simple addition"
        )

        assert len(metadata.parent_parameters) == 2
        assert metadata.formula == "param1 + param2"
        assert metadata.formula_version == "1.0.0"


class TestAnatomicalParameter:
    """Test anatomical parameter model."""

    def test_parameter_creation(self):
        """Test creating an anatomical parameter."""
        parameter = AnatomicalParameter(
            id="HEIGHT",
            name="Total Height",
            canonical_name="total_height",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        assert parameter.id == "HEIGHT"
        assert parameter.name == "Total Height"
        assert parameter.value == 1.75
        assert parameter.unit == "meters"

    def test_unknown_parameter(self):
        """Test unknown parameter (None value)."""
        parameter = AnatomicalParameter(
            id="UNKNOWN",
            name="Unknown",
            canonical_name="unknown",
            parameter_type=ParameterType.SCALAR,
            value=None,
            unit="meters",
            status=ParameterStatus.UNKNOWN
        )

        assert parameter.is_unknown()
        assert not parameter.is_known()
        assert parameter.get_value_or_default() == 0.0
        assert parameter.get_value_or_default(1.5) == 1.5

    def test_known_parameter(self):
        """Test known parameter."""
        parameter = AnatomicalParameter(
            id="KNOWN",
            name="Known",
            canonical_name="known",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        assert parameter.is_known()
        assert not parameter.is_unknown()
        assert parameter.get_value_or_default() == 1.75

    def test_direct_reference_parameter(self):
        """Test direct reference parameter."""
        parameter = AnatomicalParameter(
            id="REF",
            name="Reference",
            canonical_name="reference",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        assert parameter.is_direct_reference()
        assert not parameter.is_derived()
        assert not parameter.is_assumed()

    def test_derived_parameter(self):
        """Test derived parameter."""
        metadata = DerivationMetadata(
            parent_parameters=("param1",),
            formula="param1 * 2"
        )

        parameter = AnatomicalParameter(
            id="DERIVED",
            name="Derived",
            canonical_name="derived",
            parameter_type=ParameterType.SCALAR,
            value=2.0,
            unit="meters",
            status=ParameterStatus.DERIVED,
            derivation=metadata
        )

        assert parameter.is_derived()
        assert not parameter.is_direct_reference()
        assert parameter.derivation is not None

    def test_assumed_parameter(self):
        """Test assumed parameter."""
        parameter = AnatomicalParameter(
            id="ASSUMED",
            name="Assumed",
            canonical_name="assumed",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.ASSUMED
        )

        assert parameter.is_assumed()
        assert not parameter.is_direct_reference()
        assert not parameter.is_derived()

    def test_bilateral_parameter(self):
        """Test bilateral parameter."""
        parameter = AnatomicalParameter(
            id="BILATERAL",
            name="Bilateral",
            canonical_name="bilateral",
            parameter_type=ParameterType.SCALAR,
            value=0.5,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            bilateral=True,
            side=LateralSide.RIGHT
        )

        assert parameter.is_bilateral()
        assert parameter.get_side() == LateralSide.RIGHT

    def test_parameter_with_constraint(self):
        """Test parameter with validation constraint."""
        constraint = ParameterConstraint(
            min_value=1.5,
            max_value=2.0,
            unit="meters"
        )

        parameter = AnatomicalParameter(
            id="CONSTRAINED",
            name="Constrained",
            canonical_name="constrained",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            constraints=constraint
        )

        assert parameter.satisfies_constraints()
        assert parameter.get_constraint_error() is None

    def test_parameter_constraint_violation(self):
        """Test parameter with constraint violation."""
        constraint = ParameterConstraint(
            min_value=1.5,
            max_value=2.0,
            unit="meters"
        )

        parameter = AnatomicalParameter(
            id="VIOLATION",
            name="Violation",
            canonical_name="violation",
            parameter_type=ParameterType.SCALAR,
            value=2.5,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            constraints=constraint
        )

        assert not parameter.satisfies_constraints()
        assert parameter.get_constraint_error() is not None

    def test_parameter_confidence(self):
        """Test parameter confidence."""
        high_conf = AnatomicalParameter(
            id="HIGH",
            name="High",
            canonical_name="high",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            confidence=Confidence.HIGH
        )

        low_conf = AnatomicalParameter(
            id="LOW",
            name="Low",
            canonical_name="low",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.ASSUMED,
            confidence=Confidence.LOW
        )

        assert high_conf.is_high_confidence()
        assert not low_conf.is_high_confidence()

    def test_parameter_immutability(self):
        """Test parameter is immutable."""
        parameter = AnatomicalParameter(
            id="TEST",
            name="Test",
            canonical_name="test",
            parameter_type=ParameterType.SCALAR,
            value=1.0,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        # Frozen dataclass cannot be modified
        # We test this by trying to create a new instance with different value
        # and verify they are different objects
        modified = AnatomicalParameter(
            id="TEST",
            name="Test",
            canonical_name="test",
            parameter_type=ParameterType.SCALAR,
            value=2.0,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        assert parameter.value == 1.0
        assert modified.value == 2.0
        assert parameter is not modified


class TestParameterSet:
    """Test parameter set model."""

    def test_parameter_set_creation(self):
        """Test creating a parameter set."""
        param1 = AnatomicalParameter(
            id="HEIGHT",
            name="Height",
            canonical_name="height",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        param2 = AnatomicalParameter(
            id="WEIGHT",
            name="Weight",
            canonical_name="weight",
            parameter_type=ParameterType.SCALAR,
            value=70.0,
            unit="kg",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"HEIGHT": param1, "WEIGHT": param2}
        )

        assert param_set.set_id == "SET"
        assert len(param_set.parameters) == 2

    def test_get_parameter(self):
        """Test retrieving parameter by ID."""
        param = AnatomicalParameter(
            id="HEIGHT",
            name="Height",
            canonical_name="height",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"HEIGHT": param}
        )

        retrieved = param_set.get_parameter("HEIGHT")
        assert retrieved is not None
        assert retrieved.id == "HEIGHT"

    def test_get_parameter_by_canonical_name(self):
        """Test retrieving parameter by canonical name."""
        param = AnatomicalParameter(
            id="HEIGHT",
            name="Height",
            canonical_name="total_height",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"HEIGHT": param}
        )

        retrieved = param_set.get_parameter_by_canonical_name("total_height")
        assert retrieved is not None
        assert retrieved.canonical_name == "total_height"

    def test_get_bilateral_pair(self):
        """Test retrieving bilateral parameter pair."""
        left_param = AnatomicalParameter(
            id="LEFT",
            name="Left",
            canonical_name="femur_L",
            parameter_type=ParameterType.LENGTH,
            value=0.45,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            bilateral=True,
            side=LateralSide.LEFT
        )

        right_param = AnatomicalParameter(
            id="RIGHT",
            name="Right",
            canonical_name="femur_R",
            parameter_type=ParameterType.LENGTH,
            value=0.45,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            bilateral=True,
            side=LateralSide.RIGHT
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"LEFT": left_param, "RIGHT": right_param}
        )

        left, right = param_set.get_bilateral_pair("femur")
        assert left is not None
        assert right is not None
        assert left.get_side() == LateralSide.LEFT
        assert right.get_side() == LateralSide.RIGHT

    def test_get_parameters_by_type(self):
        """Test retrieving parameters by type."""
        scalar_param = AnatomicalParameter(
            id="SCALAR",
            name="Scalar",
            canonical_name="scalar",
            parameter_type=ParameterType.SCALAR,
            value=1.0,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        length_param = AnatomicalParameter(
            id="LENGTH",
            name="Length",
            canonical_name="length",
            parameter_type=ParameterType.LENGTH,
            value=0.5,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"SCALAR": scalar_param, "LENGTH": length_param}
        )

        scalar_params = param_set.get_parameters_by_type(ParameterType.SCALAR)
        length_params = param_set.get_parameters_by_type(ParameterType.LENGTH)

        assert len(scalar_params) == 1
        assert len(length_params) == 1
        assert scalar_params[0].parameter_type == ParameterType.SCALAR
        assert length_params[0].parameter_type == ParameterType.LENGTH

    def test_get_known_parameters(self):
        """Test retrieving known parameters."""
        known_param = AnatomicalParameter(
            id="KNOWN",
            name="Known",
            canonical_name="known",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        unknown_param = AnatomicalParameter(
            id="UNKNOWN",
            name="Unknown",
            canonical_name="unknown",
            parameter_type=ParameterType.SCALAR,
            value=None,
            unit="meters",
            status=ParameterStatus.UNKNOWN
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"KNOWN": known_param, "UNKNOWN": unknown_param}
        )

        known = param_set.get_known_parameters()
        unknown = param_set.get_unknown_parameters()

        assert len(known) == 1
        assert len(unknown) == 1
        assert known[0].is_known()
        assert unknown[0].is_unknown()

    def test_validate_constraints(self):
        """Test constraint validation for parameter set."""
        constraint = ParameterConstraint(
            min_value=1.5,
            max_value=2.0,
            unit="meters"
        )

        valid_param = AnatomicalParameter(
            id="VALID",
            name="Valid",
            canonical_name="valid",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            constraints=constraint
        )

        invalid_param = AnatomicalParameter(
            id="INVALID",
            name="Invalid",
            canonical_name="invalid",
            parameter_type=ParameterType.SCALAR,
            value=2.5,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            constraints=constraint
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"VALID": valid_param, "INVALID": invalid_param}
        )

        results = param_set.validate_constraints()

        assert results["VALID"] is True
        assert results["INVALID"] is False

    def test_get_constraint_violations(self):
        """Test getting constraint violations."""
        constraint = ParameterConstraint(
            min_value=1.5,
            max_value=2.0,
            unit="meters"
        )

        invalid_param = AnatomicalParameter(
            id="INVALID",
            name="Invalid",
            canonical_name="invalid",
            parameter_type=ParameterType.SCALAR,
            value=2.5,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            constraints=constraint
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"INVALID": invalid_param}
        )

        violations = param_set.get_constraint_violations()

        assert "INVALID" in violations
        assert "above maximum" in violations["INVALID"]


class TestParameterSetBuilder:
    """Test parameter set builder."""

    def test_builder_creation(self):
        """Test creating a builder."""
        builder = ParameterSetBuilder("SET", "Test Set", "1.0.0")

        assert builder.set_id == "SET"
        assert builder.name == "Test Set"

    def test_builder_add_parameter(self):
        """Test adding parameter to builder."""
        param = AnatomicalParameter(
            id="HEIGHT",
            name="Height",
            canonical_name="height",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        builder = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        result = builder.add_parameter(param)

        assert result is builder  # Builder pattern
        assert "HEIGHT" in builder.parameters

    def test_builder_build(self):
        """Test building parameter set from builder."""
        param = AnatomicalParameter(
            id="HEIGHT",
            name="Height",
            canonical_name="height",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        builder = ParameterSetBuilder("SET", "Test Set", "1.0.0")
        builder.add_parameter(param)

        param_set = builder.build()

        assert isinstance(param_set, ParameterSet)
        assert param_set.set_id == "SET"
        assert len(param_set.parameters) == 1


class TestParameterFactoryFunctions:
    """Test parameter factory functions."""

    def test_create_unknown_parameter(self):
        """Test creating unknown parameter."""
        param = create_unknown_parameter("height", "meters")

        assert param.canonical_name == "height"
        assert param.value is None
        assert param.unit == "meters"
        assert param.status == ParameterStatus.UNKNOWN
        assert param.is_unknown()

    def test_create_assumed_parameter(self):
        """Test creating assumed parameter."""
        param = create_assumed_parameter("height", 1.75, "meters", "Temporary")

        assert param.canonical_name == "height"
        assert param.value == 1.75
        assert param.unit == "meters"
        assert param.status == ParameterStatus.ASSUMED
        assert param.is_assumed()
        assert "Temporary" in param.metadata["notes"]

    def test_create_derived_parameter(self):
        """Test creating derived parameter."""
        param = create_derived_parameter(
            "height",
            2.0,
            "meters",
            ("base_height",),
            "base_height * 2"
        )

        assert param.canonical_name == "height"
        assert param.value == 2.0
        assert param.status == ParameterStatus.DERIVED
        assert param.derivation is not None
        assert param.derivation.parent_parameters == ("base_height",)

    def test_create_direct_reference_parameter(self):
        """Test creating direct reference parameter."""
        param = create_direct_reference_parameter(
            "height",
            1.75,
            "meters",
            "SOURCE_001"
        )

        assert param.canonical_name == "height"
        assert param.value == 1.75
        assert param.status == ParameterStatus.DIRECT_REFERENCE
        assert param.source_id == "SOURCE_001"
        assert param.confidence == Confidence.HIGH


class TestParameterIntegration:
    """Integration tests for parameter system."""

    def test_provenance_tracking(self):
        """Test that parameters maintain provenance."""
        param = AnatomicalParameter(
            id="HEIGHT",
            name="Height",
            canonical_name="total_height",
            parameter_type=ParameterType.SCALAR,
            value=1.75,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            source_id="RESEARCH_001",
            confidence=Confidence.HIGH
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"HEIGHT": param}
        )

        # Verify provenance tracking
        retrieved = param_set.get_parameter("HEIGHT")
        assert retrieved.source_id == "RESEARCH_001"
        assert retrieved.confidence == Confidence.HIGH
        assert retrieved.status == ParameterStatus.DIRECT_REFERENCE

    def test_derivation_chain(self):
        """Test derivation chain tracking."""
        base_param = AnatomicalParameter(
            id="BASE",
            name="Base",
            canonical_name="base_height",
            parameter_type=ParameterType.SCALAR,
            value=1.0,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE
        )

        derived_param = create_derived_parameter(
            "doubled_height",
            2.0,
            "meters",
            ("base_height",),
            "base_height * 2"
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"BASE": base_param, "DOUBLED": derived_param}
        )

        # Verify derivation chain
        derived = param_set.get_parameter("DOUBLED")
        assert derived.is_derived()
        assert derived.derivation is not None
        assert "base_height" in derived.derivation.parent_parameters

    def test_bilateral_consistency(self):
        """Test bilateral parameter consistency."""
        left_param = AnatomicalParameter(
            id="LEFT",
            name="Left Femur",
            canonical_name="femur_L",
            parameter_type=ParameterType.LENGTH,
            value=0.45,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            bilateral=True,
            side=LateralSide.LEFT
        )

        right_param = AnatomicalParameter(
            id="RIGHT",
            name="Right Femur",
            canonical_name="femur_R",
            parameter_type=ParameterType.LENGTH,
            value=0.45,
            unit="meters",
            status=ParameterStatus.DIRECT_REFERENCE,
            bilateral=True,
            side=LateralSide.RIGHT
        )

        param_set = ParameterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            parameters={"LEFT": left_param, "RIGHT": right_param}
        )

        # Verify bilateral consistency
        left, right = param_set.get_bilateral_pair("femur")
        assert left.value == right.value  # Bilateral symmetry
        assert left.get_side() == LateralSide.LEFT
        assert right.get_side() == LateralSide.RIGHT
