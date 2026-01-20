from ultralytics import YOLO
import cv2

class ObjectDetector:
    def __init__(self, model_name='yolov8n.pt'):
        # Load lightweight YOLO model
        self.model = YOLO(model_name)
    
    def detect(self, frame):
        """
        Detects objects in the frame.
        Returns a list of dicts:
        {
          "label": str,
          "bbox": [x, y, w, h],
          "confidence": float
        }
        """
        results = self.model(frame, verbose=False)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = self.model.names[cls]
                
                # Custom thresholds to reduce false positives
                min_conf = 0.5 # General threshold
                
                # Filter out mouse if it confuses logic? 
                # YOLO often confuses mouse with cell phone. 
                # Since we want to detect cell phone distraction, 
                # we must be VERY sure.
                if label == 'cell phone':
                    min_conf = 0.75 # Very strict
                elif label == 'mouse':
                    # User said mouse is detected as phone.
                    # If YOLO says "mouse", let it pass as mouse.
                    # If YOLO says "cell phone" but it's actually mouse...
                    # We can't know without retraining or size heuristic.
                    # A mouse is usually smaller/flatter than a phone held up?
                    pass 
                
                if conf < min_conf:
                    continue
                
                # Convert to xywh as strictly requested? 
                # User asked for [x, y, w, h]. assuming x,y is top-left.
                x = x1
                y = y1
                w = x2 - x1
                h = y2 - y1
                
                detections.append({
                    "label": label,
                    "bbox": [x, y, w, h],
                    "confidence": conf
                })
        
        return detections
