"""
Improved Emotion Detection Module
Uses MediaPipe Face Mesh for accurate facial landmark analysis.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from enum import Enum
import os

# Check for MediaPipe
HAS_MEDIAPIPE = False
try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    HAS_MEDIAPIPE = True
except ImportError:
    pass


class Emotion(Enum):
    """Detected emotions."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
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
    landmarks: Optional[np.ndarray] = None


class EmotionDetector:
    """
    Detects facial emotions using MediaPipe Face Mesh or OpenCV Haar cascades.
    Analyzes facial geometry for emotion classification.
    """
    
    # Key facial landmark indices for emotion detection
    # Based on MediaPipe Face Mesh 468 landmarks
    FACE_INDICES = {
        'left_eye_outer': 33, 'left_eye_inner': 133,
        'right_eye_outer': 362, 'right_eye_inner': 263,
        'left_eyebrow_outer': 70, 'left_eyebrow_inner': 107,
        'right_eyebrow_outer': 300, 'right_eyebrow_inner': 336,
        'nose_tip': 1, 'nose_bottom': 2,
        'mouth_left': 61, 'mouth_right': 291,
        'mouth_top': 13, 'mouth_bottom': 14,
        'left_eye_top': 159, 'left_eye_bottom': 145,
        'right_eye_top': 386, 'right_eye_bottom': 374,
        'chin': 152, 'forehead': 10
    }
    
    def __init__(
        self,
        min_face_size: int = 80,
        stability_frames: int = 5
    ):
        self.min_face_size = min_face_size
        self.stability_frames = stability_frames
        self.emotion_history: List[Emotion] = []
        self.stable_emotion: Optional[Emotion] = None
        
        self.backend = "opencv"
        self.detector = None
        
        # Try MediaPipe Face Mesh
        if HAS_MEDIAPIPE:
            try:
                model_path = self._get_model_path()
                if model_path:
                    base_options = mp_python.BaseOptions(model_asset_path=model_path)
                    options = mp_vision.FaceLandmarkerOptions(
                        base_options=base_options,
                        running_mode=mp_vision.RunningMode.IMAGE,
                        num_faces=1,
                        min_face_detection_confidence=0.5,
                        min_tracking_confidence=0.5,
                        output_face_blendshapes=True  # For emotion analysis
                    )
                    self.detector = mp_vision.FaceLandmarker.create_from_options(options)
                    self.backend = "mediapipe"
                    print("Using MediaPipe Face Mesh (accurate)")
            except Exception as e:
                print(f"MediaPipe Face failed: {e}")
        
        if self.backend == "opencv":
            # Fallback to Haar cascades
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.smile_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_smile.xml'
            )
            print("Using OpenCV Haar cascades (basic)")
    
    def _get_model_path(self) -> Optional[str]:
        """Get or download face landmarker model."""
        model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "face_landmarker.task")
        
        if os.path.exists(model_path):
            return model_path
        
        try:
            import urllib.request
            url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            print("Downloading face model...")
            urllib.request.urlretrieve(url, model_path)
            print(f"Model saved to {model_path}")
            return model_path
        except Exception as e:
            print(f"Could not download model: {e}")
            return None
    
    def detect(self, frame: np.ndarray) -> Optional[EmotionResult]:
        """Detect emotion from face."""
        if self.backend == "mediapipe":
            return self._detect_mediapipe(frame)
        else:
            return self._detect_opencv(frame)
    
    def _detect_mediapipe(self, frame: np.ndarray) -> Optional[EmotionResult]:
        """Detect using MediaPipe Face Mesh."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        result = self.detector.detect(mp_image)
        
        if not result.face_landmarks:
            self._reset_stability()
            return None
        
        h, w = frame.shape[:2]
        landmarks = result.face_landmarks[0]
        
        # Convert to numpy
        lm_array = np.array([[lm.x * w, lm.y * h, lm.z] for lm in landmarks])
        
        # Get face bounding box
        x_coords = lm_array[:, 0]
        y_coords = lm_array[:, 1]
        x_min, x_max = int(min(x_coords)), int(max(x_coords))
        y_min, y_max = int(min(y_coords)), int(max(y_coords))
        face_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
        
        # Analyze blendshapes if available
        if result.face_blendshapes:
            emotion, confidence, all_emotions = self._analyze_blendshapes(result.face_blendshapes[0])
        else:
            # Fallback to geometric analysis
            emotion, confidence, all_emotions = self._analyze_geometry(lm_array, w, h)
        
        emotion = self._update_stability(emotion)
        
        return EmotionResult(
            emotion=emotion,
            confidence=confidence,
            face_bbox=face_bbox,
            all_emotions=all_emotions,
            landmarks=lm_array
        )
    
    def _analyze_blendshapes(self, blendshapes) -> Tuple[Emotion, float, Dict[str, float]]:
        """Analyze MediaPipe face blendshapes for emotion."""
        # Convert blendshapes to dict
        bs = {b.category_name: b.score for b in blendshapes}
        
        emotions = {
            'happy': 0.0,
            'sad': 0.0,
            'angry': 0.0,
            'surprised': 0.0,
            'neutral': 0.3,
            'fear': 0.0,
            'disgust': 0.0
        }
        
        # Happy indicators
        mouth_smile_left = bs.get('mouthSmileLeft', 0)
        mouth_smile_right = bs.get('mouthSmileRight', 0)
        smile = (mouth_smile_left + mouth_smile_right) / 2
        if smile > 0.3:
            emotions['happy'] = min(smile * 1.5, 1.0)
        
        # Surprised indicators
        eye_wide_left = bs.get('eyeWideLeft', 0)
        eye_wide_right = bs.get('eyeWideRight', 0)
        brow_up = (bs.get('browInnerUp', 0) + bs.get('browOuterUpLeft', 0) + bs.get('browOuterUpRight', 0)) / 3
        jaw_open = bs.get('jawOpen', 0)
        if (eye_wide_left + eye_wide_right) / 2 > 0.3 and brow_up > 0.2:
            emotions['surprised'] = min((eye_wide_left + eye_wide_right + brow_up + jaw_open) / 3, 1.0)
        
        # Angry indicators
        brow_down_left = bs.get('browDownLeft', 0)
        brow_down_right = bs.get('browDownRight', 0)
        eye_squint_left = bs.get('eyeSquintLeft', 0)
        eye_squint_right = bs.get('eyeSquintRight', 0)
        if (brow_down_left + brow_down_right) / 2 > 0.3:
            emotions['angry'] = min((brow_down_left + brow_down_right + eye_squint_left + eye_squint_right) / 3, 1.0)
        
        # Sad indicators
        mouth_frown_left = bs.get('mouthFrownLeft', 0)
        mouth_frown_right = bs.get('mouthFrownRight', 0)
        if (mouth_frown_left + mouth_frown_right) / 2 > 0.2:
            emotions['sad'] = min((mouth_frown_left + mouth_frown_right) / 1.5, 1.0)
        
        # Fear indicators
        if brow_up > 0.3 and jaw_open > 0.2 and emotions['surprised'] < 0.5:
            emotions['fear'] = min(brow_up + jaw_open, 1.0) * 0.6
        
        # Disgust indicators  
        nose_sneer_left = bs.get('noseSneerLeft', 0)
        nose_sneer_right = bs.get('noseSneerRight', 0)
        if (nose_sneer_left + nose_sneer_right) / 2 > 0.2:
            emotions['disgust'] = min((nose_sneer_left + nose_sneer_right), 1.0)
        
        # Find dominant
        dominant = max(emotions.items(), key=lambda x: x[1])
        if dominant[1] < 0.25:
            dominant = ('neutral', 0.5)
        
        return Emotion(dominant[0]), dominant[1], emotions
    
    def _analyze_geometry(self, landmarks: np.ndarray, w: int, h: int) -> Tuple[Emotion, float, Dict[str, float]]:
        """Analyze facial geometry for emotion (fallback)."""
        emotions = {
            'happy': 0.0, 'sad': 0.0, 'angry': 0.0,
            'surprised': 0.0, 'neutral': 0.3, 'fear': 0.0, 'disgust': 0.0
        }
        
        try:
            # Mouth aspect ratio
            mouth_left = landmarks[self.FACE_INDICES['mouth_left']]
            mouth_right = landmarks[self.FACE_INDICES['mouth_right']]
            mouth_top = landmarks[self.FACE_INDICES['mouth_top']]
            mouth_bottom = landmarks[self.FACE_INDICES['mouth_bottom']]
            
            mouth_width = np.linalg.norm(mouth_right[:2] - mouth_left[:2])
            mouth_height = np.linalg.norm(mouth_bottom[:2] - mouth_top[:2])
            mouth_ratio = mouth_height / (mouth_width + 1e-6)
            
            # Eye openness
            left_eye_top = landmarks[self.FACE_INDICES['left_eye_top']]
            left_eye_bottom = landmarks[self.FACE_INDICES['left_eye_bottom']]
            eye_openness = np.linalg.norm(left_eye_bottom[:2] - left_eye_top[:2])
            
            # Eyebrow position relative to eyes
            left_brow = landmarks[self.FACE_INDICES['left_eyebrow_inner']]
            left_eye = landmarks[self.FACE_INDICES['left_eye_top']]
            brow_dist = left_eye[1] - left_brow[1]
            
            # Emotion scoring
            if mouth_ratio > 0.3:  # Mouth open
                if eye_openness > 10:  # Eyes wide
                    emotions['surprised'] = 0.7
                else:
                    emotions['happy'] = 0.6
            elif mouth_ratio < 0.1:  # Mouth closed/tight
                if brow_dist < 15:  # Brows furrowed
                    emotions['angry'] = 0.5
                else:
                    emotions['neutral'] = 0.6
            
        except (IndexError, KeyError):
            pass
        
        dominant = max(emotions.items(), key=lambda x: x[1])
        return Emotion(dominant[0]), dominant[1], emotions
    
    def _detect_opencv(self, frame: np.ndarray) -> Optional[EmotionResult]:
        """Detect using OpenCV Haar cascades."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5,
            minSize=(self.min_face_size, self.min_face_size)
        )
        
        if len(faces) == 0:
            self._reset_stability()
            return None
        
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face_roi = gray[y:y+h, x:x+w]
        
        # Detect smile
        smiles = self.smile_cascade.detectMultiScale(
            face_roi[h//2:], scaleFactor=1.7, minNeighbors=20, minSize=(25, 25)
        )
        
        emotions = {
            'happy': 0.0, 'sad': 0.0, 'angry': 0.0,
            'surprised': 0.0, 'neutral': 0.4, 'fear': 0.0, 'disgust': 0.0
        }
        
        if len(smiles) > 0:
            emotions['happy'] = 0.7
        
        emotion = self._update_stability(Emotion(max(emotions, key=emotions.get)))
        
        return EmotionResult(
            emotion=emotion,
            confidence=max(emotions.values()),
            face_bbox=(x, y, w, h),
            all_emotions=emotions
        )
    
    def _update_stability(self, emotion: Emotion) -> Emotion:
        """Prevent emotion flickering."""
        self.emotion_history.append(emotion)
        if len(self.emotion_history) > self.stability_frames:
            self.emotion_history.pop(0)
        
        if len(self.emotion_history) >= self.stability_frames:
            from collections import Counter
            most_common = Counter(self.emotion_history).most_common(1)[0]
            if most_common[1] >= self.stability_frames // 2 + 1:
                self.stable_emotion = most_common[0]
        
        return self.stable_emotion if self.stable_emotion else emotion
    
    def _reset_stability(self):
        self.emotion_history.clear()
        self.stable_emotion = None
    
    def visualize(self, frame: np.ndarray, result: EmotionResult) -> np.ndarray:
        """Draw face box and emotion."""
        vis_frame = frame.copy()
        
        if result.face_bbox:
            x, y, w, h = result.face_bbox
            color = self._emotion_color(result.emotion)
            cv2.rectangle(vis_frame, (x, y), (x+w, y+h), color, 2)
            
            emoji = self.get_emoji(result.emotion)
            label = f"{result.emotion.value.title()} {emoji} ({result.confidence:.0%})"
            
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(vis_frame, (x, y - 25), (x + tw + 10, y), color, -1)
            cv2.putText(vis_frame, label, (x + 5, y - 7),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return vis_frame
    
    def _emotion_color(self, emotion: Emotion) -> Tuple[int, int, int]:
        colors = {
            Emotion.HAPPY: (0, 255, 0),
            Emotion.SAD: (255, 0, 0),
            Emotion.ANGRY: (0, 0, 255),
            Emotion.SURPRISED: (255, 255, 0),
            Emotion.NEUTRAL: (128, 128, 128),
            Emotion.FEAR: (128, 0, 255),
            Emotion.DISGUST: (0, 128, 0),
            Emotion.UNKNOWN: (100, 100, 100)
        }
        return colors.get(emotion, (255, 255, 255))
    
    def get_emoji(self, emotion: Emotion) -> str:
        emojis = {
            Emotion.HAPPY: "😊", Emotion.SAD: "😢", Emotion.ANGRY: "😠",
            Emotion.SURPRISED: "😲", Emotion.NEUTRAL: "😐", Emotion.FEAR: "😨",
            Emotion.DISGUST: "🤢", Emotion.UNKNOWN: "🤔"
        }
        return emojis.get(emotion, "🤔")
    
    def cleanup(self):
        if self.detector:
            self.detector.close()
