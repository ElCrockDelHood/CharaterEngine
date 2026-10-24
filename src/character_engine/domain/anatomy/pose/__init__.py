"""Rest-pose transforms applied to canonical bone data (pure Python, no data invention)."""

from .tpose import POSES, apply_pose, apply_tpose, arm_subtree

__all__ = ["POSES", "apply_pose", "apply_tpose", "arm_subtree"]
