"""
MEMO Lite Demo - No Heavy Dependencies
Showcases logging, configuration, motion detection, and context awareness.
Does NOT require YOLO/PyTorch - uses only lightweight features.
"""

import cv2
import time
import sys
from pathlib import Path

# Import new MEMO components (lightweight only)
try:
    from utils import get_logger, setup_logging
    from config import get_config
    from reasoning.context_manager import ContextManager
    from camera_input import CameraSource
    
    # Import motion detector separately (doesn't need torch)
    sys.path.insert(0, str(Path(__file__).parent))
    from perception.motion_detector import MotionDetector
    
except ImportError as e:
    print(f"Import error: {e}")
    print("\nMissing dependencies. Install with:")
    print("  pip install opencv-python colorlog pyyaml psutil")
    sys.exit(1)

def main():
    print("\n" + "=" * 60)
    print("MEMO LITE DEMO - Advanced Features (No PyTorch Required)")
    print("=" * 60 + "\n")
    
    # Setup logging
    try:
        setup_logging(level="INFO", log_to_file=True, log_to_console=True)
        logger = get_logger(__name__)
    except Exception as e:
        print(f"Logging setup failed: {e}")
        print("Continuing without logging...")
        logger = None
    
    def log(level, msg):
        """Fallback logging if logger fails."""
        if logger:
            getattr(logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")
    
    log('info', "=" * 60)
    log('info', "MEMO Lite Demo - No Heavy Dependencies")
    log('info', "=" * 60)
    
    # Load configuration
    try:
        config = get_config("config.json")
        log('info', f"✓ Loaded configuration from config.json")
        log('info', f"  Camera source: {config.camera.source}")
        log('info', f"  Logging level: {config.system.logging_level}")
        log('info', f"  Personality mode: {config.system.personality_mode}")
        
        # Validate configuration
        errors = config.validate()
        if errors:
            log('warning', f"Configuration validation found {len(errors)} issues:")
            for error in errors:
                log('warning', f"  - {error}")
        else:
            log('info', "✓ Configuration validated successfully")
    except Exception as e:
        log('error', f"Configuration error: {e}")
        log('info', "Using default settings...")
        # Create minimal config
        class MinConfig:
            class camera:
                source = 0
                width = 640
                height = 480
                rotation = 0
            class perception:
                enable_motion = True
            class system:
                logging_level = "INFO"
                personality_mode = "helpful"
        config = MinConfig()
    
    # Initialize camera
    try:
        log('info', "Initializing camera...")
        camera = CameraSource(
            source=config.camera.source,
            width=config.camera.width,
            height=config.camera.height,
            rotation=config.camera.rotation
        )
        log('info', "✓ Camera initialized successfully")
    except Exception as e:
        log('error', f"Failed to initialize camera: {e}")
        print("\nTroubleshooting:")
        print("  1. Check camera is connected")
        print("  2. Try different source (0, 1, 2) in config.json")
        print("  3. Close other apps using camera")
        return
    
    # Initialize motion detector
    try:
        log('info', "Initializing motion detector...")
        motion_detector = MotionDetector(
            threshold=25,
            min_area=500,
            use_mog2=False  # False for speed
        )
        log('info', "✓ Motion detector ready")
    except Exception as e:
        log('error', f"Motion detector failed: {e}")
        motion_detector = None
    
    # Initialize context manager
    try:
        context_manager = ContextManager()
        log('info', "✓ Context manager initialized")
        
        # Get initial greeting
        greeting = context_manager.get_greeting("Jayadeep")
        if greeting:
            log('info', f"🗣️  Greeting: {greeting}")
            print(f"\n✨ {greeting}\n")
    except Exception as e:
        log('error', f"Context manager failed: {e}")
        context_manager = None
    
    # Main loop
    log('info', "Starting demo loop...")
    print("\nKeyboard Controls:")
    print("  q - Quit")
    print("  m - Toggle motion detection")
    print("  r - Reset motion detector")
    print("  g - Force greeting")
    print("  c - Show context")
    print("  h - Show help\n")
    
    frame_count = 0
    last_motion_log = 0
    user_present = False
    motion_enabled = True
    
    window_name = "MEMO Lite Demo (No PyTorch)"
    cv2.namedWindow(window_name)
    
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            frame_count += 1
            timestamp = time.time()
            
            # Motion detection
            if motion_detector and motion_enabled:
                try:
                    motion_detected, motion_score, motion_regions = motion_detector.detect(frame)
                    
                    # Log significant motion
                    if motion_detected and (timestamp - last_motion_log) > 5.0:
                        log('info', f"Motion! Score: {motion_score:.3f}, Regions: {len(motion_regions)}")
                        last_motion_log = timestamp
                        
                        # Check if this could be user arriving
                        if not user_present and motion_score > 0.05:
                            user_present = True
                            if context_manager:
                                context_manager.update_presence(True)
                                greeting = context_manager.get_greeting("Jayadeep")
                                if greeting:
                                    log('info', f"🗣️  {greeting}")
                                    print(f"\n✨ {greeting}\n")
                    
                    # Visualize motion
                    if motion_regions:
                        frame = motion_detector.visualize(frame, motion_regions)
                except Exception as e:
                    log('error', f"Motion detection error: {e}")
            
            # Update context
            if context_manager:
                try:
                    context_manager.update_presence(user_present)
                    context_summary = context_manager.get_context_summary()
                except Exception as e:
                    log('error', f"Context update error: {e}")
                    context_summary = {}
            else:
                context_summary = {}
            
            # Display info overlay
            h, w = frame.shape[:2]
            
            # Background for text
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (450, 180), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
            
            # Info text
            info_y = 30
            line_height = 25
            
            # Header
            cv2.putText(frame, "MEMO LITE - No PyTorch Required", 
                       (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            info_y += line_height
            
            # Context info
            if context_summary:
                cv2.putText(frame, f"Time: {context_summary.get('time_of_day', 'N/A')}", 
                           (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                info_y += line_height
                
                cv2.putText(frame, f"User: {context_summary.get('user_state', 'N/A')}", 
                           (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                info_y += line_height
                
                cv2.putText(frame, f"Session: {context_summary.get('session_duration', 'N/A')}", 
                           (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                info_y += line_height
            
            # Motion info
            if motion_detector:
                motion_color = (0, 255, 0) if (motion_enabled and 'motion_detected' in locals() and motion_detected) else (100, 100, 100)
                motion_text = f"Motion: {'ON' if motion_enabled else 'OFF'}"
                if motion_enabled and 'motion_score' in locals():
                    motion_text += f" ({motion_score:.2%})"
                cv2.putText(frame, motion_text, (20, info_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, motion_color, 1)
                info_y += line_height
            
            # Frame counter
            cv2.putText(frame, f"Frames: {frame_count}", 
                       (20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Status bar (bottom)
            cv2.putText(frame, "Press 'h' for help | 'q' to quit", 
                       (20, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            
            # Show frame
            cv2.imshow(window_name, frame)
            
            # Keyboard controls
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                log('info', "User requested quit")
                break
            elif key == ord('m'):
                motion_enabled = not motion_enabled
                log('info', f"Motion detection: {'ON' if motion_enabled else 'OFF'}")
            elif key == ord('r') and motion_detector:
                motion_detector.reset()
                log('info', "Motion detector reset")
            elif key == ord('g') and context_manager:
                greeting = context_manager.get_greeting("Jayadeep")
                if greeting:
                    log('info', f"🗣️  {greeting}")
                    print(f"\n✨ {greeting}\n")
            elif key == ord('c') and context_summary:
                print("\n" + "=" * 40)
                print("Context Summary:")
                for key, value in context_summary.items():
                    print(f"  {key}: {value}")
                print("=" * 40 + "\n")
            elif key == ord('h'):
                print("\n" + "=" * 60)
                print("Keyboard Controls:")
                print("  q - Quit")
                print("  m - Toggle motion detection")
                print("  r - Reset motion detector")
                print("  g - Force greeting")
                print("  c - Show context summary")
                print("  h - Show this help")
                print("=" * 60 + "\n")
            
            # Log every 100 frames
            if frame_count % 100 == 0 and logger:
                logger.debug(f"Processed {frame_count} frames")
    
    except KeyboardInterrupt:
        log('info', "Interrupted by user")
    except Exception as e:
        log('error', f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        log('info', "Shutting down...")
        camera.release()
        cv2.destroyAllWindows()
        
        # Save configuration if available
        try:
            if hasattr(config, 'save'):
                config.save("config.json")
                log('info', "Configuration saved")
        except:
            pass
        
        log('info', "MEMO Lite Demo completed")
        log('info', f"Total frames: {frame_count}")
        if context_summary:
            log('info', f"Session: {context_summary.get('session_duration', 'N/A')}")
        
        # Show log location
        log_dir = Path("logs")
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            if log_files:
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                print(f"\n📄 Logs saved to: {latest_log}\n")

if __name__ == "__main__":
    main()
