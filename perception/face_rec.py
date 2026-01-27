"""
MEMO - Face Recognition Module
===============================

This module provides face recognition capabilities using FaceNet (InceptionResnetV1).

Features:
    - Face embedding extraction using pre-trained FaceNet model (VGGFace2)
    - Single-user registration and recognition
    - Cosine similarity matching for robust identification
    - Persistent user profile storage (embedding + name)

Architecture:
    - Model: InceptionResnetV1 (FaceNet variant)
    - Pretrained: VGGFace2 dataset (3.31M identities)
    - Embedding Size: 512-dimensional vector
    - Input: 160x160 RGB face crop

Recognition Pipeline:
    1. Receive face bounding box from object detector
    2. Crop and resize face region to 160x160
    3. Normalize pixel values: (x - 127.5) / 128.0
    4. Extract 512-dim embedding via InceptionResnetV1
    5. Compare with stored embedding using cosine similarity
    6. Return identity if similarity > 0.6 threshold

Storage:
    - user_embedding.npy: 512-dim numpy array
    - user_name.txt: Registered user's name

Dependencies:
    - torch
    - facenet-pytorch
    - numpy
    - opencv-python

Example:
    >>> face_rec = FaceRecognizer()
    >>> # Register a new user
    >>> face_rec.register_face(frame, bbox=[100, 50, 150, 150], name="Jayadeep")
    >>> # Recognize in subsequent frames
    >>> identity = face_rec.recognize(frame, bbox)
    >>> print(f"Detected: {identity}")

Performance:
    - Inference: ~50ms on CPU, ~10ms on CUDA
    - Accuracy: ~99.65% on LFW dataset

Author: Jayadeep / Jay7-Tech
Module: perception/face_rec.py
"""

import torch
from facenet_pytorch import InceptionResnetV1
import numpy as np
import cv2
import os


class FaceRecognizer:
    """
    Face recognition using FaceNet (InceptionResnetV1).
    
    This class provides face recognition capabilities for identifying
    registered users in video frames. It uses FaceNet embeddings and
    cosine similarity matching.
    
    Attributes:
        device (str): Computation device ('cpu' or 'cuda').
        resnet (Model): InceptionResnetV1 model for embedding extraction.
        known_embedding (ndarray): 512-dim embedding of registered user.
        user_name (str): Name of registered user.
    
    Example:
        >>> face_rec = FaceRecognizer()
        >>> # Register your face
        >>> face_rec.register_face(frame, [100, 50, 150, 150], "Jayadeep")
        >>> # Later, recognize
        >>> identity = face_rec.recognize(frame, [100, 50, 150, 150])
        >>> print(f"Hello, {identity}!")  # "Hello, Jayadeep!"
    """
    
    def __init__(self):
        """
        Initialize FaceRecognizer with InceptionResnetV1 model.
        
        Automatically selects CUDA if available, otherwise uses CPU.
        Loads any existing user profile from disk.
        """
        self.device = 'cpu'  # Use CPU to avoid interfering with YOLO GPU usage if any
        if torch.cuda.is_available():
            self.device = 'cuda'
            
        print(f"FaceRec using device: {self.device}")
        
        # Load Pretrained Model (vggface2 or casia-webface)
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        
        self.known_embedding = None
        self.user_name = "User"
        
        # Load known face if exists
        self.load_user()

    def load_user(self) -> None:
        """
        Load saved user profile from disk.
        
        Loads:
            - user_embedding.npy: 512-dimensional face embedding
            - user_name.txt: Registered user's name
        
        Called automatically during initialization.
        """
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
        
    def save_user(self, embedding: np.ndarray, name: str = "User") -> None:
        """
        Save user profile to disk.
        
        Args:
            embedding (ndarray): 512-dimensional face embedding vector.
            name (str): User's name to associate with the embedding.
        
        Saves:
            - user_embedding.npy: The embedding array
            - user_name.txt: The user's name
        """
        if embedding is not None:
            self.known_embedding = embedding
            self.user_name = name
            np.save("user_embedding.npy", embedding)
            with open("user_name.txt", "w") as f:
                f.write(name)
            print(f"FaceRec: Saved profile for {name}")

    def get_embedding(self, face_crop: np.ndarray) -> np.ndarray:
        """
        Extract 512-dimensional face embedding from a cropped face image.
        
        Processing Pipeline:
            1. Resize to 160x160 (InceptionResnetV1 input size)
            2. Convert BGR to RGB color space
            3. Normalize: (pixel - 127.5) / 128.0
            4. Convert to PyTorch tensor
            5. Forward pass through InceptionResnetV1
        
        Args:
            face_crop (ndarray): BGR face image (any size).
        
        Returns:
            ndarray: 512-dimensional embedding vector.
            None: If input is invalid or empty.
        
        Note:
            The embedding is L2-normalizable but returned raw from model.
            Cosine similarity is used for matching in recognize().
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

    def recognize(self, frame: np.ndarray, bbox: list) -> str:
        """
        Recognize a face in the frame and return the identity.
        
        Extracts embedding from the face region and compares it to
        the stored user embedding using cosine similarity.
        
        Args:
            frame (ndarray): Full BGR video frame.
            bbox (list): Face bounding box as [x, y, width, height].
        
        Returns:
            str: User's name if cosine similarity > 0.6 threshold.
            None: If no match, no registered user, or invalid bbox.
        
        Algorithm:
            1. Crop face region from frame
            2. Extract embedding via get_embedding()
            3. Normalize both embeddings to unit vectors
            4. Compute cosine similarity: dot(emb, known)
            5. Return name if similarity > 0.6
        
        Example:
            >>> identity = face_rec.recognize(frame, det['bbox'])
            >>> if identity:
            ...     print(f"Welcome back, {identity}!")
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
