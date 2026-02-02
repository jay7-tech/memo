"""
MEMO - Optimized Main Application
==================================
VERSION: 1.2.0 (Headless Fix applied)
High-performance desktop companion with adaptive processing.

Features:
    - Event-driven architecture
    - Adaptive frame skipping based on CPU load
    - Unified perception pipeline
    - Non-blocking TTS
    - Resource-aware processing
    
Usage:
    python main_optimized.py [camera_source] [rotation]
    
    Examples:
        python main_optimized.py              # Default webcam
        python main_optimized.py 1            # Secondary camera
        python main_optimized.py 0 90         # Rotated 90 degrees
        python main_optimized.py http://...   # IP camera stream
"""

import os
from dotenv import load_dotenv
load_dotenv() # Load variables from .env

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import cv2
import threading
import time
import sys
import json
from typing import Optional, Dict, Any

# Core imports
from core import (
    EventBus, EventType, Event,
    PerformanceMonitor, PerceptionPipeline,
    CommandProcessor, get_event_bus, get_perf_monitor,
    AIPersonality, init_personality, get_personality
)

# Component imports
from camera_input import CameraSource
from state import SceneState
from reasoning import RulesEngine

from interface import QueryHandler
from interface.tts_engine import init_tts, speak, speak_now, stop_tts


class MEMOApp:
    """
    Main MEMO Application Controller.
    
    Orchestrates all modules with optimized processing flow.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize MEMO with configuration."""
        self.config = self._load_config(config_path)
        self.running = True
        
        # Core systems
        self.event_bus = get_event_bus()
        self.perf_monitor = get_perf_monitor()
        
        # State
        self.scene_state = SceneState()
        
        # Processing
        self.perception = PerceptionPipeline(self.config.get('perception', {}))
        self.command_processor = CommandProcessor(self.event_bus)
        self.command_processor.on_quit = self._handle_quit  # Wire up quit callback
        self.query_handler = QueryHandler()
        
        # AI Personality
        ai_config = self.config.get('ai', {})
        if not ai_config.get('gemini_api_key'):
            ai_config['gemini_api_key'] = os.environ.get('GEMINI_API_KEY')
        self.personality = init_personality(ai_config)
        
        # Rules engine with personality for dynamic responses
        self.rules_engine = RulesEngine(personality=self.personality)
        
        # Voice
        self.voice_input = None
        
        # Dashboard
        self.dashboard = self.config.get('enable_dashboard', True)
        self.dashboard_thread = None
        
        # Register event handlers (CRITICAL: Required for commands to work!)
        self._setup_event_handlers()
        
        # Terminal Input Thread
        self.terminal_thread = threading.Thread(target=self._terminal_input_loop, daemon=True)
        self.terminal_thread.start()
        
        # Stats
        self.frame_count = 0
        
        # Burst Mode State (Pi 5 Optimization)
        p_cfg = self.config.get('perception', {})
        self.burst_enabled = p_cfg.get('burst_mode', False)
        self.burst_interval = p_cfg.get('burst_interval', 30.0)
        self.burst_duration = p_cfg.get('burst_duration', 2.0)
        self.startup_end_time = time.time() + p_cfg.get('startup_duration', 10.0)
        self.last_burst_time = time.time()
        self.trigger_end_time = self.startup_end_time # Start awake
        self.last_tts_time = 0
        self.verbose_logging = False
        self.is_prompting = False # Flag to silence logs during user input
        self.is_prompting = False # Flag to silence logs during user input
        self.vision_active = True # Track vision state for power management
        self.forced_sleep = False # Manual sleep override flag
        
        # Display settings
        sys_cfg = self.config.get('system', {})
        force_headless = sys_cfg.get('headless_mode', False)
        
        # Determine display mode:
        # 1. Defaults to False if Pi
        # 2. Defaults to True if PC
        # 3. Overridden by config 'headless_mode'
        # 4. Overridden by CLI args
        if force_headless:
            self.show_display = False
        else:
            self.show_display = not self.perf_monitor.is_raspberry_pi
        
        # Check command line for headless override
        if "--headless" in sys.argv:
            self.show_display = False
        elif "--show" in sys.argv:
            self.show_display = True
            
        print(f"[MEMO] Initialized | Pi Mode: {self.perf_monitor.is_raspberry_pi} | Display: {self.show_display}")
        
        if not self.show_display:
            print("[System] Running in headless mode. Controlling via terminal and dashboard.")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Using defaults: {e}")
            return {}
    
    def _setup_event_handlers(self):
        """Register event bus handlers."""
        self.event_bus.subscribe(EventType.FOCUS_MODE_CHANGED, self._on_focus_change)
        self.event_bus.subscribe(EventType.SYSTEM_ALERT, self._on_system_alert)
        self.event_bus.subscribe(EventType.VOICE_COMMAND, self._on_voice_command)
        self.event_bus.subscribe(EventType.DISTRACTION_DETECTED, self._on_distraction)
    
    def _on_focus_change(self, event: Event):
        """Handle focus mode changes."""
        enabled = event.data.get('enabled', False)
        self.scene_state.focus_mode = enabled
        status = "enabled" if enabled else "disabled"
        print(f">> SYSTEM: Focus Mode {status.upper()}")
        # Use AI personality for varied response
        if enabled:
            speak(self.personality.focus_on())
        else:
            speak(self.personality.focus_off())
    
    def _on_system_alert(self, event: Event):
        """Handle system alerts."""
        action = event.data.get('action')
        
        if action == 'register_face':
            name = event.data.get('name', 'User')
            self.scene_state.register_name = name
            self.scene_state.register_trigger = True
            
        elif action == 'selfie':
            self.scene_state.selfie_trigger = True
            
        elif action == 'toggle_voice':
            if self.voice_input:
                new_state = not self.voice_input.is_listening_active
                self.voice_input.set_active(new_state)
                status = "ENABLED" if new_state else "DISABLED"
                speak(f"Voice {status}")
    
    def _on_voice_command(self, event: Event):
        """Handle voice commands."""
        # WAKE UP VISION on any voice interaction
        if self.burst_enabled:
            print(">> SYSTEM: Vision WAKE (Trigger)")
            self.trigger_end_time = time.time() + 10.0 

        text = event.data.get('text', '')
        response = self.command_processor.process(
            text, 
            {'scene_state': self.scene_state}
        )
        
        if response:
            print(f">> MEMO: {response}")
            speak(response)
            # Log to dashboard
            from interface.dashboard import add_log
            add_log(response, "ai")
        else:
            # Pass to query handler (uses AI personality for complex questions)
            response = self.query_handler.handle_query(text, self.scene_state, personality=self.personality)
            if response:
                print(f">> MEMO: {response}")
                speak(response)
                # Log to dashboard
                from interface.dashboard import add_log
                add_log(response, "ai")
    
    def _on_distraction(self, event: Event):
        """Handle distraction detection."""
        if self.scene_state.focus_mode:
            obj = event.data.get('object', 'distraction')
            if time.time() - self.last_tts_time > 5.0:
                # Log to dashboard
                from interface.dashboard import add_log
                add_log(f"DISTRACTION ALERT: {obj}", "alert")
                
                # Use AI for witty distraction alert
                if 'phone' in obj.lower():
                    speak(self.personality.phone_alert())
                else:
                    speak(self.personality.generate(f"Distraction alert: {obj}", self.scene_state, "quick"))
                self.last_tts_time = time.time()
    
    def _handle_quit(self):
        """Handle quit command from voice or text."""
        print(">> SYSTEM: Quit command received")
        speak_now(self.personality.goodbye())
        self.running = False
    
    def _init_voice(self, callback):
        """Initialize voice input module (Pro > Standard)."""
        # 1. Try High-Fidelity Pro Engine
        try:
            from interface.speech_pro import HighFidelityTranscriber
            print("[Voice] Loading High-Fidelity Engine...")
            self.voice_input = HighFidelityTranscriber(
                callback_func=callback,
                model_size="tiny.en",
                compute_type="int8" # Light on Pi
            )
            self.voice_input.start()
            print("[Voice] ✓ Pro Engine initialized")
            return
        except Exception as e:
            print(f"[Voice] Pro Engine skipped: {e}")

        # 2. Fallback to Standard
        try:
            from interface.voice_input import VoiceListener
            self.voice_input = VoiceListener(callback_func=callback)
            print("[Voice] Standard Input module initialized")
        except Exception as e:
            print(f"[Voice] Init failed: {e}")
            self.voice_input = None
    
    def _init_dashboard(self):
        """Initialize web dashboard."""
        try:
            from interface import dashboard
            dashboard.set_scene_state(self.scene_state)
            dash_thread = threading.Thread(target=dashboard.start_server, daemon=True)
            dash_thread.start()
            self.dashboard = dashboard
            print("[Dashboard] Started at http://localhost:5000")
        except Exception as e:
            print(f"[Dashboard] Init failed: {e}")
    
    def _process_frame(self, frame) -> Optional[Dict[str, Any]]:
        """
        Process a single frame through the perception pipeline.
        
        Uses adaptive processing based on system load.
        """
        self.frame_count += 1
        self.perf_monitor.record_frame()
        
        # --- GLOBAL SLEEP/WAKE LOGIC ---
        now = time.time()
        
        # 0. Check Manual Override Commands
        if self.scene_state.wake_request:
            self.forced_sleep = False # Wake up!
            self.trigger_end_time = now + 30.0
            self.scene_state.wake_request = False
            print(">> SYSTEM: Vision WAKE (Manual)")

        if getattr(self.scene_state, 'sleep_request', False):
            self.forced_sleep = True # Force sleep
            self.trigger_end_time = 0 
            self.startup_end_time = 0
            self.scene_state.sleep_request = False
            print(">> SYSTEM: Vision SLEEP (Manual)")
            
        # 1. Determine Target State
        should_be_awake = False
        
        if self.scene_state.focus_mode:
            should_be_awake = True
            self.forced_sleep = False # Focus overrides sleep
            
        elif self.burst_enabled:
            # Burst Mode Logic
            if now < self.startup_end_time: should_be_awake = True
            elif now < self.trigger_end_time: should_be_awake = True
            elif now - self.last_burst_time > self.burst_interval:
                self.last_burst_time = now
                self.trigger_end_time = now + self.burst_duration
                should_be_awake = True
                print(f">> SYSTEM: Vision WAKE (Periodic - {self.burst_duration}s)")
        else:
            # PC Mode (Always On)
            should_be_awake = True
        
        # 2. Apply Forced Sleep Override
        if self.forced_sleep:
            should_be_awake = False
            
        # 3. Apply State
        self.vision_active = should_be_awake
        self.scene_state.vision_active = should_be_awake
        
        if not should_be_awake:
             return {'detections': [], 'pose': None, 'identity': None}
             
         # --- END SLEEP LOGIC ---


        # Determine what to run this frame
        run_detection = not self.perf_monitor.should_skip_frame(self.frame_count)
        run_pose = run_detection
        if self.burst_enabled:
             # In burst mode, we want maximum accuracy when awake
             run_face = run_detection
        else:
             run_face = self.frame_count % 10 == 0  # Legacy mode
        
        # Run perception
        result = self.perception.process(
            frame,
            run_detection=run_detection,
            run_pose=run_pose,
            run_face=run_face
        )
        
        return result
    
    def _update_state(self, frame, perception_result):
        """Update scene state with perception results."""
        timestamp = time.time()
        h, w = frame.shape[:2]
        
        detections = perception_result.get('detections', [])
        pose_data = perception_result.get('pose')
        identity = perception_result.get('identity')
        pose_data = perception_result.get('pose')
        identity = perception_result.get('identity')
        face_score = perception_result.get('face_score', 0.0)
        
        # Sync verbose logging
        self.verbose_logging = self.scene_state.verbose_logging
        
        # Emit debug logs to dashboard if available AND enabled
        if self.dashboard and self.verbose_logging and face_score > 0:
             try:
                 from interface.dashboard import socketio
                 socketio.emit('perception_log', {
                     'time': time.strftime("%H:%M:%S"),
                     'msg': f"Face: {identity or 'None'} (Score: {face_score:.3f})"
                 })
             except:
                 pass

        # Update state (Pass identity for persistence)
        self.scene_state.update(detections, pose_data, identity, timestamp, w, h)
        
        # Throttled object logging (Silenced during prompting)
        visible_labels = [d['label'] for d in detections]
        # if not self.is_prompting and self.frame_count % 30 == 0 and visible_labels:
        #     print(f"[Vision] Detecting: {visible_labels}")
        
        # Check for new presence/absence for logging
        # Use PERSISTED identity from scene_state, not the raw one
        persisted_id = self.scene_state.human.get('identity')
        if persisted_id and identity and identity != persisted_id:
             # Wait, this logic is tricky if identity is None but persisted is set.
             # Just log if we get a new confirmed identity
             pass
             
        # Check rules
        
        # Check rules
        events = self.rules_engine.check_rules(self.scene_state, timestamp)

        for event_text in events:
            if event_text.startswith("TTS:") and time.time() - self.last_tts_time > 5.0:
                text_to_say = event_text.replace("TTS:", "").strip()
                speak(text_to_say)
                self.last_tts_time = time.time()
                # Log to dashboard
                from interface.dashboard import add_log
                add_log(f"Spoke: {text_to_say}", "ai")
            
            # Only print events if verbose logging is enabled
            if self.verbose_logging:
                print(f"[EVENT] {event_text}")
                
        # Check for dashboard commands
        self._check_dashboard_commands()

    def _check_dashboard_commands(self):
        """Process commands sent from the web dashboard."""
        while not self.scene_state.pending_commands.empty():
            try:
                cmd = self.scene_state.pending_commands.get_nowait()
                print(f">> DASHBOARD CMD: {cmd}")
                self.event_bus.publish(Event(
                    EventType.VOICE_COMMAND,
                    {'text': cmd}
                ))
            except:
                break

    
    def _handle_triggers(self, frame):
        """Handle special triggers like selfie and registration."""
        if frame is None:
            return

        # Registration trigger
        if self.scene_state.register_trigger:
            # Create a clean copy if needed
            clean_frame = frame.copy()
            pose_data = self.perception._last_pose
            if pose_data and 'keypoints' in pose_data:
                kp = pose_data['keypoints']
                if 'NOSE' in kp:
                    self.perception._init_face_rec()
                    if self.perception._face_rec:
                        nose = kp['NOSE']
                        x, y = int(nose[0]) - 100, int(nose[1]) - 100
                        
                        success = self.perception._face_rec.register_face(
                            clean_frame, [x, y, 200, 240],
                            name=self.scene_state.register_name
                        )
                        
                        if success:
                            name = self.scene_state.register_name
                            print(f">> SYSTEM: Face registered for {name}")
                            speak(f"Face registered. I will remember you, {name}.")
                            self.scene_state.register_trigger = False
                        else:
                            print(">> SYSTEM: Registration failed. Look closer.")
        
        # Selfie trigger
        if self.scene_state.selfie_trigger:
            clean_frame = frame.copy()
            timestamp_str = time.strftime("%Y%m%d-%H%M%S")
            filename = f"selfie_{timestamp_str}.jpg"
            cv2.imwrite(filename, clean_frame)
            print(f">> SYSTEM: Saved {filename}")
            speak("Great shot! Photo saved.")
            self.scene_state.selfie_trigger = False
    
    def _draw_overlay(self, frame, perception_result):
        """Draw debug overlay on frame."""
        detections = perception_result.get('detections', [])
        pose_data = perception_result.get('pose')
        
        # Draw bounding boxes
        for det in detections:
            x, y, w, h = map(int, det['bbox'])
            label = det['label']
            conf = det['confidence']
            
            color = (0, 255, 0)  # Green
            
            # Show Identity on Person Box
            if label == 'person':
                identity = self.scene_state.human.get('identity')
                if identity:
                    label = f"{identity} ({conf:.2f})"
                    color = (0, 255, 255) # Yellow for recognized
                else:
                    label = f"Person ({conf:.2f})"
            elif label == 'cell phone' and self.scene_state.focus_mode:
                color = (0, 0, 255)  # Red for distraction
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Draw pose keypoints (Only if verbose)
        if self.verbose_logging and pose_data and 'keypoints' in pose_data:
            for name, (px, py) in pose_data['keypoints'].items():
                cv2.circle(frame, (int(px), int(py)), 4, (255, 0, 0), -1)
        
        # Draw status overlay (Only if verbose)
        if self.verbose_logging:
            stats = self.perf_monitor.get_stats()
            identity = self.scene_state.human.get('identity', 'Unknown')
            pose_state = self.scene_state.human.get('pose_state', 'unknown')
            focus = "ON" if self.scene_state.focus_mode else "OFF"
            
            # Status bar
            y_offset = 30
            cv2.putText(frame, f"FPS: {stats['fps']} | CPU: {stats['cpu']}%",
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"Pose: {pose_state}",
                       (10, y_offset + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"Identity: {identity}",
                       (10, y_offset + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            focus_color = (0, 0, 255) if self.scene_state.focus_mode else (150, 150, 150)
            cv2.putText(frame, f"Focus: {focus}",
                       (10, y_offset + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, focus_color, 2)
        
        return frame
    
    def _terminal_input_loop(self):
        """Handle console input in background thread."""
        print("\n=== MEMO Commands ===")
        print("  focus on/off  - Toggle distraction detection (Keeps Vision ON)")
        print("  y / scan      - Wake Vision for 30s")
        print("  stop scan     - Sleep Vision immediately")
        print("  register <name> - Register your face (or type 'r')")
        print("  where is <obj> - Find object location")
        print("  voice on/off  - Toggle voice input")
        print("  logs on/off   - Toggle event logging")
        print("  quit          - Exit")
        print("=====================\n")
        
        while self.running:
            try:
                user_input = input().strip()
                if not user_input:
                    continue
                
                cmd = user_input # Use original case for command processor
                cmd_lower = user_input.lower()
                
                # STRICT quit matching to avoid false positives (e.g. "stop scan")
                if cmd_lower in ['quit', 'exit', 'shutdown', 'q']:
                    print(">> SYSTEM: Quit command received")
                    self.running = False
                    break
                
                # Process other commands
                elif cmd_lower == 'voice on' and self.voice_input:
                    self.voice_input.set_active(True)
                    print(">> SYSTEM: Voice input ENABLED")
                    speak_now("Voice input enabled. I'm listening.")
                    
                elif cmd_lower == 'voice off' and self.voice_input:
                    self.voice_input.set_active(False)
                    print(">> SYSTEM: Voice input DISABLED")
                    speak_now("Voice input stopped.")
                
                elif cmd_lower == 'logs on':
                    self.verbose_logging = True
                    print(">> SYSTEM: Verbose logging ENABLED")
                    
                elif cmd_lower == 'logs off':
                    self.verbose_logging = False
                    print(">> SYSTEM: Verbose logging DISABLED")
                    
                elif cmd_lower in ['y', 'scan', 'look', 'scan on', 'start vision']:
                    if self.burst_enabled:
                         print("\n>> SYSTEM: Vision WAKE (Manual Trigger)")
                         self.trigger_end_time = time.time() + 30.0
                    else:
                         print(">> Burst mode disabled. Vision is always on.")

                elif cmd_lower in ['stop scan', 'stop look', 'stop vision']:
                    if self.burst_enabled:
                        print("\n>> SYSTEM: Vision SLEEP (Manual Stop)")
                        self.trigger_end_time = time.time() # Expires immediately
                    else:
                        print(">> Burst mode disabled. Cannot sleep.")

                elif cmd_lower == 'r' or cmd_lower == 'register':
                    print("\n>> INTERACTIVE REGISTRATION")
                    # Prompt directly in the terminal thread
                    try:
                        self.is_prompting = True
                        name = input(">> Enter Name: ").strip()
                        self.is_prompting = False
                        
                        if name:
                            self.event_bus.publish(Event(
                                EventType.SYSTEM_ALERT,
                                {'action': 'register_face', 'name': name}
                            ))
                            print(f">> SYSTEM: Triggering registration for '{name}'...")
                        else:
                            print(">> Registration cancelled (no name).")
                    except EOFError:
                        break
                    except:
                        pass
                
                else:
                    # Process as command
                    response = self.command_processor.process(
                        user_input,
                        {'scene_state': self.scene_state}
                    )
                    
                    if response:
                        print(f">> MEMO: {response}")
                        speak(response)
                    else:
                        # Pass to query handler (Pass personality for LLM fallback)
                        response = self.query_handler.handle_query(user_input, self.scene_state, personality=self.personality)
                        if response:
                            print(f">> MEMO: {response}")
                            speak(response)
                            # Log to dashboard
                            from interface.dashboard import add_log
                            add_log(response, "ai")
                
            except EOFError:
                self.running = False
                break
            except Exception as e:
                print(f"[Input] Error: {e}")
    
    # Consolidated terminal loop is already running in self.terminal_thread
    # No duplicate needed here.

    def run(self, source=0, rotation=0):
        """
        Main application loop.
        
        Args:
            source: Camera source (int for webcam, str for URL)
            rotation: Frame rotation in degrees (0, 90, 180, 270)
        """
        # Initialize TTS
        init_tts()
        speak(self.personality.startup_message())
        
        # Initialize camera
        try:
            cam = CameraSource(source=source, rotation=rotation)
        except Exception as e:
            print(f"[Camera] Error: {e}")
            return
        
        # Warmup with first frame
        print("[MEMO] Waiting for camera...")
        warmup_frame = None
        for _ in range(30):  # Try for 3 seconds
            warmup_frame = cam.get_frame()
            if warmup_frame is not None:
                break
            time.sleep(0.1)
        
        if warmup_frame is not None:
            # Resize for processing
            h, w = warmup_frame.shape[:2]
            if h > 720:
                scale = 720 / h
                warmup_frame = cv2.resize(warmup_frame, (int(w * scale), 720))
            
            self.perception.warmup(warmup_frame)
        
        # Initialize voice input
        def on_voice(text):
            text = text.replace("hello pc", "").strip()
            self.event_bus.publish(Event(
                EventType.VOICE_COMMAND,
                {'text': text}
            ))
        
        self._init_voice(on_voice)
        
        # Initialize dashboard
        self._init_dashboard()
        
        if not self.running:
            return

        print("\n[MEMO] System ready!")
        print(f"[MEMO] Dashboard: http://localhost:5000")
        print("[MEMO] Press 'q' in window or type 'quit' to exit\n")
        
        # We already said startup_message() at the very beginning of run()
        # No need for a second greeting here.

        
        # Main loop
        while self.running:
            frame = cam.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            # Resize if needed
            h, w = frame.shape[:2]
            if h > 720:
                scale = 720 / h
                frame = cv2.resize(frame, (int(w * scale), 720))
            
            # Process frame
            perception_result = self._process_frame(frame)
            
            # Dynamic Power Management
            if self.vision_active:
                if cam.low_power_mode:
                    cam.set_low_power(False)
            else:
                if not cam.low_power_mode:
                    cam.set_low_power(True)
                # IMPORTANT: Yield CPU when sleeping to prevent 100% Core usage in tight loop!
                time.sleep(0.1)
            
            # Update state
            self._update_state(frame, perception_result)
            
            # Handle triggers (Pass frame directly, it's still clean here)
            self._handle_triggers(frame)
            
            # Draw overlay only if needed (for display or dashboard update)
            should_draw = self.show_display or (self.dashboard and self.frame_count % 5 == 0)
            if should_draw:
                frame = self._draw_overlay(frame, perception_result)
            
            # Update dashboard (throttled)
            if self.dashboard and self.frame_count % 5 == 0:
                try:
                    # Resize to optimized preview size for dashboard
                    preview = cv2.resize(frame, (480, 270))
                    self.dashboard.update_frame(preview)
                except:
                    pass
            
            # Display
            if self.show_display:
                cv2.imshow("MEMO Vision", frame)
                
                # Handle keyboard (Only works if display window has focus)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.running = False
                elif key == ord('f'):
                    new_state = not self.scene_state.focus_mode
                    self.event_bus.publish(Event(
                        EventType.FOCUS_MODE_CHANGED,
                        {'enabled': new_state}
                    ))
                elif key == ord('s'):
                    self.scene_state.selfie_trigger = True
                elif key == ord('v') and self.voice_input:
                    new_state = not self.voice_input.is_listening_active
                    self.voice_input.set_active(new_state)
                    status = "ENABLED" if new_state else "DISABLED"
                    speak(f"Voice {status}")
            else:
                # Still check if we should quit via console or other events
                # Just a tiny sleep to keep CPU sane
                time.sleep(0.01)
        
        # Cleanup
        print("\n[MEMO] Shutting down...")
        self.scene_state.save_memory()
        cam.release()
        if self.show_display:
            cv2.destroyAllWindows()
        stop_tts()
        self.event_bus.stop()
        print("[MEMO] Goodbye!")


def main():
    """Entry point."""
    source = 0
    rotation = 0
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        source = int(arg) if arg.isdigit() else arg
    
    if len(sys.argv) > 2:
        try:
            rotation = int(sys.argv[2])
        except ValueError:
            pass
    
    app = MEMOApp()
    try:
        app.run(source=source, rotation=rotation)
    except KeyboardInterrupt:
        pass  # Clean exit on Ctrl+C
    except Exception as e:
        print(f"\n[MEMO] Error: {e}")
    finally:
        # Force kill any lingering threads (like dashboard/voice)
        try:
            sys.exit(0)
        except SystemExit:
            # Fix terminal echo on Linux/Pi if it got broken
            if os.name != 'nt':
                os.system('stty sane')
            os._exit(0)


if __name__ == "__main__":
    main()
