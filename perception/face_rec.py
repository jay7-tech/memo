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
        """Load users from disk."""
        if not os.path.exists(self.users_file):
            return
        
        try:
            with open(self.users_file, 'r') as f:
                user_meta = json.load(f)
            
            for name, meta in user_meta.items():
                emb_file = os.path.join(self.embeddings_dir, f"{name}.npy")
                if os.path.exists(emb_file):
                    embedding = np.load(emb_file)
                    self.users[name] = {
                        'embedding': embedding,
                        'registered': meta.get('registered', 0)
                    }
            
            print(f"[FaceRec] ✓ Loaded {len(self.users)} users: {list(self.users.keys())}")
            
        except Exception as e:
            print(f"[FaceRec] Error loading users: {e}")
    
    def _save_users(self):
        """Save users to disk."""
        try:
            # Save metadata
            meta = {}
            for name, data in self.users.items():
                meta[name] = {'registered': data.get('registered', 0)}
                
                # Save embedding
                emb_file = os.path.join(self.embeddings_dir, f"{name}.npy")
                np.save(emb_file, data['embedding'])
            
            with open(self.users_file, 'w') as f:
                json.dump(meta, f, indent=2)
            
            print(f"[FaceRec] ✓ Saved {len(self.users)} users")
            
        except Exception as e:
            print(f"[FaceRec] Error saving users: {e}")
    
    def _migrate_legacy(self):
        """Migrate from old single-user format."""
        legacy_emb = "user_embedding.npy"
        legacy_name = "user_name.txt"
        
        if os.path.exists(legacy_emb) and os.path.exists(legacy_name):
            try:
                embedding = np.load(legacy_emb)
                with open(legacy_name, 'r') as f:
                    name = f.read().strip()
                
                if name and name not in self.users:
                    self.users[name] = {
                        'embedding': embedding,
                        'registered': os.path.getmtime(legacy_emb)
                    }
                    self._save_users()
                    print(f"[FaceRec] ✓ Migrated legacy user: {name}")
                
                # Optionally remove legacy files
                # os.remove(legacy_emb)
                # os.remove(legacy_name)
                
            except Exception as e:
                print(f"[FaceRec] Legacy migration failed: {e}")
    
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
        name: str = "User"
    ) -> bool:
        """
        Register a new user's face.
        
        Args:
            frame: Full BGR video frame
            bbox: Face bounding box [x, y, width, height]
            name: User's name
        
        Returns:
            True if registration successful
        """
        if self.model is None:
            print("[FaceRec] Model not available")
            return False
            
        if frame is None:
            print("[FaceRec] Cannot register face: No frame provided")
            return False
            
        # Extract face crop
        x, y, w, h = map(int, bbox)
        h_img, w_img = frame.shape[:2]
        
        # Clamp to image bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        
        if w < 30 or h < 30:
            print("[FaceRec] Face too small")
            return False
        
        crop = frame[y:y+h, x:x+w]
        embedding = self.get_embedding(crop)
        
        if embedding is None:
            print("[FaceRec] Could not extract embedding")
            return False
        
        # Store user
        import time
        self.users[name] = {
            'embedding': embedding,
            'registered': time.time()
        }
        
        self._save_users()
        print(f"[FaceRec] ✓ Registered: {name}")
        return True
    
    def recognize(
        self,
        frame: np.ndarray,
        bbox: List[int]
    ) -> Optional[str]:
        """
        Recognize a face and return the user's name.
        
        Args:
            frame: Full BGR video frame
            bbox: Face bounding box [x, y, width, height]
        
        Returns:
            User's name if recognized, None otherwise
        """
        if self.model is None or not self.users:
            return None
        
        # Extract face crop
        x, y, w, h = map(int, bbox)
        h_img, w_img = frame.shape[:2]
        
        # Clamp to bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        
        if w < 20 or h < 20:
            return None
        
        crop = frame[y:y+h, x:x+w]
        embedding = self.get_embedding(crop)
        
        if embedding is None:
            return None
        
        # Compare with all users
        best_match = None
        best_similarity = 0.0
        
        # Normalize query embedding
        emb_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        for name, data in self.users.items():
            known_emb = data['embedding']
            known_norm = known_emb / (np.linalg.norm(known_emb) + 1e-8)
            
            # Cosine similarity
            similarity = float(np.dot(emb_norm, known_norm))
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = name
        
        # Return match if above threshold
        if best_similarity >= self.threshold:
            print(f"[FaceRec] Match: {best_match} ({best_similarity:.2f})")
            return best_match
        else:
            if best_match:
                print(f"[FaceRec] Unknown (Best: {best_match} @ {best_similarity:.2f})")
    
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
    recognizer = FaceRecognizer()
    if recognizer.users:
        first_user = list(recognizer.users.keys())[0]
        return recognizer.users[first_user]['embedding'], first_user
    return None, "User"


# Quick test
if __name__ == "__main__":
    print("Testing FaceRecognizer...")
    
    face_rec = FaceRecognizer()
    print(f"Registered users: {face_rec.list_users()}")
    print(f"User count: {face_rec.get_user_count()}")
    
    # Test with webcam
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            # Fake bbox for center of frame
            h, w = frame.shape[:2]
            bbox = [w//4, h//4, w//2, h//2]
            
            # Test recognition
            result = face_rec.recognize(frame, bbox)
            print(f"Recognition result: {result}")
        
        cap.release()
    
    print("Test complete")
