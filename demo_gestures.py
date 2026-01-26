"""
Gesture Recognition Demo
Test hand gesture detection with MediaPipe.
"""

import cv2
import sys
from pathlib import Path

try:
    from utils import get_logger, setup_logging
    from config import get_config
    from camera_input import CameraSource
    
    # Import gesture recognizer
    sys.path.insert(0, str(Path(__file__).parent))
    from perception.gesture_recognizer import GestureRecognizer, Gesture
    
except ImportError as e:
    print(f"Import error: {e}")
    print("\nMissing dependencies. Install with:")
    print("  pip install mediapipe opencv-python")
    sys.exit(1)

def main():
    print("\n" + "=" * 60)
    print("MEMO Gesture Recognition Demo")
    print("=" * 60 + "\n")
    
    # Setup logging
    setup_logging(level="INFO")
    logger = get_logger(__name__)
    
    logger.info("Initializing gesture recognition demo...")
    
    # Load config
    config = get_config("config.json")
    
    # Initialize camera
    try:
        camera = CameraSource(
            source=config.camera.source,
            width=config.camera.width,
            height=config.camera.height
        )
        logger.info("✓ Camera initialized")
    except Exception as e:
        logger.error(f"Camera failed: {e}")
        return
    
    # Initialize gesture recognizer
    try:
        gesture_recognizer = GestureRecognizer(
            max_num_hands=1,
            min_detection_confidence=0.5,
            stability_frames=3
        )
        logger.info("✓ Gesture recognizer ready")
    except Exception as e:
        logger.error(f"Gesture recognizer failed: {e}")
        print("\nIs MediaPipe installed?")
        print("  pip install mediapipe")
        return
    
    print("\nSupported Gestures:")
    print("  ✌️  Peace Sign   - Take Selfie 📸")
    print("  ✊ Fist         - Pause Voice/Speaking ⏸️")
    print("  ✋ Open Palm    - Play/Resume ▶️")
    print("  👍 Thumbs Up    - Confirm / Like")
    print("  👎 Thumbs Down  - Reject / Dislike")
    print("  👆 Point Up     - Volume Up")
    print("  👇 Point Down   - Volume Down")
    print("  👌 OK Sign      - Acknowledge")
    print("\nPress 'q' to quit\n")
    
    window_name = "MEMO Gesture Demo"
    cv2.namedWindow(window_name)
    
    last_gesture = None
    gesture_action_map = {
        Gesture.PEACE: "📸 Taking Selfie! Say cheese!",
        Gesture.FIST: "⏸️ Paused - Voice/Speaking stopped",
        Gesture.OPEN_PALM: "▶️ Playing - Resumed",
        Gesture.THUMBS_UP: "👍 Great!",
        Gesture.THUMBS_DOWN: "👎 Noted",
        Gesture.POINT_UP: "🔊 Volume Up",
        Gesture.POINT_DOWN: "🔉 Volume Down",
        Gesture.OK: "👌 Acknowledged",
    }
    
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue
            
            # Detect gesture
            result = gesture_recognizer.detect(frame)
            
            if result:
                # Visualize
                frame = gesture_recognizer.visualize(frame, result)
                
                # Log new gestures
                if result.gesture != last_gesture and result.gesture != Gesture.UNKNOWN:
                    logger.info(f"Gesture: {result.gesture.value} ({result.confidence:.0%})")
                    
                    # Trigger action
                    action = gesture_action_map.get(result.gesture)
                    if action:
                        print(f"\n{action}\n")
                    
                    last_gesture = result.gesture
            else:
                last_gesture = None
                # Show "No hand detected" message
                cv2.putText(
                    frame,
                    "Show your hand to camera",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 255, 255),
                    2
                )
            
            # Show frame
            cv2.imshow(window_name, frame)
            
            # Keyboard
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        logger.info("Shutting down...")
        gesture_recognizer.cleanup()
        camera.release()
        cv2.destroyAllWindows()
        logger.info("Demo complete")

if __name__ == "__main__":
    main()
