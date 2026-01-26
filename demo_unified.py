"""
MEMO Unified Perception Demo
Combines Motion Detection + Gesture Recognition + Emotion Detection
"""

import cv2
import time
import sys
from pathlib import Path

try:
    from utils import get_logger, setup_logging
    from config import get_config
    from camera_input import CameraSource
    
    sys.path.insert(0, str(Path(__file__).parent))
    from perception.motion_detector import MotionDetector
    from perception.gesture_recognizer import GestureRecognizer, Gesture
    from perception.emotion_detector import EmotionDetector, Emotion
    from reasoning.context_manager import ContextManager
    
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def main():
    print("\n" + "=" * 70)
    print("   MEMO UNIFIED PERCEPTION DEMO")
    print("   Motion + Gestures + Emotions + Context Awareness")
    print("=" * 70 + "\n")
    
    setup_logging(level="INFO")
    logger = get_logger(__name__)
    
    logger.info("Initializing MEMO unified perception...")
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
    
    # Initialize perception modules
    motion_detector = MotionDetector(threshold=25, min_area=500)
    logger.info("✓ Motion detector ready")
    
    gesture_recognizer = GestureRecognizer(stability_frames=3)
    logger.info("✓ Gesture recognizer ready")
    
    emotion_detector = EmotionDetector(stability_frames=5)
    logger.info("✓ Emotion detector ready")
    
    context_manager = ContextManager()
    greeting = context_manager.get_greeting("Jayadeep")
    if greeting:
        print(f"\n✨ {greeting}\n")
    logger.info("✓ Context manager ready")
    
    print("\nPerception Features Active:")
    print("  🔄 Motion Detection  - Wake/Security alerts")
    print("  🖐️ Gesture Control   - Peace/Fist/Palm commands")
    print("  😊 Emotion Detection - Facial expression analysis")
    print("  🕐 Context Awareness - Time-based interactions")
    print("\nPress 'q' to quit, 'h' for help\n")
    
    window_name = "MEMO Unified Perception"
    cv2.namedWindow(window_name)
    
    # State tracking
    frame_count = 0
    last_motion_time = 0
    last_gesture = None
    last_emotion = None
    is_paused = False
    
    # Gesture actions
    gesture_actions = {
        Gesture.PEACE: ("📸 Selfie!", "peace"),
        Gesture.FIST: ("⏸️ Paused", "pause"),
        Gesture.OPEN_PALM: ("▶️ Playing", "play"),
        Gesture.THUMBS_UP: ("👍 Great!", "like"),
        Gesture.THUMBS_DOWN: ("👎 Noted", "dislike"),
    }
    
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue
            
            frame_count += 1
            current_time = time.time()
            h, w = frame.shape[:2]
            
            # 1. MOTION DETECTION
            motion_detected, motion_score, motion_regions = motion_detector.detect(frame)
            
            if motion_detected and (current_time - last_motion_time) > 5.0:
                logger.info(f"Motion detected! Score: {motion_score:.2%}")
                last_motion_time = current_time
                context_manager.update_presence(True)
            
            # Draw motion regions
            for region in motion_regions[:3]:  # Max 3 regions
                cv2.rectangle(frame, (region.x, region.y),
                             (region.x + region.width, region.y + region.height),
                             (0, 0, 255), 1)
            
            # 2. GESTURE RECOGNITION (every 2nd frame for performance)
            gesture_result = None
            if frame_count % 2 == 0:
                gesture_result = gesture_recognizer.detect(frame)
                
                if gesture_result and gesture_result.gesture != last_gesture:
                    if gesture_result.gesture in gesture_actions:
                        action_text, action_type = gesture_actions[gesture_result.gesture]
                        logger.info(f"Gesture: {gesture_result.gesture.value} -> {action_text}")
                        print(f"\n{action_text}\n")
                        
                        # Handle pause/play
                        if action_type == "pause":
                            is_paused = True
                        elif action_type == "play":
                            is_paused = False
                    
                    last_gesture = gesture_result.gesture
                
                if gesture_result:
                    frame = gesture_recognizer.visualize(frame, gesture_result)
            
            # 3. EMOTION DETECTION (every 3rd frame for performance)
            emotion_result = None
            if frame_count % 3 == 0:
                emotion_result = emotion_detector.detect(frame)
                
                if emotion_result and emotion_result.emotion != last_emotion:
                    if emotion_result.emotion != Emotion.UNKNOWN:
                        emoji = emotion_detector.get_emoji(emotion_result.emotion)
                        logger.info(f"Emotion: {emotion_result.emotion.value} {emoji}")
                    last_emotion = emotion_result.emotion
                
                if emotion_result:
                    frame = emotion_detector.visualize(frame, emotion_result)
            
            # 4. STATUS PANEL (top-left)
            panel_h = 150
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (280, panel_h), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
            
            y = 30
            line_h = 22
            
            # Title
            cv2.putText(frame, "MEMO Perception", (20, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            y += line_h + 5
            
            # Motion
            motion_color = (0, 255, 0) if motion_detected else (100, 100, 100)
            cv2.putText(frame, f"Motion: {'YES' if motion_detected else 'NO'} ({motion_score:.1%})",
                       (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, motion_color, 1)
            y += line_h
            
            # Gesture
            if gesture_result:
                gesture_text = gesture_result.gesture.value.replace('_', ' ').title()
            else:
                gesture_text = "None"
            cv2.putText(frame, f"Gesture: {gesture_text}", (20, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y += line_h
            
            # Emotion
            if emotion_result:
                emoji = emotion_detector.get_emoji(emotion_result.emotion)
                emotion_text = f"{emotion_result.emotion.value.title()} {emoji}"
            else:
                emotion_text = "No face"
            cv2.putText(frame, f"Emotion: {emotion_text}", (20, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y += line_h
            
            # State
            state_text = "PAUSED" if is_paused else "ACTIVE"
            state_color = (0, 0, 255) if is_paused else (0, 255, 0)
            cv2.putText(frame, f"State: {state_text}", (20, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, state_color, 1)
            
            # Context (bottom-left)
            context = context_manager.get_context_summary()
            cv2.putText(frame, f"Time: {context['time_of_day']} | Session: {context['session_duration']}",
                       (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            
            # Frame counter (bottom-right)
            cv2.putText(frame, f"Frame: {frame_count}", (w - 120, h - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('h'):
                print("\n" + "=" * 50)
                print("Controls:")
                print("  q - Quit")
                print("  h - Show this help")
                print("\nGestures:")
                print("  ✌️ Peace  -> Take Selfie")
                print("  ✊ Fist   -> Pause")
                print("  ✋ Palm   -> Play/Resume")
                print("  👍 Thumbs -> Like")
                print("=" * 50 + "\n")
    
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        logger.info("Shutting down...")
        gesture_recognizer.cleanup()
        camera.release()
        cv2.destroyAllWindows()
        logger.info(f"Demo complete. Processed {frame_count} frames.")

if __name__ == "__main__":
    main()
