import time
import threading
import os
import cv2
import numpy as np
import math
from pathlib import Path
from PIL import Image
from typing import Dict, List, Optional
import random

# Initial safe imports
try:
    from .driver import LCD_ST7735
    HARDWARE_AVAILABLE = True
except ImportError as e:
    print(f"[LCD] ⚠️ Hardware Driver Missing: {e}")
    if "lgpio" in str(e):
        print("[LCD] Hint: Run 'sudo apt install python3-lgpio' (Pi 5)")
    print("[LCD] Ensuring Simulation Mode.")
    HARDWARE_AVAILABLE = False
except Exception as e:
    print(f"[LCD] Driver Critical Error: {e}")
    HARDWARE_AVAILABLE = False

class LCDManager:
    def __init__(self, assets_path=None, rotation=90):
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # Paths
        if assets_path:
            self.assets_dir = Path(assets_path)
        else:
            self.assets_dir = Path(__file__).parent / "assets"
            
        # Hardware / Sim
        self.lcd = None
        self.sim_mode = True
        
        # Try Hardware
        if HARDWARE_AVAILABLE:
            try:
                self.lcd = LCD_ST7735(rotation=rotation)
                self.sim_mode = False
                print("[LCD] Hardware Initialized.")
            except Exception as e:
                print(f"[LCD] Hardware Init Failed: {e}")
                self.sim_mode = True
        
        if self.sim_mode:
            print("[LCD] Running in Simulation Mode (OpenCV Window).")

        # Animation State
        self.anims: Dict[str, List[Image.Image]] = {}
        self.current_frames = []
        self.current_anim_name = ""
        self.frame_idx = 0
        self.fps_ms = 100
        self.loop = True
        self.fallback_to_idle = True
        self.idle_variant = "center"
        self.mode = "IDLE" # IDLE, ANIMATING
        self.mode = "IDLE" # IDLE, ANIMATING
        self.last_idle_move = time.time()
        self.last_frame_sim = None # Buffer for main thread rendering
        self.paused = False # Fix: Initialize paused state
        
        # Preload Assets
        self._load_assets()

    def _load_assets(self):
        """Load minimal set of frames to memory."""
        print(f"[LCD] Loading assets from {self.assets_dir}...")
        
        target_size = (128, 128)
        
        if not self.assets_dir.exists():
            print(f"[LCD] Warning: Assets dir {self.assets_dir} missing!")
            return

        for folder in self.assets_dir.iterdir():
            if folder.is_dir():
                frames = []
                # robust loading
                files = sorted(list(folder.glob("*.png")) + list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")))
                # Filter out temp files
                files = [f for f in files if not f.name.startswith('.')]
                
                for fp in files:
                    try:
                        img = Image.open(fp).convert("RGB")
                        if img.size != target_size:
                            img = img.resize(target_size, Image.Resampling.LANCZOS)
                        frames.append(img)
                    except Exception:
                        pass
                if frames:
                    # Normalize to lowercase for robust lookup
                    key = folder.name.lower()
                    self.anims[key] = frames
                    print(f"  - Loaded {key} ({len(frames)} frames)")
        
        # Set default
        self.current_frames = self.anims.get("idle_center", [])

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[LCD] Manager Started.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.lcd:
            self.lcd.close()

    def play(self, name: str, loop=False, fps_ms=100, fallback_to_idle=True):
        """Thread-safe request to play animation."""
        with self.lock:
            # --- Aliasing / Fallback Logic ---
            # If the requested name isn't found, try known aliases
            original_name = name
            if name not in self.anims:
                aliases = {
                    "focus_warning": ["distraction", "warn", "angry"],
                    "focus_scan": ["focus_police", "scan"],
                    "happy": ["laugh", "wink"],
                    "love": ["wink", "happy"],
                    "distraction": ["focus_warning", "warn"], # Reverse alias just in case
                }
                
                found_alias = False
                if original_name in aliases:
                    for alias in aliases[original_name]:
                        if alias in self.anims:
                            print(f"[LCD] '{original_name}' not found. Using alias '{alias}'")
                            name = alias
                            found_alias = True
                            break
                            
                if not found_alias:
                    print(f"[LCD] ⚠️ Animation '{original_name}' not found! Available: {list(self.anims.keys())}")
                    return 
            
            # ---------------------------------

            if name not in self.anims:
                print(f"[LCD] ⚠️ Animation '{name}' not found! (Double Check)")
                return 
            
            # Optimization: If already playing this LOOPING animation, don't reset
            if loop and self.mode == "ANIMATING" and self.current_anim_name == name:
                return
            
            # Debug print only when actually switching
            if self.current_anim_name != name:
                print(f"[LCD] >> Switching to '{name}' (loop={loop}, fps={fps_ms})")

            self.current_frames = self.anims[name]
            self.current_anim_name = name
            self.frame_idx = 0
            self.fps_ms = fps_ms
            self.loop = loop
            self.fallback_to_idle = fallback_to_idle
            self.mode = "ANIMATING" if not loop else "IDLE" # Wait, if loop is True, mode should be animating?
            # Actually logic in run_loop line 210 resets mode to IDLE only if fallback triggers
            # But line 125 says: self.mode = "ANIMATING" if not loop else "IDLE" ??
            # If loop=True, we WANT mode=ANIMATING so it keeps playing. 
            # If mode=IDLE, run_loop line 223 executes idle logic random moves. 
            # So for Loop=True, mode must be ANIMATING?
            # Let's fix that too.
            self.mode = "ANIMATING"
            
            if "idle" in name:
                # If we explicitly play an idle anim, maybe allow idle logic?
                self.idle_variant = name.replace("idle_", "")
                self.last_idle_move = time.time()
                if loop: self.mode = "IDLE" # Restore original behavior for idle anims

    # --- High Level Behaviors ---
    
    def set_listening(self):
        """Eyes wide, attentive, pulsating."""
        self.play("listening", loop=True, fps_ms=80)

    def set_thinking(self):
        """Eyes looking around / searching."""
        self.play("thinking", loop=True, fps_ms=100)

    def set_speaking(self):
        """Default to idle center for now (or mouth if avail)."""
        self.play("idle_center", loop=True, fps_ms=150)

    def trigger_flash(self, post_flash_anim="idle_center"):
        """Camera flash effect (White -> Fade). High priority."""
        self.play("flash", loop=False, fps_ms=30, fallback_to_idle=True)
        # Note: The fallback will go to the previous idle variant. 
        # If we want to force something after flash, we'd need a queue or callback.

    def trigger_eureka(self):
        """Happy flash before speaking."""
        self.play("wink", loop=False, fps_ms=60, fallback_to_idle=True)

    # --- New Interactive Expressions ---
    
    def set_focus_mode(self, active: bool):
        """Serious mode for productivity."""
        if active:
            # Use scan animation for active monitoring
            self.play("focus_scan", loop=True, fps_ms=100)
        else:
            self.play("idle_center", loop=True, fps_ms=100)

    def trigger_distraction(self):
        """Angry 'No Phone' warning."""
        # Play distraction anim (focus_warning)
        # Note: Caller usually ensures we return to focus_scan via set_focus_mode check
        self.play("focus_warning", loop=False, fps_ms=60, fallback_to_idle=False) 
        # Hack: After non-loop, it might drift. 
        # But main loop logic handles state.
        
    def trigger_selfie(self):
        """Camera shutter and flash."""
        self.play("selfie_cam", loop=False, fps_ms=50, fallback_to_idle=True)

    def get_current_frame(self):
        """Get the latest frame for main thread rendering (Sim Mode)."""
        with self.lock:
            if hasattr(self, 'last_frame_sim') and self.last_frame_sim:
                return self.last_frame_sim
        return None

    def _run_loop(self):
        while self.running:
            start_time = time.time()
            
            # 1. Get current frame
            frame_img = None
            with self.lock:
                # 1. Update Animation State
                if not self.paused:
                    if self.current_frames:
                        # Update index based on FPS
                        elapsed = (time.time() - start_time) * 1000
                        if elapsed > self.fps_ms:
                            self.frame_idx += 1
                            start_time = time.time()
                        
                        # Wrap or Stop
                        if self.frame_idx >= len(self.current_frames):
                            if self.loop:
                                self.frame_idx = 0
                            else:
                                self.frame_idx = len(self.current_frames) - 1
                                # Check fallback
                                if self.fallback_to_idle:
                                    self.mode = "IDLE"
                                else:
                                    # Hold last frame
                                    frame_img = self.current_frames[-1]
                        
                        # Set frame if not holding (and not wrapped yet if just reset)
                        if self.frame_idx < len(self.current_frames):
                            frame_img = self.current_frames[self.frame_idx]

            # 2. Render Hardware (Sim handled externally)
            # If CLOCK mode, override frame_img with dynamic clock
            if self.mode == "CLOCK":
                from datetime import datetime
                from PIL import ImageDraw, ImageFont
                
                # Create base image (Cyan on Black)
                frame_img = Image.new("RGB", (128, 128), (0, 0, 0))
                draw = ImageDraw.Draw(frame_img)
                
                # Time
                try:
                    # Time
                    now = datetime.now()
                    time_str = now.strftime("%I:%M")
                    ampm = now.strftime("%p")
                    
                    # Draw Time (Large)
                    try:
                        # Try loading a bolder font if possible, else default
                        font = ImageFont.truetype("arial.ttf", 36)
                    except:
                        font = ImageFont.load_default()

                    # Draw text (Handle old Pillow that crashes on size argument)
                    # We manually scale or just accept default size if load_default used
                    draw.text((20, 45), time_str, fill=(0, 255, 255), font=font)
                    draw.text((90, 60), ampm, fill=(0, 200, 200), font=font)
                    
                    # Draw Zzz Icon (Pulse)
                    pulse = abs(math.sin(time.time() * 2)) 
                    z_color = (int(0 + 100*pulse), int(255*pulse), int(255*pulse))
                    draw.text((55, 90), "zZZ", fill=z_color, font=font)
                except Exception as e:
                    print(f"[LCD] Clock Error: {e}")
                
            if frame_img:
                self.last_frame_sim = frame_img # Store for main thread
                if self.lcd:
                    self.lcd.display_image(frame_img)

            # 3. Idle Logic (Look around)
            with self.lock:
                if self.mode == "IDLE":
                    if time.time() - self.last_idle_move > 6.0:
                        # Random drift logic (Simplified for new assets)
                        # Just ensure we have a valid idle animation
                        pass
                        
            # 4. FPS Sleep
            elapsed = (time.time() - start_time) * 1000
            wait_ms = max(10, self.fps_ms - elapsed)
            time.sleep(wait_ms / 1000.0)
            
    def set_clock_mode(self, active: bool):
        with self.lock:
            if active:
                self.mode = "CLOCK"
                self.fps_ms = 1000 # Update every second
            else:
                self.mode = "ANIMATING"
                self.play("idle_center", loop=True)
