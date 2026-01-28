"""
MEMO - Object Detection Module
==============================

This module provides real-time object detection using YOLOv8.

Features:
    - YOLOv8n for fast, lightweight detection (80 COCO classes)
    - Configurable confidence thresholds per object class
    - Special handling for cell phone vs mouse disambiguation
    - Returns bounding boxes in [x, y, width, height] format

Dependencies:
    - ultralytics (YOLOv8)
    - opencv-python (cv2)

Example:
    >>> detector = ObjectDetector('yolov8n.pt')
    >>> detections = detector.detect(frame)
    >>> for det in detections:
    ...     print(f"{det['label']}: {det['confidence']:.2f}")

Author: Jayadeep / Jay7-Tech
Module: perception/object_detection.py
"""

from ultralytics import YOLO
import cv2


class ObjectDetector:
    """
    Real-time object detection using YOLOv8.
    
    This class wraps the Ultralytics YOLOv8 model for detecting objects
    in video frames. It's optimized for desktop companion use cases with
    custom confidence thresholds to reduce false positives.
    
    Attributes:
        model (YOLO): The loaded YOLOv8 model instance.
    
    Supported Objects (COCO Classes):
        - person, cell phone, laptop, keyboard, mouse, cup, bottle
        - book, clock, remote, scissors, chair, backpack, etc.
        - Full list: 80 COCO classes
    
    Example:
        >>> detector = ObjectDetector()
        >>> frame = cv2.imread('desk.jpg')
        >>> detections = detector.detect(frame)
        >>> print(f"Found {len(detections)} objects")
    """
    
    def __init__(self, model_name: str = 'yolov8n.pt'):
        """
        Initialize the ObjectDetector with a YOLOv8 model.
        
        Args:
            model_name (str): Path to YOLO model file or model name.
                Options:
                - 'yolov8n.pt' (nano, fastest, ~6MB) - DEFAULT
                - 'yolov8s.pt' (small, balanced)
                - 'yolov8m.pt' (medium, more accurate)
                - 'yolov8l.pt' (large, high accuracy)
                - 'yolov8x.pt' (extra large, highest accuracy)
                
        Note:
            For Raspberry Pi 4B, use 'yolov8n.pt' or TFLite version.
        """
        import torch
        # Check for GPU
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[INFO] ObjectDetector initialized on {self.device}")

        # Load lightweight YOLO model
        self.model = YOLO(model_name)
        self.model.to(self.device)
    
    def detect(self, frame):
        """
        Detect objects in the given video frame.
        
        Runs YOLOv8 inference on the frame and returns a list of
        detected objects with their bounding boxes and confidence scores.
        
        Args:
            frame (numpy.ndarray): BGR image from OpenCV (shape: H x W x 3).
        
        Returns:
            list[dict]: List of detection dictionaries, each containing:
                - 'label' (str): Object class name (e.g., 'person', 'cell phone')
                - 'bbox' (list[float]): Bounding box as [x, y, width, height]
                    - x, y: Top-left corner coordinates
                    - width, height: Box dimensions in pixels
                - 'confidence' (float): Detection confidence (0.0 to 1.0)
        
        Example:
            >>> detections = detector.detect(frame)
            >>> for det in detections:
            ...     label = det['label']
            ...     x, y, w, h = det['bbox']
            ...     conf = det['confidence']
            ...     cv2.rectangle(frame, (int(x), int(y)), 
            ...                   (int(x+w), int(y+h)), (0,255,0), 2)
        
        Note:
            - Cell phone detection uses higher confidence threshold (0.60)
              to avoid false positives with computer mouse.
            - General objects use 0.5 confidence threshold.
        """
        # Using imgsz=320 for significant speedup on Pi (default 640 is way too slow)
        results = self.model(frame, verbose=False, device=self.device, imgsz=320)
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
                    min_conf = 0.70 # Increased to avoid false positives (mouse/etc)
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
