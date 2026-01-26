"""
Motion Detection Module
Detects movement in camera frames for wake/security features.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class MotionRegion:
    """Represents a region where motion was detected."""
    x: int
    y: int
    width: int
    height: int
    score: float  # Motion intensity (0-1)


class MotionDetector:
    """
    Detects motion using background subtraction.
    Optimized for Raspberry Pi 4B performance.
    """
    
    def __init__(
        self,
        threshold: int = 25,
        min_area: int = 500,
        history: int = 20,
        use_mog2: bool = False
    ):
        """
        Initialize motion detector.
        
        Args:
            threshold: Pixel difference threshold for simple detection
            min_area: Minimum contour area to consider as motion
            history: Number of frames for MOG2 background model
            use_mog2: Use MOG2 (slower but more accurate) vs simple diff
        """
        self.threshold = threshold
        self.min_area = min_area
        self.prev_frame: Optional[np.ndarray] = None
        self.use_mog2 = use_mog2
        
        if use_mog2:
            # MOG2 background subtractor (more accurate but slower)
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=history,
                varThreshold=16,
                detectShadows=False
            )
        else:
            self.bg_subtractor = None
    
    def detect(self, frame: np.ndarray) -> Tuple[bool, float, List[MotionRegion]]:
        """
        Detect motion in the current frame.
        
        Args:
            frame: Current BGR frame
            
        Returns:
            Tuple of (motion_detected, motion_score, motion_regions)
        """
        if self.use_mog2:
            return self._detect_mog2(frame)
        else:
            return self._detect_simple(frame)
    
    def _detect_simple(self, frame: np.ndarray) -> Tuple[bool, float, List[MotionRegion]]:
        """Simple frame differencing method (fast)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # First frame initialization
        if self.prev_frame is None:
            self.prev_frame = gray
            return False, 0.0, []
        
        # Compute frame difference
        frame_diff = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_diff, self.threshold, 255, cv2.THRESH_BINARY)[1]
        
        # Dilate to fill holes
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(
            thresh.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Analyze motion
        motion_regions = []
        total_motion_pixels = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            total_motion_pixels += area
            
            # Calculate motion score for this region
            score = min(area / (frame.shape[0] * frame.shape[1]), 1.0)
            motion_regions.append(MotionRegion(x, y, w, h, score))
        
        # Overall motion score (percentage of frame with motion)
        motion_score = total_motion_pixels / (frame.shape[0] * frame.shape[1])
        motion_detected = motion_score > 0.01  # 1% of frame
        
        # Update previous frame
        self.prev_frame = gray
        
        return motion_detected, motion_score, motion_regions
    
    def _detect_mog2(self, frame: np.ndarray) -> Tuple[bool, float, List[MotionRegion]]:
        """MOG2 background subtraction method (more accurate)."""
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Threshold and clean up
        _, thresh = cv2.threshold(fg_mask, 244, 255, cv2.THRESH_BINARY)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(
            thresh.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Analyze motion
        motion_regions = []
        total_motion_pixels = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            total_motion_pixels += area
            
            score = min(area / (frame.shape[0] * frame.shape[1]), 1.0)
            motion_regions.append(MotionRegion(x, y, w, h, score))
        
        # Overall motion score
        motion_score = total_motion_pixels / (frame.shape[0] * frame.shape[1])
        motion_detected = motion_score > 0.01
        
        return motion_detected, motion_score, motion_regions
    
    def reset(self) -> None:
        """Reset the motion detector state."""
        self.prev_frame = None
        if self.bg_subtractor:
            # Recreate background subtractor
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=20,
                varThreshold=16,
                detectShadows=False
            )
    
    def visualize(self, frame: np.ndarray, regions: List[MotionRegion]) -> np.ndarray:
        """
        Draw motion regions on frame for debugging.
        
        Args:
            frame: Original frame
            regions: List of detected motion regions
            
        Returns:
            Frame with motion regions drawn
        """
        vis_frame = frame.copy()
        
        for region in regions:
            # Draw bounding box
            cv2.rectangle(
                vis_frame,
                (region.x, region.y),
                (region.x + region.width, region.y + region.height),
                (0, 255, 0),
                2
            )
            
            # Add score label
            label = f"Motion: {region.score:.2f}"
            cv2.putText(
                vis_frame,
                label,
                (region.x, region.y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )
        
        return vis_frame
