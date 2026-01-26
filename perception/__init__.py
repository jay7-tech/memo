"""
MEMO Perception Package
Lazy imports to avoid loading heavy dependencies unless needed.
"""

# Lazy imports - only import when accessed
def __getattr__(name):
    if name == "ObjectDetector":
        from .object_detection import ObjectDetector
        return ObjectDetector
    elif name == "PoseEstimator":
        from .pose_estimation import PoseEstimator
        return PoseEstimator
    elif name == "FaceRecognizer":
        from .face_rec import FaceRecognizer
        return FaceRecognizer
    elif name == "MotionDetector":
        from .motion_detector import MotionDetector
        return MotionDetector
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['ObjectDetector', 'PoseEstimator', 'FaceRecognizer', 'MotionDetector']
