"""
Hand Gesture Recognition Module
Uses MediaPipe Hands for real-time gesture detection.
"""

import cv2
import numpy as np
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False


class Gesture(Enum):
    """Supported hand gestures."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    PEACE = "peace"
    WAVE = "wave"
    STOP = "stop"
    POINT_UP = "point_up"
    POINT_DOWN = "point_down"
    FIST = "fist"
    OPEN_PALM = "open_palm"
    OK = "ok"
    UNKNOWN = "unknown"


@dataclass
class GestureResult:
    """Result of gesture detection."""
    gesture: Gesture
    confidence: float
    hand_landmarks: Optional[np.ndarray] = None
    handedness: str = "Right"  # "Right" or "Left"


class GestureRecognizer:
    """
    Recognizes hand gestures using MediaPipe Hands.
    Optimized for Raspberry Pi 4B performance.
    """
    
    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        stability_frames: int = 3
    ):
        """
        Initialize gesture recognizer.
        
        Args:
            max_num_hands: Maximum number of hands to detect
            min_detection_confidence: Confidence threshold for detection
            min_tracking_confidence: Confidence threshold for tracking
            stability_frames: Frames needed to confirm gesture (prevent flickering)
        """
        if not HAS_MEDIAPIPE:
            raise ImportError("MediaPipe not installed. Run: pip install mediapipe")
        
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Gesture stability tracking
        self.stability_frames = stability_frames
        self.gesture_history: List[Gesture] = []
        self.stable_gesture: Optional[Gesture] = None
        
        # Landmark indices
        self.LANDMARKS = {
            'WRIST': 0,
            'THUMB_TIP': 4,
            'THUMB_IP': 3,
            'THUMB_MCP': 2,
            'INDEX_TIP': 8,
            'INDEX_PIP': 6,
            'INDEX_MCP': 5,
            'MIDDLE_TIP': 12,
            'MIDDLE_PIP': 10,
            'RING_TIP': 16,
            'RING_PIP': 14,
            'PINKY_TIP': 20,
            'PINKY_PIP': 18
        }
    
    def detect(self, frame: np.ndarray) -> Optional[GestureResult]:
        """
        Detect gesture in frame.
        
        Args:
            frame: BGR image
            
        Returns:
            GestureResult if hand detected, None otherwise
        """
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        if not results.multi_hand_landmarks:
            self._reset_stability()
            return None
        
        # Process first hand
        hand_landmarks = results.multi_hand_landmarks[0]
        handedness = results.multi_handedness[0].classification[0].label
        
        # Convert landmarks to numpy array
        landmarks = self._landmarks_to_array(hand_landmarks)
        
        # Recognize gesture
        gesture, confidence = self._recognize_gesture(landmarks)
        
        # Update stability tracking
        gesture = self._update_stability(gesture)
        
        return GestureResult(
            gesture=gesture,
            confidence=confidence,
            hand_landmarks=landmarks,
            handedness=handedness
        )
    
    def _landmarks_to_array(self, hand_landmarks) -> np.ndarray:
        """Convert MediaPipe landmarks to numpy array."""
        landmarks = []
        for lm in hand_landmarks.landmark:
            landmarks.append([lm.x, lm.y, lm.z])
        return np.array(landmarks)
    
    def _recognize_gesture(self, landmarks: np.ndarray) -> Tuple[Gesture, float]:
        """
        Recognize gesture from hand landmarks.
        
        Args:
            landmarks: Array of shape (21, 3) with normalized coordinates
            
        Returns:
            Tuple of (Gesture, confidence)
        """
        # Calculate finger states (extended or not)
        fingers_up = self._get_fingers_up(landmarks)
        
        # Pattern matching
        if fingers_up == [0, 0, 0, 0, 0]:
            return Gesture.FIST, 0.9
        
        elif fingers_up == [1, 1, 1, 1, 1]:
            return Gesture.OPEN_PALM, 0.9
        
        elif fingers_up == [1, 0, 0, 0, 0]:  # Only thumb up
            if self._is_thumbs_up(landmarks):
                return Gesture.THUMBS_UP, 0.85
            elif self._is_thumbs_down(landmarks):
                return Gesture.THUMBS_DOWN, 0.85
        
        elif fingers_up == [0, 1, 1, 0, 0]:  # Index + middle
            return Gesture.PEACE, 0.9
        
        elif fingers_up == [0, 1, 0, 0, 0]:  # Only index
            if self._is_pointing_up(landmarks):
                return Gesture.POINT_UP, 0.85
            elif self._is_pointing_down(landmarks):
                return Gesture.POINT_DOWN, 0.85
        
        elif fingers_up == [1, 1, 0, 0, 1]:  # Thumb + index + pinky
            return Gesture.OK, 0.8
        
        # Check for wave (hand moving)
        # This would need temporal tracking - simplified for now
        
        return Gesture.UNKNOWN, 0.5
    
    def _get_fingers_up(self, landmarks: np.ndarray) -> List[int]:
        """
        Determine which fingers are extended.
        
        Returns:
            List of 5 binary values [thumb, index, middle, ring, pinky]
        """
        fingers = []
        
        # Thumb (special case - compare x instead of y)
        thumb_tip = landmarks[self.LANDMARKS['THUMB_TIP']]
        thumb_ip = landmarks[self.LANDMARKS['THUMB_IP']]
        fingers.append(1 if abs(thumb_tip[0] - thumb_ip[0]) > 0.05 else 0)
        
        # Other fingers (compare y coordinates)
        finger_tips = [
            self.LANDMARKS['INDEX_TIP'],
            self.LANDMARKS['MIDDLE_TIP'],
            self.LANDMARKS['RING_TIP'],
            self.LANDMARKS['PINKY_TIP']
        ]
        finger_pips = [
            self.LANDMARKS['INDEX_PIP'],
            self.LANDMARKS['MIDDLE_PIP'],
            self.LANDMARKS['RING_PIP'],
            self.LANDMARKS['PINKY_PIP']
        ]
        
        for tip, pip in zip(finger_tips, finger_pips):
            # Finger is up if tip is above pip (lower y value)
            fingers.append(1 if landmarks[tip][1] < landmarks[pip][1] else 0)
        
        return fingers
    
    def _is_thumbs_up(self, landmarks: np.ndarray) -> bool:
        """Check if gesture is thumbs up."""
        thumb_tip = landmarks[self.LANDMARKS['THUMB_TIP']]
        wrist = landmarks[self.LANDMARKS['WRIST']]
        # Thumb tip should be significantly above wrist
        return (wrist[1] - thumb_tip[1]) > 0.2
    
    def _is_thumbs_down(self, landmarks: np.ndarray) -> bool:
        """Check if gesture is thumbs down."""
        thumb_tip = landmarks[self.LANDMARKS['THUMB_TIP']]
        wrist = landmarks[self.LANDMARKS['WRIST']]
        # Thumb tip should be significantly below wrist
        return (thumb_tip[1] - wrist[1]) > 0.2
    
    def _is_pointing_up(self, landmarks: np.ndarray) -> bool:
        """Check if index finger is pointing up."""
        index_tip = landmarks[self.LANDMARKS['INDEX_TIP']]
        index_mcp = landmarks[self.LANDMARKS['INDEX_MCP']]
        # Index tip should be well above MCP
        return (index_mcp[1] - index_tip[1]) > 0.15
    
    def _is_pointing_down(self, landmarks: np.ndarray) -> bool:
        """Check if index finger is pointing down."""
        index_tip = landmarks[self.LANDMARKS['INDEX_TIP']]
        index_mcp = landmarks[self.LANDMARKS['INDEX_MCP']]
        # Index tip should be well below MCP
        return (index_tip[1] - index_mcp[1]) > 0.15
    
    def _update_stability(self, gesture: Gesture) -> Gesture:
        """
        Update gesture stability tracking to prevent flickering.
        
        Args:
            gesture: Currently detected gesture
            
        Returns:
            Stable gesture (only changes after multiple consistent frames)
        """
        self.gesture_history.append(gesture)
        
        # Keep only recent history
        if len(self.gesture_history) > self.stability_frames:
            self.gesture_history.pop(0)
        
        # Check if all recent frames agree
        if len(self.gesture_history) >= self.stability_frames:
            if all(g == gesture for g in self.gesture_history):
                self.stable_gesture = gesture
        
        return self.stable_gesture if self.stable_gesture else gesture
    
    def _reset_stability(self):
        """Reset stability tracking when no hand detected."""
        self.gesture_history.clear()
        self.stable_gesture = None
    
    def visualize(self, frame: np.ndarray, result: GestureResult) -> np.ndarray:
        """
        Draw hand landmarks and gesture label on frame.
        
        Args:
            frame: Original BGR frame
            result: Gesture detection result
            
        Returns:
            Frame with visualization
        """
        if result.hand_landmarks is None:
            return frame
        
        vis_frame = frame.copy()
        h, w = frame.shape[:2]
        
        # Draw landmarks
        for landmark in result.hand_landmarks:
            x, y = int(landmark[0] * w), int(landmark[1] * h)
            cv2.circle(vis_frame, (x, y), 5, (0, 255, 0), -1)
        
        # Draw gesture label
        gesture_text = result.gesture.value.replace('_', ' ').title()
        label = f"{result.handedness} Hand: {gesture_text} ({result.confidence:.0%})"
        
        # Background for text
        (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(vis_frame, (10, 10), (20 + text_w, 40 + text_h), (0, 0, 0), -1)
        
        # Text
        cv2.putText(
            vis_frame,
            label,
            (15, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2
        )
        
        return vis_frame
    
    def cleanup(self):
        """Release MediaPipe resources."""
        self.hands.close()
