"""
Hand Gesture Recognition Module
Uses OpenCV-based hand detection for compatibility with MediaPipe 0.10+.
Falls back to pure OpenCV if MediaPipe unavailable.
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Try new MediaPipe API first, then legacy, then OpenCV fallback
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    from mediapipe import solutions
    HAS_MEDIAPIPE_NEW = True
    HAS_MEDIAPIPE_LEGACY = False
except (ImportError, AttributeError):
    try:
        import mediapipe as mp
        if hasattr(mp, 'solutions'):
            HAS_MEDIAPIPE_NEW = False
            HAS_MEDIAPIPE_LEGACY = True
        else:
            HAS_MEDIAPIPE_NEW = False
            HAS_MEDIAPIPE_LEGACY = False
    except ImportError:
        HAS_MEDIAPIPE_NEW = False
        HAS_MEDIAPIPE_LEGACY = False


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
    handedness: str = "Right"


class GestureRecognizer:
    """
    Recognizes hand gestures using MediaPipe or OpenCV.
    Automatically selects best available backend.
    """
    
    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        stability_frames: int = 3
    ):
        self.stability_frames = stability_frames
        self.gesture_history: List[Gesture] = []
        self.stable_gesture: Optional[Gesture] = None
        
        # Landmark indices
        self.LANDMARKS = {
            'WRIST': 0, 'THUMB_TIP': 4, 'THUMB_IP': 3, 'THUMB_MCP': 2,
            'INDEX_TIP': 8, 'INDEX_PIP': 6, 'INDEX_MCP': 5,
            'MIDDLE_TIP': 12, 'MIDDLE_PIP': 10,
            'RING_TIP': 16, 'RING_PIP': 14,
            'PINKY_TIP': 20, 'PINKY_PIP': 18
        }
        
        self.backend = None
        self.hands = None
        
        # Try MediaPipe new API
        if HAS_MEDIAPIPE_NEW:
            try:
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=max_num_hands,
                    min_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence
                )
                self.backend = "mediapipe_new"
                print("Using MediaPipe (new API)")
            except Exception as e:
                print(f"MediaPipe new API failed: {e}")
        
        # Try MediaPipe legacy API
        if self.backend is None and HAS_MEDIAPIPE_LEGACY:
            try:
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=max_num_hands,
                    min_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence
                )
                self.backend = "mediapipe_legacy"
                print("Using MediaPipe (legacy API)")
            except Exception as e:
                print(f"MediaPipe legacy API failed: {e}")
        
        # Fallback to OpenCV skin detection
        if self.backend is None:
            self.backend = "opencv"
            print("Using OpenCV hand detection (basic)")
    
    def detect(self, frame: np.ndarray) -> Optional[GestureResult]:
        """Detect gesture in frame."""
        if self.backend in ("mediapipe_new", "mediapipe_legacy"):
            return self._detect_mediapipe(frame)
        else:
            return self._detect_opencv(frame)
    
    def _detect_mediapipe(self, frame: np.ndarray) -> Optional[GestureResult]:
        """Detect using MediaPipe."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        if not results.multi_hand_landmarks:
            self._reset_stability()
            return None
        
        hand_landmarks = results.multi_hand_landmarks[0]
        handedness = results.multi_handedness[0].classification[0].label
        
        landmarks = self._landmarks_to_array(hand_landmarks)
        gesture, confidence = self._recognize_gesture(landmarks)
        gesture = self._update_stability(gesture)
        
        return GestureResult(
            gesture=gesture,
            confidence=confidence,
            hand_landmarks=landmarks,
            handedness=handedness
        )
    
    def _detect_opencv(self, frame: np.ndarray) -> Optional[GestureResult]:
        """Detect using OpenCV skin detection (basic fallback)."""
        # Convert to HSV for skin detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Skin color range
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        # Create mask
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            self._reset_stability()
            return None
        
        # Find largest contour (hand)
        max_contour = max(contours, key=cv2.contourArea)
        
        if cv2.contourArea(max_contour) < 5000:
            self._reset_stability()
            return None
        
        # Count fingers using convex hull defects
        hull = cv2.convexHull(max_contour, returnPoints=False)
        
        try:
            defects = cv2.convexityDefects(max_contour, hull)
        except cv2.error:
            defects = None
        
        finger_count = 0
        if defects is not None:
            for i in range(defects.shape[0]):
                s, e, f, d = defects[i, 0]
                if d > 10000:  # Depth threshold
                    finger_count += 1
        
        # Simple gesture mapping based on finger count
        if finger_count >= 4:
            gesture = Gesture.OPEN_PALM
        elif finger_count == 1:
            gesture = Gesture.PEACE
        elif finger_count == 0:
            gesture = Gesture.FIST
        else:
            gesture = Gesture.UNKNOWN
        
        gesture = self._update_stability(gesture)
        
        return GestureResult(
            gesture=gesture,
            confidence=0.6,
            hand_landmarks=None,
            handedness="Right"
        )
    
    def _landmarks_to_array(self, hand_landmarks) -> np.ndarray:
        """Convert MediaPipe landmarks to numpy array."""
        landmarks = []
        for lm in hand_landmarks.landmark:
            landmarks.append([lm.x, lm.y, lm.z])
        return np.array(landmarks)
    
    def _recognize_gesture(self, landmarks: np.ndarray) -> Tuple[Gesture, float]:
        """Recognize gesture from landmarks."""
        fingers_up = self._get_fingers_up(landmarks)
        
        if fingers_up == [0, 0, 0, 0, 0]:
            return Gesture.FIST, 0.9
        elif fingers_up == [1, 1, 1, 1, 1]:
            return Gesture.OPEN_PALM, 0.9
        elif fingers_up == [1, 0, 0, 0, 0]:
            if self._is_thumbs_up(landmarks):
                return Gesture.THUMBS_UP, 0.85
            elif self._is_thumbs_down(landmarks):
                return Gesture.THUMBS_DOWN, 0.85
        elif fingers_up == [0, 1, 1, 0, 0]:
            return Gesture.PEACE, 0.9
        elif fingers_up == [0, 1, 0, 0, 0]:
            if self._is_pointing_up(landmarks):
                return Gesture.POINT_UP, 0.85
            elif self._is_pointing_down(landmarks):
                return Gesture.POINT_DOWN, 0.85
        elif fingers_up == [1, 1, 0, 0, 1]:
            return Gesture.OK, 0.8
        
        return Gesture.UNKNOWN, 0.5
    
    def _get_fingers_up(self, landmarks: np.ndarray) -> List[int]:
        """Determine which fingers are extended."""
        fingers = []
        
        # Thumb
        thumb_tip = landmarks[self.LANDMARKS['THUMB_TIP']]
        thumb_ip = landmarks[self.LANDMARKS['THUMB_IP']]
        fingers.append(1 if abs(thumb_tip[0] - thumb_ip[0]) > 0.05 else 0)
        
        # Other fingers
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            fingers.append(1 if landmarks[tip][1] < landmarks[pip][1] else 0)
        
        return fingers
    
    def _is_thumbs_up(self, landmarks: np.ndarray) -> bool:
        thumb_tip = landmarks[self.LANDMARKS['THUMB_TIP']]
        wrist = landmarks[self.LANDMARKS['WRIST']]
        return (wrist[1] - thumb_tip[1]) > 0.2
    
    def _is_thumbs_down(self, landmarks: np.ndarray) -> bool:
        thumb_tip = landmarks[self.LANDMARKS['THUMB_TIP']]
        wrist = landmarks[self.LANDMARKS['WRIST']]
        return (thumb_tip[1] - wrist[1]) > 0.2
    
    def _is_pointing_up(self, landmarks: np.ndarray) -> bool:
        index_tip = landmarks[self.LANDMARKS['INDEX_TIP']]
        index_mcp = landmarks[self.LANDMARKS['INDEX_MCP']]
        return (index_mcp[1] - index_tip[1]) > 0.15
    
    def _is_pointing_down(self, landmarks: np.ndarray) -> bool:
        index_tip = landmarks[self.LANDMARKS['INDEX_TIP']]
        index_mcp = landmarks[self.LANDMARKS['INDEX_MCP']]
        return (index_tip[1] - index_mcp[1]) > 0.15
    
    def _update_stability(self, gesture: Gesture) -> Gesture:
        """Prevent gesture flickering."""
        self.gesture_history.append(gesture)
        if len(self.gesture_history) > self.stability_frames:
            self.gesture_history.pop(0)
        if len(self.gesture_history) >= self.stability_frames:
            if all(g == gesture for g in self.gesture_history):
                self.stable_gesture = gesture
        return self.stable_gesture if self.stable_gesture else gesture
    
    def _reset_stability(self):
        """Reset tracking when no hand detected."""
        self.gesture_history.clear()
        self.stable_gesture = None
    
    def visualize(self, frame: np.ndarray, result: GestureResult) -> np.ndarray:
        """Draw hand landmarks and gesture label on frame."""
        vis_frame = frame.copy()
        h, w = frame.shape[:2]
        
        if result.hand_landmarks is not None:
            for landmark in result.hand_landmarks:
                x, y = int(landmark[0] * w), int(landmark[1] * h)
                cv2.circle(vis_frame, (x, y), 5, (0, 255, 0), -1)
        
        gesture_text = result.gesture.value.replace('_', ' ').title()
        label = f"{result.handedness} Hand: {gesture_text} ({result.confidence:.0%})"
        
        (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(vis_frame, (10, 10), (20 + text_w, 40 + text_h), (0, 0, 0), -1)
        cv2.putText(vis_frame, label, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return vis_frame
    
    def cleanup(self):
        """Release resources."""
        if self.hands is not None:
            try:
                self.hands.close()
            except:
                pass
