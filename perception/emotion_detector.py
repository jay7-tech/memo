"""
Emotion Detection Module
Uses FER (Facial Expression Recognition) library for accurate detection.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from enum import Enum

# Check for FER library
HAS_FER = False
try:
    from fer.fer import FER
    HAS_FER = True
except ImportError:
    pass


class Emotion(Enum):
    """Detected emotions."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprise"  # FER uses "surprise" not "surprised"
    NEUTRAL = "neutral"
    FEAR = "fear"
    DISGUST = "disgust"
    UNKNOWN = "unknown"


@dataclass
class EmotionResult:
    """Result of emotion detection."""
    emotion: Emotion
    confidence: float
    face_bbox: Optional[Tuple[int, int, int, int]] = None
    all_emotions: Optional[Dict[str, float]] = None


class EmotionDetector:
    """
    Detects facial emotions using FER (Facial Expression Recognition).
    Uses MTCNN for face detection and CNN for emotion classification.
    """
    
    def __init__(
        self,
        min_face_size: int = 48,
        stability_frames: int = 5,
        use_mtcnn: bool = False  # MTCNN is more accurate but slower
    ):
        self.min_face_size = min_face_size
        self.stability_frames = stability_frames
        self.emotion_history: List[Emotion] = []
        self.stable_emotion: Optional[Emotion] = None
        
        self.detector = None
        self.backend = "none"
        
        if HAS_FER:
            try:
                # Initialize FER detector
                # mtcnn=True is more accurate, mtcnn=False uses OpenCV (faster)
                self.detector = FER(mtcnn=use_mtcnn)
                self.backend = "fer_mtcnn" if use_mtcnn else "fer_opencv"
                print(f"Using FER library ({'MTCNN' if use_mtcnn else 'OpenCV'} backend)")
            except Exception as e:
                print(f"FER initialization failed: {e}")
        
        if self.detector is None:
            # Fallback to basic OpenCV
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.backend = "opencv_basic"
            print("Using OpenCV Haar cascades (basic fallback)")
    
    def detect(self, frame: np.ndarray) -> Optional[EmotionResult]:
        """Detect emotion from the frame."""
        if self.backend.startswith("fer"):
            return self._detect_fer(frame)
        else:
            return self._detect_opencv(frame)
    
    def _detect_fer(self, frame: np.ndarray) -> Optional[EmotionResult]:
        """Detect emotion using FER library."""
        # Detect emotions
        result = self.detector.detect_emotions(frame)
        
        if not result:
            self._reset_stability()
            return None
        
        # Get first face (largest usually)
        face_data = result[0]
        box = face_data['box']  # [x, y, w, h]
        emotions = face_data['emotions']  # {'angry': 0.1, 'happy': 0.8, ...}
        
        # Validate face size
        if box[2] < self.min_face_size or box[3] < self.min_face_size:
            self._reset_stability()
            return None
        
        # Find dominant emotion
        if emotions:
            dominant = max(emotions.items(), key=lambda x: x[1])
            try:
                # Handle FER's "surprise" vs our "surprised"
                emotion_name = dominant[0]
                if emotion_name == "surprise":
                    emotion = Emotion.SURPRISED
                else:
                    emotion = Emotion(emotion_name)
            except ValueError:
                emotion = Emotion.UNKNOWN
            confidence = dominant[1]
        else:
            emotion = Emotion.NEUTRAL
            confidence = 0.5
        
        # Update stability
        emotion = self._update_stability(emotion)
        
        return EmotionResult(
            emotion=emotion,
            confidence=confidence,
            face_bbox=tuple(box),
            all_emotions=emotions
        )
    
    def _detect_opencv(self, frame: np.ndarray) -> Optional[EmotionResult]:
        """Basic fallback using OpenCV."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5,
            minSize=(self.min_face_size, self.min_face_size)
        )
        
        if len(faces) == 0:
            self._reset_stability()
            return None
        
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        
        # Basic neutral detection
        emotion = self._update_stability(Emotion.NEUTRAL)
        
        return EmotionResult(
            emotion=emotion,
            confidence=0.5,
            face_bbox=(x, y, w, h),
            all_emotions={'neutral': 0.5}
        )
    
    def _update_stability(self, emotion: Emotion) -> Emotion:
        """Prevent emotion flickering with temporal smoothing."""
        self.emotion_history.append(emotion)
        
        # Keep only recent history
        if len(self.emotion_history) > self.stability_frames:
            self.emotion_history.pop(0)
        
        # Find most common emotion in history
        if len(self.emotion_history) >= 2:
            from collections import Counter
            emotion_counts = Counter(self.emotion_history)
            most_common = emotion_counts.most_common(1)[0]
            
            # Require majority to change stable emotion
            if most_common[1] >= len(self.emotion_history) // 2 + 1:
                self.stable_emotion = most_common[0]
        
        return self.stable_emotion if self.stable_emotion else emotion
    
    def _reset_stability(self):
        """Reset tracking when no face detected."""
        self.emotion_history.clear()
        self.stable_emotion = None
    
    def visualize(self, frame: np.ndarray, result: EmotionResult) -> np.ndarray:
        """Draw face box, emotion label, and emotion bars."""
        vis_frame = frame.copy()
        h, w = frame.shape[:2]
        
        if result.face_bbox:
            fx, fy, fw, fh = result.face_bbox
            color = self._get_emotion_color(result.emotion)
            
            # Draw face bounding box
            cv2.rectangle(vis_frame, (fx, fy), (fx + fw, fy + fh), color, 3)
            
            # Draw emotion label with background
            emoji = self.get_emoji(result.emotion)
            # Handle "surprise" -> "Surprised" display
            display_name = "Surprised" if result.emotion == Emotion.SURPRISED else result.emotion.value.title()
            label = f"{emoji} {display_name} ({result.confidence:.0%})"
            
            font_scale = 0.8
            thickness = 2
            (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            
            # Label background
            label_y = fy - 10 if fy > 40 else fy + fh + 30
            cv2.rectangle(vis_frame, (fx, label_y - th - 10), (fx + tw + 15, label_y + 5), color, -1)
            cv2.putText(vis_frame, label, (fx + 8, label_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
            
            # Draw emotion probability bars (right side)
            if result.all_emotions:
                bar_x = min(fx + fw + 15, w - 150)
                bar_y = fy
                bar_max_width = 100
                bar_height = 18
                bar_spacing = 5
                
                # Sort emotions by score
                sorted_emotions = sorted(result.all_emotions.items(), key=lambda x: -x[1])
                
                for i, (emo_name, score) in enumerate(sorted_emotions):
                    y_pos = bar_y + i * (bar_height + bar_spacing)
                    
                    if y_pos + bar_height > h - 20:
                        break
                    
                    # Background bar
                    cv2.rectangle(vis_frame, (bar_x, y_pos),
                                 (bar_x + bar_max_width, y_pos + bar_height), (40, 40, 40), -1)
                    
                    # Score bar
                    fill_width = int(score * bar_max_width)
                    try:
                        if emo_name == "surprise":
                            emo_enum = Emotion.SURPRISED
                        else:
                            emo_enum = Emotion(emo_name)
                        bar_color = self._get_emotion_color(emo_enum)
                    except ValueError:
                        bar_color = (128, 128, 128)
                    
                    cv2.rectangle(vis_frame, (bar_x, y_pos),
                                 (bar_x + fill_width, y_pos + bar_height), bar_color, -1)
                    
                    # Emotion label
                    display = "surp" if emo_name == "surprise" else emo_name[:4]
                    cv2.putText(vis_frame, f"{display}: {score:.0%}",
                               (bar_x + 5, y_pos + bar_height - 4),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return vis_frame
    
    def _get_emotion_color(self, emotion: Emotion) -> Tuple[int, int, int]:
        """Get BGR color for emotion."""
        colors = {
            Emotion.HAPPY: (0, 255, 100),      # Bright Green
            Emotion.SAD: (255, 150, 0),        # Blue
            Emotion.ANGRY: (0, 0, 255),        # Red
            Emotion.SURPRISED: (0, 255, 255),  # Yellow
            Emotion.NEUTRAL: (200, 200, 200),  # Gray
            Emotion.FEAR: (255, 0, 150),       # Purple
            Emotion.DISGUST: (0, 150, 0),      # Dark Green
            Emotion.UNKNOWN: (128, 128, 128)
        }
        return colors.get(emotion, (255, 255, 255))
    
    def get_emoji(self, emotion: Emotion) -> str:
        """Get emoji for emotion."""
        emojis = {
            Emotion.HAPPY: "😊",
            Emotion.SAD: "😢",
            Emotion.ANGRY: "😠",
            Emotion.SURPRISED: "😲",
            Emotion.NEUTRAL: "😐",
            Emotion.FEAR: "😨",
            Emotion.DISGUST: "🤢",
            Emotion.UNKNOWN: "🤔"
        }
        return emojis.get(emotion, "🤔")
    
    def cleanup(self):
        """Cleanup resources."""
        pass
