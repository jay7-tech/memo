"""
Emotion Detection Demo
Test facial emotion detection.
"""

import cv2
import sys
from pathlib import Path

try:
    from utils import get_logger, setup_logging
    from config import get_config
    from camera_input import CameraSource
    
    sys.path.insert(0, str(Path(__file__).parent))
    from perception.emotion_detector import EmotionDetector, Emotion
    
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def main():
    print("\n" + "=" * 60)
    print("MEMO Emotion Detection Demo")
    print("=" * 60 + "\n")
    
    setup_logging(level="INFO")
    logger = get_logger(__name__)
    
    logger.info("Initializing emotion detection demo...")
    
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
    
    # Initialize emotion detector
    try:
        emotion_detector = EmotionDetector(
            min_face_size=80,
            stability_frames=5
        )
        logger.info("✓ Emotion detector ready")
    except Exception as e:
        logger.error(f"Emotion detector failed: {e}")
        return
    
    print("\nDetectable Emotions:")
    print("  😊 Happy    😢 Sad      😠 Angry")
    print("  😲 Surprised 😐 Neutral  😨 Fear")
    print("\nPress 'q' to quit\n")
    
    window_name = "MEMO Emotion Demo"
    cv2.namedWindow(window_name)
    
    last_emotion = None
    emotion_responses = {
        Emotion.HAPPY: "You look happy! 😊 That's great!",
        Emotion.SAD: "You seem sad 😢 Is everything okay?",
        Emotion.ANGRY: "You look upset 😠 Take a deep breath...",
        Emotion.SURPRISED: "Oh! Something surprised you? 😲",
        Emotion.NEUTRAL: "Looking focused 😐",
        Emotion.FEAR: "Don't worry, I'm here 😨",
        Emotion.DISGUST: "Something unpleasant? 🤢",
    }
    
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue
            
            # Detect emotion
            result = emotion_detector.detect(frame)
            
            if result:
                # Visualize
                frame = emotion_detector.visualize(frame, result)
                
                # Log emotion changes
                if result.emotion != last_emotion and result.emotion != Emotion.UNKNOWN:
                    emoji = emotion_detector.get_emoji(result.emotion)
                    logger.info(f"Emotion: {result.emotion.value} {emoji} ({result.confidence:.0%})")
                    
                    response = emotion_responses.get(result.emotion)
                    if response:
                        print(f"\n{response}\n")
                    
                    last_emotion = result.emotion
                
                # Show emotion bar
                if result.all_emotions:
                    h = frame.shape[0]
                    bar_y = h - 120
                    
                    # Background
                    cv2.rectangle(frame, (10, bar_y - 10), (200, h - 10), (0, 0, 0), -1)
                    
                    # Emotion bars
                    bar_height = 12
                    for i, (emotion_name, score) in enumerate(result.all_emotions.items()):
                        y = bar_y + i * (bar_height + 3)
                        bar_width = int(score * 150)
                        
                        cv2.putText(frame, emotion_name[:3], (15, y + 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                        cv2.rectangle(frame, (50, y), (50 + bar_width, y + bar_height),
                                     (0, 200, 200), -1)
            else:
                # No face detected
                cv2.putText(
                    frame, "No face detected - look at camera",
                    (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2
                )
            
            cv2.imshow(window_name, frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        logger.info("Shutting down...")
        camera.release()
        cv2.destroyAllWindows()
        logger.info("Demo complete")

if __name__ == "__main__":
    main()
