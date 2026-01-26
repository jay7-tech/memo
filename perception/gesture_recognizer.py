"""
Hand Gesture Recognition Module
Uses MediaPipe Tasks API (new) or OpenCV-based detection.
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import os

# Check for MediaPipe
HAS_MEDIAPIPE = False
MP_HANDS = None

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.framework.formats import landmark_pb2
    HAS_MEDIAPIPE = True
except ImportError:
    pass


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
    Recognizes hand gestures using MediaPipe Tasks API or OpenCV fallback.
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
        self.max_num_hands = max_num_hands
        self.min_confidence = min_detection_confidence
        
        # Landmark indices
        self.LANDMARKS = {
            'WRIST': 0, 'THUMB_TIP': 4, 'THUMB_IP': 3, 'THUMB_MCP': 2,
            'INDEX_TIP': 8, 'INDEX_PIP': 6, 'INDEX_MCP': 5,
            'MIDDLE_TIP': 12, 'MIDDLE_PIP': 10,
            'RING_TIP': 16, 'RING_PIP': 14,
            'PINKY_TIP': 20, 'PINKY_PIP': 18
        }
        
        self.backend = "opencv"  # Default to OpenCV
        self.detector = None
        
        # Try MediaPipe Tasks API
        if HAS_MEDIAPIPE:
            try:
                # Download model if not exists
                model_path = self._get_model_path()
                if model_path:
                    base_options = mp_python.BaseOptions(model_asset_path=model_path)
                    options = mp_vision.HandLandmarkerOptions(
                        base_options=base_options,
                        running_mode=mp_vision.RunningMode.IMAGE,
                        num_hands=max_num_hands,
                        min_hand_detection_confidence=min_detection_confidence,
                        min_tracking_confidence=min_tracking_confidence
                    )
                    self.detector = mp_vision.HandLandmarker.create_from_options(options)
                    self.backend = "mediapipe_tasks"
                    print("Using MediaPipe Tasks API (accurate)")
            except Exception as e:
                print(f"MediaPipe Tasks failed: {e}")
        
        if self.backend == "opencv":
            print("Using OpenCV hand detection (basic)")
    
    def _get_model_path(self) -> Optional[str]:
        """Get or download the hand landmarker model."""
        model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "hand_landmarker.task")
        
        if os.path.exists(model_path):
            return model_path
        
        # Try to download
        try:
            import urllib.request
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            print(f"Downloading hand model...")
            urllib.request.urlretrieve(url, model_path)
            print(f"Model saved to {model_path}")
            return model_path
        except Exception as e:
            print(f"Could not download model: {e}")
            return None
    
    def detect(self, frame: np.ndarray) -> Optional[GestureResult]:
        """Detect gesture in frame."""
        if self.backend == "mediapipe_tasks":
            return self._detect_mediapipe_tasks(frame)
        else:
            return self._detect_opencv(frame)
    
    def _detect_mediapipe_tasks(self, frame: np.ndarray) -> Optional[GestureResult]:
        """Detect using MediaPipe Tasks API."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        result = self.detector.detect(mp_image)
        
        if not result.hand_landmarks:
            self._reset_stability()
            return None
        
        # Get first hand
        hand_lms = result.hand_landmarks[0]
        handedness = result.handedness[0][0].category_name if result.handedness else "Right"
        
        # Convert to numpy array
        landmarks = np.array([[lm.x, lm.y, lm.z] for lm in hand_lms])
        
        # Recognize gesture
        gesture, confidence = self._recognize_gesture(landmarks)
        gesture = self._update_stability(gesture)
        
        return GestureResult(
            gesture=gesture,
            confidence=confidence,
            hand_landmarks=landmarks,
            handedness=handedness
        )
    
    def _detect_opencv(self, frame: np.ndarray) -> Optional[GestureResult]:
        """Detect using OpenCV skin detection (fallback)."""
        # YCrCb color space for better skin detection
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        
        # Skin color range in YCrCb
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        
        mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
        
        # Clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            self._reset_stability()
            return None
        
        # Find largest contour
        max_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(max_contour)
        
        if area < 5000:
            self._reset_stability()
            return None
        
        # Convex hull analysis
        hull = cv2.convexHull(max_contour, returnPoints=False)
        
        # Count fingers using convexity defects
        finger_count = 0
        try:
            defects = cv2.convexityDefects(max_contour, hull)
            if defects is not None:
                for i in range(defects.shape[0]):
                    s, e, f, d = defects[i, 0]
                    start = tuple(max_contour[s][0])
                    end = tuple(max_contour[e][0])
                    far = tuple(max_contour[f][0])
                    
                    # Calculate triangle sides
                    a = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
                    b = np.sqrt((far[0] - start[0])**2 + (far[1] - start[1])**2)
                    c = np.sqrt((end[0] - far[0])**2 + (end[1] - far[1])**2)
                    
                    # Angle using cosine rule
                    angle = np.arccos((b**2 + c**2 - a**2) / (2*b*c + 1e-6))
                    
                    # Count as finger if angle < 90 degrees and depth sufficient
                    if angle <= np.pi/2 and d > 10000:
                        finger_count += 1
        except cv2.error:
            pass
        
        # Adjust: defects count gaps between fingers, so fingers = gaps + 1
        if finger_count > 0:
            finger_count += 1
        
        # Map finger count to gesture
        if finger_count >= 5:
            gesture = Gesture.OPEN_PALM
            confidence = 0.75
        elif finger_count == 2:
            gesture = Gesture.PEACE
            confidence = 0.70
        elif finger_count == 1:
            gesture = Gesture.POINT_UP
            confidence = 0.65
        elif finger_count == 0:
            gesture = Gesture.FIST
            confidence = 0.70
        else:
            gesture = Gesture.UNKNOWN
            confidence = 0.4
        
        gesture = self._update_stability(gesture)
        
        return GestureResult(
            gesture=gesture,
            confidence=confidence,
            hand_landmarks=None,
            handedness="Right"
        )
    
    def _recognize_gesture(self, landmarks: np.ndarray) -> Tuple[Gesture, float]:
        """Recognize gesture from MediaPipe landmarks."""
        fingers_up = self._get_fingers_up(landmarks)
        
        # Count fingers
        finger_count = sum(fingers_up)
        
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
        elif fingers_up == [0, 1, 1, 1, 1]:
            return Gesture.STOP, 0.8
        
        return Gesture.UNKNOWN, 0.5
    
    def _get_fingers_up(self, landmarks: np.ndarray) -> List[int]:
        """Determine which fingers are extended."""
        fingers = []
        
        # Thumb (compare x)
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        thumb_mcp = landmarks[2]
        # Check if thumb is extended outward
        if landmarks[4][0] < landmarks[3][0]:  # Left hand
            fingers.append(1 if thumb_tip[0] < thumb_mcp[0] else 0)
        else:  # Right hand
            fingers.append(1 if thumb_tip[0] > thumb_mcp[0] else 0)
        
        # Other fingers (compare y - tip should be above pip)
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            fingers.append(1 if landmarks[tip][1] < landmarks[pip][1] else 0)
        
        return fingers
    
    def _is_thumbs_up(self, landmarks: np.ndarray) -> bool:
        thumb_tip = landmarks[4]
        wrist = landmarks[0]
        return (wrist[1] - thumb_tip[1]) > 0.15
    
    def _is_thumbs_down(self, landmarks: np.ndarray) -> bool:
        thumb_tip = landmarks[4]
        wrist = landmarks[0]
        return (thumb_tip[1] - wrist[1]) > 0.15
    
    def _is_pointing_up(self, landmarks: np.ndarray) -> bool:
        index_tip = landmarks[8]
        index_mcp = landmarks[5]
        return (index_mcp[1] - index_tip[1]) > 0.1
    
    def _is_pointing_down(self, landmarks: np.ndarray) -> bool:
        index_tip = landmarks[8]
        index_mcp = landmarks[5]
        return (index_tip[1] - index_mcp[1]) > 0.1
    
    def _update_stability(self, gesture: Gesture) -> Gesture:
        """Prevent gesture flickering."""
        self.gesture_history.append(gesture)
        if len(self.gesture_history) > self.stability_frames:
            self.gesture_history.pop(0)
        
        # Most common gesture in history
        if len(self.gesture_history) >= self.stability_frames:
            from collections import Counter
            most_common = Counter(self.gesture_history).most_common(1)[0]
            if most_common[1] >= self.stability_frames - 1:
                self.stable_gesture = most_common[0]
        
        return self.stable_gesture if self.stable_gesture else gesture
    
    def _reset_stability(self):
        """Reset tracking when no hand detected."""
        self.gesture_history.clear()
        self.stable_gesture = None
    
    def visualize(self, frame: np.ndarray, result: GestureResult) -> np.ndarray:
        """Draw hand landmarks and gesture label."""
        vis_frame = frame.copy()
        h, w = frame.shape[:2]
        
        if result.hand_landmarks is not None:
            # Draw landmarks
            for i, landmark in enumerate(result.hand_landmarks):
                x, y = int(landmark[0] * w), int(landmark[1] * h)
                color = (0, 255, 0) if i in [4, 8, 12, 16, 20] else (255, 0, 0)  # Tips in green
                cv2.circle(vis_frame, (x, y), 4, color, -1)
            
            # Draw connections
            connections = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
                          (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
                          (13,17),(17,18),(18,19),(19,20),(0,17)]
            for start, end in connections:
                pt1 = (int(result.hand_landmarks[start][0] * w), int(result.hand_landmarks[start][1] * h))
                pt2 = (int(result.hand_landmarks[end][0] * w), int(result.hand_landmarks[end][1] * h))
                cv2.line(vis_frame, pt1, pt2, (0, 200, 0), 2)
        
        # Label
        gesture_text = result.gesture.value.replace('_', ' ').title()
        label = f"{result.handedness}: {gesture_text} ({result.confidence:.0%})"
        
        (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(vis_frame, (10, 10), (20 + text_w, 40 + text_h), (0, 0, 0), -1)
        cv2.putText(vis_frame, label, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return vis_frame
    
    def cleanup(self):
        """Release resources."""
        if self.detector:
            self.detector.close()
