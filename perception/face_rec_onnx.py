
import cv2
import numpy as np
import os
import json
import time
from typing import Optional, Dict, List, Tuple

# Config
YUNET_MODEL = "perception/models/face_detection_yunet_2023mar.onnx"
SFACE_MODEL = "perception/models/face_recognition_sface_2021dec.onnx"
EMBEDDINGS_DIR = "face_embeddings"
USERS_FILE = "face_users.json"

class FaceRecONNX:
    """
    Highly Optimized Face Recognition for Pi 5.
    Uses OpenCV DNN (YuNet + SFace) for 30+ FPS performance.
    """
    def __init__(self, threshold=0.70): 
        # SFace Cosine: 0.70 is the sweet spot for ONNX. 
        # (Combined with SceneState 1.0s verification timer for stability)
        self.threshold = threshold
        self.users = {}
        
        # 1. Initialize Detector (YuNet)
        if not os.path.exists(YUNET_MODEL):
            print(f"[Face] ❌ Missing Model: {YUNET_MODEL}")
            self.detector = None
            return
            
        self.detector = cv2.FaceDetectorYN.create(
            YUNET_MODEL,
            "",
            (320, 320), # Input size
            0.8, # Score threshold
            0.3, # NMS threshold
            5000 # Top K
        )
        
        # 2. Initialize Recognizer (SFace)
        if not os.path.exists(SFACE_MODEL):
            print(f"[Face] ❌ Missing Model: {SFACE_MODEL}")
            self.recognizer = None
            return

        self.recognizer = cv2.FaceRecognizerSF.create(
            SFACE_MODEL,
            ""
        )
        
        print("[Face] ✓ ONNX Engine Initialized (YuNet + SFace)")
        
        self._load_users()
        
    def _load_users(self):
        """Load user embeddings from disk."""
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
        if os.path.exists(USERS_FILE):
             try:
                with open(USERS_FILE, 'r') as f:
                    meta = json.load(f)
                
                for name, data in meta.items():
                    emb_path = os.path.join(EMBEDDINGS_DIR, f"{name}.npy")
                    if os.path.exists(emb_path):
                        embeddings = np.load(emb_path)
                        # Ensure 2D array
                        if embeddings.ndim == 1: 
                            embeddings = embeddings.reshape(1, -1)
                        self.users[name] = {
                            'embeddings': list(embeddings),
                            'registered': data.get('registered', 0)
                        }
                print(f"[Face] Loaded {len(self.users)} users.")
             except Exception as e:
                 print(f"[Face] Load error: {e}")

    def _save_users(self):
        """Save DB to disk."""
        meta = {}
        for name, data in self.users.items():
            meta[name] = {'registered': data['registered']}
            # Save vectors
            emb_path = os.path.join(EMBEDDINGS_DIR, f"{name}.npy")
            np.save(emb_path, np.vstack(data['embeddings']))
            
        with open(USERS_FILE, 'w') as f:
            json.dump(meta, f)

    def detect(self, frame):
        """Detect faces. Returns bbox + landmarks."""
        if not self.detector: return None
        
        h, w = frame.shape[:2]
        self.detector.setInputSize((w, h))
        
        # Inference
        # Faces: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
        _, faces = self.detector.detect(frame)
        return faces

    def get_features(self, frame, face_data):
        """Get 128-d normalized embedding using SFace."""
        # Align using landmarks from YuNet result
        aligned_face = self.recognizer.alignCrop(frame, face_data)
        # Extract features
        return self.recognizer.feature(aligned_face)

    def register_face(self, frame, bbox_raw=None, name="User", keypoints=None):
        """Register a detected face."""
        # 1. Detect
        faces = self.detect(frame)
        if faces is None: 
            print("No face detected for registration.")
            return False
        
        # Find best face (largest)
        # YuNet returns faces as rows.
        # Check if bbox is provided to filter?
        # For simplicity, take the largest face in frame
        
        # Sort by width
        best_face = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)[0]
        
        # Quality check: Score
        if best_face[14] < 0.9:
            print("Face quality too low (Confidence < 0.9).")
            return False
            
        # Blur check
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_roi = gray[int(best_face[1]):int(best_face[1]+best_face[3]), 
                       int(best_face[0]):int(best_face[0]+best_face[2])]
        if face_roi.size > 0:
            variance = cv2.Laplacian(face_roi, cv2.CV_64F).var()
            if variance < 100: # Threshold for blur
                print(f"Registration failed: Face too blurry (Var: {variance:.1f})")
                return False

        # Get embedding
        emb = self.get_features(frame, best_face)
        
        # Store
        if name not in self.users:
            self.users[name] = {'embeddings': [], 'registered': time.time()}
            
        # Duplicate check (Cosine Sim)
        for existing in self.users[name]['embeddings']:
            score = self.recognizer.match(existing, emb, cv2.FaceRecognizerSF_FR_COSINE)
            if score > self.threshold: 
                 print(f"Skipping duplicate angle (Score: {score:.2f})")
                 return True
                 
        self.users[name]['embeddings'].append(emb)
        self._save_users()
        print(f"[Face] Registered {name} | blur_score={variance:.1f}")
        return True

    def recognize(self, frame, bbox=None, keypoints=None):
        """
        Recognize face in frame.
        Args:
            frame: Image
            bbox: Optional [x, y, w, h] target area (e.g. from tracker/pose) to limit recognition.
        """
        faces = self.detect(frame)
        if faces is None or len(faces) == 0: return None, 0.0
        
        target_face = None
        
        if bbox:
            # Find face matching the provided bbox (IOU)
            bx, by, bw, bh = bbox
            max_iou = 0.0
            
            for face in faces:
                # face: [x, y, w, h, ...]
                fx, fy, fw, fh = face[:4]
                
                # Calculate IOU
                ix = max(bx, fx)
                iy = max(by, fy)
                iw = min(bx+bw, fx+fw) - ix
                ih = min(by+bh, fy+fh) - iy
                
                if iw > 0 and ih > 0:
                    inter = iw * ih
                    union = (bw*bh) + (fw*fh) - inter
                    iou = inter / union
                    if iou > max_iou:
                        max_iou = iou
                        target_face = face
                        
            if max_iou < 0.1: # Threshold IOU
                # print(f"No matching face for bbox found (Max IoU: {max_iou:.2f})")
                return None, 0.0
        else:
            # Default: Largest face
            target_face = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)[0]
            
        if target_face is None: return None, 0.0
        
        current_emb = self.get_features(frame, target_face)
        
        best_name = None
        best_score = 0.0
        
        # Match against database
        for name, data in self.users.items():
            local_best = 0.0
            for known_emb in data['embeddings']:
                # Ensure shapes match (1, 128)
                curr_emb_reshaped = current_emb.reshape(1, -1)
                known_emb_reshaped = known_emb.reshape(1, -1)
                
                score = self.recognizer.match(curr_emb_reshaped, known_emb_reshaped, cv2.FaceRecognizerSF_FR_COSINE)
                if score > local_best: local_best = score
            
            if local_best > best_score:
                best_score = local_best
                best_name = name
        
        if best_score > self.threshold:
            return best_name, best_score
        
        return None, best_score

    def list_users(self):
        return list(self.users.keys())

# Test
if __name__ == "__main__":
    fr = FaceRecONNX()
    print("Engine loaded.")
