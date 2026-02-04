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
        # Using imgsz=256 for speedup on Pi
        results = self.model(frame, verbose=False, device=self.device, imgsz=256, augment=False)
        
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
            # print("[DEBUG] Pose: Keypoints attribute missing")
            return []
            
        # Handle multiple people
        # xy shape: (N, 17, 2)
        kpts_batch = result.keypoints.xy.cpu().numpy()
        confs_batch = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None
        
        persons = []
        
        for i, kpts in enumerate(kpts_batch):
            confs = confs_batch[i] if confs_batch is not None else None
            
            keypoints_dict = {}
            valid_points = 0
            
            for idx, (x, y) in enumerate(kpts):
                if confs is not None and confs[idx] < 0.3:
                    continue
                if x == 0 and y == 0:
                    continue
                    
                name = self.keypoint_names.get(idx, f"KP_{idx}")
                keypoints_dict[name] = [float(x), float(y)]
                valid_points += 1
            
            if valid_points > 5: # Minimum valid points
                # Calculate simple bbox area as a proxy for 'size' to help sorting
                try:
                    xs = [p[0] for p in keypoints_dict.values()]
                    ys = [p[1] for p in keypoints_dict.values()]
                    w = max(xs) - min(xs)
                    h = max(ys) - min(ys)
                    area = w * h
                except:
                    area = 0
                    
                persons.append({
                    "keypoints": keypoints_dict,
                    "area": area
                })
            
        # Return list of persons (sorted by area usually good for default, but we return all)
        return persons # consumers must handle list
