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
from interface.lcd import LCDManager


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
        
        # LCD Face (Hardware or Sim)
        self.lcd = LCDManager()
        self.lcd.start()
        
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
        
        # Touch Sensor (New)
        try:
            from interface.touch.manager import TouchManager
            self.touch_manager = TouchManager()
            self.touch_manager.start()
        except Exception as e:
            print(f"[Touch] Init skipped: {e}")
            self.touch_manager = None
        
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
            
        print(f"[MEMO] Initialized | Pi Mode: {self.perf_monitor.is_raspberry_pi} | GUI Window: {self.show_display}")
        
        if not self.show_display:
            print("[System] Running in headless mode. Controlling via terminal and dashboard.")
        
        if self.lcd and not self.lcd.sim_mode:
            print("[System] Physical LCD Hardware: ACTIVE")
        else:
            print("[System] Physical LCD Hardware: INACTIVE (Sim Mode)")
            
        # Update State with Hardware Info
        self.scene_state.hardware_info['display_connected'] = not self.lcd.sim_mode
        self.scene_state.hardware_info['touch_connected'] = self.touch_manager is not None
        if hasattr(self.lcd, 'driver_name'):
             self.scene_state.hardware_info['lcd_type'] = self.lcd.driver_name
    
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
        
        # Update LCD
        self.lcd.set_focus_mode(enabled)

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
            self.lcd.play("love", loop=False) # Show love when registering
            
        elif action == 'selfie':
            self.scene_state.selfie_trigger = True
            self.lcd.trigger_selfie()
            
        elif action == 'toggle_voice':
            if self.voice_input:
                new_state = not self.voice_input.is_listening_active
                self.voice_input.set_active(new_state)
                status = "ENABLED" if new_state else "DISABLED"
                speak(f"Voice {status}")
                self.lcd.play("listening" if new_state else "silence", loop=False)

        elif action == 'toggle_focus':
            # Toggle Focus Mode (Tap 1)
            new_state = not self.scene_state.focus_mode
            self.event_bus.publish(Event(EventType.FOCUS_MODE_CHANGED, {'enabled': new_state}))
            
        elif action == 'sleep_mode':
            # Sleep Mode (Tap 3)
            print(">> SYSTEM: Manual Sleep Mode Triggered")
            self.scene_state.sleep_request = True
            self.lcd.play("sleep", loop=False)
            speak("Going to sleep. Goodnight.")
    
    def _on_voice_command(self, event: Event):
        """Handle voice commands."""
        # WAKE UP VISION on any voice interaction
        if self.burst_enabled:
            print(">> SYSTEM: Vision WAKE (Trigger)")
            self.trigger_end_time = time.time() + 10.0 

        text = event.data.get('text', '').lower()
        
        # LCD Triggers based on keywords
        if "laugh" in text or "joke" in text or "funny" in text:
            self.lcd.play("laugh", loop=False)
        elif "sleep" in text or "tired" in text:
            self.lcd.play("sleep", loop=False)
        elif "love" in text or "like you" in text:
            self.lcd.play("love", loop=False)
        elif "hate" in text or "bad" in text:
            self.lcd.play("hate", loop=False)
        elif "angry" in text:
             self.lcd.play("angry", loop=False)

        executed, response = self.command_processor.process(
            text, 
            {'scene_state': self.scene_state}
        )
        
        if executed:
            # Command handled (either with response or silently)
            if response:
                print(f">> MEMO: {response}")
                self.lcd.trigger_eureka() # Happy flash
                self.lcd.set_speaking()
                speak(response)
                # Log to dashboard
                from interface.dashboard import add_log
                add_log(response, "ai")
        else:
            # Pass to query handler (uses AI personality for complex questions)
            response = self.query_handler.handle_query(text, self.scene_state, personality=self.personality)
            if response:
                print(f">> MEMO: {response}")
                self.lcd.trigger_eureka()
                self.lcd.set_speaking()
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
                
                # LCD Expression
                # CONFLICT FIX: Do NOT trigger one-shot here. 
                # Let the main loop handle the continuous state (loop=True) in _update_state.
                # self.lcd.trigger_distraction()
                
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
        # 1. Standard Input module (Vosk + Beep Feedback - PREFERRED by User)
        try:
            from interface.voice_input import VoiceListener
            self.voice_input = VoiceListener(
                callback_func=callback,
                on_wake=lambda: self.lcd.set_listening(),
                on_processing=lambda: self.lcd.set_thinking()
            )
            print("[Voice] Standard Input module initialized (Vosk)")
            return
        except Exception as e:
            print(f"[Voice] Standard Init failed: {e}")

        # 2. Try High-Fidelity Pro Engine (Fallback)
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
        except Exception as e:
            print(f"[Voice] Pro Engine skipped: {e}")
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
             run_face = self.frame_count % 25 == 0  # Legacy mode
        
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
        self.scene_state.update(detections, pose_data, identity, timestamp, w, h, face_score=face_score)
        
        # Throttled object logging (Silenced during prompting)
        visible_labels = [d['label'] for d in detections]
        # if not self.is_prompting and self.frame_count % 30 == 0 and visible_labels:
        #     print(f"[Vision] Detecting: {visible_labels}")
        
        # Check for new presence/absence for logging
        # Use PERSISTED identity from scene_state, not the raw one
        
        # --- FOCUS MODE LOGIC ---
        if self.scene_state.focus_mode:
            # Check for distractions (cell phone)
            is_distracted = False
            if 'cell phone' in self.scene_state.objects:
                phone_state = self.scene_state.objects['cell phone']
                # If seen recently (< 2 seconds ago)
                if timestamp - phone_state['last_seen'] < 2.0:
                    is_distracted = True
                    
            if is_distracted:
                # 1. VISUAL STATE: Warning
                # Only switch if not already playing warning
                # (LCD Manager handles deduplication usually, but clear naming helps)
                if timestamp - self.scene_state.last_distraction_alert > 5.0:
                    # New distraction event
                    print(f">> FOCUS: Distraction Detected (Cooldown Reset)")
                    speak("Focus mode! Put that phone away!")
                    self.event_bus.publish(Event(
                        EventType.SYSTEM_ALERT,
                        {'action': 'focus_alert'}
                    ))
                    # Trigger Warning Animation (Looping?)
                    # Persist while phone is visible:
                    self.lcd.play("focus_warning", loop=True, fps_ms=100)
                    self.scene_state.last_distraction_alert = timestamp
                    self.scene_state.last_distraction_time = timestamp # Track last seen time for debouncing
                else:
                    # Maintain warning loop
                    self.lcd.play("focus_warning", loop=True, fps_ms=100)
                    self.scene_state.last_distraction_time = timestamp
                    
            elif timestamp - getattr(self.scene_state, 'last_distraction_time', 0) < 2.0:
                 # DEBOUNCE: Keep warning for 2s after phone disappears prevents flickering
                 self.lcd.play("focus_warning", loop=True, fps_ms=100)
            else:
                # 2. VISUAL STATE: Scanning
                # If no distraction, show Scanning eyes
                # Only if not doing something else (like speaking)
                # Ideally, focus_scan should be the "Idle" state when in Focus Mode.
                # But LCD manager 'fallback_to_idle' goes to 'idle_center'.
                # We need to inform LCD Manager that the "Base State" is Focus.
                # For now, explicit call:
                self.lcd.play("focus_scan", loop=True, fps_ms=60)
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
                            name=self.scene_state.register_name,
                            keypoints=kp
                        )
                        
                        if success:
                            name = self.scene_state.register_name
                            print(f">> SYSTEM: Face registered for {name}")
                            speak(f"Face registered. I will remember you, {name}.")
                            self.scene_state.register_trigger = False
                        else:
                            print(">> SYSTEM: Registration failed. Look closer.")
        
        # Selfie trigger
        # Only capture if both Trigger is ON AND we have passed the scheduled time
        # (This allows the animation to play the 'Flash' first)
        if self.scene_state.selfie_trigger:
            current_time = time.time()
            if self.scene_state.selfie_scheduled_time > 0 and current_time < self.scene_state.selfie_scheduled_time:
                # Wait for animation...
                return
                
            clean_frame = frame.copy()
            timestamp_str = time.strftime("%Y%m%d-%H%M%S")
            filename = f"selfie_{timestamp_str}.jpg"
            cv2.imwrite(filename, clean_frame)
            print(f">> SYSTEM: Saved {filename}")
            speak("Great shot! Photo saved.")
            self.scene_state.selfie_trigger = False # FIXED: Restore this line!
            self.scene_state.selfie_scheduled_time = 0.0

    def _process_dashboard_commands(self):
        """Process commands from the dashboard queue."""
        try:
            while not self.scene_state.pending_commands.empty():
                raw_cmd = self.scene_state.pending_commands.get_nowait()
                if not raw_cmd: continue
                
                cmd = str(raw_cmd).strip().lower()
                print(f"[Dashboard] DEBUG: Processing '{cmd}' (Type: {type(cmd)}, Repr: {repr(cmd)})")
                
                cmd = str(raw_cmd).strip().lower()
                print(f"[Dashboard] Processing: '{cmd}'")
                
                # Delegate to Central Handler
                # Pass 'self' (MEMOApp instance) so it can modify state
                if SystemCommandHandler.handle_system_command(self, cmd):
                    continue

                # Fallback: Query Handler
                executed, response = self.command_processor.process(
                    cmd,
                    {'scene_state': self.scene_state}
                )

                # --- Handle System Commands ---
                if response:
                    print(f">> MEMO: {response}")
                    speak(response)
                    
                if cmd == 'focus off':
                    self.scene_state.focus_mode = False
                    print(">> SYSTEM: Focus Mode DISABLED")
                    speak("Chill mode! Scroll away my friend 📱")
                    self.lcd.play("idle_center", loop=True)
                    return
                    
                if cmd == 'quit':
                    print(">> SYSTEM: Remote Shutdown Request")
                    speak("Shutting down. See ya!")
                    self.running = False
                    return
                # Route through command processor
                executed, response = self.command_processor.process(
                    cmd,
                    {'scene_state': self.scene_state}
                )
                
                if response:
                    print(f">> MEMO: {response}")
                    speak(response)
                    
        except Exception as e:
            print(f"[Error] Dashboard processing: {e}")
    
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
            
            # Show Identity on Person Box - ONLY if it matches the tracked Primary Human
            if label == 'person':
                # Check match with scene_state.human
                is_primary_human = False
                if self.scene_state.human['present'] and self.scene_state.human['keypoints']:
                    # Reconstruct bbox from keypoints to compare
                    kp = self.scene_state.human['keypoints']
                    try:
                        xs = [p[0] for p in kp.values()]
                        ys = [p[1] for p in kp.values()]
                        hx1, hy1 = min(xs), min(ys)
                        hx2, hy2 = max(xs), max(ys)
                        
                        # Compare with current detection bbox (x, y, w, h)
                        dx1, dy1 = x, y
                        dx2, dy2 = x+w, y+h
                        
                        # IOU Calc
                        ix1 = max(hx1, dx1)
                        iy1 = max(hy1, dy1)
                        ix2 = min(hx2, dx2)
                        iy2 = min(hy2, dy2)
                        
                        if ix2 > ix1 and iy2 > iy1:
                            inter = (ix2-ix1)*(iy2-iy1)
                            union = ((hx2-hx1)*(hy2-hy1)) + (w*h) - inter
                            if (inter / union) > 0.3: # Loose overlap threshold
                                is_primary_human = True
                    except:
                        pass

                if is_primary_human:
                    identity = self.scene_state.human.get('identity')
                    face_score = self.scene_state.human.get('face_score', 0.0)
                    
                    if identity:
                        label = f"{identity} ({face_score:.2f})"
                        color = (0, 255, 255) # Yellow for recognized
                    else:
                        label = f"Person (Primary)"
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
                
                cmd_lower = user_input.strip().lower()
                # DEBUG: Trace input source
                if cmd_lower:
                     print(f"DEBUG: Console Input: '{cmd_lower}' (Bytes: {[ord(c) for c in cmd_lower]})")
                
                # STRICT quit matching to avoid false positives (e.g. "stop scan")
                if cmd_lower in ['quit', 'exit', 'shutdown', 'q']:
                    print(">> SYSTEM: Quit command received")
                    self.running = False
                    break
                
                # Process other commands
                elif cmd_lower == 'voice on' and self.voice_input:
                    self.voice_input.set_active(True)
                    self.scene_state.voice_active = True # Sync state
                    print(">> SYSTEM: Voice input ENABLED")
                    speak_now("Voice input enabled. I'm listening.")
                    self.lcd.play("listening", loop=True) # Feedback
                    
                elif cmd_lower == 'voice off' and self.voice_input:
                    self.voice_input.set_active(False)
                    self.scene_state.voice_active = False # Sync state
                    print(">> SYSTEM: Voice input DISABLED")
                    speak_now("Voice input stopped.")
                    self.lcd.play("silence", loop=True)   # Show Mute Icon
                
                elif cmd_lower == 'idle':
                    print(">> SYSTEM: Entering IDLE MODE (Clock)")
                    # Idle Mode Sequence
                    self.vision_active = False
                    self.voice_input.set_active(False)
                    self.scene_state.voice_active = False
                    
                    self.lcd.set_clock_mode(True)
                    speak("Entering Idle Mode. Time to chill.")
                    
                elif cmd_lower == 'wake' or cmd_lower == 'wakeup':
                     print(">> SYSTEM: Waking up from Sleep!")
                     # Wake Sequence
                     self.vision_active = True
                     self.voice_input.set_active(True)
                     self.scene_state.voice_active = True
                     
                     self.lcd.set_clock_mode(False) # Auto plays idle
                     speak("Hey yo! I'm back!")
                
                elif cmd_lower == 'focus on':
                    self.scene_state.focus_mode = True
                    print(">> SYSTEM: Focus Mode ENABLED")
                    speak("Entering the zone! No distractions allowed!")
                    self.lcd.play("focus_scan", loop=True, fps_ms=60) # Start scanning immediately
                elif cmd_lower == 'focus off':
                    self.scene_state.focus_mode = False
                    print(">> SYSTEM: Focus Mode DISABLED")
                    speak("Chill mode! Scroll away my friend 📱")
                    self.lcd.play("idle_center", loop=True) # Reset to normal eyes
                    
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

                elif cmd_lower == 's' or cmd_lower == 'selfie' or cmd_lower == 'cheese':
                    print("\n>> SYSTEM: Triggering Selfie Mode 📸")
                    
                    # Schedule capture for 3.0s (50 frames * ~60ms)
                    self.scene_state.selfie_trigger = True
                    self.scene_state.selfie_scheduled_time = time.time() + 3.0
                    
                    self.event_bus.publish(Event(
                        EventType.SYSTEM_ALERT,
                        {'action': 'take_selfie'} # Just for logging/other listeners
                    ))
                    # Trigger LCD immediately
                    self.lcd.trigger_selfie()
                    
                else:
                    # Process as command
                    # Process as command
                    executed, response = self.command_processor.process(
                        user_input,
                        {'scene_state': self.scene_state}
                    )
                    
                    if executed:
                         if response:
                            print(f">> MEMO: {response}")
                            speak(response)
                    else:
                        # Pass to query handler (Pass personality for LLM fallback)
                        self.lcd.set_thinking()
                        response = self.query_handler.handle_query(user_input, self.scene_state, personality=self.personality)
                        if response:
                            print(f">> MEMO: {response}")
                            
                            # Simple Emotion Analysis
                            text_lower = response.lower()
                            anim_played = False
                            
                            if any(w in text_lower for w in ['love', 'heart', '❤️', 'favorite', 'cute']):
                                self.lcd.play("love", fps_ms=80)
                                anim_played = True
                            elif any(w in text_lower for w in ['happy', 'haha', 'lol', 'good', 'awesome', 'great', 'cool', 'joke']):
                                self.lcd.play("happy", fps_ms=60)
                                anim_played = True
                            elif any(w in text_lower for w in ['sad', 'sorry', 'bad', 'unfortunately', 'oh no']):
                                self.lcd.play("sad", fps_ms=100)
                                anim_played = True
                            elif any(w in text_lower for w in ['wow', 'whoa', 'omg', 'surprise', 'really?']):
                                self.lcd.play("surprised", fps_ms=50)
                                anim_played = True
                            elif any(w in text_lower for w in ['what?', 'huh', 'confused', 'weird']):
                                self.lcd.play("confused", fps_ms=100)
                                anim_played = True
                                
                            if not anim_played:
                                self.lcd.set_speaking()
                                
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
            # Safety: Ignore very short noise like 'a', 'was'
            if len(text) < 4:
                print(f"[Voice] Ignored too short: '{text}'")
                return
                
            # V5.6 Fix: Offload to prevent blocking audio thread
            threading.Thread(target=lambda: self.event_bus.publish(Event(
                EventType.VOICE_COMMAND,
                {'text': text}
            )), daemon=True).start()
        
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
            now = time.time() # START OF FRAME TIMER
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
            
            # handle dashboard commands 
            self._process_dashboard_commands()
            
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
                
                # Render LCD Simulation (if active)
                lcd_frame = self.lcd.get_current_frame()
                if lcd_frame:
                    import numpy as np
                    # Convert PIL to CV2
                    open_cv_image = np.array(lcd_frame) 
                    open_cv_image = open_cv_image[:, :, ::-1].copy() # RGB to BGR
                    display_img = cv2.resize(open_cv_image, (256, 256), interpolation=cv2.INTER_NEAREST)
                    cv2.imshow("MEMO Face", display_img)
                
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
                    self.scene_state.selfie_scheduled_time = time.time() + 3.0
                    self.lcd.trigger_selfie()
                elif key == ord('v') and self.voice_input:
                    new_state = not self.voice_input.is_listening_active
                    self.voice_input.set_active(new_state)
                    status = "ENABLED" if new_state else "DISABLED"
                    speak(f"Voice {status}")
            else:
                # Still check if we should quit via console or other events
                if not self.vision_active:
                     time.sleep(0.05) # Sleep more if vision sleeping
            
            # --- CAP FPS to 30 ---
            elapsed = time.time() - now
            target_fps = 30
            time_per_frame = 1.0 / target_fps
            if elapsed < time_per_frame:
                time.sleep(time_per_frame - elapsed)
        
        # Cleanup
        print("\n[MEMO] Shutting down...")
        self.scene_state.save_memory()
        cam.release()
        if self.show_display:
            cv2.destroyAllWindows()
        stop_tts()
        self.lcd.stop()
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
