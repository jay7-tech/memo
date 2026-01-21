import cv2
import threading
import time
import sys
import winsound

from camera_input import CameraSource
from perception import ObjectDetector, PoseEstimator
from state import SceneState
from reasoning import RulesEngine
from interface import QueryHandler

import queue
import subprocess

# Shared state
scene_state = SceneState()
query_handler = QueryHandler()
running = True
engine = None
voice_input = None
tts_queue = queue.Queue()

def tts_worker():
    """
    Worker to handle TTS using PowerShell.
    This avoids Python threading/COM issues with pyttsx3.
    """
    while True:
        text = tts_queue.get()
        if text is None:
            break
            
        try:
            # Escape single quotes for PowerShell
            safe_text = text.replace("'", "''")
            cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}');"
            
            # Run without opening a window, wait for completion to pace speech
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=False)
            
        except Exception as e:
            print(f"TTS Error: {e}")
        
        tts_queue.task_done()

def init_tts():
    # Start the worker thread
    t = threading.Thread(target=tts_worker, daemon=True)
    t.start()

def speak(text):
    # Debug print to confirm logic is triggering
    # print(f"[DEBUG] Queuing speech: {text}")
    tts_queue.put(text)

def input_loop():
    global running, voice_input
    print("System Ready. Commands: 'focus on', 'focus off', 'where is X', 'quit'.")
    while running:
        try:
            user_input = input() 
            clean_input = user_input.strip().lower()
            
            if clean_input in ['quit', 'exit']:
                running = False
                break
            elif clean_input == 'focus on':
                scene_state.focus_mode = True
                print(">> SYSTEM: Focus Mode ENABLED.")
                speak("Focus mode enabled. I will watch for distractions.")
            elif clean_input == 'focus off':
                scene_state.focus_mode = False
                print(">> SYSTEM: Focus Mode DISABLED.")
                speak("Focus mode disabled.")
            elif clean_input == 'register me':
                 print(">> SYSTEM: What should I call you? (Type name):")
                 name = input().strip()
                 if not name: name = "User"
                 print(f">> SYSTEM: Look at the camera... registering for {name}")
                 speak(f"Please look at the camera, {name}.")
                 scene_state.register_name = name
                 scene_state.register_trigger = True
                 
            elif clean_input.startswith('register '):
                 # Handle "register Jayadeep" directly
                 name = clean_input.replace('register ', '').strip()
                 if name:
                     print(f">> SYSTEM: Look at the camera... registering for {name}")
                     speak(f"Please look at the camera, {name}.")
                     scene_state.register_name = name
                     scene_state.register_name = name
                     scene_state.register_trigger = True
            elif clean_input == 'voice on':
                if voice_input:
                    voice_input.set_active(True)
                    speak("I am listening.")
                else:
                    print("Voice module not initialized.")
            elif clean_input == 'voice off':
                if voice_input:
                    voice_input.set_active(False)
                    speak("Voice input stopped.")
            else:
                response = query_handler.handle_query(user_input, scene_state)
                if response:
                    print(f"\n>> SYSTEM: {response}\n")
                    speak(response)
                
        except EOFError:
            running = False
            break
        except Exception as e:
            print(f"Input error: {e}")

def main():
    global running, voice_input
    
    # Init Audio
    init_tts()
    
    # Parse source from args
    # Usage: python main.py [source] [rotation]
    source = 0
    rotation = 0
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.isdigit():
            source = int(arg)
        else:
            source = arg
            print(f"Attempting to connect to IP Camera: {source}")
            
    if len(sys.argv) > 2:
        try:
            rotation = int(sys.argv[2])
            print(f"Rotation set to: {rotation} degrees")
        except ValueError:
            print("Invalid rotation argument. Use 0, 90, 180, or 270.")
    
    # Initialize components
    try:
        cam = CameraSource(source=source, rotation=rotation)
    except Exception as e:
        print(f"Error opening camera source '{source}': {e}")
        return

    detector = ObjectDetector(model_name='yolov8n.pt') 
    pose_estimator = PoseEstimator()
    rules_engine = RulesEngine()
    
    # Init Face Rec (Might be slow on first load)
    from perception.face_rec import FaceRecognizer
    face_rec = FaceRecognizer()
    
    # Init Voice Listener
    # We define a callback to handle voice commands
    def on_voice_command(text):
        # Inject into the text processing logic
        # Clean text
        text = text.replace("hello pc", "").strip()
        
        # Check standard commands
        # Relaxed matching: verify 'focus' and 'on'/'off' exist in the phrase
        if "focus" in text and ("on" in text or "start" in text or "enable" in text):
            scene_state.focus_mode = True
            print(">> SYSTEM: Focus Mode ENABLED (Voice)")
            speak("Focus mode enabled.")
        elif "focus" in text and ("off" in text or "stop" in text or "disable" in text):
            scene_state.focus_mode = False
            print(">> SYSTEM: Focus Mode DISABLED (Voice)")
            speak("Focus mode disabled.")
        elif "register" in text:
             # Handles "register me", "register [name]", "register face"
             # If name follows, we might want to capture it? 
             # For now, trigger the interactive one.
             print(">> SYSTEM: Voice registration triggered.")
             speak("Please look at the camera for registration.")
             scene_state.register_trigger = True
        elif "selfie" in text or "snap" in text or "photo" in text:
             print(">> SYSTEM: Taking Selfie...")
             speak("Say cheese!")
             # We rely on main loop to handle capture? Or do it here via a flag?
             # Since 'frame' is in main loop scope, we can't save it directly here easily 
             # unless we pass it or set a flag.
             # Setting a flag is cleaner.
             scene_state.selfie_trigger = True
        else:
            # Query?
            response = query_handler.handle_query(text, scene_state)
            if response:
                print(f"\n>> SYSTEM: {response}\n")
                speak(response)
    
    # Initialize Voice (might take a sec to calibrate)
    from interface.voice_input import VoiceListener
    try:
        voice_input = VoiceListener(callback_func=on_voice_command)
    except Exception as e:
        print(f"Voice Init Failed (Microphone issue?): {e}")
        voice_input = None

    input_t = threading.Thread(target=input_loop, daemon=True)
    input_t.start()
    
    # Init Dashboard
    from interface import dashboard
    try:
        dashboard.set_scene_state(scene_state)
        dash_t = threading.Thread(target=dashboard.start_server, daemon=True)
        dash_t.start()
    except Exception as e:
        print(f"Dashboard init failed: {e}")
    
    print("Starting Vision System... Press 'q' in the window or type 'quit' to stop.")
    print("To register your face, type 'register me' in the console or look at camera.")
    print("Dashboard available at: http://localhost:5000")

    last_tts_time = 0
    frame_count = 0
    
    # Persistent variables for frame skipping
    detections = []
    pose_data = None
    
    while running:
        frame = cam.get_frame()
        if frame is None:
            time.sleep(0.01) # Waiting for first frame or next frame
            continue
            
        # Resize if too large (e.g. from high-res mobile stream)
        # Keeps processing fast and fits on screen
        h_raw, w_raw = frame.shape[:2]
        max_height = 720
        if h_raw > max_height:
            scale = max_height / h_raw
            new_w = int(w_raw * scale)
            frame = cv2.resize(frame, (new_w, max_height))
            
        clean_frame = frame.copy()
            
        timestamp = time.time()
        frame_count += 1
        
        # Perception
        # Run inference every 3rd frame to reduce latency
        if frame_count % 3 == 0:
            detections = detector.detect(frame)
            pose_data = pose_estimator.estimate(frame)
        
        # Face Recognition
        # Only run every 5th frame to save CPU/GPU
        if frame_count % 5 == 0:
            # Check for person detection to get bbox
            person_bbox = None
            # Default to YOLO box for person
            for det in detections:
                if det['label'] == 'person':
                     person_bbox = det['bbox']
                     break
            
            # If YOLO found a person, refine face crop?
            # YOLO box is whole body ideally. We need FACE.
            # We don't have a face detector except FaceRecognizer internal?
            # Actually facenet-pytorch needs a cropped face.
            # Using whole body crop will FAIL.
            
            # We should use a Face Detector.
            # Wait, FaceRecognizer module I wrote doesn't have a detector!
            # It blindly checks the bbox passed.
            # If I pass the whole person body, InceptionResnet won't work well.
            
            # I need to find the face.
            # Pose keypoints! NOSE, EYES.
            if pose_data and 'keypoints' in pose_data:
                kp = pose_data['keypoints']
                if 'NOSE' in kp and 'LEFT_EAR' in kp and 'RIGHT_EAR' in kp:
                    # Construct rough face box from keypoints
                    nose = kp['NOSE']
                    l_ear = kp['LEFT_EAR']
                    r_ear = kp['RIGHT_EAR']
                    
                    # Center roughly between ears/nose
                    # Width = distance between ears * 2?
                    ear_dist = abs(l_ear[0] - r_ear[0])
                    face_w = int(ear_dist * 2.0)
                    face_h = int(face_w * 1.2)
                    
                    cx = int(nose[0])
                    cy = int(nose[1])
                    
                    x = cx - face_w // 2
                    y = cy - face_h // 2
                    
                    # Recognize
                    name = face_rec.recognize(frame, [x, y, face_w, face_h])
                    if name:
                        scene_state.human['identity'] = name
            
            # Register Command Handle (via scene_state flag or just check global?)
            # I can't check variable in main easily from input thread without event.
            # Check a file? Or just check if user typed command in `input_loop`.
            # Let's add `register_face_trigger` to scene_state.
        
        if getattr(scene_state, 'register_trigger', False):
             # Try to register
             if pose_data and 'keypoints' in pose_data:
                kp = pose_data['keypoints']
                if 'NOSE' in kp:
                     nose = kp['NOSE']
                     # Rough box
                     face_w = 200
                     face_h = 240
                     x = int(nose[0]) - 100
                     y = int(nose[1]) - 100
                     if face_rec.register_face(frame, [x, y, face_w, face_h], name=scene_state.register_name):
                         print(f">> SYSTEM: Face Registered Successfully for {scene_state.register_name}.")
                         speak(f"Face registered. I will remember you, {scene_state.register_name}.")
                         scene_state.register_trigger = False
                     else:
                         print(">> SYSTEM: Failed to register face. Look closer.")
                         
        # State Update
        h, w, _ = frame.shape
        scene_state.update(detections, pose_data, timestamp, frame_width=w, frame_height=h)
        
        # Reasoning
        events = rules_engine.check_rules(scene_state, timestamp)
        for event in events:
            print(f"[EVENT] {event}")
            
            # Text-To-Speech Handling
            # Only speak if it starts with "TTS:"
            if event.startswith("TTS:"):
                # Global cooldown to prevent overlapping talking
                if time.time() - last_tts_time > 5.0:
                    text_to_say = event.replace("TTS:", "").strip()
                    speak(text_to_say)
                    last_tts_time = time.time()
        
        # Visualization (Debug View)
        # Draw BBoxes
        for det in detections:
            x, y, w, h = map(int, det['bbox'])
            label = det['label']
            
            color = (0, 255, 0)
            if label == 'cell phone' and scene_state.focus_mode:
                color = (0, 0, 255) # Red for danger
                
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        # Draw Pose
        if pose_data and 'keypoints' in pose_data:
            kp = pose_data['keypoints']
            for name, (px, py) in kp.items():
                cv2.circle(frame, (int(px), int(py)), 4, (0, 0, 255), -1)
        
        # UI Overlay
        h_state = scene_state.human['pose_state']
        f_mode = "ON" if scene_state.focus_mode else "OFF"
        ident = scene_state.human['identity'] if scene_state.human['identity'] else "Unknown"
        
        cv2.putText(frame, f"Pose: {h_state}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(frame, f"Identity: {ident}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Focus Mode: {f_mode}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255) if scene_state.focus_mode else (200, 200, 200), 2)
        
        # Update Dashboard
        # Optimization: Update less frequently and use smaller frame
        if frame_count % 10 == 0:
            try:
                # Resize for web (bandwidth/cpu saver)
                preview = cv2.resize(frame, (480, 270))
                dashboard.update_frame(preview)
            except Exception: pass
        
        cv2.imshow("Vision System Debug", frame)
        
        # Keyboard Shortcuts
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            scene_state.save_memory() # Save on exit
            running = False
            break
        elif key == ord('f'): # Toggle Focus Mode
            scene_state.focus_mode = not scene_state.focus_mode
            status = "enabled" if scene_state.focus_mode else "disabled"
            print(f">> SYSTEM: Focus Mode {status.upper()}")
            speak(f"Focus mode {status}")
        elif key == ord('s'):
             # Trigger selfie manually
             print(">> SYSTEM: Taking Selfie (Manual)...")
             speak("Smile!")
             scene_state.selfie_trigger = True
            
        elif key == ord('v'): # Toggle Voice Mode
            if voice_input:
                new_state = not voice_input.is_listening_active
                if new_state:
                     voice_input.set_active(True)
                     speak("I am listening.")
                else:
                     voice_input.set_active(False)
                     speak("Voice input stopped.")
        
        # PROCESS SELFIE TRIGGER
        if scene_state.selfie_trigger:
             timestamp_str = time.strftime("%Y%m%d-%H%M%S")
             filename = f"selfie_{timestamp_str}.jpg"
             
             # Draw a flash effect or just save pure frame?
             # User probably wants the raw photo without bounding boxes?
             # The 'frame' variable here has detections drawn on it from Visualization step above?
             # Wait, visualization (lines 338+) happens AFTER this loop cycle?
             # No, visualization code is inside loop.
             # I need to find where visualization is.
             # Visualization happens at lines 330+ (approx).
             # If I save BEFORE visualization, I get clean image.
             # If I save AFTER, I get HUDP/HUD.
             # Usually selfies are clean.
             # But 'frame' is mutable. If I draw on it, it's dirty.
             # Let's save a copy?
             # Wait, I am at the end of loop (Input handling)?
             # Input handling is usually `cv2.waitKey` which is at the END of loop.
             # Visualization is BEFORE `cv2.imshow`.
             
             # If I want clean selfie, I should capture it earlier or use a copy.
             # But I'm inserting code at key handling (end of loop).
             # In this frame, `frame` already has boxes drawn.
             # It's okay. "HUD Selfie" is cool for a robot companion.
             
             cv2.imwrite(filename, clean_frame)
             print(f">> SYSTEM: Saved {filename}")
             speak("Photo taken.")
             scene_state.selfie_trigger = False
            
    cam.release()
    cv2.destroyAllWindows()
    scene_state.save_memory() # Double check save
    print("System Shutdown.")

if __name__ == "__main__":
    main()
