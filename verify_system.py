"""
MEMO - System Verification Script
==================================
Tests that all modules work together correctly.

Run this script to verify your MEMO installation is working.
"""

import os
import sys
import time

# Fix for OpenMP duplicate library issue (common with mixed Conda/pip installations)
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_status(module, status, message=""):
    icon = "✅" if status else "❌"
    print(f"  {icon} {module}: {message}")
    return status

def test_imports():
    """Test all module imports."""
    print_header("Testing Module Imports")
    all_pass = True
    
    # Core Python modules
    try:
        import cv2
        print_status("OpenCV", True, f"Version {cv2.__version__}")
    except ImportError as e:
        all_pass = False
        print_status("OpenCV", False, str(e))
    
    try:
        import numpy as np
        print_status("NumPy", True, f"Version {np.__version__}")
    except ImportError as e:
        all_pass = False
        print_status("NumPy", False, str(e))
    
    try:
        import torch
        cuda_status = "CUDA available" if torch.cuda.is_available() else "CPU only"
        print_status("PyTorch", True, f"Version {torch.__version__} ({cuda_status})")
    except ImportError as e:
        all_pass = False
        print_status("PyTorch", False, str(e))
    
    # MEMO modules
    try:
        from camera_input import CameraSource
        print_status("CameraSource", True, "Loaded")
    except ImportError as e:
        all_pass = False
        print_status("CameraSource", False, str(e))
    
    try:
        from perception import ObjectDetector
        print_status("ObjectDetector", True, "Loaded")
    except ImportError as e:
        all_pass = False
        print_status("ObjectDetector", False, str(e))
    
    try:
        from perception import PoseEstimator
        print_status("PoseEstimator", True, "Loaded")
    except ImportError as e:
        all_pass = False
        print_status("PoseEstimator", False, str(e))
    
    try:
        from perception import FaceRecognizer
        print_status("FaceRecognizer", True, "Loaded")
    except ImportError as e:
        all_pass = False
        print_status("FaceRecognizer", False, str(e))
    
    try:
        from perception import MotionDetector
        print_status("MotionDetector", True, "Loaded")
    except ImportError as e:
        all_pass = False
        print_status("MotionDetector", False, str(e))
    
    try:
        from state import SceneState
        print_status("SceneState", True, "Loaded")
    except ImportError as e:
        all_pass = False
        print_status("SceneState", False, str(e))
    
    try:
        from reasoning import RulesEngine
        print_status("RulesEngine", True, "Loaded")
    except ImportError as e:
        all_pass = False
        print_status("RulesEngine", False, str(e))
    
    try:
        from interface import QueryHandler
        print_status("QueryHandler", True, "Loaded")
    except ImportError as e:
        all_pass = False
        print_status("QueryHandler", False, str(e))
    
    return all_pass

def test_model_loading():
    """Test YOLO model loading."""
    print_header("Testing Model Loading")
    all_pass = True
    
    try:
        from perception import ObjectDetector
        print("  Loading YOLOv8n object detection model...")
        start = time.time()
        detector = ObjectDetector('yolov8n.pt')
        elapsed = time.time() - start
        print_status("ObjectDetector Model", True, f"Loaded in {elapsed:.2f}s")
    except Exception as e:
        all_pass = False
        print_status("ObjectDetector Model", False, str(e))
    
    try:
        from perception import PoseEstimator
        print("  Loading YOLOv8n-pose model...")
        start = time.time()
        pose = PoseEstimator('yolov8n-pose.pt')
        elapsed = time.time() - start
        print_status("PoseEstimator Model", True, f"Loaded in {elapsed:.2f}s")
    except Exception as e:
        all_pass = False
        print_status("PoseEstimator Model", False, str(e))
    
    try:
        from perception import FaceRecognizer
        print("  Loading FaceNet model...")
        start = time.time()
        face_rec = FaceRecognizer()
        elapsed = time.time() - start
        user_info = f"User: {face_rec.user_name}" if face_rec.known_embedding is not None else "No user registered"
        print_status("FaceRecognizer Model", True, f"Loaded in {elapsed:.2f}s ({user_info})")
    except Exception as e:
        all_pass = False
        print_status("FaceRecognizer Model", False, str(e))
    
    return all_pass

def test_camera():
    """Test camera functionality."""
    print_header("Testing Camera")
    
    try:
        from camera_input import CameraSource
        import cv2
        
        print("  Opening camera (index 0)...")
        camera = CameraSource(source=0, width=640, height=480)
        
        # Try to read a few frames
        success_count = 0
        for i in range(5):
            frame = camera.get_frame()
            if frame is not None:
                success_count += 1
            time.sleep(0.1)
        
        camera.release()
        
        if success_count >= 3:
            print_status("Camera", True, f"Read {success_count}/5 frames successfully")
            return True
        else:
            print_status("Camera", False, f"Only read {success_count}/5 frames")
            return False
            
    except Exception as e:
        print_status("Camera", False, str(e))
        return False

def test_detection_pipeline():
    """Test the full detection pipeline with a synthetic frame."""
    print_header("Testing Detection Pipeline")
    all_pass = True
    
    import numpy as np
    import cv2
    
    # Create a synthetic test frame (black with a white rectangle)
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(test_frame, (200, 100), (400, 350), (255, 255, 255), -1)  # White "person"
    
    try:
        from perception import ObjectDetector
        detector = ObjectDetector('yolov8n.pt')
        
        start = time.time()
        detections = detector.detect(test_frame)
        elapsed = time.time() - start
        
        print_status("ObjectDetector.detect()", True, f"Returned {len(detections)} detections in {elapsed*1000:.1f}ms")
    except Exception as e:
        all_pass = False
        print_status("ObjectDetector.detect()", False, str(e))
    
    try:
        from perception import PoseEstimator
        pose = PoseEstimator('yolov8n-pose.pt')
        
        start = time.time()
        pose_data = pose.estimate(test_frame)
        elapsed = time.time() - start
        
        keypoints = len(pose_data['keypoints']) if pose_data else 0
        print_status("PoseEstimator.estimate()", True, f"Returned {keypoints} keypoints in {elapsed*1000:.1f}ms")
    except Exception as e:
        all_pass = False
        print_status("PoseEstimator.estimate()", False, str(e))
    
    try:
        from perception import MotionDetector
        motion = MotionDetector()
        
        # Need two frames for motion detection
        motion.detect(test_frame)  # First frame (baseline)
        
        # Create slightly modified frame
        test_frame2 = test_frame.copy()
        cv2.rectangle(test_frame2, (210, 110), (410, 360), (200, 200, 200), -1)
        
        start = time.time()
        detected, score, regions = motion.detect(test_frame2)
        elapsed = time.time() - start
        
        print_status("MotionDetector.detect()", True, f"Score: {score:.4f}, Regions: {len(regions)} in {elapsed*1000:.1f}ms")
    except Exception as e:
        all_pass = False
        print_status("MotionDetector.detect()", False, str(e))
    
    return all_pass

def test_state_management():
    """Test state management."""
    print_header("Testing State Management")
    all_pass = True
    
    try:
        from state import SceneState
        scene = SceneState()
        
        # Test update with mock data
        mock_detections = [
            {"label": "person", "bbox": [100, 50, 200, 300], "confidence": 0.95},
            {"label": "laptop", "bbox": [300, 200, 150, 100], "confidence": 0.88}
        ]
        mock_pose = {
            "keypoints": {
                "NOSE": (320, 150),
                "LEFT_SHOULDER": (280, 200),
                "RIGHT_SHOULDER": (360, 200),
                "LEFT_HIP": (290, 350),
                "RIGHT_HIP": (350, 350),
                "LEFT_KNEE": (290, 450),
                "RIGHT_KNEE": (350, 450),
                "LEFT_ANKLE": (290, 550),
                "RIGHT_ANKLE": (350, 550)
            }
        }
        
        scene.update(mock_detections, mock_pose, time.time())
        
        objects_count = len(scene.objects)
        human_present = scene.human['present']
        pose_state = scene.human['pose_state']
        
        print_status("SceneState.update()", True, 
                    f"Objects: {objects_count}, Human: {human_present}, Pose: {pose_state}")
    except Exception as e:
        all_pass = False
        print_status("SceneState.update()", False, str(e))
    
    try:
        from reasoning import RulesEngine
        engine = RulesEngine()
        
        events = engine.check_rules(scene, time.time())
        print_status("RulesEngine.check_rules()", True, f"Generated {len(events)} events")
    except Exception as e:
        all_pass = False
        print_status("RulesEngine.check_rules()", False, str(e))
    
    return all_pass

def test_query_handler():
    """Test query handler."""
    print_header("Testing Query Handler")
    
    try:
        from interface import QueryHandler
        from state import SceneState
        
        handler = QueryHandler()
        scene = SceneState()
        
        # Add a test object
        scene.objects['bottle'] = {
            'last_seen': time.time(),
            'bbox': [100, 200, 50, 80],
            'position': 'left'
        }
        
        response = handler.handle_query("where is my bottle", scene)
        print_status("QueryHandler", True, f"Response: '{response[:50]}...'")
        return True
    except Exception as e:
        print_status("QueryHandler", False, str(e))
        return False

def test_full_integration():
    """Test full integration with camera (if available)."""
    print_header("Testing Full Integration (5 frames)")
    
    try:
        from camera_input import CameraSource
        from perception import ObjectDetector, PoseEstimator, MotionDetector
        from state import SceneState
        from reasoning import RulesEngine
        
        # Initialize components
        camera = CameraSource(source=0)
        detector = ObjectDetector('yolov8n.pt')
        pose_estimator = PoseEstimator('yolov8n-pose.pt')
        motion_detector = MotionDetector()
        scene_state = SceneState()
        rules_engine = RulesEngine()
        
        print("  Running integration test (5 frames)...")
        
        frame_times = []
        total_detections = 0
        
        for i in range(5):
            start = time.time()
            
            frame = camera.get_frame()
            if frame is None:
                print(f"    Frame {i+1}: Camera read failed")
                continue
            
            # Run detection
            detections = detector.detect(frame)
            pose_data = pose_estimator.estimate(frame)
            motion_detected, motion_score, _ = motion_detector.detect(frame)
            
            # Update state
            timestamp = time.time()
            scene_state.update(detections, pose_data, timestamp)
            
            # Check rules
            events = rules_engine.check_rules(scene_state, timestamp)
            
            elapsed = time.time() - start
            frame_times.append(elapsed)
            total_detections += len(detections)
            
            print(f"    Frame {i+1}: {len(detections)} objects, "
                  f"Motion: {motion_detected}, "
                  f"Time: {elapsed*1000:.0f}ms")
        
        camera.release()
        
        avg_time = sum(frame_times) / len(frame_times) if frame_times else 0
        avg_fps = 1.0 / avg_time if avg_time > 0 else 0
        
        print_status("Full Integration", True, 
                    f"Avg: {avg_time*1000:.0f}ms/frame ({avg_fps:.1f} FPS), "
                    f"Total detections: {total_detections}")
        return True
        
    except Exception as e:
        print_status("Full Integration", False, str(e))
        return False

def main():
    print("\n" + "🤖 " * 20)
    print("         MEMO SYSTEM VERIFICATION")
    print("🤖 " * 20)
    
    results = {}
    
    # Run tests
    results['imports'] = test_imports()
    results['models'] = test_model_loading()
    results['camera'] = test_camera()
    results['pipeline'] = test_detection_pipeline()
    results['state'] = test_state_management()
    results['query'] = test_query_handler()
    
    # Only run full integration if camera works
    if results['camera']:
        results['integration'] = test_full_integration()
    else:
        print_header("Skipping Full Integration (Camera not available)")
        results['integration'] = None
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            print(f"  ✅ {test_name}: PASSED")
        elif result is False:
            print(f"  ❌ {test_name}: FAILED")
        else:
            print(f"  ⏭️ {test_name}: SKIPPED")
    
    print()
    print(f"  Total: {passed} passed, {failed} failed, {skipped} skipped")
    print()
    
    if failed == 0:
        print("  🎉 ALL TESTS PASSED! MEMO is ready to use.")
        return 0
    else:
        print("  ⚠️ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
