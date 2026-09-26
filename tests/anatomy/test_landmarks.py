"""Anatomical landmark model tests."""

import pytest
from character_engine.domain.anatomy.landmarks import (
    LandmarkRegion,
    CoordinateSpace,
    Landmark,
    LandmarkSet,
    LandmarkSetBuilder,
    create_unknown_landmark,
    create_measured_landmark,
    create_midline_landmark,
    create_bilateral_landmark_pair
)
from character_engine.domain.anatomy.coordinate_system import LateralSide, CANONICAL_COORDINATE_SYSTEM
from character_engine.domain.anatomy.reference import Confidence


class TestLandmark:
    """Test landmark model."""
    
    def test_landmark_creation(self):
        """Test creating a landmark."""
        landmark = Landmark(
            id="TEST",
            name="Test Landmark",
            canonical_name="test_landmark",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        assert landmark.id == "TEST"
        assert landmark.name == "Test Landmark"
        assert landmark.coordinate == (1.0, 2.0, 3.0)
    
    def test_midline_landmark(self):
        """Test midline landmark."""
        landmark = Landmark(
            id="MIDLINE",
            name="Midline",
            canonical_name="midline",
            region=LandmarkRegion.GENERAL,
            coordinate=(0.0, 1.0, 2.0),
            coordinate_space=CoordinateSpace.WORLD,
            bilateral=False,
            side=LateralSide.MIDLINE
        )
        
        assert landmark.is_midline()
        assert not landmark.is_bilateral()
        assert landmark.get_side() == LateralSide.MIDLINE
    
    def test_bilateral_landmark(self):
        """Test bilateral landmark."""
        landmark = Landmark(
            id="LEFT",
            name="Left",
            canonical_name="left",
            region=LandmarkRegion.GENERAL,
            coordinate=(-0.5, 1.0, 2.0),
            coordinate_space=CoordinateSpace.WORLD,
            bilateral=True,
            side=LateralSide.LEFT
        )
        
        assert landmark.is_bilateral()
        assert not landmark.is_midline()
        assert landmark.is_left()
        assert not landmark.is_right()
    
    def test_coordinate_accessors(self):
        """Test coordinate accessor methods."""
        landmark = Landmark(
            id="TEST",
            name="Test",
            canonical_name="test",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        assert landmark.get_x() == 1.0
        assert landmark.get_y() == 2.0
        assert landmark.get_z() == 3.0
    
    def test_world_space_check(self):
        """Test world-space coordinate check."""
        world_landmark = Landmark(
            id="WORLD",
            name="World",
            canonical_name="world",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        local_landmark = Landmark(
            id="LOCAL",
            name="Local",
            canonical_name="local",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.LOCAL
        )
        
        assert world_landmark.is_world_space()
        assert not local_landmark.is_world_space()
    
    def test_known_landmark(self):
        """Test known landmark check."""
        known_landmark = Landmark(
            id="KNOWN",
            name="Known",
            canonical_name="known",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD,
            source_id="SOURCE_001"
        )
        
        unknown_landmark = Landmark(
            id="UNKNOWN",
            name="Unknown",
            canonical_name="unknown",
            region=LandmarkRegion.GENERAL,
            coordinate=(0.0, 0.0, 0.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        assert known_landmark.is_known()
        assert not unknown_landmark.is_known()


class TestLandmarkSet:
    """Test landmark set model."""
    
    def test_landmark_set_creation(self):
        """Test creating a landmark set."""
        landmark1 = Landmark(
            id="L1",
            name="Landmark 1",
            canonical_name="landmark1",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        landmark2 = Landmark(
            id="L2",
            name="Landmark 2",
            canonical_name="landmark2",
            region=LandmarkRegion.GENERAL,
            coordinate=(4.0, 5.0, 6.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={"L1": landmark1, "L2": landmark2}
        )
        
        assert landmark_set.set_id == "SET"
        assert len(landmark_set.landmarks) == 2
    
    def test_get_landmark(self):
        """Test retrieving landmark by ID."""
        landmark = Landmark(
            id="TEST",
            name="Test",
            canonical_name="test",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={"TEST": landmark}
        )
        
        retrieved = landmark_set.get_landmark("TEST")
        assert retrieved is not None
        assert retrieved.id == "TEST"
    
    def test_get_landmark_by_canonical_name(self):
        """Test retrieving landmark by canonical name."""
        landmark = Landmark(
            id="TEST",
            name="Test",
            canonical_name="canonical_test",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={"TEST": landmark}
        )
        
        retrieved = landmark_set.get_landmark_by_canonical_name("canonical_test")
        assert retrieved is not None
        assert retrieved.canonical_name == "canonical_test"
    
    def test_get_bilateral_pair(self):
        """Test retrieving bilateral landmark pair."""
        left = Landmark(
            id="LEFT",
            name="Left",
            canonical_name="femur_L",
            region=LandmarkRegion.HIP,
            coordinate=(-0.1, 1.0, 0.5),
            coordinate_space=CoordinateSpace.WORLD,
            bilateral=True,
            side=LateralSide.LEFT
        )
        
        right = Landmark(
            id="RIGHT",
            name="Right",
            canonical_name="femur_R",
            region=LandmarkRegion.HIP,
            coordinate=(0.1, 1.0, 0.5),
            coordinate_space=CoordinateSpace.WORLD,
            bilateral=True,
            side=LateralSide.RIGHT
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={"LEFT": left, "RIGHT": right}
        )
        
        retrieved_left, retrieved_right = landmark_set.get_bilateral_pair("femur")
        assert retrieved_left is not None
        assert retrieved_right is not None
        assert retrieved_left.is_left()
        assert retrieved_right.is_right()
    
    def test_get_landmarks_by_region(self):
        """Test retrieving landmarks by region."""
        pelvis_landmark = Landmark(
            id="PELVIS",
            name="Pelvis",
            canonical_name="pelvis",
            region=LandmarkRegion.PELVIS,
            coordinate=(0.0, 0.0, 0.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        shoulder_landmark = Landmark(
            id="SHOULDER",
            name="Shoulder",
            canonical_name="shoulder",
            region=LandmarkRegion.SHOULDER,
            coordinate=(0.0, 1.0, 0.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={"PELVIS": pelvis_landmark, "SHOULDER": shoulder_landmark}
        )
        
        pelvis_landmarks = landmark_set.get_landmarks_by_region(LandmarkRegion.PELVIS)
        shoulder_landmarks = landmark_set.get_landmarks_by_region(LandmarkRegion.SHOULDER)
        
        assert len(pelvis_landmarks) == 1
        assert len(shoulder_landmarks) == 1
        assert pelvis_landmarks[0].region == LandmarkRegion.PELVIS
    
    def test_get_midline_landmarks(self):
        """Test retrieving midline landmarks."""
        midline = Landmark(
            id="MIDLINE",
            name="Midline",
            canonical_name="midline",
            region=LandmarkRegion.GENERAL,
            coordinate=(0.0, 1.0, 0.0),
            coordinate_space=CoordinateSpace.WORLD,
            bilateral=False
        )
        
        bilateral = Landmark(
            id="BILATERAL",
            name="Bilateral",
            canonical_name="bilateral",
            region=LandmarkRegion.GENERAL,
            coordinate=(0.1, 1.0, 0.0),
            coordinate_space=CoordinateSpace.WORLD,
            bilateral=True,
            side=LateralSide.RIGHT
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={"MIDLINE": midline, "BILATERAL": bilateral}
        )
        
        midline_landmarks = landmark_set.get_midline_landmarks()
        bilateral_landmarks = landmark_set.get_bilateral_landmarks()
        
        assert len(midline_landmarks) == 1
        assert len(bilateral_landmarks) == 1
    
    def test_mirror_landmark(self):
        """Test landmark mirroring."""
        left_landmark = Landmark(
            id="LEFT",
            name="Left",
            canonical_name="left",
            region=LandmarkRegion.GENERAL,
            coordinate=(-0.5, 1.0, 2.0),
            coordinate_space=CoordinateSpace.WORLD,
            bilateral=True,
            side=LateralSide.LEFT
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={}
        )
        
        mirrored = landmark_set.mirror_landmark(left_landmark)
        
        assert mirrored.get_side() == LateralSide.RIGHT
        assert mirrored.get_x() == 0.5  # Sign flipped
        assert mirrored.get_y() == 1.0  # Preserved
        assert mirrored.get_z() == 2.0  # Preserved
    
    def test_validate_bilateral_symmetry(self):
        """Test bilateral symmetry validation."""
        left = Landmark(
            id="LEFT",
            name="Left",
            canonical_name="femur_L",
            region=LandmarkRegion.HIP,
            coordinate=(-0.1, 1.0, 0.5),
            coordinate_space=CoordinateSpace.WORLD,
            bilateral=True,
            side=LateralSide.LEFT
        )
        
        right = Landmark(
            id="RIGHT",
            name="Right",
            canonical_name="femur_R",
            region=LandmarkRegion.HIP,
            coordinate=(0.1, 1.0, 0.5),
            coordinate_space=CoordinateSpace.WORLD,
            bilateral=True,
            side=LateralSide.RIGHT
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={"LEFT": left, "RIGHT": right}
        )
        
        results = landmark_set.validate_bilateral_symmetry()
        
        assert "femur" in results
        assert results["femur"] is True  # Should be symmetric


class TestLandmarkSetBuilder:
    """Test landmark set builder."""
    
    def test_builder_creation(self):
        """Test creating a builder."""
        builder = LandmarkSetBuilder("SET", "Test Set", "1.0.0")
        
        assert builder.set_id == "SET"
        assert builder.name == "Test Set"
    
    def test_builder_add_landmark(self):
        """Test adding landmark to builder."""
        landmark = Landmark(
            id="TEST",
            name="Test",
            canonical_name="test",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        builder = LandmarkSetBuilder("SET", "Test Set", "1.0.0")
        result = builder.add_landmark(landmark)
        
        assert result is builder  # Builder pattern
        assert "TEST" in builder.landmarks
    
    def test_builder_build(self):
        """Test building landmark set from builder."""
        landmark = Landmark(
            id="TEST",
            name="Test",
            canonical_name="test",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        builder = LandmarkSetBuilder("SET", "Test Set", "1.0.0")
        builder.add_landmark(landmark)
        
        landmark_set = builder.build()
        
        assert isinstance(landmark_set, LandmarkSet)
        assert landmark_set.set_id == "SET"
        assert len(landmark_set.landmarks) == 1


class TestLandmarkFactoryFunctions:
    """Test landmark factory functions."""
    
    def test_create_unknown_landmark(self):
        """Test creating unknown landmark."""
        landmark = create_unknown_landmark("test", LandmarkRegion.GENERAL)
        
        assert landmark.canonical_name == "test"
        assert landmark.coordinate == (0.0, 0.0, 0.0)
        assert landmark.confidence == Confidence.UNKNOWN
        assert not landmark.is_known()
    
    def test_create_measured_landmark(self):
        """Test creating measured landmark."""
        landmark = create_measured_landmark(
            "test",
            LandmarkRegion.GENERAL,
            (1.0, 2.0, 3.0),
            "SOURCE_001"
        )
        
        assert landmark.canonical_name == "test"
        assert landmark.coordinate == (1.0, 2.0, 3.0)
        assert landmark.source_id == "SOURCE_001"
        assert landmark.confidence == Confidence.HIGH
        assert landmark.is_known()
    
    def test_create_midline_landmark(self):
        """Test creating midline landmark."""
        landmark = create_midline_landmark(
            "midline",
            LandmarkRegion.GENERAL,
            (0.0, 1.0, 0.0),
            "SOURCE_001"
        )
        
        assert landmark.canonical_name == "midline"
        assert landmark.is_midline()
        assert landmark.get_side() == LateralSide.MIDLINE
        assert not landmark.is_bilateral()
    
    def test_create_bilateral_landmark_pair(self):
        """Test creating bilateral landmark pair."""
        left, right = create_bilateral_landmark_pair(
            "femur",
            LandmarkRegion.HIP,
            (-0.1, 1.0, 0.5),
            (0.1, 1.0, 0.5),
            "SOURCE_001"
        )
        
        assert left.is_left()
        assert right.is_right()
        assert left.canonical_name == "femur_L"
        assert right.canonical_name == "femur_R"
        assert left.get_x() == -0.1
        assert right.get_x() == 0.1


class TestLandmarkIntegration:
    """Integration tests for landmark system."""
    
    def test_landmark_coordinate_system_integration(self):
        """Test landmark integration with coordinate system."""
        landmark = Landmark(
            id="TEST",
            name="Test",
            canonical_name="test",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={"TEST": landmark},
            coordinate_system=CANONICAL_COORDINATE_SYSTEM
        )
        
        # Verify coordinate system integration
        assert landmark_set.coordinate_system == CANONICAL_COORDINATE_SYSTEM
        assert landmark_set.coordinate_system.is_right_handed()
    
    def test_bilateral_symmetry_verification(self):
        """Test bilateral symmetry verification across multiple pairs."""
        pairs = [
            ("femur", LandmarkRegion.HIP, (-0.1, 1.0, 0.5), (0.1, 1.0, 0.5)),
            ("tibia", LandmarkRegion.KNEE, (-0.08, 0.5, 0.3), (0.08, 0.5, 0.3)),
            ("humerus", LandmarkRegion.SHOULDER, (-0.15, 1.5, 0.4), (0.15, 1.5, 0.4))
        ]
        
        landmarks = {}
        for name, region, left_coord, right_coord in pairs:
            left, right = create_bilateral_landmark_pair(name, region, left_coord, right_coord, "SOURCE_001")
            landmarks[f"{name}_L"] = left
            landmarks[f"{name}_R"] = right
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks=landmarks
        )
        
        results = landmark_set.validate_bilateral_symmetry()
        
        # All pairs should be symmetric
        assert all(results.values())
        assert len(results) == 3
    
    def test_landmark_provenance_tracking(self):
        """Test that landmarks maintain provenance."""
        landmark = Landmark(
            id="TEST",
            name="Test",
            canonical_name="test",
            region=LandmarkRegion.GENERAL,
            coordinate=(1.0, 2.0, 3.0),
            coordinate_space=CoordinateSpace.WORLD,
            source_id="RESEARCH_001",
            confidence=Confidence.HIGH,
            notes="Measured from reference data"
        )
        
        landmark_set = LandmarkSet(
            set_id="SET",
            name="Test Set",
            version="1.0.0",
            landmarks={"TEST": landmark}
        )
        
        # Verify provenance tracking
        retrieved = landmark_set.get_landmark("TEST")
        assert retrieved.source_id == "RESEARCH_001"
        assert retrieved.confidence == Confidence.HIGH
        assert "Measured from reference data" in retrieved.notes
