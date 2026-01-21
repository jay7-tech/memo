import torch
from facenet_pytorch import InceptionResnetV1
import numpy as np
import cv2
import os

class FaceRecognizer:
    def __init__(self):
        self.device = 'cpu' # Use CPU to avoid interfering with YOLO GPU usage if any
        if torch.cuda.is_available():
            self.device = 'cuda'
            
        print(f"FaceRec using device: {self.device}")
        
        # Load Pretrained Model (vggface2 or casia-webface)
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        
        self.known_embedding = None
        self.user_name = "User"
        
        # Load known face if exists
        self.load_user()

    def load_user(self):
        if os.path.exists("user_embedding.npy"):
            try:
                self.known_embedding = np.load("user_embedding.npy")
                # Try to load name
                if os.path.exists("user_name.txt"):
                    with open("user_name.txt", "r") as f:
                        self.user_name = f.read().strip()
                else:
                    self.user_name = "User"
                
                print(f"FaceRec: Loaded profile for {self.user_name}")
            except:
                pass
        
    def save_user(self, embedding, name="User"):
        if embedding is not None:
            self.known_embedding = embedding
            self.user_name = name
            np.save("user_embedding.npy", embedding)
            with open("user_name.txt", "w") as f:
                f.write(name)
            print(f"FaceRec: Saved profile for {name}")

    def get_embedding(self, face_crop):
        """
        Expects a BGR face crop (numpy array).
        """
        if face_crop is None or face_crop.size == 0:
            return None
            
        # Resize to 160x160 (Stack requirements for InceptionResnetV1)
        img = cv2.resize(face_crop, (160, 160))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Normalize/Whiten: (x - 127.5) / 128.0
        # Facenet-pytorch expects [0, 1] range if using its transform, 
        # BUT standard practice for this model is fixed standardization.
        # Actually facenet-pytorch's fixed_image_standardization does (x - 127.5)/128.0
        
        img = np.float32(img)
        img = (img - 127.5) / 128.0
        
        # To Tensor: (C, H, W)
        img_tensor = torch.tensor(img).permute(2, 0, 1).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            emb = self.resnet(img_tensor)
            
        return emb.cpu().numpy()[0]

    def recognize(self, frame, bbox):
        """
        bbox: [x, y, w, h]
        Returns: name (str) or None
        """
        x, y, w, h = map(int, bbox)
        
        # Check bounds
        h_img, w_img = frame.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        
        if w < 20 or h < 20: return None
        
        crop = frame[y:y+h, x:x+w]
        emb = self.get_embedding(crop)
        
        if self.known_embedding is not None and emb is not None:
            # Calculate distance (Euclidean makes most sense for FaceNet)
            # dist = np.linalg.norm(emb - self.known_embedding)
            
            # Cosine Similarity is often better for embeddings
            # (A . B) / (|A| * |B|)
            # Vectors from InceptionResnetV1 are usually not normalized to unit length by default?
            # Actually they are NOT.
            
            emb_norm = emb / np.linalg.norm(emb)
            known_norm = self.known_embedding / np.linalg.norm(self.known_embedding)
            
            cos_sim = np.dot(emb_norm, known_norm)
            
            # Threshold: > 0.6 is usually same person for Facenet
            # Let's say 0.7 to be safe/secure
            
            if cos_sim > 0.6: # Tunable
                return self.user_name
        
        return None
        
    def register_face(self, frame, bbox, name="User"):
        x, y, w, h = map(int, bbox)
        h_img, w_img = frame.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        
        crop = frame[y:y+h, x:x+w]
        emb = self.get_embedding(crop)
        
        if emb is not None:
             self.save_user(emb, name)
             return True
        return False
