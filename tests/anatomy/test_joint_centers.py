"""Joint center model tests."""

import pytest
from character_engine.domain.anatomy.joints import (
    JointType,
    JointCenterType,
    JointCenter,
    JointCenterSet,
    JointCenterSetBuilder,
    create_unknown_joint_center,
    create_measured_joint_center,
    create_bilateral_joint_center_pair
)
from character_engine.domain.anatomy.coordinate_system import LateralSide
from character_engine.domain.anatomy.reference import Confidence


class TestJointCenter:
    """Test joint center model."""
    
    def test_joint_center_creation(self):
        """Test creating a joint center."""
        joint_center = JointCenter(
            id="SHOULDER_L",
            name="Left Shoulder",
            canonical_name="shoulder_L",
            joint_type=JointType.SHOULDER,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.2, 0.0, 1.5),
            bilateral=True,
            side=LateralSide.LEFT
        )
        
        assert joint_center.id == "SHOULDER_L"
        assert joint_center.joint_type == JointType.SHOULDER
        assert joint_center.center_type == JointCenterType.ANATOMICAL_CENTER
    
    def test_anatomical_center_check(self):
        """Test anatomical center check."""
        anatomical = JointCenter(
            id="ANATOMICAL",
            name="Anatomical",
            canonical_name="anatomical",
            joint_type=JointType.SHOULDER,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        bone_endpoint = JointCenter(
            id="BONE",
            name="Bone Endpoint",
            canonical_name="bone",
            joint_type=JointType.SHOULDER,
            center_type=JointCenterType.BONE_ENDPOINT,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        assert anatomical.is_anatomical_center()
        assert not anatomical.is_bone_endpoint()
        assert bone_endpoint.is_bone_endpoint()
        assert not bone_endpoint.is_anatomical_center()
    
    def test_bilateral_joint_center(self):
        """Test bilateral joint center."""
        left = JointCenter(
            id="LEFT",
            name="Left",
            canonical_name="left",
            joint_type=JointType.HIP,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(-0.1, 0.0, 0.9),
            bilateral=True,
            side=LateralSide.LEFT
        )
        
        right = JointCenter(
            id="RIGHT",
            name="Right",
            canonical_name="right",
            joint_type=JointType.HIP,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.1, 0.0, 0.9),
            bilateral=True,
            side=LateralSide.RIGHT
        )
        
        assert left.is_bilateral()
        assert left.is_left()
        assert not left.is_right()
        assert right.is_right()
        assert not right.is_left()
    
    def test_coordinate_accessors(self):
        """Test coordinate accessor methods."""
        joint_center = JointCenter(
            id="TEST",
            name="Test",
            canonical_name="test",
            joint_type=JointType.KNEE,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(1.0, 2.0, 3.0)
        )
        
        assert joint_center.get_x() == 1.0
        assert joint_center.get_y() == 2.0
        assert joint_center.get_z() == 3.0
    
    def test_known_joint_center(self):
        """Test known joint center check."""
        known = JointCenter(
            id="KNOWN",
            name="Known",
            canonical_name="known",
            joint_type=JointType.ANKLE,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.1, 0.0, 0.1),
            source_id="SOURCE_001"
        )
        
        unknown = JointCenter(
            id="UNKNOWN",
            name="Unknown",
            canonical_name="unknown",
            joint_type=JointType.ANKLE,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        assert known.is_known()
        assert not unknown.is_known()


class TestJointCenterSet:
    """Test joint center set model."""
    
    def test_joint_center_set_creation(self):
        """Test creating a joint center set."""
        jc1 = JointCenter(
            id="SHOULDER_L",
            name="Left Shoulder",
            canonical_name="shoulder_L",
            joint_type=JointType.SHOULDER,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.2, 0.0, 1.5)
        )
        
        jc2 = JointCenter(
            id="HIP_L",
            name="Left Hip",
            canonical_name="hip_L",
            joint_type=JointType.HIP,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(-0.1, 0.0, 0.9)
        )
        
        joint_center_set = JointCenterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            joint_centers={"SHOULDER_L": jc1, "HIP_L": jc2}
        )
        
        assert joint_center_set.set_id == "SET"
        assert len(joint_center_set.joint_centers) == 2
    
    def test_get_joint_center(self):
        """Test retrieving joint center by ID."""
        jc = JointCenter(
            id="TEST",
            name="Test",
            canonical_name="test",
            joint_type=JointType.ELBOW,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        joint_center_set = JointCenterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            joint_centers={"TEST": jc}
        )
        
        retrieved = joint_center_set.get_joint_center("TEST")
        assert retrieved is not None
        assert retrieved.id == "TEST"
    
    def test_get_joint_center_by_canonical_name(self):
        """Test retrieving joint center by canonical name."""
        jc = JointCenter(
            id="TEST",
            name="Test",
            canonical_name="canonical_test",
            joint_type=JointType.WRIST,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        joint_center_set = JointCenterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            joint_centers={"TEST": jc}
        )
        
        retrieved = joint_center_set.get_joint_center_by_canonical_name("canonical_test")
        assert retrieved is not None
        assert retrieved.canonical_name == "canonical_test"
    
    def test_get_bilateral_pair(self):
        """Test retrieving bilateral joint center pair."""
        left = JointCenter(
            id="LEFT",
            name="Left",
            canonical_name="hip_L",
            joint_type=JointType.HIP,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(-0.1, 0.0, 0.9),
            bilateral=True,
            side=LateralSide.LEFT
        )
        
        right = JointCenter(
            id="RIGHT",
            name="Right",
            canonical_name="hip_R",
            joint_type=JointType.HIP,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.1, 0.0, 0.9),
            bilateral=True,
            side=LateralSide.RIGHT
        )
        
        joint_center_set = JointCenterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            joint_centers={"LEFT": left, "RIGHT": right}
        )
        
        retrieved_left, retrieved_right = joint_center_set.get_bilateral_pair("hip")
        assert retrieved_left is not None
        assert retrieved_right is not None
        assert retrieved_left.is_left()
        assert retrieved_right.is_right()
    
    def test_get_joint_centers_by_type(self):
        """Test retrieving joint centers by type."""
        shoulder = JointCenter(
            id="SHOULDER",
            name="Shoulder",
            canonical_name="shoulder",
            joint_type=JointType.SHOULDER,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        hip = JointCenter(
            id="HIP",
            name="Hip",
            canonical_name="hip",
            joint_type=JointType.HIP,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        joint_center_set = JointCenterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            joint_centers={"SHOULDER": shoulder, "HIP": hip}
        )
        
        shoulder_jcs = joint_center_set.get_joint_centers_by_type(JointType.SHOULDER)
        hip_jcs = joint_center_set.get_joint_centers_by_type(JointType.HIP)
        
        assert len(shoulder_jcs) == 1
        assert len(hip_jcs) == 1
        assert shoulder_jcs[0].joint_type == JointType.SHOULDER
    
    def test_get_anatomical_centers(self):
        """Test retrieving anatomical centers."""
        anatomical = JointCenter(
            id="ANATOMICAL",
            name="Anatomical",
            canonical_name="anatomical",
            joint_type=JointType.SHOULDER,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        bone_endpoint = JointCenter(
            id="BONE",
            name="Bone",
            canonical_name="bone",
            joint_type=JointType.SHOULDER,
            center_type=JointCenterType.BONE_ENDPOINT,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        joint_center_set = JointCenterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            joint_centers={"ANATOMICAL": anatomical, "BONE": bone_endpoint}
        )
        
        anatomical_centers = joint_center_set.get_anatomical_centers()
        bone_endpoints = joint_center_set.get_bone_endpoints()
        
        assert len(anatomical_centers) == 1
        assert len(bone_endpoints) == 1
        assert anatomical_centers[0].is_anatomical_center()
        assert bone_endpoints[0].is_bone_endpoint()


class TestJointCenterSetBuilder:
    """Test joint center set builder."""
    
    def test_builder_creation(self):
        """Test creating a builder."""
        builder = JointCenterSetBuilder("SET", "Test Set", "1.0.0")
        
        assert builder.set_id == "SET"
        assert builder.name == "Test Set"
    
    def test_builder_add_joint_center(self):
        """Test adding joint center to builder."""
        jc = JointCenter(
            id="TEST",
            name="Test",
            canonical_name="test",
            joint_type=JointType.KNEE,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        builder = JointCenterSetBuilder("SET", "Test Set", "1.0.0")
        result = builder.add_joint_center(jc)
        
        assert result is builder  # Builder pattern
        assert "TEST" in builder.joint_centers
    
    def test_builder_build(self):
        """Test building joint center set from builder."""
        jc = JointCenter(
            id="TEST",
            name="Test",
            canonical_name="test",
            joint_type=JointType.ANKLE,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.0, 0.0, 0.0)
        )
        
        builder = JointCenterSetBuilder("SET", "Test Set", "1.0.0")
        builder.add_joint_center(jc)
        
        joint_center_set = builder.build()
        
        assert isinstance(joint_center_set, JointCenterSet)
        assert joint_center_set.set_id == "SET"
        assert len(joint_center_set.joint_centers) == 1


class TestJointCenterFactoryFunctions:
    """Test joint center factory functions."""
    
    def test_create_unknown_joint_center(self):
        """Test creating unknown joint center."""
        jc = create_unknown_joint_center("test", JointType.SHOULDER)
        
        assert jc.canonical_name == "test"
        assert jc.coordinate == (0.0, 0.0, 0.0)
        assert jc.confidence == Confidence.UNKNOWN
        assert not jc.is_known()
    
    def test_create_measured_joint_center(self):
        """Test creating measured joint center."""
        jc = create_measured_joint_center(
            "test",
            JointType.HIP,
            (0.1, 0.0, 0.9),
            "SOURCE_001"
        )
        
        assert jc.canonical_name == "test"
        assert jc.coordinate == (0.1, 0.0, 0.9)
        assert jc.source_id == "SOURCE_001"
        assert jc.confidence == Confidence.HIGH
        assert jc.is_known()
    
    def test_create_bilateral_joint_center_pair(self):
        """Test creating bilateral joint center pair."""
        left, right = create_bilateral_joint_center_pair(
            "hip",
            JointType.HIP,
            (-0.1, 0.0, 0.9),
            (0.1, 0.0, 0.9),
            "SOURCE_001"
        )
        
        assert left.is_left()
        assert right.is_right()
        assert left.canonical_name == "hip_L"
        assert right.canonical_name == "hip_R"
        assert left.get_x() == -0.1
        assert right.get_x() == 0.1


class TestJointCenterIntegration:
    """Integration tests for joint center system."""
    
    def test_joint_center_provenance_tracking(self):
        """Test that joint centers maintain provenance."""
        jc = JointCenter(
            id="TEST",
            name="Test",
            canonical_name="test",
            joint_type=JointType.SHOULDER,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.2, 0.0, 1.5),
            source_id="ISB_001",
            confidence=Confidence.HIGH,
            parent_bone="clavicle",
            child_bone="humerus",
            notes="Calculated using ISB recommendations"
        )
        
        joint_center_set = JointCenterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            joint_centers={"TEST": jc}
        )
        
        # Verify provenance tracking
        retrieved = joint_center_set.get_joint_center("TEST")
        assert retrieved.source_id == "ISB_001"
        assert retrieved.confidence == Confidence.HIGH
        assert retrieved.parent_bone == "clavicle"
        assert retrieved.child_bone == "humerus"
        assert "ISB recommendations" in retrieved.notes
    
    def test_joint_center_type_distinction(self):
        """Test distinction between joint center types."""
        anatomical = JointCenter(
            id="ANATOMICAL",
            name="Anatomical",
            canonical_name="anatomical",
            joint_type=JointType.HIP,
            center_type=JointCenterType.ANATOMICAL_CENTER,
            coordinate=(0.1, 0.0, 0.9)
        )
        
        bone_endpoint = JointCenter(
            id="BONE",
            name="Bone Endpoint",
            canonical_name="bone",
            joint_type=JointType.HIP,
            center_type=JointCenterType.BONE_ENDPOINT,
            coordinate=(0.1, 0.0, 0.9)
        )
        
        joint_center_set = JointCenterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            joint_centers={"ANATOMICAL": anatomical, "BONE": bone_endpoint}
        )
        
        anatomical_centers = joint_center_set.get_anatomical_centers()
        bone_endpoints = joint_center_set.get_bone_endpoints()
        
        # Verify type distinction
        assert len(anatomical_centers) == 1
        assert len(bone_endpoints) == 1
        assert anatomical_centers[0].center_type == JointCenterType.ANATOMICAL_CENTER
        assert bone_endpoints[0].center_type == JointCenterType.BONE_ENDPOINT
    
    def test_all_joint_types_representation(self):
        """Test that all major joint types can be represented."""
        joint_types = [
            JointType.SHOULDER,
            JointType.ELBOW,
            JointType.WRIST,
            JointType.HIP,
            JointType.KNEE,
            JointType.ANKLE
        ]
        
        joint_centers = {}
        for i, joint_type in enumerate(joint_types):
            jc = JointCenter(
                id=f"JC_{i}",
                name=f"Joint {i}",
                canonical_name=f"joint_{i}",
                joint_type=joint_type,
                center_type=JointCenterType.ANATOMICAL_CENTER,
                coordinate=(0.0, 0.0, 0.0)
            )
            joint_centers[f"JC_{i}"] = jc
        
        joint_center_set = JointCenterSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            joint_centers=joint_centers
        )
        
        # Verify all joint types are represented
        for joint_type in joint_types:
            type_jcs = joint_center_set.get_joint_centers_by_type(joint_type)
            assert len(type_jcs) == 1
            assert type_jcs[0].joint_type == joint_type
