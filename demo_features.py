"""
MEMO Demo - Showcase New Features
Demonstrates logging, configuration, motion detection, and context awareness.
"""

import cv2
import time
from pathlib import Path

# Import new MEMO components
from utils import get_logger, setup_logging
from config import get_config
from perception.motion_detector import MotionDetector
from reasoning.context_manager import ContextManager
from camera_input import CameraSource

def main():
    # Setup logging
    setup_logging(level="INFO", log_to_file=True, log_to_console=True)
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("MEMO Advanced Features Demo")
    logger.info("=" * 60)
    
    # Load configuration
    config = get_config("config.json")
    logger.info(f"Loaded configuration from config.json")
    logger.info(f"Camera source: {config.camera.source}")
    logger.info(f"Logging level: {config.system.logging_level}")
    logger.info(f"Personality mode: {config.system.personality_mode}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.warning(f"Configuration validation found {len(errors)} issues:")
        for error in errors:
            logger.warning(f"  - {error}")
    else:
        logger.info("Configuration validated successfully")
    
    # Initialize components
    try:
        logger.info("Initializing camera...")
        camera = CameraSource(
            source=config.camera.source,
            width=config.camera.width,
            height=config.camera.height,
            rotation=config.camera.rotation
        )
        logger.info("Camera initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return
    
    # Initialize motion detector
    logger.info("Initializing motion detector...")
    motion_detector = MotionDetector(
        threshold=25,
        min_area=500,
        use_mog2=False  # False for speed
    )
    logger.info("Motion detector ready")
    
    # Initialize context manager
    context_manager = ContextManager()
    logger.info("Context manager initialized")
    
    # Get initial greeting
    greeting = context_manager.get_greeting("Jayadeep")
    if greeting:
        logger.info(f"🗣️  Greeting: {greeting}")
        print(f"\n{greeting}\n")
    
    # Main loop
    logger.info("Starting main demo loop (Press 'q' to quit)")
    frame_count = 0
    last_motion_log = 0
    user_present = False
    
    window_name = "MEMO Feature Demo"
    cv2.namedWindow(window_name)
    
    while True:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        
        frame_count += 1
        timestamp = time.time()
        
        # Motion detection (every frame for demo)
        if config.perception.enable_motion:
            motion_detected, motion_score, motion_regions = motion_detector.detect(frame)
            
            # Log significant motion
            if motion_detected and (timestamp - last_motion_log) > 5.0:
                logger.info(f"Motion detected! Score: {motion_score:.3f}, Regions: {len(motion_regions)}")
                last_motion_log = timestamp
                
                # Check if this could be user arriving
                if not user_present and motion_score > 0.05:
                    user_present = True
                    context_manager.update_presence(True)
                    greeting = context_manager.get_greeting("Jayadeep")
                    if greeting:
                        logger.info(f"🗣️  {greeting}")
                        print(f"\n{greeting}\n")
            
            # Visualize motion
            if motion_regions:
                frame = motion_detector.visualize(frame, motion_regions)
        
        # Update context
        context_manager.update_presence(user_present)
        
        # Display info overlay
        h, w = frame.shape[:2]
        
        # Background for text
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (450, 180), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        
        # Info text
        info_y = 30
        line_height = 25
        
        # Context info
        context_summary = context_manager.get_context_summary()
        cv2.putText(frame, f"Time of Day: {context_summary['time_of_day']}", 
                   (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        info_y += line_height
        
        cv2.putText(frame, f"User State: {context_summary['user_state']}", 
                   (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        info_y += line_height
        
        cv2.putText(frame, f"Session: {context_summary['session_duration']}", 
                   (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        info_y += line_height
        
        # Motion info
        if config.perception.enable_motion:
            motion_color = (0, 255, 0) if motion_detected else (100, 100, 100)
            motion_text = f"Motion: {'YES' if motion_detected else 'NO'}"
            if motion_detected:
                motion_text += f" ({motion_score:.2%})"
            cv2.putText(frame, motion_text, (20, info_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, motion_color, 2)
            info_y += line_height
        
        # Frame counter
        cv2.putText(frame, f"Frame: {frame_count}", 
                   (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        # Config info (bottom)
        cv2.putText(frame, f"Personality: {config.system.personality_mode}", 
                   (20, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"Logging: {config.system.logging_level}", 
                   (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Show frame
        cv2.imshow(window_name, frame)
        
        # Keyboard controls
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            logger.info("User requested quit")
            break
        elif key == ord('m'):
            # Toggle motion detection
            config.perception.enable_motion = not config.perception.enable_motion
            logger.info(f"Motion detection: {'ON' if config.perception.enable_motion else 'OFF'}")
        elif key == ord('r'):
            # Reset motion detector
            motion_detector.reset()
            logger.info("Motion detector reset")
        elif key == ord('g'):
            # Force greeting
            greeting = context_manager.get_greeting("Jayadeep")
            if greeting:
                logger.info(f"🗣️  {greeting}")
                print(f"\n{greeting}\n")
        elif key == ord('c'):
            # Show context summary
            logger.info("=" * 40)
            logger.info("Context Summary:")
            for key, value in context_summary.items():
                logger.info(f"  {key}: {value}")
            logger.info("=" * 40)
        elif key == ord('h'):
            # Show help
            print("\n" + "=" * 60)
            print("Keyboard Controls:")
            print("  q - Quit")
            print("  m - Toggle motion detection")
            print("  r - Reset motion detector")
            print("  g - Force greeting")
            print("  c - Show context summary in log")
            print("  h - Show this help")
            print("=" * 60 + "\n")
        
        # Log every 100 frames
        if frame_count % 100 == 0:
            logger.debug(f"Processed {frame_count} frames")
    
    # Cleanup
    logger.info("Shutting down...")
    camera.release()
    cv2.destroyAllWindows()
    
    # Save configuration if modified
    config.save("config.json")
    logger.info("Configuration saved")
    
    logger.info("MEMO Demo completed successfully")
    logger.info(f"Total frames processed: {frame_count}")
    logger.info(f"Session duration: {context_summary['session_duration']}")
    
    # Show log location
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Logs saved to: {latest_log}")

if __name__ == "__main__":
    main()
