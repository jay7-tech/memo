from ultralytics import YOLO
import cv2
import numpy as np

class PoseEstimator:
    def __init__(self, model_name='yolov8n-pose.pt'):
        import torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[INFO] PoseEstimator initialized on {self.device}")
        
        self.model = YOLO(model_name)
        self.model.to(self.device)
        
        # COCO Keypoint Index Mapping to nice names (consistent with Logic I wrote)
        self.keypoint_names = {
            0: 'NOSE',
            1: 'LEFT_EYE',
            2: 'RIGHT_EYE',
            3: 'LEFT_EAR',
            4: 'RIGHT_EAR',
            5: 'LEFT_SHOULDER',
            6: 'RIGHT_SHOULDER',
            7: 'LEFT_ELBOW',
            8: 'RIGHT_ELBOW',
            9: 'LEFT_WRIST',
            10: 'RIGHT_WRIST',
            11: 'LEFT_HIP',
            12: 'RIGHT_HIP',
            13: 'LEFT_KNEE',
            14: 'RIGHT_KNEE',
            15: 'LEFT_ANKLE',
            16: 'RIGHT_ANKLE'
        }

    def estimate(self, frame):
        """
        Returns:
        {
          "keypoints": {
            "joint_name": [x, y] # Pixel coordinates
          }
        }
        or None if no person/pose detected.
        """
        results = self.model(frame, verbose=False, device=self.device, imgsz=320)
        
        # We only care about the *primary* person (highest confidence or first)
        # YOLO pose results structure:
        # result.keypoints is a Keypoints object
        # result.keypoints.xy is Tensor [N, 17, 2]
        # result.keypoints.conf is Tensor [N, 17]
        
        if not results:
            print("[DEBUG] Pose: No results returned from model")
            return None
            
        result = results[0]
        # Check if boxes exist (meaning a person was detected)
        if result.boxes is None or len(result.boxes) == 0:
            # print("[DEBUG] Pose: No person detected by pose model") # specific debug to avoid spam if empty
            return None
            
        # Debug: Found a person
        # print(f"[DEBUG] Pose: Detected {len(result.boxes)} persons by pose model")

        if result.keypoints is None or result.keypoints.xy is None:
            print("[DEBUG] Pose: Keypoints attribute missing")
            return None
            
        # Get first person (usually most confident)
        # xy shape: (1, 17, 2)
        # Note: result.keypoints.xy is a Tensor. Verify shape.
        
        # If multiple detections, result.keypoints.xy has shape [N, 17, 2]
        # We take index 0.
        
        kpts = result.keypoints.xy[0].cpu().numpy() # [17, 2]
        confs = result.keypoints.conf[0].cpu().numpy() if result.keypoints.conf is not None else None
        
        keypoints_dict = {}
        
        valid_points = 0
        for idx, (x, y) in enumerate(kpts):
            # YOLO returns 0,0 for missing points sometimes, or check conf
            if confs is not None and confs[idx] < 0.3: # Was 0.5 - Lowered for stability
                continue
            if x == 0 and y == 0:
                continue
                
            name = self.keypoint_names.get(idx, f"KP_{idx}")
            keypoints_dict[name] = [float(x), float(y)]
            valid_points += 1
            
        if not keypoints_dict:
            print(f"[DEBUG] Pose: Person found but all keypoints filtered. Confs: {confs}")
            return None
            
        return {"keypoints": keypoints_dict}
