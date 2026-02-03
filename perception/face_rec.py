"""
MEMO - Face Recognition Module (Multi-User)
============================================
Supports multiple user profiles with persistent storage.

Features:
    - Multi-user face registration and recognition
    - Cosine similarity matching with configurable threshold
    - Persistent storage in JSON format
    - Best match selection among all users
    - Backward compatible with single-user files

Architecture:
    - Model: InceptionResnetV1 (FaceNet variant)
    - Pretrained: VGGFace2 dataset
    - Embedding Size: 512-dimensional vector
    - Input: 160x160 RGB face crop
"""

import torch
import numpy as np
import cv2
import os
import json
from typing import Optional, Dict, List, Tuple

# Check for facenet-pytorch
HAS_FACENET = False
try:
    from facenet_pytorch import InceptionResnetV1
    HAS_FACENET = True
except ImportError:
    pass


class FaceRecognizer:
    """
    Multi-user face recognition using FaceNet.
    
    Supports registering multiple users and recognizing any of them.
    Embeddings are stored persistently and loaded on startup.
    """
    
    def __init__(
        self,
        threshold: float = 0.75, # Strict threshold
        users_file: str = "face_users.json",
        embeddings_dir: str = "face_embeddings"
    ):
        """
        Initialize FaceRecognizer.
        
        Args:
            threshold: Cosine similarity threshold for recognition (0.0-1.0)
            users_file: Path to JSON file storing user metadata
            embeddings_dir: Directory to store user embeddings
        """
        self.threshold = threshold
        self.users_file = users_file
        self.embeddings_dir = embeddings_dir
        
        # Check if facenet-pytorch is available
        if not HAS_FACENET:
            print("[FaceRec] facenet-pytorch not available - face recognition disabled")
            self.model = None
            self.users = {}
            return
        
        # Device selection
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[FaceRec] Using device: {self.device}")
        
        # Load model
        try:
            self.model = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
            print("[FaceRec] ✓ Model loaded")
        except Exception as e:
            print(f"[FaceRec] Model load failed: {e}")
            self.model = None
            self.users = {}
            return
        
        # User storage: {"name": {"embedding": np.array, "registered": timestamp}}
        self.users: Dict[str, Dict] = {}
        
        # Create embeddings directory
        os.makedirs(self.embeddings_dir, exist_ok=True)
        
        # Load existing users
        self._load_users()
        
        # Migrate from old single-user format if exists
        self._migrate_legacy()
    
    def _load_users(self):
        """Load users from disk with migration support."""
        if not os.path.exists(self.users_file):
            return
        
        try:
            with open(self.users_file, 'r') as f:
                user_meta = json.load(f)
            
            for name, meta in user_meta.items():
                emb_file = os.path.join(self.embeddings_dir, f"{name}.npy")
                
                embeddings_list = []
                if os.path.exists(emb_file):
                    data = np.load(emb_file)
                    # Migration: Single vector (512,) -> Multi vector (N, 512)
                    if data.ndim == 1:
                        data = data.reshape(1, -1)
                    
                    filters_passed = 0
                    for vec in data:
                        embeddings_list.append(vec)
                        filters_passed += 1

                if embeddings_list:
                    self.users[name] = {
                        'embeddings': embeddings_list,
                        'registered': meta.get('registered', 0)
                    }
            
            print(f"[FaceRec] ✓ Loaded {len(self.users)} users (Multi-Vector Enabled)")
            
        except Exception as e:
            print(f"[FaceRec] Error loading users: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_users(self):
        """Save users to disk (Stacked Embeddings)."""
        try:
            meta = {}
            for name, data in self.users.items():
                meta[name] = {'registered': data.get('registered', 0)}
                
                # Stack list of arrays -> (N, 512)
                if data['embeddings']:
                    stacked = np.vstack(data['embeddings'])
                    emb_file = os.path.join(self.embeddings_dir, f"{name}.npy")
                    np.save(emb_file, stacked)
            
            with open(self.users_file, 'w') as f:
                json.dump(meta, f, indent=2)
            
            # print(f"[FaceRec] ✓ Saved DB")
            
        except Exception as e:
            print(f"[FaceRec] Error saving users: {e}")

    def align_face(self, frame, keypoints):
        """
        Geometrically align face based on eye position.
        """
        if not keypoints: 
            return frame
            
        # Extract eye logic
        # Expecting keypoints dict with 'LEFT_EYE' and 'RIGHT_EYE'
        if 'LEFT_EYE' not in keypoints or 'RIGHT_EYE' not in keypoints:
            return frame
            
        left_eye = keypoints['LEFT_EYE']   # (x, y)
        right_eye = keypoints['RIGHT_EYE'] # (x, y)
        
        # Calculate angle
        dY = right_eye[1] - left_eye[1]
        dX = right_eye[0] - left_eye[0]
        angle = np.degrees(np.arctan2(dY, dX))
        
        # Eye center
        eye_center = ((left_eye[0] + right_eye[0]) // 2, (left_eye[1] + right_eye[1]) // 2)
        
        # Get rotation matrix (rotate around eye center)
        M = cv2.getRotationMatrix2D(eye_center, angle, 1.0)
        
        # Apply strict rotation
        h, w = frame.shape[:2]
        aligned = cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_CUBIC)
        
        # print(f"[FaceRec] Aligned face: {angle:.1f} deg")
        return aligned

    def check_blur(self, img, threshold=50.0):
        """
        Check image variance (Laplacian) to detect blur.
        Higher threshold = Stricter.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        score = cv2.Laplacian(gray, cv2.CV_64F).var()
        is_blurry = score < threshold
        return is_blurry, score
    
    def _migrate_legacy(self):
        """Migrate from old single-user format."""
        legacy_emb = "user_embedding.npy"
        legacy_name = "user_name.txt"
        
        if os.path.exists(legacy_emb) and os.path.exists(legacy_name):
            try:
                embedding = np.load(legacy_emb)
                with open(legacy_name, 'r') as f:
                    name = f.read().strip()
                
                if name:
                    if name not in self.users:
                        self.users[name] = {'embeddings': [], 'registered': os.path.getmtime(legacy_emb)}
                    self.users[name]['embeddings'].append(embedding)
                    self._save_users()
                    print(f"[FaceRec] ✓ Migrated legacy user: {name}")
            except: pass
    
    def get_embedding(self, face_crop: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract face embedding from cropped face image.
        
        Args:
            face_crop: BGR face image (any size)
        
        Returns:
            512-dimensional embedding or None
        """
        if self.model is None:
            return None
        
        if face_crop is None or face_crop.size == 0:
            return None
        
        try:
            # Resize to 160x160
            img = cv2.resize(face_crop, (160, 160))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Normalize: (x - 127.5) / 128.0
            img = np.float32(img)
            img = (img - 127.5) / 128.0
            
            # To tensor: (C, H, W)
            img_tensor = torch.tensor(img).permute(2, 0, 1).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                emb = self.model(img_tensor)
            
            return emb.cpu().numpy()[0]
            
        except Exception as e:
            print(f"[FaceRec] Embedding error: {e}")
            return None
    
    def register_face(
        self,
        frame: np.ndarray,
        bbox: List[int],
        name: str = "User",
        keypoints: Optional[Dict] = None
    ) -> bool:
        """
        Register a user face with Alignment and Quality Checks.
        Appends to existing memory bank.
        """
    def check_head_pose(self, keypoints, threshold=0.6):
        """
        Check if face is frontal using eye-nose symmetry.
        Returns: True if frontal, False if profile/missing features.
        """
        if not keypoints: return True # No pose data, rely on L2 check
        
        # FAIL-CLOSE: If eyes are missing, it's likely a profile view -> REJECT
        if 'LEFT_EYE' not in keypoints or 'RIGHT_EYE' not in keypoints:
            # print("[FaceRec] Rejected: Missing eyes (Profile)")
            return False 
            
        if 'NOSE' not in keypoints:
            return True 
            
        nose = keypoints['NOSE']
        l_eye = keypoints['LEFT_EYE']
        r_eye = keypoints['RIGHT_EYE']
        
        # Distances
        d_left = abs(nose[0] - l_eye[0])
        d_right = abs(nose[0] - r_eye[0])
        total = d_left + d_right
        if total == 0: return True
        
        symmetry = abs(d_left - d_right) / total
        return symmetry < threshold

    def register_face(
        self,
        frame: np.ndarray,
        bbox: List[int],
        name: str = "User",
        keypoints: Optional[Dict] = None
    ) -> bool:
        """
        Register a user face with Alignment and Quality Checks.
        """
        if self.model is None: return False
        if frame is None: return False
        
        # 0. Pose Check (Frontal Only for Registration)
        if keypoints and not self.check_head_pose(keypoints, threshold=0.4): # Strict for Reg
            print(f"[FaceRec] ⚠️ Look straight at camera (Profile detected)")
            return False

        # 1. Alignment (if pose data allows)
        work_frame = frame
        if keypoints:
            work_frame = self.align_face(frame, keypoints)
            
        # 2. Extract Crop
        x, y, w, h = map(int, bbox)
        h_img, w_img = work_frame.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)
        
        if w < 40 or h < 40: # Stricter size
            print(f"[FaceRec] ⚠️ Face too small to register ({w}x{h})")
            return False
            
        crop = work_frame[y:y+h, x:x+w]
        
        # 3. Blur Check
        is_blurry, score = self.check_blur(crop)
        if is_blurry:
            print(f"[FaceRec] ⚠️ Image too blurry (Score: {score:.1f})")
            return False
            
        # 4. Get Embedding
        embedding = self.get_embedding(crop)
        if embedding is None: return False
        
        # 5. Store in Memory Bank
        import time
        if name not in self.users:
            self.users[name] = {'embeddings': [], 'registered': time.time()}
            
        # Avoid duplicates (Dot product > 0.95 considered same vector)
        is_duplicate = False
        for existing in self.users[name]['embeddings']:
            sim = np.dot(existing, embedding) / (np.linalg.norm(existing) * np.linalg.norm(embedding))
            if sim > 0.95:
                is_duplicate = True
                break
        
        if not is_duplicate:
            self.users[name]['embeddings'].append(embedding)
            # Cap at 10 embeddings per user (FIFO if needed, but for now just cap)
            if len(self.users[name]['embeddings']) > 10:
                self.users[name]['embeddings'].pop(0) # Remove oldest
                
            self._save_users()
            count = len(self.users[name]['embeddings'])
            print(f"[FaceRec] ✓ Registered '{name}' (Sample #{count})")
            return True
        else:
            print(f"[FaceRec] Sample skipped (Duplicate angle)")
            return True # Treat as success since we already know this angle
    
    def recognize(
        self,
        frame: np.ndarray,
        bbox: List[int],
        keypoints: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Recognize using L2 Euclidean Distance (Standard).
        """
        if self.model is None or not self.users:
            return None, 0.0
            
        # 0. Strict Pose Check
        if keypoints and not self.check_head_pose(keypoints, threshold=0.6):
            return None, 0.0
            
        # 1. Align
        work_frame = frame
        if keypoints:
            work_frame = self.align_face(frame, keypoints)
        
        # 2. Crop
        x, y, w, h = map(int, bbox)
        h_img, w_img = work_frame.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)
        
        if w < 20 or h < 20: return None, 0.0
        
        crop = work_frame[y:y+h, x:x+w]
        embedding = self.get_embedding(crop)
        if embedding is None: return None, 0.0
        
        # 3. L2 Distance Match
        best_match = None
        best_dist = 10.0 # High init
        
        for name, data in self.users.items():
            for known_emb in data['embeddings']:
                # Euclidean Distance: sqrt(sum((a-b)^2))
                dist = float(np.linalg.norm(embedding - known_emb))
                
                if dist < best_dist:
                    best_dist = dist
                    best_match = name
        
        # Threshold: Lower is better. 
        # < 0.9 is strong match. > 1.1 is different person.
        l2_threshold = 0.7
        
        if best_dist < l2_threshold:
            # Convert to "Confidence" for UI (Inverse of distance)
            # 0.0 dist -> 1.0 conf. 1.0 dist -> 0.0 conf.
            confidence = max(0.0, 1.0 - (best_dist / 1.2))
            return best_match, confidence
        else:
            return None, 0.0
    
    def list_users(self) -> List[str]:
        """Get list of registered users."""
        return list(self.users.keys())
    
    def remove_user(self, name: str) -> bool:
        """
        Remove a registered user.
        
        Args:
            name: User's name to remove
        
        Returns:
            True if user was removed
        """
        if name in self.users:
            del self.users[name]
            
            # Remove embedding file
            emb_file = os.path.join(self.embeddings_dir, f"{name}.npy")
            if os.path.exists(emb_file):
                os.remove(emb_file)
            
            self._save_users()
            print(f"[FaceRec] Removed user: {name}")
            return True
        
        return False
    
    def get_user_count(self) -> int:
        """Get number of registered users."""
        return len(self.users)


# Backward compatibility: maintain old function signatures
def load_user() -> Tuple[Optional[np.ndarray], str]:
    """Legacy function for backward compatibility."""
    return None, "User"


# Quick test
if __name__ == "__main__":
    print("Testing Updated FaceRecognizer...")
    
    fr = FaceRecognizer()
    print(f"Users: {fr.list_users()}")
    print(f"User count: {fr.get_user_count()}")
    
    # Test with webcam
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            # Fake bbox for center of frame
            h, w = frame.shape[:2]
            bbox = [w//4, h//4, w//2, h//2]
            
            # Test recognition
            result, similarity = fr.recognize(frame, bbox)
            print(f"Recognition result: {result}, Similarity: {similarity:.3f}")
        
        cap.release()
    
    print("Test complete")
