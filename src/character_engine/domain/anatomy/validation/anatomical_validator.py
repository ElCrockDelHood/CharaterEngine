"""Anatomical validator for skeletal reconstruction.

This module implements anatomical validation checks based on the A0.2
test specification, focusing on scale, joint centers, landmarks, and parameters.
"""

from typing import Dict, Any, Optional, List
from ..parameters import ParameterSet, ParameterSetBuilder, create_direct_reference_parameter
from ..landmarks import LandmarkSet, LandmarkSetBuilder, create_measured_landmark, create_bilateral_landmark_pair, LandmarkRegion, CoordinateSpace, LateralSide
from ..joints import JointCenterSet
from ..spine import SpineModel
from ..hands import HandModel
from ..feet import FootModel
from ..coordinate_system import CANONICAL_TOLERANCE
from .result import (
    AnatomicalValidationResult,
    AnatomicalValidationReport,
    AnatomicalValidationReportBuilder,
    AnatomicalValidationStatus,
    create_pass_result,
    create_fail_result,
    create_warning_result,
    create_unknown_result
)


class AnatomicalValidator:
    """Validator for anatomical correctness of reconstructed skeletons."""
    
    def __init__(self):
        self.tolerance = CANONICAL_TOLERANCE
    
    def validate_all(self, 
                    parameter_set: ParameterSet,
                    landmark_set: Optional[LandmarkSet] = None,
                    joint_center_set: Optional[JointCenterSet] = None,
                    spine_model: Optional[SpineModel] = None,
                    hand_models: Optional[List[HandModel]] = None,
                    foot_models: Optional[List[FootModel]] = None) -> AnatomicalValidationReport:
        """Run all anatomical validation checks.
        
        Args:
            parameter_set: Set of anatomical parameters
            landmark_set: Set of anatomical landmarks
            joint_center_set: Set of joint centers
            spine_model: Spine model
            hand_models: List of hand models
            foot_models: List of foot models
            
        Returns:
            Complete anatomical validation report
        """
        builder = AnatomicalValidationReportBuilder(
            report_id="ANATOMICAL_VALIDATION",
            skeleton_id="RECONSTRUCTED_SKELETON"
        )
        
        # Phase 1: Basic Scale Tests (BS-01 to BS-04)
        builder.add_result(self.validate_bs_01_height(parameter_set))
        builder.add_result(self.validate_bs_02_height_width_ratio(parameter_set))
        builder.add_result(self.validate_bs_03_head_proportion(parameter_set))
        builder.add_result(self.validate_bs_04_limb_proportions(parameter_set))
        
        # Phase 1: Joint Center Tests (JC-01 to JC-06)
        if joint_center_set:
            builder.add_result(self.validate_jc_01_shoulder_continuity(joint_center_set))
            builder.add_result(self.validate_jc_02_elbow_continuity(joint_center_set))
            builder.add_result(self.validate_jc_03_wrist_continuity(joint_center_set))
            builder.add_result(self.validate_jc_04_hip_continuity(joint_center_set))
            builder.add_result(self.validate_jc_05_knee_continuity(joint_center_set))
            builder.add_result(self.validate_jc_06_ankle_continuity(joint_center_set))
        else:
            # Add unknown results for joint center tests
            for i in range(1, 7):
                builder.add_result(create_unknown_result(
                    f"JC-0{i}",
                    f"Joint Center Test {i}",
                    "Joint center data not available"
                ))
        
        # Phase 1: Landmark Tests (LA-01 to LA-04)
        if landmark_set:
            builder.add_result(self.validate_la_01_landmark_completeness(landmark_set))
            builder.add_result(self.validate_la_02_bilateral_symmetry(landmark_set))
            builder.add_result(self.validate_la_03_midline_alignment(landmark_set))
            builder.add_result(self.validate_la_04_coordinate_validity(landmark_set))
        else:
            # Add unknown results for landmark tests
            for i in range(1, 5):
                builder.add_result(create_unknown_result(
                    f"LA-0{i}",
                    f"Landmark Test {i}",
                    "Landmark data not available"
                ))
        
        # Phase 1: Anatomical Parameter Tests (AP-01 to AP-05)
        builder.add_result(self.validate_ap_01_total_height(parameter_set))
        builder.add_result(self.validate_ap_02_torso_proportion(parameter_set))
        builder.add_result(self.validate_ap_03_upper_limb_proportion(parameter_set))
        builder.add_result(self.validate_ap_04_lower_limb_proportion(parameter_set))
        builder.add_result(self.validate_ap_05_bilateral_consistency(parameter_set))
        
        return builder.build()
    
    def validate_bs_01_height(self, parameter_set: ParameterSet) -> AnatomicalValidationResult:
        """BS-01: Validate total height is within normal human range (1.7-1.9m)."""
        height_param = parameter_set.get_parameter_by_canonical_name("total_height")
        
        if height_param is None or not height_param.is_known():
            return create_unknown_result("BS-01", "Total Height Validation", "Height parameter not available")
        
        height = height_param.value
        min_height = 1.7
        max_height = 1.9
        
        if min_height <= height <= max_height:
            return create_pass_result(
                "BS-01",
                "Total Height Validation",
                f"{min_height}-{max_height}m",
                f"{height:.2f}m"
            )
        else:
            deviation = f"{abs(height - 1.8):.2f}m"
            if height < min_height:
                deviation = f"-{abs(height - min_height):.2f}m"
            else:
                deviation = f"+{abs(height - max_height):.2f}m"
            
            return create_fail_result(
                "BS-01",
                "Total Height Validation",
                f"{min_height}-{max_height}m",
                f"{height:.2f}m",
                deviation,
                source="parameter model",
                recommendation="Adjust total height parameter to within normal human range"
            )
    
    def validate_bs_02_height_width_ratio(self, parameter_set: ParameterSet) -> AnatomicalValidationResult:
        """BS-02: Validate height/width ratio is within normal range."""
        height_param = parameter_set.get_parameter_by_canonical_name("total_height")
        shoulder_width_param = parameter_set.get_parameter_by_canonical_name("shoulder_width")
        
        if height_param is None or not height_param.is_known():
            return create_unknown_result("BS-02", "Height/Width Ratio Validation", "Height parameter not available")
        
        if shoulder_width_param is None or not shoulder_width_param.is_known():
            return create_unknown_result("BS-02", "Height/Width Ratio Validation", "Shoulder width parameter not available")
        
        height = height_param.value
        shoulder_width = shoulder_width_param.value
        ratio = height / shoulder_width
        
        # Normal ratio range approximately 2.0-3.0
        min_ratio = 2.0
        max_ratio = 3.0
        
        if min_ratio <= ratio <= max_ratio:
            return create_pass_result(
                "BS-02",
                "Height/Width Ratio Validation",
                f"{min_ratio}-{max_ratio}",
                f"{ratio:.2f}"
            )
        else:
            deviation = f"{abs(ratio - 2.5):.2f}"
            return create_fail_result(
                "BS-02",
                "Height/Width Ratio Validation",
                f"{min_ratio}-{max_ratio}",
                f"{ratio:.2f}",
                deviation,
                source="parameter model",
                recommendation="Adjust shoulder width or height to achieve normal proportion"
            )
    
    def validate_bs_03_head_proportion(self, parameter_set: ParameterSet) -> AnatomicalValidationResult:
        """BS-03: Validate head height is approximately 1/8 of total height."""
        height_param = parameter_set.get_parameter_by_canonical_name("total_height")
        head_height_param = parameter_set.get_parameter_by_canonical_name("head_height")
        
        if height_param is None or not height_param.is_known():
            return create_unknown_result("BS-03", "Head Proportion Validation", "Height parameter not available")
        
        if head_height_param is None or not head_height_param.is_known():
            return create_unknown_result("BS-03", "Head Proportion Validation", "Head height parameter not available")
        
        height = height_param.value
        head_height = head_height_param.value
        expected_head_height = height / 8.0
        
        # Allow ±20% tolerance
        tolerance = 0.2
        min_expected = expected_head_height * (1 - tolerance)
        max_expected = expected_head_height * (1 + tolerance)
        
        if min_expected <= head_height <= max_expected:
            return create_pass_result(
                "BS-03",
                "Head Proportion Validation",
                f"{expected_head_height:.3f}m (1/8 of height)",
                f"{head_height:.3f}m"
            )
        else:
            deviation = f"{abs(head_height - expected_head_height):.3f}m"
            return create_fail_result(
                "BS-03",
                "Head Proportion Validation",
                f"{expected_head_height:.3f}m (1/8 of height)",
                f"{head_height:.3f}m",
                deviation,
                source="parameter model",
                recommendation="Adjust head height to approximately 1/8 of total height"
            )
    
    def validate_bs_04_limb_proportions(self, parameter_set: ParameterSet) -> AnatomicalValidationResult:
        """BS-04: Validate limb proportions are within normal ranges."""
        # Check upper arm length
        upper_arm_param = parameter_set.get_parameter_by_canonical_name("upper_arm_length")
        forearm_param = parameter_set.get_parameter_by_canonical_name("forearm_length")
        
        if upper_arm_param is None or not upper_arm_param.is_known():
            return create_unknown_result("BS-04", "Limb Proportions Validation", "Upper arm length not available")
        
        if forearm_param is None or not forearm_param.is_known():
            return create_unknown_result("BS-04", "Limb Proportions Validation", "Forearm length not available")
        
        upper_arm = upper_arm_param.value
        forearm = forearm_param.value
        
        # Upper arm should be slightly longer than forearm
        ratio = upper_arm / forearm
        
        # Normal ratio range approximately 1.0-1.2
        min_ratio = 1.0
        max_ratio = 1.2
        
        if min_ratio <= ratio <= max_ratio:
            return create_pass_result(
                "BS-04",
                "Limb Proportions Validation",
                f"{min_ratio}-{max_ratio}",
                f"{ratio:.2f}"
            )
        else:
            deviation = f"{abs(ratio - 1.1):.2f}"
            return create_fail_result(
                "BS-04",
                "Limb Proportions Validation",
                f"{min_ratio}-{max_ratio}",
                f"{ratio:.2f}",
                deviation,
                source="parameter model",
                recommendation="Adjust upper arm or forearm length to achieve normal proportion"
            )
    
    def validate_jc_01_shoulder_continuity(self, joint_center_set: JointCenterSet) -> AnatomicalValidationResult:
        """JC-01: Validate shoulder joint center continuity."""
        # This would check that shoulder joint center is at expected location
        # For now, return unknown as joint center calculation not implemented
        return create_unknown_result("JC-01", "Shoulder Joint Center Continuity", "Joint center calculation not implemented")
    
    def validate_jc_02_elbow_continuity(self, joint_center_set: JointCenterSet) -> AnatomicalValidationResult:
        """JC-02: Validate elbow joint center continuity."""
        return create_unknown_result("JC-02", "Elbow Joint Center Continuity", "Joint center calculation not implemented")
    
    def validate_jc_03_wrist_continuity(self, joint_center_set: JointCenterSet) -> AnatomicalValidationResult:
        """JC-03: Validate wrist joint center continuity."""
        return create_unknown_result("JC-03", "Wrist Joint Center Continuity", "Joint center calculation not implemented")
    
    def validate_jc_04_hip_continuity(self, joint_center_set: JointCenterSet) -> AnatomicalValidationResult:
        """JC-04: Validate hip joint center continuity."""
        return create_unknown_result("JC-04", "Hip Joint Center Continuity", "Joint center calculation not implemented")
    
    def validate_jc_05_knee_continuity(self, joint_center_set: JointCenterSet) -> AnatomicalValidationResult:
        """JC-05: Validate knee joint center continuity."""
        return create_unknown_result("JC-05", "Knee Joint Center Continuity", "Joint center calculation not implemented")
    
    def validate_jc_06_ankle_continuity(self, joint_center_set: JointCenterSet) -> AnatomicalValidationResult:
        """JC-06: Validate ankle joint center continuity."""
        return create_unknown_result("JC-06", "Ankle Joint Center Continuity", "Joint center calculation not implemented")
    
    def validate_la_01_landmark_completeness(self, landmark_set: LandmarkSet) -> AnatomicalValidationResult:
        """LA-01: Validate landmark set completeness."""
        # Check if we have reasonable number of landmarks
        landmark_count = len(landmark_set.landmarks)
        
        # Expect at least 20 landmarks for basic validation
        min_landmarks = 20
        
        if landmark_count >= min_landmarks:
            return create_pass_result(
                "LA-01",
                "Landmark Completeness",
                f"≥{min_landmarks}",
                f"{landmark_count}"
            )
        else:
            deviation = f"-{min_landmarks - landmark_count}"
            return create_fail_result(
                "LA-01",
                "Landmark Completeness",
                f"≥{min_landmarks}",
                f"{landmark_count}",
                deviation,
                source="landmark model",
                recommendation="Add more anatomical landmarks to meet minimum requirements"
            )
    
    def validate_la_02_bilateral_symmetry(self, landmark_set: LandmarkSet) -> AnatomicalValidationResult:
        """LA-02: Validate bilateral landmark symmetry."""
        # Check bilateral symmetry
        symmetry_results = landmark_set.validate_bilateral_symmetry(tolerance=0.002)
        
        if not symmetry_results:
            return create_unknown_result("LA-02", "Bilateral Symmetry", "No bilateral landmarks to validate")
        
        failed_pairs = [name for name, passed in symmetry_results.items() if not passed]
        
        if not failed_pairs:
            return create_pass_result(
                "LA-02",
                "Bilateral Symmetry",
                "All pairs symmetric",
                f"{len(symmetry_results)} pairs"
            )
        else:
            return create_fail_result(
                "LA-02",
                "Bilateral Symmetry",
                "All pairs symmetric",
                f"{len(failed_pairs)} pairs failed",
                f"{len(failed_pairs)} asymmetric",
                source="landmark model",
                recommendation=f"Fix asymmetry in: {', '.join(failed_pairs[:3])}"
            )
    
    def validate_la_03_midline_alignment(self, landmark_set: LandmarkSet) -> AnatomicalValidationResult:
        """LA-03: Validate midline landmark alignment."""
        midline_landmarks = landmark_set.get_midline_landmarks()
        
        if not midline_landmarks:
            return create_unknown_result("LA-03", "Midline Alignment", "No midline landmarks to validate")
        
        # Check if midline landmarks have X ≈ 0
        misaligned = []
        for landmark in midline_landmarks:
            if abs(landmark.get_x()) > 0.001:  # 1mm tolerance
                misaligned.append(landmark.canonical_name)
        
        if not misaligned:
            return create_pass_result(
                "LA-03",
                "Midline Alignment",
                "X ≈ 0",
                f"{len(midline_landmarks)} landmarks aligned"
            )
        else:
            return create_fail_result(
                "LA-03",
                "Midline Alignment",
                "X ≈ 0",
                f"{len(misaligned)} misaligned",
                f"{len(misaligned)} misaligned",
                source="landmark model",
                recommendation=f"Fix midline alignment for: {', '.join(misaligned[:3])}"
            )
    
    def validate_la_04_coordinate_validity(self, landmark_set: LandmarkSet) -> AnatomicalValidationResult:
        """LA-04: Validate coordinate validity (finite values, no NaN)."""
        invalid_count = 0
        for landmark in landmark_set.landmarks.values():
            coord = landmark.coordinate
            if not all(
                abs(x) < 1e10 for x in coord
            ):  # Check for unreasonably large values
                invalid_count += 1
        
        if invalid_count == 0:
            return create_pass_result(
                "LA-04",
                "Coordinate Validity",
                "All finite",
                f"{len(landmark_set.landmarks)} landmarks"
            )
        else:
            return create_fail_result(
                "LA-04",
                "Coordinate Validity",
                "All finite",
                f"{invalid_count} invalid",
                f"{invalid_count} invalid",
                source="landmark model",
                recommendation="Fix invalid coordinates"
            )
    
    def validate_ap_01_total_height(self, parameter_set: ParameterSet) -> AnatomicalValidationResult:
        """AP-01: Validate total height parameter is set and reasonable."""
        height_param = parameter_set.get_parameter_by_canonical_name("total_height")
        
        if height_param is None:
            return create_fail_result(
                "AP-01",
                "Total Height Parameter",
                "Set and reasonable",
                "Not set",
                "Missing",
                source="parameter model",
                recommendation="Add total_height parameter"
            )
        
        if not height_param.is_known():
            return create_fail_result(
                "AP-01",
                "Total Height Parameter",
                "Set and reasonable",
                "Unknown",
                "Unknown value",
                source="parameter model",
                recommendation="Set total_height value"
            )
        
        # Check if value is reasonable (0.5m to 2.5m)
        if 0.5 <= height_param.value <= 2.5:
            return create_pass_result(
                "AP-01",
                "Total Height Parameter",
                "Set and reasonable",
                f"{height_param.value:.2f}m"
            )
        else:
            return create_fail_result(
                "AP-01",
                "Total Height Parameter",
                "Set and reasonable",
                f"{height_param.value:.2f}m",
                "Out of range",
                source="parameter model",
                recommendation="Set total_height to reasonable range (0.5-2.5m)"
            )
    
    def validate_ap_02_torso_proportion(self, parameter_set: ParameterSet) -> AnatomicalValidationResult:
        """AP-02: Validate torso height proportion."""
        height_param = parameter_set.get_parameter_by_canonical_name("total_height")
        torso_param = parameter_set.get_parameter_by_canonical_name("torso_height")
        
        if height_param is None or not height_param.is_known():
            return create_unknown_result("AP-02", "Torso Proportion", "Height parameter not available")
        
        if torso_param is None or not torso_param.is_known():
            return create_unknown_result("AP-02", "Torso Proportion", "Torso height parameter not available")
        
        # Torso should be approximately 1/3 of total height
        ratio = torso_param.value / height_param.value
        
        if 0.25 <= ratio <= 0.40:  # Allow 25-40% range
            return create_pass_result(
                "AP-02",
                "Torso Proportion",
                "25-40% of height",
                f"{ratio*100:.1f}%"
            )
        else:
            return create_fail_result(
                "AP-02",
                "Torso Proportion",
                "25-40% of height",
                f"{ratio*100:.1f}%",
                f"{abs(ratio - 0.333)*100:.1f}% deviation",
                source="parameter model",
                recommendation="Adjust torso height to approximately 1/3 of total height"
            )
    
    def validate_ap_03_upper_limb_proportion(self, parameter_set: ParameterSet) -> AnatomicalValidationResult:
        """AP-03: Validate upper limb proportion."""
        height_param = parameter_set.get_parameter_by_canonical_name("total_height")
        upper_arm_param = parameter_set.get_parameter_by_canonical_name("upper_arm_length")
        
        if height_param is None or not height_param.is_known():
            return create_unknown_result("AP-03", "Upper Limb Proportion", "Height parameter not available")
        
        if upper_arm_param is None or not upper_arm_param.is_known():
            return create_unknown_result("AP-03", "Upper Limb Proportion", "Upper arm length not available")
        
        # Upper arm should be approximately 1/6 of total height
        ratio = upper_arm_param.value / height_param.value
        
        if 0.15 <= ratio <= 0.20:  # Allow 15-20% range
            return create_pass_result(
                "AP-03",
                "Upper Limb Proportion",
                "15-20% of height",
                f"{ratio*100:.1f}%"
            )
        else:
            return create_fail_result(
                "AP-03",
                "Upper Limb Proportion",
                "15-20% of height",
                f"{ratio*100:.1f}%",
                f"{abs(ratio - 0.167)*100:.1f}% deviation",
                source="parameter model",
                recommendation="Adjust upper arm length to approximately 1/6 of total height"
            )
    
    def validate_ap_04_lower_limb_proportion(self, parameter_set: ParameterSet) -> AnatomicalValidationResult:
        """AP-04: Validate lower limb proportion."""
        height_param = parameter_set.get_parameter_by_canonical_name("total_height")
        thigh_param = parameter_set.get_parameter_by_canonical_name("thigh_length")
        
        if height_param is None or not height_param.is_known():
            return create_unknown_result("AP-04", "Lower Limb Proportion", "Height parameter not available")
        
        if thigh_param is None or not thigh_param.is_known():
            return create_unknown_result("AP-04", "Lower Limb Proportion", "Thigh length not available")
        
        # Thigh should be approximately 1/4 of total height
        ratio = thigh_param.value / height_param.value
        
        if 0.20 <= ratio <= 0.30:  # Allow 20-30% range
            return create_pass_result(
                "AP-04",
                "Lower Limb Proportion",
                "20-30% of height",
                f"{ratio*100:.1f}%"
            )
        else:
            return create_fail_result(
                "AP-04",
                "Lower Limb Proportion",
                "20-30% of height",
                f"{ratio*100:.1f}%",
                f"{abs(ratio - 0.25)*100:.1f}% deviation",
                source="parameter model",
                recommendation="Adjust thigh length to approximately 1/4 of total height"
            )
    
    def validate_ap_05_bilateral_consistency(self, parameter_set: ParameterSet) -> AnatomicalValidationResult:
        """AP-05: Validate bilateral parameter consistency."""
        # Check left-right pairs for consistency
        inconsistent_pairs = []
        
        bilateral_pairs = [
            ("femur_L", "femur_R"),
            ("tibia_L", "tibia_R"),
            ("humerus_L", "humerus_R"),
            ("radius_L", "radius_R")
        ]
        
        for left_name, right_name in bilateral_pairs:
            left_param = parameter_set.get_parameter_by_canonical_name(left_name)
            right_param = parameter_set.get_parameter_by_canonical_name(right_name)
            
            if left_param and right_param and left_param.is_known() and right_param.is_known():
                # Check if lengths are consistent within tolerance
                if abs(left_param.value - right_param.value) > 0.005:  # 5mm tolerance
                    inconsistent_pairs.append((left_name, right_name))
        
        if not inconsistent_pairs:
            return create_pass_result(
                "AP-05",
                "Bilateral Consistency",
                "All pairs consistent",
                f"{len(bilateral_pairs)} pairs checked"
            )
        else:
            return create_fail_result(
                "AP-05",
                "Bilateral Consistency",
                "All pairs consistent",
                f"{len(inconsistent_pairs)} pairs inconsistent",
                f"{len(inconsistent_pairs)} inconsistent",
                source="parameter model",
                recommendation=f"Fix bilateral consistency for: {', '.join([f'{p[0]}/{p[1]}' for p in inconsistent_pairs[:2]])}"
            )


def create_anatomical_validator() -> AnatomicalValidator:
    """Create an anatomical validator instance."""
    return AnatomicalValidator()
