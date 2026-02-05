
import sys
import os
import cv2
import numpy as np
import time

# Add current directory to path
sys.path.append(os.getcwd())

from core.engine import PerceptionPipeline, PerformanceMonitor

def test_inference_non_blocking():
    print("Initializing Pipeline...")
    pipeline = PerceptionPipeline()
    
    # Create dummy frame (640x480)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Warmup
    pipeline.warmup(frame)
    
    print("\nRunning Non-Blocking Check (10 frames)...")
    
    total_process_time = 0
    results_received = 0
    
    for i in range(10):
        start = time.time()
        # This call should be INSTANT now (just checks futures and submits)
        result = pipeline.process(frame, run_detection=True, run_pose=True, run_face=True)
        duration = time.time() - start
        
        total_process_time += duration
        
        det_count = len(result.get('detections', []))
        if det_count > 0:
            results_received += 1
            
        print(f"Frame {i+1}: Process Time={duration:.4f}s")
        time.sleep(0.05) # Simulate main loop frame pacing
    
    avg_time = total_process_time / 10
    print(f"\nAverage Process Time: {avg_time:.4f}s")
    
    if avg_time < 0.05:
        print("[SUCCESS] Pipeline is non-blocking!")
    else:
        print("[WARNING] Pipeline is still blocking significantly.")

if __name__ == "__main__":
    test_inference_non_blocking()
